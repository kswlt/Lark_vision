# ============================================================
# RM CONTROL — 单容器 Dockerfile（multi-stage）
# Stage 1: Node 构建前端 → dist/
# Stage 2: Python 运行时 + backend + dist/
# 默认 Mock 模式（无需飞书/相机），真实配置通过 .env 或环境变量注入。
# ============================================================

# ---------- Stage 1: frontend build ----------
# Node 22 LTS：与 GitHub Actions (actions/setup-node@v4, node-version: 22) 保持一致，
# 避免 jsdom / undici 等依赖在 Node 20 下的 EBADENGINE engine mismatch。
FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
RUN npm run build
# 产物在 /build/dist/

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_SOURCE=mock \
    CAMERA_ENABLED=false \
    HOST=0.0.0.0 \
    PORT=8080

WORKDIR /app

# 核心后端依赖（不含摄像头/人脸识别）
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 后端源码 + 前端产物
COPY backend/ /app/backend/
COPY --from=frontend /build/dist/ /app/dist/

# 非 root 运行
RUN useradd -r -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=5).status==200 else 1)" || exit 1

CMD ["python", "backend/app.py"]
