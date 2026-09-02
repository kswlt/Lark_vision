# -*- coding: utf-8 -*-
"""
从 Task[] 与工时记录聚合出 Dashboard / Groups / Robots / Matrix / Leaderboard / People。
不维护独立进度字段，全部由任务数据现算，避免数据不一致。
"""
from datetime import date, timedelta

from config.feishu_fields import ALLOWED_GROUPS, ALLOWED_ROBOTS


def _today():
    return date.today()


def _due_soon(task, horizon=7):
    due = task.get("dueDate")
    if not due or task.get("overdue") or task.get("actualFinishDate"):
        return False
    try:
        diff = (date.fromisoformat(due) - _today()).days
    except (ValueError, TypeError):
        return False
    return 0 <= diff <= horizon


def compute_counts(tasks):
    return {
        "total": len(tasks),
        "done": sum(1 for t in tasks if t.get("actualFinishDate")),
        "overdue": sum(1 for t in tasks if t.get("overdue")),
        "critical": sum(1 for t in tasks if t.get("priority") == "important_urgent"),
        "blocked": sum(1 for t in tasks if t.get("blocked")),
        "stale": sum(1 for t in tasks if (t.get("daysSinceUpdate") or 0) >= 3),
        "dueSoon": sum(1 for t in tasks if _due_soon(t)),
    }


def compute_trend(tasks, days=14):
    """近 N 天任务完成趋势：按实际完成日期统计当日完成数与累计完成数。"""
    today = _today()
    buckets = []
    idx = {}
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        key = d.isoformat()
        b = {"date": d.strftime("%m.%d"), "done": 0, "cum": 0}
        buckets.append(b)
        idx[key] = b
    for t in tasks:
        af = t.get("actualFinishDate")
        if not af:
            continue
        try:
            dd = date.fromisoformat(af)
        except (ValueError, TypeError):
            continue
        b = idx.get(dd.isoformat())
        if b is not None:
            b["done"] += 1
    running = 0
    for b in buckets:
        running += b["done"]
        b["cum"] = running
    return buckets



def compute_milestones(season_milestones):
    today = _today()
    out = []
    for m in season_milestones:
        try:
            d = date.fromisoformat(m["date"])
        except (ValueError, TypeError):
            continue
        days = (d - today).days
        out.append({
            "id": m["id"],
            "name": m["name"],
            "date": m["date"],
            "daysLeft": days,
            "overdue": days < 0,
        })
    return out


def _highlight_score(t):
    s = 0
    if t.get("blocked"):
        s += 100
    if t.get("overdue"):
        s += 50 + (t.get("overdueDays") or 0)
    if t.get("priority") == "important_urgent":
        s += 30
    elif t.get("priority") == "important":
        s += 10
    s += (t.get("daysSinceUpdate") or 0) * 2
    return s


def compute_highlights(tasks, limit=8):
    active = [t for t in tasks if not t.get("actualFinishDate")]
    active.sort(key=_highlight_score, reverse=True)
    return active[:limit]


def compute_timeline(tasks, horizon=7):
    out = []
    for t in tasks:
        if t.get("actualFinishDate"):
            continue
        due = t.get("dueDate")
        if not due:
            continue
        try:
            diff = (date.fromisoformat(due) - _today()).days
        except (ValueError, TypeError):
            continue
        if 0 <= diff <= horizon:
            out.append(t)
    out.sort(key=lambda t: (t.get("dueDate") or "9999", t.get("id") or ""))
    return out


def compute_matrix(tasks):
    robots = list(ALLOWED_ROBOTS) + [None]
    rows = {r: {g: {"total": 0, "overdue": 0} for g in ALLOWED_GROUPS} for r in robots}
    for t in tasks:
        g = t.get("group")
        r = t.get("robot")
        if g not in ALLOWED_GROUPS:
            continue
        if r not in rows:
            rows[r] = {gg: {"total": 0, "overdue": 0} for gg in ALLOWED_GROUPS}
        rows[r][g]["total"] += 1
        if t.get("overdue"):
            rows[r][g]["overdue"] += 1
    return [{"robot": r, "cells": rows[r]} for r in rows]


