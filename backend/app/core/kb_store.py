"""示例知识库读写（虚构数据，公开演示用）

- 读：backend/app/data/kb_seed.json（种子条目）
- 写：backend/data/kb_entries.json（运行时沉淀，已 gitignore）
- distill_contribution：把人工确认的审查发现提炼为可复用知识条目（真实转换逻辑）
"""
import json
import os
import re

from app import config


def _ensure_runtime():
    os.makedirs(config.RUNTIME_DIR, exist_ok=True)


def list_entries():
    """返回全部知识条目（运行时文件不存在时从种子初始化）"""
    _ensure_runtime()
    if not os.path.exists(config.KB_ENTRIES_JSON):
        with open(config.KB_SEED_JSON, 'r', encoding='utf-8') as f:
            seed = json.load(f)
        with open(config.KB_ENTRIES_JSON, 'w', encoding='utf-8') as f:
            json.dump(seed, f, ensure_ascii=False, indent=2)
        return list(seed)
    with open(config.KB_ENTRIES_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save(entries):
    _ensure_runtime()
    with open(config.KB_ENTRIES_JSON, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def next_entry_id(entries):
    """生成下一个条目 ID（KB-YYYY-NNN，按现有最大序号 +1）"""
    ids = [e['id'] for e in entries]
    max_no = 0
    for i in ids:
        m = re.search(r'-(\d+)$', i)
        if m:
            max_no = max(max_no, int(m.group(1)))
    from datetime import datetime
    return f"KB-{datetime.now().year}-{max_no + 1:03d}"


def distill_contribution(project_name, findings, confirmed_ids=None):
    """将人工确认的审查发现提炼为知识条目（真实转换逻辑）

    规则：
    - 只纳入 severity in (high, medium) 且已确认（adopt）的发现
    - 标题：<产品名> · <首条发现主题>设计要点
    - 正文：每条发现一条要点（描述 + 建议）
    - 标签：由命中规则名提炼（取规则名去后缀后的核心词）

    Args:
        project_name: 产品/项目名（用于条目标题）
        findings: 审查发现列表
        confirmed_ids: 已确认采纳的 id 集合（None = 全部）

    Returns:
        dict: 新知识条目（未持久化）
    """
    confirmed_ids = confirmed_ids if confirmed_ids is not None else {f['id'] for f in findings}
    adopted = [f for f in findings
               if f['id'] in confirmed_ids and f.get('severity') in ('high', 'medium')]
    if not adopted:
        return None

    first = adopted[0]
    topic = re.sub(r'[（(].*?[)）]', '', first.get('rule_name', '审查')).strip() or '审查'

    tags = []
    for f in adopted:
        name = f.get('rule_name', '')
        m = re.search(r'[··]?\s*([\u4e00-\u9fa5A-Za-z]+(?:设计|检查|一致性|试验|容差))', name)
        if m:
            core = m.group(1)
            if core not in tags:
                tags.append(core)
    if not tags:
        tags = ['审查经验', '设计要点']

    body = []
    for f in adopted:
        line = f.get('description', '')
        if f.get('suggestion'):
            line = f"{line}（建议：{f['suggestion']}）"
        body.append(line)

    return {
        'id': None,  # 由调用方分配
        'title': f"{project_name} · {topic}设计要点",
        'category': '20_Products / 60_Evaluation_Criteria（示例分类）',
        'tags': tags[:4],
        'body': body,
        'source': '审查发现 ' + ', '.join(f['id'] for f in adopted) + '（人工确认后沉淀）',
        'added': '刚刚',
    }


def add_entry(entry):
    """追加知识条目并持久化，返回带 ID 的完整条目"""
    entries = list_entries()
    if not entry.get('id'):
        entry['id'] = next_entry_id(entries)
    entries.insert(0, entry)
    _save(entries)
    return entry


def reset():
    """复位示例知识库（删除运行时文件，下次读取回到种子）"""
    if os.path.exists(config.KB_ENTRIES_JSON):
        os.remove(config.KB_ENTRIES_JSON)
