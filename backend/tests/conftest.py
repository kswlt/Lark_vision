"""pytest 全局配置：确保 backend 目录在 sys.path，测试统一使用 mock 数据源。"""
import os
import sys

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# 关键：清除真实飞书凭证环境变量，避免 import app 时从 backend/.env 加载真实配置
# （测试绝不依赖真实飞书账号 / Secret / 网络）
for _k in [k for k in os.environ if k.startswith("FEISHU_") or k == "DATA_SOURCE"]:
    os.environ.pop(_k, None)

# 测试默认显式 mock 数据源（不依赖真实飞书凭证/网络）
os.environ.setdefault("DATA_SOURCE", "mock")
os.environ.setdefault("FEISHU_WORKTIME_SOURCE", "mock")
