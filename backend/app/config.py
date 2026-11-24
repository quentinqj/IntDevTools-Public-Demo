"""IntDevTools Public Demo v2 · 后端配置

路径与运行参数。环境变量可覆盖：
  PORT          API 端口（默认 8000）
  LLM_API_KEY   BYOK：设置后审查引擎的 "other" 规则走真实 LLM
  LLM_BASE_URL  兼容 OpenAI 的接口地址（默认 https://api.openai.com/v1）
  LLM_MODEL     模型名（默认 gpt-4o-mini）
"""
import os

# ── 目录定位 ──────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPO_ROOT = os.path.dirname(BACKEND_DIR)                                   # 仓库根
APP_DIR = os.path.join(BACKEND_DIR, 'app')
DEMO_DATA = os.path.join(REPO_ROOT, 'demo-data')
PROJECT_DIR = os.path.join(DEMO_DATA, 'project_sc2026')
KB_DIR = os.path.join(DEMO_DATA, 'kb')

# ── 输入数据（真实读取 demo-data 下的样例文件） ─────────────
REQUIREMENTS_CSV = os.path.join(PROJECT_DIR, 'requirements.csv')
DESIGN_DOC_MD = os.path.join(PROJECT_DIR, 'syra_design.md')
PROJECT_MD = os.path.join(PROJECT_DIR, 'project.md')
STANDARDS_MD = os.path.join(KB_DIR, '10_standards.md')

# ── 引擎配置（公开版，通用产品大类，无真实产品数据） ─────────
RULES_JSON = os.path.join(APP_DIR, 'data', 'review_rules.json')
PRODUCT_TYPES_JSON = os.path.join(APP_DIR, 'data', 'product_types.json')
EVAL_CATEGORIES_JSON = os.path.join(APP_DIR, 'data', 'evaluation_categories.json')
KB_SEED_JSON = os.path.join(APP_DIR, 'data', 'kb_seed.json')

# ── 运行时存储（backend/data/ 已 gitignore） ───────────────
RUNTIME_DIR = os.path.join(BACKEND_DIR, 'data')
TRANSIT_JSON = os.path.join(RUNTIME_DIR, 'transit.json')
FLOW_STATE_JSON = os.path.join(RUNTIME_DIR, 'flow_state.json')
KB_ENTRIES_JSON = os.path.join(RUNTIME_DIR, 'kb_entries.json')

# ── 服务参数 ─────────────────────────────────────────────
PORT = int(os.environ.get('PORT', '8000'))
HOST = '127.0.0.1'

# ── LLM（BYOK，绝不提交 key） ────────────────────────────
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o-mini')
LLM_TIMEOUT = int(os.environ.get('LLM_TIMEOUT', '30'))

def llm_configured() -> bool:
    return bool(LLM_API_KEY)

def runtime_mode() -> str:
    return 'llm' if llm_configured() else 'rules'
