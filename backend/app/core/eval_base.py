"""评价基准生成（来自 IntDevTools 05_eval_base_gen/modules/generator/services.py 的真实逻辑）

- generate_evaluation_base：按产品大类生成评价基准（通用大类）
- enrich_with_review_findings：将人工确认的审查发现转换为产品特有评价项
"""
import json
import os

from app import config

SEVERITY_LEVELS = ['必须', '推荐', '参考']
SEVERITY_DEFAULT = '推荐'
MAX_ITEMS_PER_CATEGORY = 5


def _load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_product_types():
    return _load_json(config.PRODUCT_TYPES_JSON)


def load_evaluation_categories():
    return _load_json(config.EVAL_CATEGORIES_JSON)


def get_product_type(product_type_id):
    """获取产品类型定义"""
    for pt in load_product_types():
        if pt['id'] == product_type_id:
            return pt
    return None


def get_applicable_categories(product_type_id):
    """获取指定产品适用的评价分类"""
    pt = get_product_type(product_type_id)
    if not pt:
        return []
    cat_map = {c['id']: c for c in load_evaluation_categories()}
    return [cat_map[cid] for cid in pt.get('applicable_categories', []) if cid in cat_map]


def generate_evaluation_base(product_type_id, severity='推荐'):
    """生成评价基准（真实生成逻辑）

    Args:
        product_type_id: str, 产品大类 ID
        severity: str, 严重度（必须/推荐/参考）

    Returns:
        dict: {product_type, product_name, standards, severity, categories:[...]}
        无效产品类型返回 None
    """
    product_types = load_product_types()
    categories = load_evaluation_categories()
    max_items = MAX_ITEMS_PER_CATEGORY

    pt = next((p for p in product_types if p['id'] == product_type_id), None)
    if not pt:
        return None

    cat_map = {c['id']: c for c in categories}
    result = {
        'product_type': pt['id'],
        'product_name': pt['name'],
        'standards': pt.get('standards', []),
        'severity': severity,
        'categories': [],
    }

    for cat_id in pt.get('applicable_categories', []):
        cat = cat_map.get(cat_id)
        if not cat:
            continue
        items = cat.get('typical_items', [])
        selected = items[:min(len(items), max_items)]
        result['categories'].append({
            'id': cat['id'],
            'name': cat['name'],
            'description': cat['description'],
            'selected_items': [{'name': item, 'severity': severity} for item in selected],
        })

    return result


def enrich_with_review_findings(ev_base, findings, confirmed_ids=None):
    """将人工确认（adopt）的审查发现转换为产品特有评价项（真实转换逻辑）

    规则：severity in (high, medium) 且已确认的发现 → 追加为"产品特有"评价项，
    来源标注为对应审查发现，确保评价清单可追溯到审查报告。

    Args:
        ev_base: generate_evaluation_base() 的输出
        findings: 审查发现列表（含 id/severity/suggestion）
        confirmed_ids: 已确认采纳的 finding id 集合；None 表示全部采纳

    Returns:
        dict: ev_base + {"special_items": [...]}
    """
    confirmed_ids = confirmed_ids if confirmed_ids is not None else {f['id'] for f in findings}
    special = []
    for f in findings:
        if f['id'] not in confirmed_ids:
            continue
        if f.get('severity') not in ('high', 'medium'):
            continue
        suggestion = f.get('suggestion') or f.get('description', '')
        special.append({
            'source': f['id'],
            'source_rule': f.get('rule_name', ''),
            'name': suggestion[:40],
            'severity': '推荐',
        })
    ev_base = dict(ev_base)
    ev_base['special_items'] = special
    return ev_base


def to_test_manifest(project_id, product_type_id, ev_base, confirmed_ids=None):
    """把评价基准转为 test_manifest（符合 test_manifest.schema.json）

    kind=common 为通用大类评价；kind=special 为产品特有评价。
    """
    items = []
    for cat in ev_base.get('categories', []):
        for it in cat.get('selected_items', []):
            items.append({
                'category': cat['name'],
                'validation_item': it['name'],
                'doc_name': f"评价记录_{cat['name']}.md",
                'template_path': 'demo-data/templates（示例）',
            })
    for sp in ev_base.get('special_items', []):
        items.append({
            'category': '产品特有（审查发现转化）',
            'validation_item': sp['name'],
            'doc_name': f"评价记录_产品特有_{sp['source']}.md",
            'template_path': f"来源: {sp['source_rule']}",
        })
    return {
        'project_id': project_id,
        'product_type_id': product_type_id,
        'kind': 'common',
        'generated_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        'items': items,
    }
