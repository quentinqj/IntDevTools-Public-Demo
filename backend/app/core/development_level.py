"""开发等级判定（来自 IntDevTools 01_req_tracker/core/development_level/services.py 的真实逻辑）

提供开发难度与开发等级的映射判定逻辑，以及向数据总线中转的写入能力。
"""
from datetime import datetime, timezone

# 难度 → 等级映射表
DIFFICULTY_LEVEL_MAP = {
    'low': 'L1',
    'medium': 'L2',
    'high': 'L3',
    'critical': 'L4',
}

# 等级 → 描述映射表
LEVEL_LABEL_MAP = {
    'L1': '简单开发 — 单体功能/少量变更',
    'L2': '标准开发 — 常规功能/模块级变更',
    'L3': '复杂开发 — 多模块/跨系统交互',
    'L4': '高难度开发 — 新平台/安全关键/多系统集成',
    'L5': '极高难度开发 — 全新技术/战略级项目（预留）',
}

# 难度 → 描述映射表
DIFFICULTY_LABEL_MAP = {
    'low': '简单 — 需求明确、技术成熟、无外部依赖',
    'medium': '中等 — 需求较明确、需少量新技术或外部协作',
    'high': '困难 — 需求复杂、需多项新技术或跨团队协作',
    'critical': '极高 — 需求关键、突破性技术、安全关键系统',
}


def determine_level(difficulty):
    """根据难度判定开发等级

    Args:
        difficulty: str, 开发难度（low/medium/high/critical）

    Returns:
        str: 开发等级（L1/L2/L3/L4/L5），无效输入返回 None
    """
    return DIFFICULTY_LEVEL_MAP.get(difficulty)


def get_level_label(level):
    """获取开发等级的中文描述"""
    return LEVEL_LABEL_MAP.get(level, level)


def get_difficulty_label(difficulty):
    """获取开发难度的中文描述"""
    return DIFFICULTY_LABEL_MAP.get(difficulty, difficulty)


def build_transit_payload(project_id, difficulty, level, reason=None):
    """构建发送到数据总线中转的 payload（符合 development_level.schema.json）"""
    payload = {
        'project_id': project_id,
        'difficulty': difficulty,
        'level': level,
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    if reason:
        payload['reason'] = reason
    return payload


def assess_requirement(project_id, difficulty, standards=None, verification_items=None):
    """需求导入 → 能力评估（真实逻辑组合）

    - determine_level(): 难度 → 等级（真实判定逻辑）
    - build_transit_payload(): 构建总线 payload
    - 返回可解释结果：level + level_label + reason

    Args:
        project_id: int
        difficulty: str (low/medium/high/critical)
        standards: list[str]，AI/规则匹配到的示例标准（可空）
        verification_items: list[str]，建议验证条目（可空）

    Returns:
        dict: {project_id, difficulty, difficulty_label, level, level_label,
               reason, standards, verification_items}
        无效 difficulty 返回 None
    """
    level = determine_level(difficulty)
    if not level:
        return None

    reason = (f'根据需求难度"{difficulty}"（{get_difficulty_label(difficulty)}）'
              f'自动判定为"{level}"（{get_level_label(level)}）')
    return {
        'project_id': project_id,
        'difficulty': difficulty,
        'difficulty_label': get_difficulty_label(difficulty),
        'level': level,
        'level_label': get_level_label(level),
        'reason': reason,
        'standards': standards or [],
        'verification_items': verification_items or [],
    }
