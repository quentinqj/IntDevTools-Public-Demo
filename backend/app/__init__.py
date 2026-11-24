"""IntDevTools Public Demo v2 · Flask 应用工厂

单进程同时提供：
- API（/api/...，4 个真实组件：开发等级 / 设计审查 / 评价基准 / 数据总线）
- 静态前端（仓库根 demo/index.html）
"""
import os

from flask import Flask, request

from app import config


def create_app():
    app = Flask(
        __name__,
        static_folder=config.REPO_ROOT,
        static_url_path='',
    )
    app.config['JSON_AS_ASCII'] = False

    from app.routes import api_bp
    app.register_blueprint(api_bp)

    # 简单 CORS（允许本地 file:// 直接调用 API）
    @app.after_request
    def add_cors(resp):
        if request.path.startswith('/api/'):
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

    # 根路径重定向到演示页
    @app.route('/')
    def index():
        from flask import redirect
        return redirect('/demo/index.html')

    return app
