"""IntDevTools Public Demo v2 · 启动入口"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, config

app = create_app()

if __name__ == '__main__':
    print(f"IntDevTools Public Demo v2 后端已启动")
    print(f"  模式: {config.runtime_mode()} ({'BYOK LLM: ' + config.LLM_MODEL if config.llm_configured() else '确定性规则，离线可跑'})")
    print(f"  打开: http://{config.HOST}:{config.PORT}/")
    app.run(host=config.HOST, port=config.PORT, debug=False)
