"""样例数据读取（真实读取 demo-data 下的虚构样例文件）

- load_requirements(): 解析 requirements.csv
- parse_design_doc(): 解析 syra_design.md → 文档块（审查输入）
- load_standards(): 解析 10_standards.md → 标准表（数据驱动）
- match_standards(text): 按关键词匹配标准（数据驱动规则匹配）
"""
import csv
import re

from app import config


def load_requirements():
    """读取需求 CSV → list[dict]"""
    with open(config.REQUIREMENTS_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for r in rows:
        r['syra_count'] = int(r.get('syra_count') or 0)
    return rows


def parse_design_doc():
    """解析设计文档 MD → 文档块 [{id, btype, location, text}]（审查引擎输入）"""
    with open(config.DESIGN_DOC_MD, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    blocks = []
    current_title = None
    current_parts = []
    block_id = 1

    def flush():
        nonlocal current_title, current_parts, block_id
        if current_title is not None and current_parts:
            blocks.append({
                'id': block_id,
                'btype': 'section',
                'location': current_title,
                'text': '\n'.join(current_parts).strip(),
            })
            block_id += 1
        current_parts = []

    for raw in lines:
        line = raw.rstrip('\n').strip()
        if re.match(r'^#{2,4}\s+\d+\.', line):
            flush()
            current_title = re.sub(r'^#{2,4}\s+', '', line)
            continue
        if re.match(r'^#{2,4}\s+', line):
            flush()
            current_title = re.sub(r'^#{2,4}\s+', '', line)
            continue
        if line and current_title is not None:
            current_parts.append(line)
    flush()
    return blocks


def load_standards():
    """解析标准表 MD → list[dict{id, label, purpose, keywords, verification}]"""
    with open(config.STANDARDS_MD, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    standards = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 5:
            continue
        code = cells[0]
        if code in ('编号', '---'):
            continue
        keywords = [k.strip() for k in cells[3].split(',') if k.strip()]
        verification = [v.strip() for v in cells[4].split(',') if v.strip()]
        standards.append({
            'id': code,
            'label': cells[1],
            'purpose': cells[2],
            'keywords': keywords,
            'verification': verification,
        })
    return standards


def match_standards(text):
    """按关键词匹配标准（数据驱动规则匹配）

    对需求文本，逐条标准的 keywords 做包含匹配，返回命中标准、命中词，
    以及该标准数据中定义的验证条目（真实系统的"验证条目→SYQT"数据流）。

    Args:
        text: 需求标题/内容

    Returns:
        (matched_standards, verification_items)
    """
    matched = []
    verification = []
    for std in load_standards():
        hit = [k for k in std['keywords'] if k in text]
        if hit:
            matched.append({
                'id': std['id'],
                'label': std['label'],
                'purpose': std['purpose'],
                'matched_keywords': hit,
            })
            for v in std.get('verification', []):
                item = f"{v}（依据 {std['id']} {std['label']}）"
                if item not in verification:
                    verification.append(item)
    return matched, verification
