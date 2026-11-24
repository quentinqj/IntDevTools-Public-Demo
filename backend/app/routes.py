"""API 路由：4 步交付链的真实后端入口"""
import json
import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app import config
from app.core import data_bus, data_loader, eval_base, flow, kb_store, llm_gateway
from app.core import development_level as dev_level
from app.core import review_engine

api_bp = Blueprint('api', __name__)


def _ok(data, message='ok'):
    return jsonify({'code': 0, 'message': message, 'data': data})


def _err(message, status=400):
    return jsonify({'code': 1, 'message': message, 'data': None}), status


def _load_rules():
    with open(config.RULES_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_project_profile():
    """解析 demo-data/project_sc2026/project.md → dict（真实文件读取）"""
    profile = {}
    with open(config.PROJECT_MD, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|', line.strip())
            if not m:
                continue
            k, v = m.group(1).strip(), m.group(2).strip()
            if k and k != '字段' and v:
                profile[k] = v
    return profile


def _find_requirement(req_id):
    for r in data_loader.load_requirements():
        if r['req_id'] == req_id:
            return r
    return None


def _adopted_findings(project_id):
    """从流状态读取已确认采纳的发现（用于评价/沉淀）"""
    confirmations = flow.get_confirmations(project_id)
    draft = flow.get_review_draft(project_id)
    adopted = []
    for f in draft:
        if f['id'] in confirmations and confirmations[f['id']] == 'adopt':
            adopted.append(f)
    return adopted


# ── 基础 ────────────────────────────────────────────────

@api_bp.route('/api/health')
def health():
    return _ok({
        'mode': config.runtime_mode(),
        'llm_configured': config.llm_configured(),
        'llm_model': config.LLM_MODEL if config.llm_configured() else '',
    })


@api_bp.route('/api/project/<int:project_id>')
def project(project_id):
    return _ok({
        'project_id': project_id,
        'profile': _load_project_profile(),
        'product_types': eval_base.load_product_types(),
    })


@api_bp.route('/api/requirements')
def requirements():
    return _ok({'requirements': data_loader.load_requirements()})


@api_bp.route('/api/standards')
def standards():
    return _ok({'standards': data_loader.load_standards()})


@api_bp.route('/api/design-doc/<int:project_id>')
def design_doc(project_id):
    return _ok({'blocks': data_loader.parse_design_doc()})


@api_bp.route('/api/kb')
def kb_list():
    return _ok({'entries': kb_store.list_entries()})


# ── ① 需求导入 → 能力评估 ─────────────────────────────

@api_bp.route('/api/assessment', methods=['POST'])
def assessment():
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')
    req_id = data.get('requirement_id', 'REQ-002')
    difficulty = (data.get('difficulty') or 'medium').strip().lower()

    if not project_id:
        return _err('缺少 project_id')

    req = _find_requirement(req_id)
    if not req:
        return _err(f'未找到需求 {req_id}')

    matched, verification = data_loader.match_standards(req['title'])
    result = dev_level.assess_requirement(project_id, difficulty, matched, verification)
    if not result:
        return _err(f"无效的开发难度，可选值：{', '.join(dev_level.DIFFICULTY_LEVEL_MAP.keys())}")

    # 写入数据总线（development_level，Schema 校验）
    payload = dev_level.build_transit_payload(
        project_id, difficulty, result['level'], reason=result['reason'])
    data_bus.put_transit('development_level', project_id, payload)

    result['requirement'] = req
    result['difficulty_valid'] = True
    return _ok(result)


# ── ② 设计审查 ─────────────────────────────────────────

@api_bp.route('/api/review', methods=['POST'])
def review():
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')
    strictness = data.get('strictness', 'standard')

    if not project_id:
        return _err('缺少 project_id')

    if data_bus.get_transit('development_level', project_id) is None:
        return _err('链路顺序错误：请先完成 ① 需求评估（transit 无 development_level）')

    blocks = data_loader.parse_design_doc()
    rules = _load_rules()
    gw = llm_gateway.get_gateway()
    llm = gw if gw.available() else None

    findings = review_engine.review_doc_by_rules(blocks, rules, strictness=strictness, llm=llm)

    # 附上来源与建议（schema 消费侧字段）
    for f in findings:
        f['category'] = f.get('rule_name', '')
        if not f.get('suggestion'):
            f['suggestion'] = ''
        f['id'] = f"{f['rule_id']}-{f.get('block_id') or 0}"
        f['severity'] = review_engine.normalize_severity(f.get('severity', 'medium'))
        f['confirmed'] = False

    flow.set_review_draft(project_id, findings)
    return _ok({
        'findings': findings,
        'mode': config.runtime_mode(),
        'rules_count': len(rules),
        'blocks_count': len(blocks),
    })


@api_bp.route('/api/review/confirm', methods=['POST'])
def review_confirm():
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')
    confirmations = data.get('confirmations') or {}

    if not project_id:
        return _err('缺少 project_id')

    draft = flow.get_review_draft(project_id)
    if not draft:
        return _err('没有待确认的审查结果，请先执行 ② 设计审查')

    # 仅允许 draft 中存在的 finding id
    valid_ids = {f['id'] for f in draft}
    unknown = set(confirmations.keys()) - valid_ids
    if unknown:
        return _err(f'包含无效的 finding id: {sorted(unknown)}')
    for fid, act in confirmations.items():
        if act not in ('adopt', 'reject'):
            return _err(f'无效的确认动作: {act}（可选 adopt/reject）')

    flow.set_confirmations(project_id, confirmations)

    adopted = _adopted_findings(project_id)
    rejected = [f for f in draft if f['id'] in confirmations and confirmations[f['id']] == 'reject']

    # 构建 review_result（符合 review_result.schema.json）
    from app.core.data_bus import validate_data
    payload = {
        'project_id': project_id,
        'status': 'passed' if not adopted else 'failed',
        'findings': [
            {
                'severity': f['severity'],
                'category': f.get('rule_name', ''),
                'description': f['description'],
                'suggestion': f.get('suggestion', ''),
            }
            for f in adopted
        ],
        'confirmed_by_user': True,
        'reviewed_at': datetime.now(timezone.utc).isoformat(),
    }
    data_bus.put_transit('review_result', project_id, payload)

    return _ok({
        'status': payload['status'],
        'adopted_count': len(adopted),
        'rejected_count': len(rejected),
        'transit': data_bus.get_transit('review_result', project_id),
    })


# ── ③ 评价基准 ─────────────────────────────────────────

@api_bp.route('/api/eval-base', methods=['POST'])
def eval_base_generate():
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')
    product_type_id = data.get('product_type_id', 'controller')
    severity = data.get('severity', '推荐')

    if not project_id:
        return _err('缺少 project_id')
    if severity not in eval_base.SEVERITY_LEVELS:
        return _err(f'无效严重度，可选：{eval_base.SEVERITY_LEVELS}')

    result = data_bus.get_transit('review_result', project_id)
    if result is None:
        return _err('链路顺序错误：请先完成 ② 审查确认（transit 无 review_result）')

    ev = eval_base.generate_evaluation_base(product_type_id, severity=severity)
    if ev is None:
        return _err(f'未知产品大类: {product_type_id}')

    adopted = _adopted_findings(project_id)
    ev = eval_base.enrich_with_review_findings(ev, adopted)

    return _ok({
        'product_type': ev['product_type'],
        'product_name': ev['product_name'],
        'standards': ev['standards'],
        'severity': ev['severity'],
        'categories': ev['categories'],
        'special_items': ev['special_items'],
        'total_items': sum(len(c['selected_items']) for c in ev['categories']) + len(ev['special_items']),
    })


@api_bp.route('/api/eval-base/confirm', methods=['POST'])
def eval_base_confirm():
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')
    product_type_id = data.get('product_type_id', 'controller')

    if not project_id:
        return _err('缺少 project_id')

    adopted = _adopted_findings(project_id)
    ev = eval_base.generate_evaluation_base(product_type_id, severity='推荐')
    if ev is None:
        return _err(f'未知产品大类: {product_type_id}')
    ev = eval_base.enrich_with_review_findings(ev, adopted)

    manifest = eval_base.to_test_manifest(project_id, product_type_id, ev)
    data_bus.put_transit('test_manifest', project_id, manifest)

    return _ok({
        'manifest_items': len(manifest['items']),
        'transit': data_bus.get_transit('test_manifest', project_id),
    })


# ── ④ 知识沉淀 ─────────────────────────────────────────

@api_bp.route('/api/kb/contribute', methods=['POST'])
def kb_contribute():
    data = request.get_json(silent=True) or {}
    project_id = data.get('project_id')

    if not project_id:
        return _err('缺少 project_id')

    if data_bus.get_transit('test_manifest', project_id) is None:
        return _err('链路顺序错误：请先完成 ③ 评价确认（transit 无 test_manifest）')

    adopted = _adopted_findings(project_id)
    profile = _load_project_profile()
    project_name = profile.get('项目名称', '某传感器控制器开发')

    entry = kb_store.distill_contribution(project_name, adopted)
    if entry is None:
        return _err('没有可沉淀的已采纳发现（需要 high/medium 且 adopt 的发现）')

    saved = kb_store.add_entry(entry)
    return _ok({'entry': saved, 'entries_count': len(kb_store.list_entries())})


# ── 数据总线（透明访问） ───────────────────────────────

@api_bp.route('/api/transit/<type_name>/<int:project_id>', methods=['GET', 'PUT', 'POST'])
def transit(type_name, project_id):
    try:
        if request.method in ('PUT', 'POST'):
            body = request.get_json(silent=True) or {}
            result = data_bus.put_transit(type_name, project_id, body)
            return _ok(result, message='写入成功')
        result = data_bus.get_transit(type_name, project_id)
        if result is None:
            return _err('未找到 transit 数据', status=404)
        return _ok(result)
    except ValueError as e:
        return _err(f'数据校验失败: {e}', status=400)


# ── 复位（演示用） ─────────────────────────────────────

@api_bp.route('/api/reset', methods=['POST'])
def reset():
    data_bus.reset()
    flow.reset()
    kb_store.reset()
    return _ok({'reset': True})


