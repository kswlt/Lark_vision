# -*- coding: utf-8 -*-
"""
飞书多维表格原始记录 -> 前端统一 Task 模型。
所有飞书数据必须先经过这里 normalize，React 不直接理解飞书复杂字段。
同时在这里做受控词清洗：视觉->算法、英雄->重装、通用->None。
"""
from datetime import date, datetime

from config.feishu_fields import (
    FEISHU_FIELDS,
    GROUP_ALIASES,
    PRIORITY_MAP,
    ROBOT_ALIASES,
)


def normalize_field(value):
    """文本字段：兼容纯字符串与富文本数组 [{text:...}]。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = []
        for seg in value:
            if isinstance(seg, dict):
                parts.append(str(seg.get("text", "")))
            else:
                parts.append(str(seg))
        return "".join(parts).strip()
    if isinstance(value, dict):
        return str(value.get("text", "")).strip()
    return str(value).strip()


def normalize_date(value):
    """日期字段：兼容毫秒时间戳 / "YYYY-MM-DD HH:mm" 字符串，统一返回 YYYY-MM-DD。"""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000.0).strftime("%Y-%m-%d")
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        return value.strip()[:10] if len(value.strip()) >= 10 else None
    return None


def normalize_person(value):
    """人员字段：[{id, name, en_name, avatar_url}]，取第一个。"""
    if isinstance(value, list) and value:
        p = value[0]
        if isinstance(p, dict):
            return {
                "id": p.get("id") or p.get("open_id") or p.get("user_id"),
                "name": p.get("name") or p.get("en_name"),
                "avatarUrl": p.get("avatar_url")
                or (p.get("avatar") or {}).get("avatar_72")
                or (p.get("avatar") or {}).get("avatar_240"),
            }
    return None


def normalize_group(value):
    s = normalize_field(value)
    if not s:
        return None
    return GROUP_ALIASES.get(s, s)


def normalize_robot(value):
    s = normalize_field(value)
    if not s:
        return None
    mapped = ROBOT_ALIASES.get(s, s)
    if mapped is None:
        # 通用兵种被禁止 -> 视为未指定
        return None
    return mapped


def normalize_priority(value):
    s = normalize_field(value)
    return PRIORITY_MAP.get(s, "normal")


def normalize_task(record, fields=None):
    fields = fields or FEISHU_FIELDS
    f = record.get("fields", {}) or {}
    rid = record.get("record_id", "")

    def field(key):
        return f.get(fields.get(key), None)

    title = normalize_field(field("title"))
    if not title:
        title = normalize_field(f.get("任务是什么（通俗详细写，严禁用ai）"))

    due = normalize_date(field("due_date"))
    actual = normalize_date(field("actual_finish_date"))
    today = date.today()

    # 延期判断：以表格"是否延期"人工标记为准（✅正常 / 🚨已延期）。
    # 仅当表格无该字段标记时才用 due 超期辅助判断。
    flag = field("overdue")
    flag_text = normalize_field(flag)
    flagged = False
    if isinstance(flag, bool):
        flagged = flag
    elif flag_text:
        flagged = "延期" in flag_text or "逾期" in flag_text
    has_flag = bool(flag) or bool(flag_text)

    if has_flag:
        overdue = flagged
    else:
        # 无人工标记：未完成且超期 -> 延期
        overdue = False
        if due and not actual:
            if (today - date.fromisoformat(due)).days > 0:
                overdue = True

    overdue_days = None
    if overdue and due:
        diff = (today - date.fromisoformat(due)).days
        overdue_days = max(diff, 0)
        # 已完成且实际完成晚于计划：按实际偏差计算
        if actual and actual > due:
            overdue_days = (date.fromisoformat(actual) - date.fromisoformat(due)).days

    person = normalize_person(field("owner"))
    latest = normalize_field(field("latest_update"))
    latest_time = normalize_date(field("latest_update_time"))
    days_since = None
    if latest_time:
        try:
            days_since = (today - date.fromisoformat(latest_time)).days
        except ValueError:
            days_since = None

    # 历史进展：来自"进展历史"字段；若为空则退化为单条最新进展
    history_raw = normalize_field(field("history"))
    history = None
    if history_raw:
        lines = [ln.strip() for ln in history_raw.splitlines() if ln.strip()]
        history = [{"time": None, "text": ln} for ln in lines]
    elif latest:
        history = [{"time": latest_time, "text": latest}]

    task_id = normalize_field(field("id"))
    # 表格"编号"列多数为空或为纯数字占位（如"1"、"2"），不可作为唯一 id
    if not task_id or task_id.isdigit() or len(task_id) < 3:
        task_id = rid or "TASK-000000"
    if not task_id:
        task_id = "TASK-" + (rid[-6:] if rid else "000000")

    return {
        "id": task_id,
        "title": title,
        "group": normalize_group(field("group")),
        "robot": normalize_robot(field("robot")),
        "ownerId": person["id"] if person else None,
        "ownerName": person["name"] if person else None,
        "ownerAvatarUrl": person["avatarUrl"] if person else None,
        "dueDate": due,
        "actualFinishDate": actual,
        "overdue": overdue,
        "overdueDays": overdue_days,
        "priority": normalize_priority(field("priority")),
        "latestUpdate": latest,
        "latestUpdateTime": latest_time,
        "daysSinceUpdate": days_since,
        "dependency": normalize_field(field("dependency")) or None,
        "blocked": bool(field("blocked")) if isinstance(field("blocked"), bool) else False,
        "history": history,
    }
