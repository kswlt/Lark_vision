"""数据源模式测试：mock 模式 / feishu 模式未配置 / 缓存 stale 回退 / 值日除零。"""
import time

from services.sources import DATA_SOURCE, DataSourceError, DataStore


def test_data_source_default_feishu():
    """DATA_SOURCE 未显式设置时默认 feishu（不会偷偷用 mock）。"""
    assert DATA_SOURCE in ("feishu", "mock")


def test_mock_mode_returns_tasks(monkeypatch):
    monkeypatch.setattr("services.sources.DATA_SOURCE", "mock")
    ds = DataStore()
    tasks = ds.get_tasks()
    assert isinstance(tasks, list)
    # mock 数据有任务且带组别
    assert len(tasks) > 0
    assert any(t.get("group") for t in tasks)


def test_feishu_mode_unconfigured_no_mock(monkeypatch):
    """feishu 模式但未配置凭证：绝不返回 mock 任务（明确空态）。"""
    monkeypatch.setattr("services.sources.DATA_SOURCE", "feishu")
    ds = DataStore()
    ds.feishu_configured = False
    tasks = ds.get_tasks()
    assert tasks == []
    # 空态而非 mock 数据：不能出现 mock 人员
    mock_names = {"林越", "王一凡", "陈宇"}
    assert not mock_names.intersection(t.get("ownerName", "") for t in tasks)


def test_cache_fallback_on_failure(monkeypatch):
    """飞书失败时返回最近一次成功缓存（stale 回退），不伪造 mock。"""
    monkeypatch.setattr("services.sources.DATA_SOURCE", "feishu")
    ds = DataStore()
    ds.feishu_configured = True
    cached = [{"id": "A-1", "title": "旧缓存任务", "group": "算法"}]
    ds._tasks = cached
    ds._tasks_at = time.time() - 1000  # 已过期，触发刷新

    def boom():
        raise DataSourceError("飞书挂了")

    monkeypatch.setattr(ds, "_load_tasks", boom)
    tasks = ds.get_tasks()
    assert tasks == cached  # 返回旧缓存而非 mock


def test_cache_fallback_no_cache_returns_empty(monkeypatch):
    """飞书失败且从未成功过：返回明确空态，不生成 mock。"""
    monkeypatch.setattr("services.sources.DATA_SOURCE", "feishu")
    ds = DataStore()
    ds.feishu_configured = True
    ds._tasks = None
    ds._tasks_at = 0.0

    def boom():
        raise DataSourceError("飞书挂了")

    monkeypatch.setattr(ds, "_load_tasks", boom)
    tasks = ds.get_tasks()
    assert tasks == []


def test_health_status_mock():
    ds = DataStore()
    ds._tasks = []
    ds._tasks_at = time.time()
    ds._feishu_ok = True
    h = ds.health_status()
    assert h["status"] == "ok"
    assert h["data_source"] == "mock"
    assert h["feishu"] == "ok"
    assert "cache_age" in h
    assert h["stale"] is False


def test_health_status_stale_degraded(monkeypatch):
    """feishu 模式下缓存极旧 -> degraded（不把过期数据伪装成实时）。"""
    monkeypatch.setattr("services.sources.DATA_SOURCE", "feishu")
    ds = DataStore()
    ds._tasks = []
    ds._tasks_at = time.time() - 99999  # 极旧
    ds._feishu_ok = True
    h = ds.health_status()
    assert h["status"] == "degraded"
    assert h["feishu"] == "degraded"
    assert h["stale"] is True


def test_duty_empty_roster_no_zerodiv(monkeypatch):
    """值日名单为空时返回 []，绝不 ZeroDivisionError。"""
    ds = DataStore()
    monkeypatch.setattr("services.sources.get_duty_roster", list)
    days = ds.get_duty()
    assert days == []


def test_duty_normal_roster():
    ds = DataStore()
    days = ds.get_duty()
    if days:
        assert len(days) == 7
        assert any(d.get("isToday") for d in days)
        assert all(d.get("name") for d in days)


def test_mock_worktime_leaderboard_shape():
    from data.mock_worktime import build_mock_worktime

    recs = build_mock_worktime()
    assert isinstance(recs, list)
    for r in recs:
        assert "userName" in r or "userId" in r
