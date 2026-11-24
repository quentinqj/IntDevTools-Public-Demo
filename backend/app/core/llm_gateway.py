"""统一 LLM 网关（BYOK，来自 IntDevTools 02_prereview/core/llm 的真实逻辑裁剪版）

- 未配置 LLM_API_KEY → 不初始化（规则模式）
- 配置后：chat() 调用兼容 OpenAI 的 /chat/completions
- chat_json()：解析 + 修复 LLM 返回的 JSON（截断/包裹等常见问题）
"""
import json
import logging
import re

import requests

from app import config

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM 调用异常"""


def _repair_json(content: str):
    """尝试修复 LLM 返回的 JSON（截断/未闭合/包裹）"""
    if content is None:
        return None
    content = content.strip()
    if not content:
        return None

    # 1. 代码块提取
    blocks = re.findall(r'```(?:json)?\s*\n?(.*?)```', content, re.DOTALL)
    for block in reversed(blocks):
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            continue

    # 2. 数组截断：截到最后一个完整对象，闭合数组
    if content.startswith('['):
        try:
            brace = 0
            last_end = -1
            for i, ch in enumerate(content):
                if ch == '{':
                    brace += 1
                elif ch == '}':
                    brace -= 1
                    if brace == 0:
                        last_end = i
            if last_end > 0:
                fixed = content[:last_end + 1] + ']'
                return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    # 3. 直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 4. 补闭合符
    for suffix in ['"}]', '"}', '}', ']']:
        try:
            return json.loads(content + suffix)
        except json.JSONDecodeError:
            continue
    return None


def _extract_json_content(text: str):
    """从 LLM 输出文本中提取 JSON"""
    # 优先找 ```json``` 块
    blocks = re.findall(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    for block in reversed(blocks):
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            continue
    # 再找整个内容
    return _repair_json(text)


class LLMGateway:
    """统一网关：endpoint + model + key（从环境变量读取，绝不落盘）"""

    def __init__(self):
        self.base_url = config.LLM_BASE_URL
        self.model = config.LLM_MODEL
        self.api_key = config.LLM_API_KEY
        self.timeout = config.LLM_TIMEOUT

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages, temperature=0.1, max_tokens=2048):
        """调用 chat/completions，返回 content 文本"""
        if not self.available():
            raise LLMError('未配置 LLM_API_KEY（BYOK 模式）')
        url = f"{self.base_url}/chat/completions"
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            content = data['choices'][0]['message']['content']
            if not content:
                reasoning = data['choices'][0].get('message', {}).get('reasoning_content', '')
                content = reasoning or ''
            return content
        except requests.RequestException as e:
            raise LLMError(f'LLM HTTP 调用失败: {e}') from e
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError(f'LLM 响应解析失败: {e}') from e

    def chat_json(self, messages, temperature=0.1):
        """调用 LLM 并解析 JSON（含修复）"""
        text = self.chat(messages, temperature=temperature)
        parsed = _extract_json_content(text)
        if parsed is None:
            raise LLMError('LLM 返回内容无法解析为 JSON')
        # 归一化：期望数组
        if isinstance(parsed, dict):
            list_keys = [k for k, v in parsed.items() if isinstance(v, list)]
            if len(list_keys) == 1 and len(parsed) == 1:
                return parsed[list_keys[0]]
            return [parsed]
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
        return []


def get_gateway() -> LLMGateway:
    """返回网关实例（未配置 key 时 available()==False）"""
    return LLMGateway()
