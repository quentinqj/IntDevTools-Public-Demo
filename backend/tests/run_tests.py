"""IntDevTools Public Demo v2 · 自动测试（run_tests.py 风格）

覆盖：开发等级判定 / 数据总线 Schema 校验 / 评价基准生成 / 审查引擎 / 4 步链路 E2E。

用法：
    cd backend && python tests/run_tests.py
退出码：0 全部通过；1 有失败。
"""
import os
import sys

# 让 tests 目录能 import backend 包
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PASSED = []
FAILED = []


def check(name, condition, detail=''):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  {detail}")


def reset_all():
    from app.core import data_bus, flow, kb_store
    data_bus.reset()
    flow.reset()
    kb_store.reset()


# ─────────────────────────────────────────────────────────
def test_development_level():
    print("\n== 开发等级判定（真实逻辑） ==")
    from app.core import development_level as dl

    check("L1: low", dl.determine_level('low') == 'L1', dl.determine_level('low'))
    check("L2: medium", dl.determine_level('medium') == 'L2')
    check("L3: high", dl.determine_level('high') == 'L3')
    check("L4: critical", dl.determine_level('critical') == 'L4')
    check("非法难度返回 None", dl.determine_level('ultra') is None)

    result = dl.assess_requirement(101, 'medium',
                                   standards=[{'id': 'STD-02'}],
                                   verification_items=['环境光抗扰试验'])
    check("assess 返回 level=L2", result and result['level'] == 'L2')
    check("assess 返回可解释 reason", result and 'L2' in result['reason'] and '标准开发' in result['reason'])
    check("assess 无效难度返回 None", dl.assess_requirement(101, 'bad') is None)


def test_data_bus():
    print("\n== 数据总线（真实 transit 逻辑 + Schema 校验） ==")
    from app.core import data_bus

    reset_all()
    payload = {'project_id': 101, 'level': 'L2', 'difficulty': 'medium',
               'reason': '测试', 'updated_at': '2026-08-20T00:00:00+00:00'}
    r = data_bus.put_transit('development_level', 101, payload)
    check("put/get 回环", data_bus.get_transit('development_level', 101)['data']['level'] == 'L2')

    try:
        data_bus.get_transit('bad_type', 101)
        check("未知类型抛 ValueError", False)
    except ValueError:
        check("未知类型抛 ValueError", True)

    try:
        data_bus.put_transit('development_level', 101, {'level': 'L2'})  # 缺 project_id/difficulty
        check("缺 required 字段被拒", False)
    except ValueError:
        check("缺 required 字段被拒", True)

    try:
        data_bus.put_transit('development_level', 101, {'project_id': 101, 'level': 'L9', 'difficulty': 'low'})
        check("enum 越界被拒", False)
    except ValueError:
        check("enum 越界被拒", True)

    try:
        data_bus.put_transit('development_level', 101, {'project_id': 101, 'level': 'L2', 'difficulty': 'low', 'hack': 1})
        check("additionalProperties=false 被拒", False)
    except ValueError:
        check("additionalProperties=false 被拒", True)

    try:
        data_bus.put_transit('review_result', 101, {'project_id': 101, 'status': 'failed', 'findings': []})
        check("review_result 合法写入", True)
    except ValueError as e:
        check("review_result 合法写入", False, str(e))

    reset_all()


def test_eval_base():
    print("\n== 评价基准生成（真实逻辑） ==")
    from app.core import eval_base

    ev = eval_base.generate_evaluation_base('controller', severity='必须')
    check("controller 生成成功", ev is not None)
    check("产品名正确", ev and ev['product_name'] == '控制器/PLC')
    check("含标准", ev and len(ev['standards']) >= 1)
    check("严重度生效", ev and ev['severity'] == '必须')
    check("每类条目 ≤ 上限", ev and all(len(c['selected_items']) <= eval_base.MAX_ITEMS_PER_CATEGORY for c in ev['categories']))
    check("未知产品返回 None", eval_base.generate_evaluation_base('nope') is None)

    findings = [
        {'id': 'F-01', 'severity': 'high', 'rule_name': '电磁兼容设计检查', 'suggestion': '补充频段分析'},
        {'id': 'F-02', 'severity': 'medium', 'rule_name': '参数容差检查', 'suggestion': '定义下限'},
        {'id': 'F-03', 'severity': 'low', 'rule_name': '术语一致性', 'suggestion': '统一术语'},
    ]
    ev2 = eval_base.enrich_with_review_findings(ev, findings, confirmed_ids={'F-01', 'F-02'})
    check("only high/medium 转 special", len(ev2['special_items']) == 2)
    check("special 带来源", all(s['source'] in ('F-01', 'F-02') for s in ev2['special_items']))

    manifest = eval_base.to_test_manifest(101, 'controller', ev2)
    check("manifest 条目 > 0", len(manifest['items']) > 0)
    check("manifest 必需字段齐全", all(all(k in it for k in ('category', 'validation_item', 'doc_name')) for it in manifest['items']))


