"""设计审查引擎（来自 IntDevTools 02_prereview/modules/review/engine 的真实逻辑）

- review_doc_by_rules：按规则逐条审查文档块（批次循环 + 单条派发）
- 可审查性闸门：assess_feasibility（D1~D4 真实评估，零成本）
- 确定性检查：file_exists / cell_not_empty / checkbox_all_checked / keyword_present / term_consistency
- 复杂规则（other）：LLM 模式走真实 LLM 提示词；规则模式走关键字匹配（均输出依据）

输出每条发现均带：命中规则、命中位置（evidence）、判定依据（ng_condition）、建议、置信度。
"""
import fnmatch
import json
import logging
import re

logger = logging.getLogger(__name__)

# ── 可审查性评估（来自 feasibility.py 的真实逻辑） ──────────
FULLY_REVIEWABLE = 'fully_reviewable'
PARTIALLY_REVIEWABLE = 'partially_reviewable'
NEEDS_MANUAL_REVIEW = 'needs_manual_review'
NOT_REVIEWABLE = 'not_reviewable'

_UNSUPPORTED_EXTS = {'.pdf', '.xls', '.doc', '.ppt'}
_IMAGE_SIGNAL_WORDS = [
    '图片', '图像', '截图', '图示', '流程图', '示意图', '照片',
    'グラフ', '図', '図表', '画像',
    'image', 'screenshot', 'diagram', 'chart', 'picture',
]
_FORMAT_SIGNAL_WORDS = [
    '红色', '绿色', '蓝色', '黄色', '颜色', '字体', '加粗', '斜体',
    '背景色', '填充色', '边框', '高亮', '条件格式', '标红', '涂色', '着色',
    '赤色', '青色', '色付き', 'フォント', '太字',
    'color', 'colour', 'font', 'bold', 'italic', 'background',
    'border', 'highlight', 'conditional format',
]
_NATURAL_LANG_LOCATION_WORDS = [
    '末尾', '最后', '开头', '中间', '某', '大约', '附近',
    '相应', '相关', '对应',
    '最後', '先頭', '中間', '付近',
]


def assess_feasibility(rule: dict) -> tuple:
    """评估审查定义的可审查性（真实逻辑）

    Returns:
        (level, reason)：如 (FULLY_REVIEWABLE, '') / (NEEDS_MANUAL_REVIEW, 'D1:...')
    """
    reasons = []

    # D4: 文件类型兼容性
    pattern = (rule.get('target_file_pattern') or '').lower()
    exts = re.findall(r'\.\w+', pattern)
    unsupported = [e for e in exts if e in _UNSUPPORTED_EXTS]
    if exts and len(unsupported) == len(exts):
        return (NOT_REVIEWABLE, 'D4:目标文件类型当前不支持解析')
    if unsupported:
        reasons.append('D4_partial:部分目标文件类型不支持解析')

    # D1: 图片/视觉内容依赖
    check_logic = rule.get('check_logic', '') or ''
    for w in _IMAGE_SIGNAL_WORDS:
        if w in check_logic:
            reasons.append('D1:审查内容依赖图片/截图/流程图')
            break

    # D2: 格式/样式依赖
    for w in _FORMAT_SIGNAL_WORDS:
        if w in check_logic:
            reasons.append('D2:审查内容依赖颜色/字体/格式')
            break

    # D3: 位置为自然语言
    target_location = rule.get('target_location', '') or ''
    for w in _NATURAL_LANG_LOCATION_WORDS:
        if w in target_location:
            reasons.append('D3:审查位置为自然语言描述')
            break

    if any(r.startswith('D1') or r.startswith('D2') for r in reasons):
        return (NEEDS_MANUAL_REVIEW, ';'.join(reasons))
    if reasons:
        return (PARTIALLY_REVIEWABLE, ';'.join(reasons))
    return (FULLY_REVIEWABLE, '')


# ── 通用工具 ─────────────────────────────────────────────

def glob_match(pattern: str, text: str) -> bool:
    """glob 匹配（支持逗号分隔的多个模式）"""
    for p in pattern.split(','):
        p = p.strip()
        if not p:
            continue
        if fnmatch.fnmatch(text, p) or fnmatch.fnmatch(text.lower(), p.lower()):
            return True
    return False


