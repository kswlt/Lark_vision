#!/usr/bin/env bash
# ============================================================
# RM CONTROL — Linux/macOS 停止脚本（按 PID 精确停止）
# 优先 app.pid；无 PID 文件时按 8080 端口定位监听进程。
# 不会 pkill python 误杀其它进程。
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ -f app.pid ]; then
    PID_=$(cat app.pid 2>/dev/null || echo "")
    if [ -n "$PID_" ] && kill -0 "$PID_" 2>/dev/null; then
        kill "$PID_" 2>/dev/null || true
        sleep 1
        # 仍在则强杀
        if kill -0 "$PID_" 2>/dev/null; then
            kill -9 "$PID_" 2>/dev/null || true
        fi
        echo "[ok] 已停止 PID=$PID_"
    else
        echo "[warn] PID=$PID_ 未在运行"
    fi
    rm -f app.pid
    exit 0
fi

# fallback: 按 8080 端口定位
if command -v fuser >/dev/null 2>&1; then
    if fuser -k 8080/tcp 2>/dev/null; then
        echo "[ok] 已停止监听 8080 的进程"
        exit 0
    fi
fi
if command -v ss >/dev/null 2>&1; then
    PID_=$(ss -ltnp 2>/dev/null | awk '/:8080 /{print $0}' | grep -oP 'pid=\K[0-9]+' | head -n1 || true)
    if [ -n "$PID_" ]; then
        kill "$PID_" 2>/dev/null || true
        echo "[ok] 已停止 PID=$PID_（监听 8080）"
        exit 0
    fi
fi
echo "[warn] 未找到运行中的 Dashboard 进程"
