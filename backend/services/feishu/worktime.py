# -*- coding: utf-8 -*-
"""
工时数据来源与清洗。
统一输出记录模型：
  {userId, userName, group, date, checkInTime, checkOutTime, durationMinutes, avatarUrl}
异常记录（没下班打卡/重复/负时间/异常超长/跨天异常/空 user）一律不进榜，只写日志，绝不 500。
"""
import logging
import threading
import time
from datetime import datetime

from config.feishu_fields import FEISHU_WORKTIME_FIELDS
from config.duty import get_unchecked_monitor

logger = logging.getLogger("feishu")

MAX_DAILY_MINUTES = 16 * 60  # 单日超过 16h 视为异常
MIN_DAILY_MINUTES = 1

# 全量用户列表缓存（避免每次考勤刷新都拉通讯录）
_USER_IDS_CACHE = {"ids": None, "at": 0.0}
_USER_IDS_TTL = 30 * 60
_USER_IDS_LOCK = threading.Lock()


def _fetch_all_user_ids(client):
    """从通讯录拉取全部成员 user_id（一级部门 + 子部门递归），带 30min 缓存。"""
    now = time.time()
    with _USER_IDS_LOCK:
        if _USER_IDS_CACHE["ids"] and now - _USER_IDS_CACHE["at"] < _USER_IDS_TTL:
            return _USER_IDS_CACHE["ids"]
    ids = []
    seen = set()

    def walk(did):
        page_token = None
        while True:
            params = {
                "department_id": did,
                "user_id_type": "user_id",
                "department_id_type": "open_department_id",
                "page_size": 50,
            }
            if page_token:
                params["page_token"] = page_token
            data = client.get("/open-apis/contact/v3/users/find_by_department", params)
            for u in (data.get("items") or []):
                uid = u.get("user_id")
                if uid and uid not in seen:
                    seen.add(uid)
                    ids.append(uid)
            # 子部门
            for sd in (data.get("departments") or []):
                sid = sd.get("open_department_id")
                if sid:
                    walk(sid)
            if data.get("has_more") and data.get("page_token"):
                page_token = data["page_token"]
            else:
                break

    try:
        data = client.get(
            "/open-apis/contact/v3/departments",
            {"parent_department_id": "0", "department_id_type": "open_department_id"},
        )
        depts = [d.get("open_department_id") for d in (data.get("items") or [])] or ["0"]
        for did in depts:
            walk(did)
    except Exception as e:  # noqa: BLE001
        logger.warning("worktime: 拉取通讯录用户失败: %s", e)
        return []
    with _USER_IDS_LOCK:
        _USER_IDS_CACHE["ids"] = ids
        _USER_IDS_CACHE["at"] = now
    logger.info("worktime: 通讯录用户 %d 人", len(ids))
    return ids


def clean_record(rec):
    if not rec.get("userId"):
        logger.warning("worktime: 空 user 记录，丢弃 %s", rec)
        return None
    dur = rec.get("durationMinutes")
    if dur is None or dur <= 0 or dur > MAX_DAILY_MINUTES:
        logger.warning("worktime: 异常时长 %s 用户 %s，丢弃", dur, rec.get("userId"))
        return None
    if not rec.get("date"):
        logger.warning("worktime: 无日期记录 user=%s，丢弃", rec.get("userId"))
        return None
    return rec


def load_from_bitable(client, app_token, table_id, fields=None):
    from .bitable import list_records

    fields = fields or FEISHU_WORKTIME_FIELDS
    records = list_records(client, app_token, table_id)
    out = []
    for rec in records:
        f = rec.get("fields", {}) or {}
        uval = f.get(fields["user"])
        person = uval[0] if (isinstance(uval, list) and uval) else None
        uid = (person or {}).get("id") or (person or {}).get("open_id") or (person or {}).get("user_id")
        uname = (person or {}).get("name")
        d = f.get(fields["date"])
        if isinstance(d, (int, float)):
            try:
                d = datetime.fromtimestamp(d / 1000.0).strftime("%Y-%m-%d")
            except (OverflowError, OSError, ValueError):
                d = None
        cin = f.get(fields["check_in"])
        cout = f.get(fields["check_out"])
        dur = f.get(fields["duration"])
        if dur is None and cin and cout:
            dur = _compute_duration(cin, cout)
        row = {
            "userId": uid,
            "userName": uname,
            "group": None,
            "date": d,
            "checkInTime": cin,
            "checkOutTime": cout,
            "durationMinutes": int(dur) if dur is not None else None,
            "avatarUrl": (person or {}).get("avatar_url"),
        }
        clean = clean_record(row)
        if clean:
            out.append(clean)
    return out