def normalize_severity(sev: str) -> str:
    """统一严重度为 high/medium/low（真实系统 schema 枚举）"""
    return {'high': 'high', 'mid': 'medium', 'medium': 'medium',
            'low': 'low', 'info': 'low'}.get(sev, 'medium')


def _doc_text(blocks) -> str:
    return '\n'.join(b.get('text', '') for b in blocks)


# ── 确定性检查（真实方法） ───────────────────────────────

def check_file_exists(blocks, rule, strictness):
    """检查文件是否存在（glob 匹配）"""
    target_pattern = rule.get('target_file_pattern', '')
    ng_condition = rule.get('ng_condition', '')
    if not target_pattern:
        return []

    matched = []
    for b in blocks:
        loc = b.get('location', '')
        text = b.get('text', '')
        if glob_match(target_pattern, loc) or glob_match(target_pattern, text):
            matched.append(loc or text)
    if not matched:
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': None, 'location': '文件系统',
            'evidence': '',
            'description': f"未找到符合模式 '{target_pattern}' 的文件。{ng_condition}",
            'severity': 'high', 'suggestion': rule.get('suggestion', ''),
            'confidence': 1.0, 'status': 'open',
        }]
    return [{
        'rule_id': rule['id'], 'rule_name': rule['rule_name'],
        'block_id': None, 'location': '', 'evidence': '; '.join(matched[:5]),
        'description': '', 'severity': '', 'suggestion': '',
        'confidence': 1.0, 'status': 'ok', 'ok_evidence': '; '.join(matched[:5]),
    }]


def check_cell_not_empty(blocks, rule, strictness):
    """检查单元格非空（target_location 精确匹配）"""
    target_location = rule.get('target_location', '')
    ng_condition = rule.get('ng_condition', '')
    matching = [b for b in blocks if target_location in b.get('location', '')]
    if not matching:
        return []  # 无法定位 → 不适用（真实系统回退 LLM，公开版保持确定性）
    empty = [b for b in matching if not (b.get('text') or '').strip()]
    if empty:
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': b['id'], 'location': b['location'],
            'evidence': b['location'],
            'description': f"单元格为空。{ng_condition}",
            'severity': 'medium', 'suggestion': rule.get('suggestion', ''),
            'confidence': 1.0, 'status': 'open',
        } for b in empty]
    filled = [f"{b['location']}=\"{b['text'][:50]}\"" for b in matching]
    return [{
        'rule_id': rule['id'], 'rule_name': rule['rule_name'],
        'block_id': None, 'location': '', 'description': '',
        'severity': '', 'suggestion': '', 'confidence': 1.0, 'status': 'ok',
        'ok_evidence': '非空单元格：' + ', '.join(filled[:5]),
    }]


def check_checkbox_all_checked(blocks, rule, strictness):
    """检查勾选框全勾选（[x]/[ ] 文本匹配）"""
    ng_condition = rule.get('ng_condition', '')
    unchecked = []
    checked = 0
    for b in blocks:
        text = b.get('text', '')
        for m in re.finditer(r'\[([ xX])\][^\n]*', text):
            if m.group(1) in 'xX':
                checked += 1
            else:
                unchecked.append(b.get('location', '') or b.get('text', '')[:30])
    if unchecked:
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': None, 'location': loc, 'evidence': loc,
            'description': f"存在未勾选项。{ng_condition}", 'severity': 'medium',
            'suggestion': rule.get('suggestion', ''), 'confidence': 1.0,
            'status': 'open',
        } for loc in unchecked[:10]]
    return [{
        'rule_id': rule['id'], 'rule_name': rule['rule_name'],
        'block_id': None, 'location': '', 'description': '', 'severity': '',
        'suggestion': '', 'confidence': 1.0, 'status': 'ok',
        'ok_evidence': f"勾选项全部已勾选（{checked} 项）",
    }]


