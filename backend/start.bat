@echo off
rem IntDevTools Public Demo v2 · 一键启动（Windows）
cd /d "%~dp0"
if not exist .venv (
  echo [1/3] 创建虚拟环境 .venv ...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo [2/3] 安装依赖 ...
python -m pip install -r requirements.txt
echo [3/3] 启动服务 (http://127.0.0.1:8000/)
python run.py
