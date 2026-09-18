"""Camera / face-checkin 鉴权测试（不需要真实相机，内部相机服务不可达时优雅降级）。

覆盖：
- CAMERA_PUBLIC=false：无 token -> 401；错误 token -> 403；正确 token -> 通过
- viewer session cookie：POST /api/viewer/session 建 cookie 后自动通过
- CAMERA_PUBLIC=true：无需 token
- face-latest / face-checkin / camera/status 等端点权限一致
- query token 仅作 Legacy 兼容保留
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATA_SOURCE", "mock")

import app as app_module


@pytest.fixture()
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def _private_env(monkeypatch):
    """CAMERA_PUBLIC=false + 仅配置 VIEWER_TOKEN（隔离 ADMIN_TOKEN 干扰）。"""
    monkeypatch.setattr(app_module, "CAMERA_PUBLIC", False)
    monkeypatch.setattr(app_module, "VIEWER_TOKEN", "viewer-token-1")
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "")


PROTECTED_PATHS = [
    "/api/camera/status",
    "/api/camera/frame",
    "/api/camera/stream",
    "/api/attendance/face-latest",
    "/api/attendance/face-checkin",
]


def test_private_no_token_401(client, monkeypatch):
    _private_env(monkeypatch)
    for path in PROTECTED_PATHS:
        r = client.get(path)
        assert r.status_code == 401, f"{path} 无 token 应 401，实际 {r.status_code}"


def test_private_wrong_token_403(client, monkeypatch):
    _private_env(monkeypatch)
    for path in PROTECTED_PATHS:
        r = client.get(path, headers={"Authorization": "Bearer wrong-token"})
        assert r.status_code == 403, f"{path} 错误 token 应 403，实际 {r.status_code}"


def test_private_correct_viewer_token_bearer(client, monkeypatch):
    _private_env(monkeypatch)
    for path in PROTECTED_PATHS:
        r = client.get(path, headers={"Authorization": "Bearer viewer-token-1"})
        assert r.status_code == 200, f"{path} 正确 Bearer token 应通过，实际 {r.status_code}"


def test_private_admin_token_also_allowed(client, monkeypatch):
    monkeypatch.setattr(app_module, "CAMERA_PUBLIC", False)
    monkeypatch.setattr(app_module, "VIEWER_TOKEN", "viewer-token-1")
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "admin-token-1")
    r = client.get("/api/camera/status", headers={"Authorization": "Bearer admin-token-1"})
    assert r.status_code == 200


def test_private_legacy_query_token_still_works(client, monkeypatch):
    """query token 仅作 Legacy 兼容保留，不删除旧用法。"""
    _private_env(monkeypatch)
    r = client.get("/api/camera/status?token=viewer-token-1")
    assert r.status_code == 200


def test_public_no_token_allowed(client, monkeypatch):
    monkeypatch.setattr(app_module, "CAMERA_PUBLIC", True)
    monkeypatch.setattr(app_module, "VIEWER_TOKEN", "viewer-token-1")
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "")
    for path in PROTECTED_PATHS:
        r = client.get(path)
        assert r.status_code == 200, f"{path} CAMERA_PUBLIC=true 应放行，实际 {r.status_code}"


# ---------------- viewer session cookie ----------------

def test_session_rejects_missing_token(client, monkeypatch):
    _private_env(monkeypatch)
    r = client.post("/api/viewer/session", json={})
    assert r.status_code == 400


def test_session_rejects_wrong_token(client, monkeypatch):
    _private_env(monkeypatch)
    r = client.post("/api/viewer/session", json={"token": "wrong"})
    assert r.status_code == 403
    assert "Set-Cookie" not in r.headers


def test_session_rejects_when_no_tokens_configured(client, monkeypatch):
    monkeypatch.setattr(app_module, "CAMERA_PUBLIC", False)
    monkeypatch.setattr(app_module, "VIEWER_TOKEN", "")
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "")
    r = client.post("/api/viewer/session", json={"token": "anything"})
    assert r.status_code == 503  # 未配置任何 token，明确拒绝而非静默放行


def test_session_cookie_grant_access(client, monkeypatch):
    _private_env(monkeypatch)
    r = client.post("/api/viewer/session", json={"token": "viewer-token-1"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"
    assert "Set-Cookie" in r.headers
    # test_client 自动携带 cookie：所有受保护端点应直接通过，无需 Header/query
    for path in PROTECTED_PATHS:
        r2 = client.get(path)
        assert r2.status_code == 200, f"{path} 带 session cookie 应通过，实际 {r2.status_code}"


def test_session_cookie_is_http_only(client, monkeypatch):
    _private_env(monkeypatch)
    r = client.post("/api/viewer/session", json={"token": "viewer-token-1"})
    set_cookie = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie


def test_face_checkin_contains_names_only_when_authorized(client, monkeypatch):
    """face-checkin 含成员身份数据：未授权 401，授权后返回名单结构。"""
    _private_env(monkeypatch)
    r = client.get("/api/attendance/face-checkin")
    assert r.status_code == 401
    r2 = client.get(
        "/api/attendance/face-checkin", headers={"Authorization": "Bearer viewer-token-1"}
    )
    assert r2.status_code == 200
    d = r2.get_json()
    assert "names" in d and "date" in d  # 无真实打卡记录时返回空名单，绝不 500
