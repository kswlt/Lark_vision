#!/usr/bin/env bash
# ============================================================
# RM CONTROL — Linux/macOS 一键初始化（首次部署）
# 用法：
#   chmod +x scripts/*.sh
#   ./scripts/setup.sh
# 幂等：已存在 .venv / .env / team.yaml 不会被覆盖。
# ============================================================
set -euo pipefail

# 自动定位项目根目录（不依赖当前 shell 所在目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "== RM CONTROL setup (Linux) =="

# ---------- 1. Python ----------
PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
        if "$c" -c 'import sys; exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
            PY="$c"
            echo "[ok] Python found: $($PY --version) ($PY)"
            break
        fi
    fi
done
if [ -z "$PY" ]; then
    echo "[error] 未找到 Python 3.10+。Ubuntu 安装：sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

# ---------- 2. .venv ----------
if [ ! -x ".venv/bin/python" ]; then
    echo "[..] 创建虚拟环境 .venv ..."
    "$PY" -m venv .venv
fi
VENV_PY="$ROOT_DIR/.venv/bin/python"
echo "[ok] 使用虚拟环境: $VENV_PY"

# ---------- 3. backend 依赖 ----------
echo "[..] 安装 backend/requirements.txt ..."
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r backend/requirements.txt

# ---------- 4. Node ----------
if ! command -v node >/dev/null 2>&1; then
    echo "[error] 未找到 node。Ubuntu 安装：sudo apt install nodejs npm"
    exit 1
fi
echo "[ok] Node found: $(node --version)"

# ---------- 5. frontend 依赖 + build ----------
echo "[..] 安装 frontend 依赖 (npm ci --legacy-peer-deps) ..."
(cd frontend && npm ci --legacy-peer-deps)
echo "[..] 构建 frontend (npm run build) ..."
(cd frontend && npm run build)

# ---------- 6. 配置文件 ----------
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "[ok] 已创建 backend/.env（首次部署默认 DATA_SOURCE=mock, CAMERA_ENABLED=false）"
else
    echo "[skip] backend/.env 已存在，未覆盖"
fi
if [ ! -f "backend/config/team.yaml" ]; then
    cp backend/config/team.example.yaml backend/config/team.yaml
    echo "[ok] 已创建 backend/config/team.yaml"
else
    echo "[skip] backend/config/team.yaml 已存在，未覆盖"
fi

# ---------- 7. 目录 ----------
mkdir -p logs data

echo
echo "== Setup 完成 =="
echo "启动:  ./scripts/start.sh"
echo "停止:  ./scripts/stop.sh"
echo "访问:  http://localhost:8080"
echo "配置:  编辑 backend/.env 切换 DATA_SOURCE=feishu + 填入飞书凭证"
