"""任务聚合测试：空数据、错误字段、计数/排行/分组逻辑。"""
from datetime import date, timedelta

from services import aggregates
from services.feishu.normalize import normalize_task


def _task(**kw):
    t = {
        "id": "T-1", "title": "任务", "group": "算法", "robot": "哨兵",
        "priority": "normal", "overdue": False, "blocked": False,
        "dueDate": None, "actualFinishDate": None, "daysSinceUpdate": None,
        "ownerId": None, "ownerName": None,
    }
    t.update(kw)
    return t


def test_compute_counts_empty():
    c = aggregates.compute_counts([])
    assert c["total"] == 0
    assert c["done"] == 0 and c["overdue"] == 0 and c["critical"] == 0
    assert c["blocked"] == 0 and c["stale"] == 0 and c["dueSoon"] == 0


def test_compute_counts_values():
    tasks = [
        _task(id="1", overdue=True, priority="important_urgent", blocked=True, daysSinceUpdate=5),
        _task(id="2", actualFinishDate=date.today().isoformat()),
        _task(id="3", dueDate=(date.today() + timedelta(days=2)).isoformat()),
    ]
    c = aggregates.compute_counts(tasks)
    assert c["total"] == 3
    assert c["done"] == 1
    assert c["overdue"] == 1
    assert c["critical"] == 1
    assert c["blocked"] == 1
    assert c["stale"] == 1
    assert c["dueSoon"] == 1


def test_compute_highlights_empty():
    assert aggregates.compute_highlights([]) == []
    assert aggregates.compute_timeline([]) == []
    # matrix/robots 返回含机器人骨架的矩阵（每行 total=0），不能崩溃
    m = aggregates.compute_matrix([])
    assert isinstance(m, list) and len(m) > 0
    assert all(all(c["total"] == 0 for c in row["cells"].values()) for row in m)
    g = aggregates.compute_groups([])
    assert isinstance(g, list) and len(g) > 0
    assert all(row["total"] == 0 for row in g)
    r = aggregates.compute_robots([])
    assert isinstance(r, list) and len(r) > 0


def test_compute_groups_filters_unknown():
    """未在 ALLOWED_GROUPS 中的组别不应出现在分组统计里（或至少不崩溃）。"""
    tasks = [
        _task(group="算法"),
        _task(group="电控"),
        _task(group="不存在的组"),
    ]
    groups = aggregates.compute_groups(tasks)
    keys = {g.get("group") for g in groups}
    assert "算法" in keys
    assert "电控" in keys
    assert "不存在的组" not in keys


def test_compute_worktime_leaderboard_empty():
    lb = aggregates.compute_worktime_leaderboard([], "week")
    assert isinstance(lb, list)


def test_normalize_then_aggregate_roundtrip():
    """normalize_task -> compute_counts 全链路不崩溃（错误字段容忍）。"""
    raw = [
        {"record_id": "r1", "fields": {"任务是什么（通俗详细写，严禁用ai）": "x", "组别": "视觉"}},
        {"record_id": "r2", "fields": {}},
        {"record_id": "r3", "fields": {"兵种": "通用", "重要紧急程度": "超紧急限时"}},
    ]
    tasks = [normalize_task(r) for r in raw]
    assert tasks[0]["group"] == "算法"  # 视觉 -> 算法
    assert tasks[1]["group"] is None
    assert tasks[2]["robot"] is None  # 通用 -> None
    c = aggregates.compute_counts(tasks)
    assert c["total"] == 3