def compute_groups(tasks):
    out = []
    for g in ALLOWED_GROUPS:
        gt = [t for t in tasks if t.get("group") == g]
        out.append({
            "group": g,
            "total": len(gt),
            "overdue": sum(1 for t in gt if t.get("overdue")),
            "critical": sum(1 for t in gt if t.get("priority") == "important_urgent"),
            "blocked": sum(1 for t in gt if t.get("blocked")),
            "stale": sum(1 for t in gt if (t.get("daysSinceUpdate") or 0) >= 3),
        })
    return out


def compute_robots(tasks):
    robot_keys = list(ALLOWED_ROBOTS) + [None]
    out = []
    for r in robot_keys:
        rt = [t for t in tasks if t.get("robot") == r]
        out.append({
            "robot": r if r else "none",
            "total": len(rt),
            "done": sum(1 for t in rt if t.get("actualFinishDate")),
            "overdue": sum(1 for t in rt if t.get("overdue")),
            "critical": sum(1 for t in rt if t.get("priority") == "important_urgent"),
            "blocked": sum(1 for t in rt if t.get("blocked")),
            "stale": sum(1 for t in rt if (t.get("daysSinceUpdate") or 0) >= 3),
            "dueSoon": sum(1 for t in rt if _due_soon(t)),
        })
    return out


def _week_start(today):
    return today - timedelta(days=today.weekday())


def _month_start(today):
    return today.replace(day=1)


def _sum_range(records, start):
    acc = {}
    for rec in records:
        try:
            d = date.fromisoformat(rec["date"])
        except (ValueError, TypeError):
            continue
        if d < start:
            continue
        uid = rec["userId"]
        if uid not in acc:
            acc[uid] = {
                "userId": uid,
                "userName": rec.get("userName"),
                "group": rec.get("group"),
                "avatarUrl": rec.get("avatarUrl"),
                "minutes": 0,
            }
        acc[uid]["minutes"] += int(rec.get("durationMinutes") or 0)
    return acc


def compute_worktime_leaderboard(records, range_key, limit=10):
    today = _today()
    start = _week_start(today) if range_key == "week" else _month_start(today)
    acc = _sum_range(records, start)
    out = []
    for uid, info in acc.items():
        out.append({
            "userId": uid,
            "userName": info["userName"] or uid,
            "group": info["group"],
            "avatarUrl": info["avatarUrl"],
            "weekMinutes": info["minutes"] if range_key == "week" else 0,
            "monthMinutes": 0 if range_key == "week" else info["minutes"],
        })
    out.sort(key=lambda x: x["weekMinutes"] + x["monthMinutes"], reverse=True)
    return out[:limit]


def compute_worktime_people(records):
    """返回每人本周/本月工时（用于 People 页）。"""
    today = _today()
    ws, ms = _week_start(today), _month_start(today)
    wacc = _sum_range(records, ws)
    macc = _sum_range(records, ms)
    uids = set(list(wacc.keys()) + list(macc.keys()))
    out = []
    for uid in uids:
        w = wacc.get(uid, {})
        m = macc.get(uid, {})
        out.append({
            "userId": uid,
            "userName": (w.get("userName") or m.get("userName")) or uid,
            "group": w.get("group") or m.get("group"),
            "avatarUrl": w.get("avatarUrl") or m.get("avatarUrl"),
            "weekMinutes": w.get("minutes", 0),
            "monthMinutes": m.get("minutes", 0),
        })
    out.sort(key=lambda x: x["monthMinutes"], reverse=True)
    return out


def compute_people(worktime_people, tasks):
    """People 页：工时 + 任务归属。"""
    by_owner = {}
    for t in tasks:
        if t.get("actualFinishDate"):
            continue
        oid = t.get("ownerId")
        if not oid:
            continue
        by_owner.setdefault(oid, {"active": 0, "overdue": 0})
        by_owner[oid]["active"] += 1
        if t.get("overdue"):
            by_owner[oid]["overdue"] += 1

    out = []
    for p in worktime_people:
        o = by_owner.get(p["userId"], {"active": 0, "overdue": 0})
        out.append({
            "userId": p["userId"],
            "userName": p["userName"],
            "group": p["group"],
            "avatarUrl": p["avatarUrl"],
            "weekMinutes": p["weekMinutes"],
            "monthMinutes": p["monthMinutes"],
            "activeTasks": o["active"],
            "overdueTasks": o["overdue"],
        })
    out.sort(key=lambda x: x["monthMinutes"], reverse=True)
    return out
