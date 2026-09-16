"""Flask API 测试：health API、管理员鉴权（无 Token 拒绝）、静态路由。"""
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


def test_health_api(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    d = r.get_json()
    assert d["status"] == "ok"
    assert d["data_source"] == "mock"
    assert "feishu" in d
    assert "cache_age" in d
    assert "last_success_sync" in d
    assert "stale" in d


def test_admin_api_rejected_without_token(client, monkeypatch):
    """未配置 ADMIN_TOKEN 时，管理接口必须被拒绝（503），防止误开放。"""
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "")
    r = client.post("/api/admin/checkin/sync")
    assert r.status_code == 503
    r2 = client.post("/api/admin/attendance/sync")
    assert r2.status_code == 503


def test_admin_api_wrong_token(client, monkeypatch):
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "secret-token-1")
    r = client.post("/api/admin/checkin/sync", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_admin_api_correct_token(client, monkeypatch):
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "secret-token-1")
    # 飞书未配置 -> 鉴权通过但返回明确业务错误，而不是静默成功
    monkeypatch.setattr(app_module.store, "client", None)
    monkeypatch.setattr(app_module.store, "feishu_configured", False)
    r = client.post("/api/admin/checkin/sync", headers={"Authorization": "Bearer secret-token-1"})
    assert r.status_code == 503  # 飞书未配置 -> 503 Service Unavailable
    d = r.get_json()
    assert d["status"] == "error"  # 明确提示飞书未配置，而不是静默成功


def test_old_sync_get_route_removed(client):
    """旧的 GET /api/checkin/sync 必须已移除（GET=读取，修改状态必须 POST）。"""
    r = client.get("/api/checkin/sync")
    assert r.status_code == 404


def test_dashboard_apis(client):
    assert client.get("/api/tasks").status_code == 200
    assert client.get("/api/dashboard").status_code == 200
    assert client.get("/api/groups").status_code == 200
    assert client.get("/api/robots").status_code == 200
    assert client.get("/api/people").status_code == 200
    assert client.get("/api/duty").status_code == 200


def test_meta_api_returns_team_config(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data["teamName"], str) and data["teamName"]
    assert isinstance(data["groups"], list) and len(data["groups"]) > 0
    assert isinstance(data["robots"], list) and len(data["robots"]) > 0
    assert isinstance(data["groupAliases"], dict)
    assert isinstance(data["robotAliases"], dict)
    assert isinstance(data["priorityLabels"], dict)


def test_unknown_api_404_json(client):
    r = client.get("/api/nonexistent")
    assert r.status_code == 404
    assert r.is_json


def test_dist_not_built_message(client):
    """首页路由不崩溃：dist 已构建则返回 index.html(200)，未构建则返回 503 明确提示。"""
    r = client.get("/")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.data
    else:
        assert r.is_json
        assert r.get_json().get("status") == "error"