def load_from_attendance(client, start_date, end_date):
    """
    调用飞书考勤"获取打卡结果"接口（自建应用，需"导出打卡数据"权限）。
    POST /open-apis/attendance/v1/user_tasks/query?employee_type=employee_id
    先拉全量通讯录 user_id（分批 ≤50），再解析每条记录的实际上下班打卡时间。
    缺卡/未打卡/无时间戳的记录一律跳过，绝不 500。
    """
    user_ids = _fetch_all_user_ids(client)
    if not user_ids:
        logger.warning("worktime: 无通讯录用户，考勤返回空")
        return []
    start_int = int(start_date.replace("-", ""))
    end_int = int(end_date.replace("-", ""))
    out = []
    for i in range(0, len(user_ids), 50):
        batch = user_ids[i:i + 50]
        try:
            data = client.post(
                "/open-apis/attendance/v1/user_tasks/query?employee_type=employee_id",
                {
                    "user_ids": batch,
                    "check_date_from": start_int,
                    "check_date_to": end_int,
                    "need_overtime_result": True,
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("worktime: 考勤查询批次失败: %s", e)
            continue
        for item in (data.get("user_task_results") or []):
            uid = item.get("user_id")
            name = item.get("employee_name")
            day = item.get("day")
            d = None
            if isinstance(day, (int, float)):
                try:
                    d = datetime.strptime(str(int(day)), "%Y%m%d").strftime("%Y-%m-%d")
                except ValueError:
                    d = None
            for rc in (item.get("records") or []):
                cin = (rc.get("check_in_record") or {}).get("check_time")
                cout = (rc.get("check_out_record") or {}).get("check_time")
                if not cin or not cout:
                    continue  # 缺卡/未打卡，跳过
                try:
                    cin_ts = int(cin)
                    cout_ts = int(cout)
                except (ValueError, TypeError):
                    continue
                dur = int((cout_ts - cin_ts) / 60.0)
                row = {
                    "userId": uid,
                    "userName": name,
                    "group": None,
                    "date": d,
                    "checkInTime": cin_ts,
                    "checkOutTime": cout_ts,
                    "durationMinutes": dur,
                    "avatarUrl": None,
                }
                clean = clean_record(row)
                if clean:
                    out.append(clean)
    logger.info("worktime: 考勤有效打卡记录 %d 条", len(out))
    return out


def _compute_duration(cin, cout):
    """由上下班时间字符串估算时长（分钟）；失败返回 None。"""
    try:
        def parse(t):
            s = str(t).strip()
            if len(s) > 10:
                return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            return datetime.strptime(s, "%H:%M:%S")

        a = parse(cin)
        b = parse(cout)
        delta = (b - a).total_seconds() / 60.0
        if delta < 0:
            delta += 24 * 60  # 跨天（如 22:00 -> 次日 02:00）
        return int(delta)
    except (ValueError, AttributeError, TypeError):
        return None


def load_unchecked_today(client):
    """
    查询"今日"未打卡成员名单（用于首页醒目滚动提醒）。

    判定口径：当天有考勤班次（check_in_result / check_out_result 不为 NoNeedCheck），
    但上下班均未正常打卡（结果非 Normal）的成员视为"未打卡"。
    无需打卡（NoNeedCheck，如周末/未排班）不计入。异常情况不抛错，绝不 500。
    """
    user_ids = _fetch_all_user_ids(client)
    if not user_ids:
        logger.warning("worktime: 无通讯录用户，未打卡名单为空")
        return []
    today_int = int(datetime.now().strftime("%Y%m%d"))
    unchecked = []
    for i in range(0, len(user_ids), 50):
        batch = user_ids[i:i + 50]
        try:
            data = client.post(
                "/open-apis/attendance/v1/user_tasks/query?employee_type=employee_id",
                {
                    "user_ids": batch,
                    "check_date_from": today_int,
                    "check_date_to": today_int,
                    "need_overtime_result": True,
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("worktime: 未打卡名单查询失败: %s", e)
            continue
        for item in (data.get("user_task_results") or []):
            name = item.get("employee_name") or item.get("user_id")
            records = item.get("records") or []
            has_shift = False
            checked = False
            for rc in records:
                cin_res = rc.get("check_in_result")
                cout_res = rc.get("check_out_result")
                if cin_res not in (None, "NoNeedCheck") or cout_res not in (None, "NoNeedCheck"):
                    has_shift = True
                if cin_res == "Normal" or cout_res == "Normal":
                    checked = True
            if has_shift and not checked:
                unchecked.append(name)
    # 仅保留监控名单内的成员（名单可热编辑，避免显示非队员）
    monitor = set(get_unchecked_monitor())
    if monitor:
        unchecked = [n for n in unchecked if n in monitor]
    logger.info("worktime: 今日未打卡 %d 人", len(unchecked))
    return unchecked
