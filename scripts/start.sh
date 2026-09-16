#!/usr/bin/env bash
# ============================================================
# RM CONTROL — Linux/macOS 启动脚本
# 用法：./scripts/start.sh
# PID 写入 app.pid，stop.sh 按 PID 精确停止。
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

VENV_PY="$ROOT_DIR/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
    echo "[error] 未找到虚拟环境: $VENV_PY"
    echo "请先运行: ./scripts/setup.sh"
    exit 1
fi

mkdir -p logs

# 清旧 PID
if [ -f app.pid ]; then
    OLD=$(cat app.pid 2>/dev/null || echo "")
    if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
        kill "$OLD" 2>/dev/null || true
        sleep 1
    fi
    rm -f app.pid
fi

echo "== 启动 RM CONTROL =="
nohup "$VENV_PY" backend/app.py \
    >> logs/console.log 2>> logs/console_err.log &
PID=$!
echo "$PID" > app.pid
sleep 2

if kill -0 "$PID" 2>/dev/null; then
    echo "[ok] Dashboard 已启动 PID=$PID  http://localhost:8080"
    echo "日志: logs/console.log  /  logs/console_err.log"
else
    echo "[error] 启动失败，请查看 logs/console_err.log"
    rm -f app.pid
    exit 1
fi