def check_keyword_present(blocks, rule, strictness):
    """检查关键词存在（输出接口保护等可精确匹配的规则）"""
    keywords = rule.get('keywords', [])
    if not keywords:
        return []
    hits = []
    for b in blocks:
        text = b.get('text', '')
        if all(k in text for k in keywords):
            hits.append(b)
    if hits:
        b = hits[0]
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': b['id'], 'location': b['location'],
            'evidence': b['text'][:80], 'description': '', 'severity': '',
            'suggestion': '', 'confidence': 1.0, 'status': 'ok',
            'ok_evidence': f"{rule.get('ok_message', '')}：{b['location']}",
        }]
    return [{
        'rule_id': rule['id'], 'rule_name': rule['rule_name'],
        'block_id': None, 'location': '全文档', 'evidence': '',
        'description': rule.get('ng_condition', '未找到关键内容'),
        'severity': normalize_severity(rule.get('severity_ng', 'high')),
        'suggestion': rule.get('suggestion', ''), 'confidence': 0.9, 'status': 'open',
    }]


def check_term_consistency(blocks, rule, strictness):
    """检查术语一致性：同一概念多种写法同时出现 → 发现"""
    terms = rule.get('terms', [])
    if len(terms) < 2:
        return []
    found = {}
    for b in blocks:
        for t in terms:
            if t in b.get('text', '') and t not in found:
                found[t] = b
    if len(found) >= 2:
        variants = ' / '.join(found.keys())
        evidence = '; '.join(f"{t}@{found[t]['location']}" for t in found)
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': None, 'location': '全文档', 'evidence': evidence,
            'description': f"{rule.get('ng_condition', '')}（发现写法：{variants}）",
            'severity': normalize_severity(rule.get('severity_ng', 'low')),
            'suggestion': rule.get('suggestion', ''), 'confidence': 0.98,
            'status': 'open',
        }]
    return []


def _check_keyword_rule(blocks, rule, strictness):
    """复杂规则（other）的确定性实现：关键字命中 + 必含项检查

    命中规则：文档中存在任一关键字 → 规则适用
    判定：必含项（must_include）全部存在 → OK；否则 → NG（带证据）
    """
    keywords = rule.get('keywords', [])
    must_include = rule.get('must_include', [])
    if not keywords:
        return []

    matched_blocks = []
    for b in blocks:
        text = b.get('text', '')
        hit = [k for k in keywords if k in text]
        if hit:
            matched_blocks.append((b, hit))

    if not matched_blocks:
        return []  # 规则不适用（文档无相关主题）

    doc = _doc_text(blocks)
    missing = [m for m in must_include if m not in doc]
    matched_keyword_count = len({k for _, hits in matched_blocks for k in hits})
    confidence = round(min(0.98, 0.5 + 0.15 * matched_keyword_count), 2)

    if not missing:
        first = matched_blocks[0][0]
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': first['id'], 'location': first['location'],
            'evidence': first['text'][:80], 'description': '', 'severity': '',
            'suggestion': '', 'confidence': confidence, 'status': 'ok',
            'ok_evidence': f"{rule.get('rule_name')}：文档已包含全部必含项（{', '.join(must_include)}）",
        }]

    b, hits = matched_blocks[0]
    return [{
        'rule_id': rule['id'], 'rule_name': rule['rule_name'],
        'block_id': b['id'], 'location': b['location'],
        'evidence': b['text'][:100],
        'description': f"{rule.get('ng_condition', '')}（命中位置：{b['location']}，命中词：{', '.join(hits)}）",
        'severity': normalize_severity(rule.get('severity_ng', 'medium')),
        'suggestion': rule.get('suggestion', ''),
        'confidence': confidence, 'status': 'open',
    }]


# ── LLM 复杂规则（BYOK 模式，提示词来自真实系统） ──────────

