# -*- coding: utf-8 -*-
"""
飞书考勤工时数据 -> 飞书电子表格 同步器。

把飞书考勤 API 的打卡记录（每人每天）同步到电子表格，便于备份和查看。
字段：日期、姓名、星期、上班时间、下班时间、工时(小时)、工时(分钟)
幂等：按 (日期, 姓名) 去重，已存在的记录跳过。
数据源：飞书考勤 API（load_from_attendance）
目标：飞书电子表格（FEISHU_ATTENDANCE_SHEET_TOKEN / FEISHU_ATTENDANCE_SHEET_ID）
"""
import logging
import os
from datetime import datetime, timedelta

from .worktime import load_from_attendance

logger = logging.getLogger("feishu")

HEADERS = ["日期", "姓名", "星期", "上班时间", "下班时间", "工时(小时)", "工时(分钟)"]


def _ts_to_hm(ts):
    """时间戳 -> HH:MM"""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%H:%M")
    except (ValueError, TypeError, OSError):
        return ""


def _weekday(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return "一二三四五六日"[dt.weekday()]
    except (ValueError, TypeError, IndexError):
        return ""


def _sheets_read_existing(client, token, sheet_id):
    """读取电子表格 A:B 已有 (日期, 姓名) -> set"""
    existing = set()
    try:
        data = client.get("/sheets/v2/spreadsheets/%s/values/%s!A:B" % (token, sheet_id))
        vr = data.get("valueRange") or {}
        rows = vr.get("values") or []
        for i, row in enumerate(rows):
            if i == 0:
                continue  # 表头
            if not row or len(row) < 2:
                continue
            d = row[0]
            n = row[1]
            if d and n:
                existing.add((str(d), str(n)))
    except Exception as e:  # noqa: BLE001
        logger.warning("attendance sync: read existing failed: %s", e)
    return existing


def _sheets_ensure_header(client, token, sheet_id):
    """检查表头，不存在则用 values_append 写入（飞书 sheets v2 写入端点兼容）。"""
    try:
        data = client.get("/sheets/v2/spreadsheets/%s/values/%s!A1:G1" % (token, sheet_id))
        vr = data.get("valueRange") or {}
        rows = vr.get("values") or []
        first = rows[0] if rows else []
        if first and first[0]:
            return
    except Exception:
        pass
    try:
        client.post(
            "/sheets/v2/spreadsheets/%s/values_append" % token,
            {"valueRange": {"range": "%s!A:G" % sheet_id, "values": [HEADERS]}},
        )
        logger.info("attendance sync: header written via values_append")
    except Exception as e:  # noqa: BLE001
        logger.warning("attendance sync: write header failed: %s", e)


def _sheets_append(client, token, sheet_id, rows):
    """追加多行到电子表格"""
    if not rows:
        return 0
    try:
        client.post(
            "/sheets/v2/spreadsheets/%s/values_append" % token,
            {"valueRange": {"range": "%s!A:G" % sheet_id, "values": rows}},
        )
        return len(rows)
    except Exception as e:  # noqa: BLE001
        logger.warning("attendance sync: append failed: %s", e)
        return 0


def sync_attendance_to_sheets(client, days=30):
    """
    把飞书考勤数据同步到电子表格。
    days: 同步最近多少天的数据（默认 30 天，飞书考勤 API 上限）
    返回 {'scanned','created','skipped','error'}
    """
    result = {"scanned": 0, "created": 0, "skipped": 0, "error": None}
    token = os.environ.get("FEISHU_ATTENDANCE_SHEET_TOKEN", "").strip()
    sheet_id = os.environ.get("FEISHU_ATTENDANCE_SHEET_ID", "").strip()
    if not token or not sheet_id:
        result["error"] = "未配置 FEISHU_ATTENDANCE_SHEET_TOKEN / FEISHU_ATTENDANCE_SHEET_ID"
        logger.warning(result["error"])
        return result

    today = datetime.now().date()
    start = (today - timedelta(days=days - 1)).isoformat()
    end = today.isoformat()

    try:
        records = load_from_attendance(client, start, end)
    except Exception as e:  # noqa: BLE001
        result["error"] = "读取飞书考勤失败: %s" % e
        logger.warning(result["error"])
        return result

    result["scanned"] = len(records)
    if not records:
        logger.info("attendance sync: 无考勤记录")
        return result

    _sheets_ensure_header(client, token, sheet_id)
    existing = _sheets_read_existing(client, token, sheet_id)

    todo = []
    for rec in records:
        key = (rec.get("date", ""), rec.get("userName", ""))
        if key in existing:
            result["skipped"] += 1
            continue
        dur_min = rec.get("durationMinutes") or 0
        todo.append([
            rec.get("date", ""),
            rec.get("userName", ""),
            _weekday(rec.get("date", "")),
            _ts_to_hm(rec.get("checkInTime")),
            _ts_to_hm(rec.get("checkOutTime")),
            round(dur_min / 60.0, 2),
            dur_min,
        ])

    if todo:
        created = _sheets_append(client, token, sheet_id, todo)
        result["created"] = created

    logger.info(
        "attendance sync done: scanned=%s created=%s skipped=%s error=%s",
        result["scanned"], result["created"], result["skipped"], result["error"],
    )
    return result
