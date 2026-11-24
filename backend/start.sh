#!/usr/bin/env bash
# IntDevTools Public Demo v2 · 一键启动（macOS / Linux）
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "[1/3] 创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "[2/3] 安装依赖 ..."
pip install -r requirements.txt
echo "[3/3] 启动服务 (http://127.0.0.1:8000/)"
python run.py