def _check_with_llm(blocks, rule, strictness, llm):
    """使用 LLM 进行复杂判断（真实提示词，来自 engine_rule.py）"""
    blocks_text = '\n'.join(
        f"[B{b['id']}] ({b['location']}) {b['text'][:500]}" for b in blocks
    )
    prompt = f"""你是一名严格的文档审查员。请根据以下审查定义，检查文档。

【审查定义】
- 规则名称: {rule['rule_name']}
- 检查逻辑: {rule.get('check_logic', '')}
- 目标文件模式: {rule.get('target_file_pattern', '')}
- OK条件: {rule.get('ok_condition', '')}
- NG条件: {rule.get('ng_condition', '')}
- 严格程度: {strictness}

【文档内容】
{blocks_text}

【审查要求】
1. 如果找到满足 OK 条件的内容，在 ok_evidence 中注明具体位置和内容。
2. 如果发现 NG 问题，在 location 和 description 中说明。
3. 无法确认时判定为 NG。

返回 JSON 数组（仅1个元素）：
[{{"result": "ok" 或 "ng", "ok_evidence": "", "location": "", "description": "", "severity": "high/mid/low"}}]
只返回 JSON 数组。"""
    try:
        data = llm.chat_json([{'role': 'user', 'content': prompt}])
    except Exception as e:
        logger.error('LLM 判断失败（规则 %s）: %s', rule.get('rule_name', ''), e)
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': None, 'location': '', 'evidence': '',
            'description': f'LLM 调用失败，需人工确认：{e}', 'severity': 'medium',
            'suggestion': '', 'confidence': 0.0, 'status': 'manual',
        }]
    if not data or not isinstance(data, list) or not data:
        return []
    item = data[0]
    if item.get('result') == 'ng':
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': None, 'location': item.get('location', ''),
            'evidence': item.get('location', ''),
            'description': item.get('description', rule.get('ng_condition', '')),
            'severity': normalize_severity(item.get('severity', 'mid')),
            'suggestion': rule.get('suggestion', ''),
            'confidence': 0.9, 'status': 'open',
        }]
    return [{
        'rule_id': rule['id'], 'rule_name': rule['rule_name'],
        'block_id': None, 'location': '', 'description': '', 'severity': '',
        'suggestion': '', 'confidence': 0.9, 'status': 'ok',
        'ok_evidence': item.get('ok_evidence', ''),
    }]


# ── 主入口 ───────────────────────────────────────────────

def _check_single_rule(blocks, rule, strictness, llm=None):
    """检查单个审查定义规则"""
    # 可审查性闸门：不可审查/需人工 → 短路返回
    level, reason = assess_feasibility(rule)
    if level == NOT_REVIEWABLE:
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': None, 'location': '', 'evidence': '',
            'description': f'不可审查：{reason}', 'severity': 'high',
            'suggestion': '建议删除或改写为可提取文本的描述',
            'confidence': 0.0, 'status': 'manual',
        }]
    if level == NEEDS_MANUAL_REVIEW:
        return [{
            'rule_id': rule['id'], 'rule_name': rule['rule_name'],
            'block_id': None, 'location': '', 'evidence': '',
            'description': f'需人工审查：{reason}', 'severity': 'medium',
            'suggestion': rule.get('suggestion', '请人工确认'),
            'confidence': 0.0, 'status': 'manual',
        }]

    check_method = rule.get('check_method', 'other')
    if check_method == 'file_exists':
        return check_file_exists(blocks, rule, strictness)
    elif check_method == 'cell_not_empty':
        return check_cell_not_empty(blocks, rule, strictness)
    elif check_method == 'checkbox_all_checked':
        return check_checkbox_all_checked(blocks, rule, strictness)
    elif check_method == 'keyword_present':
        return check_keyword_present(blocks, rule, strictness)
    elif check_method == 'term_consistency':
        return check_term_consistency(blocks, rule, strictness)
    elif check_method == 'other':
        if llm is not None:
            return _check_with_llm(blocks, rule, strictness, llm)
        return _check_keyword_rule(blocks, rule, strictness)
    logger.warning('未知的检查方法: %s', check_method)
    return []


def review_doc_by_rules(blocks, rules, strictness='standard', llm=None, progress_cb=None):
    """基于审查定义审查文档块（真实引擎入口）

    Args:
        blocks: [{id, btype, location, text}, ...]
        rules: [{id, rule_name, check_method, keywords, ...}, ...]
        strictness: relaxed / standard / strict
        llm: LLM 网关实例（None 表示确定性规则模式）
        progress_cb: 进度回调(rule, idx, total)

    Returns:
        list of finding dict
    """
    if not blocks or not rules:
        return []
    all_findings = []
    total = len(rules)
    for idx, rule in enumerate(rules):
        if progress_cb:
            progress_cb(rule, idx + 1, total)
        try:
            findings = _check_single_rule(blocks, rule, strictness, llm=llm)
            all_findings.extend(findings)
        except Exception as e:
            logger.error('规则 %s 检查异常: %s', rule.get('id'), e)
    return all_findings
