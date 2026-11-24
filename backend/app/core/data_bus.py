"""数据总线（来自 IntDevTools 07_data_service/modules/transit 的真实逻辑）

- put_transit / get_transit：写入/读取跨工具中转数据
- validate_data：轻量 JSON Schema 校验（draft-07 子集，无 jsonschema 依赖）
- 存储：文件落地（backend/data/transit.json），替换原系统 SQLite，逻辑一致
"""
import json
import os
from datetime import datetime, timezone

from app import config

SCHEMA_FILES = {
    'development_level': 'development_level.schema.json',
    'review_result': 'review_result.schema.json',
    'test_manifest': 'test_manifest.schema.json',
}
VALID_TYPES = set(SCHEMA_FILES.keys())


def _schema_dir() -> str:
    return os.path.join(config.BACKEND_DIR, 'app', 'data', 'schemas')


def _load_schema(type_name: str) -> dict:
    path = os.path.join(_schema_dir(), SCHEMA_FILES[type_name])
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ── 轻量 Schema 校验（draft-07 子集）────────────────────────

def _validate_value(value, schema_def: dict, path: str):
    """校验单个值是否符合 schema 属性定义"""
    expected_type = schema_def.get('type')
    if expected_type == 'string':
        if not isinstance(value, str):
            raise ValueError(f"'{path}': 期望 string, 实际 {type(value).__name__}")
        enum_vals = schema_def.get('enum')
        if enum_vals and value not in enum_vals:
            raise ValueError(f"'{path}': 值 '{value}' 不在允许范围 {enum_vals}")
    elif expected_type == 'integer':
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"'{path}': 期望 integer, 实际 {type(value).__name__}")
    elif expected_type == 'boolean':
        if not isinstance(value, bool):
            raise ValueError(f"'{path}': 期望 boolean, 实际 {type(value).__name__}")
    elif expected_type == 'array':
        if not isinstance(value, list):
            raise ValueError(f"'{path}': 期望 array, 实际 {type(value).__name__}")
        item_schema = schema_def.get('items', {})
        item_props = item_schema.get('properties', {})
        item_required = item_schema.get('required', [])
        item_additional = item_schema.get('additionalProperties', True)
        for idx, item in enumerate(value):
            item_path = f"{path}[{idx}]"
            for req_field in item_required:
                if req_field not in item:
                    raise ValueError(f"'{item_path}' 缺少 required 字段 '{req_field}'")
            for key, val in item.items():
                if key in item_props:
                    _validate_value(val, item_props[key], f"{item_path}.{key}")
                elif not item_additional:
                    raise ValueError(f"'{item_path}' 不允许额外字段 '{key}'")
    elif expected_type == 'object':
        if not isinstance(value, dict):
            raise ValueError(f"'{path}': 期望 object, 实际 {type(value).__name__}")
    elif isinstance(expected_type, list):
        if value is None:
            return
        for t in expected_type:
            if t == 'null':
                continue
            test_schema = dict(schema_def, type=t)
            try:
                _validate_value(value, test_schema, path)
                return
            except ValueError:
                continue
        raise ValueError(f"'{path}': 值不匹配任何允许类型 {expected_type}")


def validate_data(type_name: str, data: dict):
    """按 Schema 校验 data，失败抛 ValueError"""
    schema = _load_schema(type_name)
    required = schema.get('required', [])
    properties = schema.get('properties', {})
    additional = schema.get('additionalProperties', True)

    for field in required:
        if field not in data:
            raise ValueError(f"缺少 required 字段 '{field}'")

    for key, value in data.items():
        if key in properties:
            _validate_value(value, properties[key], key)
        elif not additional:
            raise ValueError(f"不允许额外字段 '{key}'")


# ── 文件存储 ─────────────────────────────────────────────

def _store() -> dict:
    """读取全部 transit 数据 {type: {project_id: {data, updated_at}}}"""
    if not os.path.exists(config.TRANSIT_JSON):
        return {}
    try:
        with open(config.TRANSIT_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(store: dict):
    os.makedirs(config.RUNTIME_DIR, exist_ok=True)
    with open(config.TRANSIT_JSON, 'w', encoding='utf-8') as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _now():
    return datetime.now(timezone.utc).isoformat()


# ── 数据读写 ─────────────────────────────────────────────

def put_transit(type_name: str, project_id: int, data: dict) -> dict:
    """写入 transit 数据（upsert），返回序列化结果"""
    if type_name not in VALID_TYPES:
        raise ValueError(f"无效 transit 类型: '{type_name}'，可选: {sorted(VALID_TYPES)}")
    validate_data(type_name, data)

    store = _store()
    bucket = store.setdefault(type_name, {})
    key = str(project_id)
    record = bucket.get(key)
    if record:
        record['data'] = data
        record['updated_at'] = _now()
    else:
        bucket[key] = {'data': data, 'updated_at': _now()}
    _save(store)
    return _to_dict(type_name, project_id, bucket[key])


def get_transit(type_name: str, project_id: int):
    """读取 transit 数据，返回 dict；不存在返回 None"""
    if type_name not in VALID_TYPES:
        raise ValueError(f"无效 transit 类型: '{type_name}'")
    record = _store().get(type_name, {}).get(str(project_id))
    if not record:
        return None
    return _to_dict(type_name, project_id, record)


def _to_dict(type_name: str, project_id: int, record: dict) -> dict:
    return {
        'type': type_name,
        'project_id': project_id,
        'data': record['data'],
        'updated_at': record.get('updated_at'),
    }


def reset():
    """清空中转数据（演示复位用）"""
    if os.path.exists(config.TRANSIT_JSON):
        os.remove(config.TRANSIT_JSON)
