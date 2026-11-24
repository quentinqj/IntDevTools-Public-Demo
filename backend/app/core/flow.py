"""运行态流状态（backend/data/flow_state.json，已 gitignore）

记录演示链路中间态：审查草稿（未确认发现）与逐条确认结果。
确认后的正式数据写入数据总线（transit），此处只保存确认选择。
"""
import json
import os

from app import config


def _ensure_runtime():
    os.makedirs(config.RUNTIME_DIR, exist_ok=True)


def _load() -> dict:
    if not os.path.exists(config.FLOW_STATE_JSON):
        return {}
    try:
        with open(config.FLOW_STATE_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(state: dict):
    _ensure_runtime()
    with open(config.FLOW_STATE_JSON, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _proj(state, project_id) -> dict:
    return state.setdefault(str(project_id), {})


def set_review_draft(project_id, findings):
    state = _load()
    bucket = _proj(state, project_id)
    bucket['review_draft'] = findings
    bucket['confirmations'] = {}
    _save(state)


def get_review_draft(project_id):
    state = _load()
    return state.get(str(project_id), {}).get('review_draft') or []


def set_confirmations(project_id, confirmations):
    """保存逐条确认结果 {finding_id: adopt|reject}"""
    state = _load()
    bucket = _proj(state, project_id)
    bucket['confirmations'] = confirmations
    _save(state)
    return confirmations


def get_confirmations(project_id):
    state = _load()
    return state.get(str(project_id), {}).get('confirmations') or {}


def reset():
    """清空流状态（演示复位用）"""
    if os.path.exists(config.FLOW_STATE_JSON):
        os.remove(config.FLOW_STATE_JSON)