def test_review_engine():
    print("\n== 设计审查引擎（真实规则引擎） ==")
    import json
    from app import config
    from app.core import review_engine
    from app.core import data_loader

    blocks = data_loader.parse_design_doc()
    with open(config.RULES_JSON, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    check("空 blocks → 空结果", review_engine.review_doc_by_rules([], rules) == [])
    check("空 rules → 空结果", review_engine.review_doc_by_rules(blocks, []) == [])
    check("设计文档解析出 4 块", len(blocks) == 4, str(len(blocks)))

    findings = review_engine.review_doc_by_rules(blocks, rules, strictness='standard')
    by_rule = {f['rule_id']: f for f in findings}

    check("R-202 EMC 命中（high）", by_rule.get('R-202') and by_rule['R-202']['severity'] == 'high')
    check("R-202 带命中位置证据", by_rule.get('R-202') and by_rule['R-202'].get('evidence') != '')
    check("R-118 容差命中（medium）", by_rule.get('R-118') and by_rule['R-118']['severity'] == 'medium')
    check("R-007 术语不一致命中", by_rule.get('R-007') is not None)
    check("R-301 短路保护 OK", by_rule.get('R-301') and by_rule['R-301']['status'] == 'ok')
    check("R-402 不适用 → 无发现", by_rule.get('R-402') is None)
    check("R-501 需人工审查", by_rule.get('R-501') and by_rule['R-501']['status'] == 'manual')
    check("R-501 severity=medium", by_rule.get('R-501') and by_rule['R-501']['severity'] == 'medium')
    check("置信度在有效范围", all(0 <= f['confidence'] <= 1 for f in findings))

    # feasibility 闸门
    level, reason = review_engine.assess_feasibility(
        {'check_logic': '外观核对依赖图片/截图', 'target_file_pattern': '*.md'})
    check("图片依赖 → needs_manual", level == review_engine.NEEDS_MANUAL_REVIEW and 'D1' in reason)
    level2, _ = review_engine.assess_feasibility({'check_logic': '纯文本检查', 'target_file_pattern': '*.md'})
    check("纯文本 → fully_reviewable", level2 == review_engine.FULLY_REVIEWABLE)


def test_e2e_chain():
    print("\n== 4 步链路 E2E（Flask test client） ==")
    from app import create_app, config

    reset_all()
    app = create_app()
    client = app.test_client()

    r = client.get('/api/health')
    data = r.get_json()
    check("health code=0", data['code'] == 0)
    check("默认规则模式", data['data']['mode'] == 'rules')

    r = client.get('/api/requirements')
    reqs = r.get_json()['data']['requirements']
    check("需求 CSV 解析出 3 条", len(reqs) == 3)

    # ① 评估
    r = client.post('/api/assessment', json={'project_id': 101, 'requirement_id': 'REQ-002', 'difficulty': 'medium'})
    d = r.get_json()
    check("评估 code=0", d['code'] == 0)
    check("评估 level=L2", d['data']['level'] == 'L2')
    check("评估匹配到标准", len(d['data']['standards']) >= 1)
    check("评估写入 transit", client.get('/api/transit/development_level/101').get_json()['data']['data']['level'] == 'L2')

    # ② 审查（先复位再验证顺序错误）
    reset_all()
    r = client.post('/api/review', json={'project_id': 101})
    check("未评估先审查 → 400", r.status_code == 400)

    client.post('/api/assessment', json={'project_id': 101, 'requirement_id': 'REQ-002', 'difficulty': 'medium'})
    r = client.post('/api/review', json={'project_id': 101})
    d = r.get_json()
    check("审查 code=0", d['code'] == 0)
    fids = [f['id'] for f in d['data']['findings']]
    check("审查发现含 R-202", any(f.startswith('R-202') for f in fids))

    # 确认
    r = client.post('/api/review/confirm', json={'project_id': 101, 'confirmations': {'bad-id': 'adopt'}})
    check("无效 finding id → 400", r.status_code == 400)

    conf = {fid: ('adopt' if fid.startswith('R-202') or fid.startswith('R-118') else 'reject') for fid in fids}
    r = client.post('/api/review/confirm', json={'project_id': 101, 'confirmations': conf})
    d = r.get_json()
    check("确认 code=0", d['code'] == 0)
    check("审查结论 failed", d['data']['status'] == 'failed')
    check("review_result 已入 transit", client.get('/api/transit/review_result/101').get_json()['code'] == 0)

    # ③ 评价
    r = client.post('/api/eval-base', json={'project_id': 101, 'product_type_id': 'controller'})
    d = r.get_json()
    check("评价 code=0", d['code'] == 0)
    check("评价含通用项", len(d['data']['categories']) > 0)
    check("评价含产品特有项（审查转化）", len(d['data']['special_items']) >= 1)

    r = client.post('/api/eval-base/confirm', json={'project_id': 101})
    d = r.get_json()
    check("评价确认 code=0", d['code'] == 0)
    check("test_manifest 已入 transit", client.get('/api/transit/test_manifest/101').get_json()['code'] == 0)

    # ④ 知识沉淀
    r = client.post('/api/kb/contribute', json={'project_id': 101})
    d = r.get_json()
    check("沉淀 code=0", d['code'] == 0)
    entry = d['data']['entry']
    check("新条目标题含项目名", '传感器控制器' in entry['title'])
    check("新条目含来源", '审查发现' in entry.get('source', ''))
    check("KB 列表含新条目", any(e['id'] == entry['id'] for e in client.get('/api/kb').get_json()['data']['entries']))

    reset_all()


def main():
    print("IntDevTools Public Demo v2 · run_tests.py")
    print("=" * 60)
    test_development_level()
    test_data_bus()
    test_eval_base()
    test_review_engine()
    test_e2e_chain()
    reset_all()
    print("\n" + "=" * 60)
    print(f"PASS: {len(PASSED)}   FAIL: {len(FAILED)}")
    if FAILED:
        print("失败项:")
        for f in FAILED:
            print("  -", f)
        sys.exit(1)
    print("全部通过 ✅")


if __name__ == '__main__':
    main()
