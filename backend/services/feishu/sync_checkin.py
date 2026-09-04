# -*- coding: utf-8 -*-
"""
人脸识别补充打卡 -> 飞书同步器。

支持两种目标（按 .env 配置自动选择）：
  A. 电子表格（推荐）：FEISHU_CHECKIN_SPREADSHEET_TOKEN + FEISHU_CHECKIN_SHEET_ID
     写入 https://idf6jvjjmj.feishu.cn/sheets/<token>
  B. 多维表格（备选）：FEISHU_CHECKIN_TABLE_ID 或 base 内名为"打卡记录"的表

数据源：希沃 C:\\RoboMasterDashboard\\data\\face_checkin_YYYYMMDD.json
幂等：按 (日期, 姓名) 去重，已存在的记录跳过，绝不重复写入。
写权限未开通时只记录日志，绝不抛异常影响主服务。
"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("feishu")

# backend/services/feishu/ -> 项目根（data 在项目根下）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # = backend/
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")  # = 项目根/data

CHECKIN_TABLE_NAME = "打卡记录"
HEADERS = ["日期", "姓名", "星期", "打卡方式"]


# ---------------------------------------------------------------------------
# 本地扫描
# ---------------------------------------------------------------------------
def scan_local_checkin():
    """扫描希沃 data/face_checkin_*.json -> [{'date','name'}]，按日期排序。"""
    out = []
    if not os.path.isdir(DATA_DIR):
        return out
    for fn in sorted(os.listdir(DATA_DIR)):
        if not (fn.startswith("face_checkin_") and fn.endswith(".json")):
            continue
        try:
            with open(os.path.join(DATA_DIR, fn), encoding="utf-8") as f:
                data = json.load(f)
            d = data.get("date") or ""
            for name in (data.get("names") or []):
                if name and d:
                    out.append({"date": d, "name": name})
        except Exception as e:  # noqa: BLE001
            logger.warning("scan checkin file %s failed: %s", fn, e)
    return out


def _weekday(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return "一二三四五六日"[dt.weekday()]
    except (ValueError, TypeError, IndexError):
        return ""


def _row_values(r):
    return [r["date"], r["name"], _weekday(r["date"]), "人脸识别"]


# ---------------------------------------------------------------------------
# 模式 A：电子表格（sheets）
# ---------------------------------------------------------------------------
def _sheets_read_all(client, token, sheet_id):
    """读取电子表格 A:D 全部 -> set(('date','name'))。"""
    existing = set()
    try:
        data = client.get("/sheets/v2/spreadsheets/%s/values/%s!A:D" % (token, sheet_id))
        vr = data.get("valueRange") or {}
        rows = vr.get("values") or []
        for i, row in enumerate(rows):
            if i == 0:
                continue  # 跳过表头
            if not row or len(row) < 2:
                continue
            d = row[0]
            n = row[1]
            if d and n:
                existing.add((str(d), str(n)))
    except Exception as e:  # noqa: BLE001
        logger.warning("sheets read existing failed: %s", e)
    return existing


def _sheets_ensure_header(client, token, sheet_id):
    """检查表头，不存在则写入 A1:D1。"""
    try:
        data = client.get("/sheets/v2/spreadsheets/%s/values/%s!A1:D1" % (token, sheet_id))
        vr = data.get("valueRange") or {}
        rows = vr.get("values") or []
        first = rows[0] if rows else []
        if first and first[0]:
            return  # 表头已存在
    except Exception:
        pass
    try:
        client.put(
            "/sheets/v2/spreadsheets/%s/values/%s!A1:D1" % (token, sheet_id),
            {"valueRange": {"range": "%s!A1:D1" % sheet_id, "values": [HEADERS]}},
        )
        logger.info("sheets header written")
    except Exception as e:  # noqa: BLE001
        logger.warning("sheets write header failed: %s", e)


def _sheets_append(client, token, sheet_id, rows):
    """追加多行到电子表格。"""
    if not rows:
        return 0
    try:
        client.post(
            "/sheets/v2/spreadsheets/%s/values_append" % token,
            {"valueRange": {"range": "%s!A:D" % sheet_id, "values": rows}},
        )
        return len(rows)
    except Exception as e:  # noqa: BLE001
        logger.warning("sheets append failed: %s", e)
        return 0


def sync_to_sheets(client):
    """同步到电子表格。返回 {'scanned','created','skipped','error'}。"""
    result = {"scanned": 0, "created": 0, "skipped": 0, "error": None}
    token = os.environ.get("FEISHU_CHECKIN_SPREADSHEET_TOKEN", "").strip()
    sheet_id = os.environ.get("FEISHU_CHECKIN_SHEET_ID", "").strip()
    if not token or not sheet_id:
        result["error"] = "未配置 FEISHU_CHECKIN_SPREADSHEET_TOKEN / FEISHU_CHECKIN_SHEET_ID"
        return result
    rows = scan_local_checkin()
    result["scanned"] = len(rows)
    if not rows:
        logger.info("checkin sync(sheets): 无本地打卡记录，跳过")
        return result
    _sheets_ensure_header(client, token, sheet_id)
    existing = _sheets_read_all(client, token, sheet_id)
    todo = [r for r in rows if (r["date"], r["name"]) not in existing]
    result["skipped"] = len(rows) - len(todo)
    if todo:
        values = [_row_values(r) for r in todo]
        created = _sheets_append(client, token, sheet_id, values)
        result["created"] = created
    logger.info(
        "checkin sync(sheets) done: scanned=%s created=%s skipped=%s error=%s",
        result["scanned"], result["created"], result["skipped"], result["error"],
    )
    return result


# ---------------------------------------------------------------------------
# 模式 B：多维表格（bitable）— 保留备选
# ---------------------------------------------------------------------------
def find_table_id(client, app_token):
    data = client.get("/bitable/v1/apps/%s/tables?page_size=100" % app_token)
    for t in (data.get("items") or []):
        if t.get("name") == CHECKIN_TABLE_NAME:
            return t.get("table_id")
    return None


def list_existing_bitable(client, app_token, table_id):
    existing = set()
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        data = client.get(
            "/bitable/v1/apps/%s/tables/%s/records" % (app_token, table_id), params
        )
        for rec in (data.get("items") or []):
            f = rec.get("fields") or {}
            d = f.get("日期")
            n = f.get("姓名")
            if d and n:
                existing.add((str(d), str(n)))
        if data.get("has_more") and data.get("page_token"):
            page_token = data["page_token"]
        else:
            break
    return existing


def sync_to_bitable(client, app_token):
    result = {"scanned": 0, "created": 0, "skipped": 0, "error": None}
    rows = scan_local_checkin()
    result["scanned"] = len(rows)
    if not rows:
        return result
    try:
        table_id = os.environ.get("FEISHU_CHECKIN_TABLE_ID", "").strip() or find_table_id(
            client, app_token
        )
    except Exception as e:  # noqa: BLE001
        result["error"] = "查找打卡记录表失败: %s" % e
        return result
    if not table_id:
        result["error"] = "未找到飞书表「%s」" % CHECKIN_TABLE_NAME
        return result
    try:
        existing = list_existing_bitable(client, app_token, table_id)
    except Exception as e:  # noqa: BLE001
        result["error"] = "读取已有打卡记录失败: %s" % e
        return result
    todo = [r for r in rows if (r["date"], r["name"]) not in existing]
    result["skipped"] = len(rows) - len(todo)
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        payload = {
            "records": [
                {"fields": {"日期": r["date"], "姓名": r["name"], "星期": _weekday(r["date"]), "打卡方式": "人脸识别"}}
                for r in batch
            ]
        }
        try:
            client.post(
                "/bitable/v1/apps/%s/tables/%s/records/batch_create" % (app_token, table_id),
                payload,
            )
            result["created"] += len(batch)
        except Exception as e:  # noqa: BLE001
            result["error"] = "批量写入失败: %s" % e
            break
    return result


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------
def sync_checkin_to_feishu(client, app_token=None):
    """
    同步本地打卡到飞书。
    优先电子表格（配置了 SPREADSHEET_TOKEN），否则多维表格。
    """
    token = os.environ.get("FEISHU_CHECKIN_SPREADSHEET_TOKEN", "").strip()
    if token:
        return sync_to_sheets(client)
    if app_token:
        return sync_to_bitable(client, app_token)
    return {"scanned": 0, "created": 0, "skipped": 0, "error": "未配置任何飞书写入目标"}
