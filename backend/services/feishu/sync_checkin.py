# -*- coding: utf-8 -*-
"""
人脸识别补充打卡 -> 飞书多维表格"打卡记录"表 同步器。

数据源：希沃 C:\\RoboMasterDashboard\\data\\face_checkin_YYYYMMDD.json（每天一个文件）
目标：飞书 base 内名为"打卡记录"的表（找不到则返回错误，不自动创建以免误操作）
幂等：按 (日期, 姓名) 去重，已存在的记录跳过，绝不重复写入。
写权限未开通时（Feishu 91403）只记录日志，绝不抛异常影响主服务。
"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("feishu")

# backend/services/feishu/ -> 项目根（data 在项目根下，与人脸服务写盘位置一致）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # = backend/
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")  # = 项目根/data

CHECKIN_TABLE_NAME = "打卡记录"
FIELDS = {"date": "日期", "name": "姓名", "weekday": "星期", "source": "打卡方式"}


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


def find_table_id(client, app_token):
    """在 base 下查找"打卡记录"表；找不到返回 None。"""
    data = client.get("/bitable/v1/apps/%s/tables?page_size=100" % app_token)
    for t in (data.get("items") or []):
        if t.get("name") == CHECKIN_TABLE_NAME:
            return t.get("table_id")
    return None


def list_existing(client, app_token, table_id):
    """列出已有记录 -> set(('date','name'))，用于幂等去重。"""
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
            d = f.get(FIELDS["date"])
            n = f.get(FIELDS["name"])
            if d and n:
                existing.add((str(d), str(n)))
        if data.get("has_more") and data.get("page_token"):
            page_token = data["page_token"]
        else:
            break
    return existing


def sync_checkin_to_feishu(client, app_token):
    """全量同步本地打卡 -> 飞书表（幂等）。返回 {'scanned','created','skipped','error'}。"""
    result = {"scanned": 0, "created": 0, "skipped": 0, "error": None}
    rows = scan_local_checkin()
    result["scanned"] = len(rows)
    if not rows:
        logger.info("checkin sync: 无本地打卡记录，跳过")
        return result
    try:
        table_id = os.environ.get("FEISHU_CHECKIN_TABLE_ID", "").strip() or find_table_id(
            client, app_token
        )
    except Exception as e:  # noqa: BLE001
        result["error"] = "查找打卡记录表失败: %s" % e
        logger.warning(result["error"])
        return result
    if not table_id:
        result["error"] = "未找到飞书表「%s」（应用需为 base 可编辑协作者，且已建该表）" % CHECKIN_TABLE_NAME
        logger.warning(result["error"])
        return result
    try:
        existing = list_existing(client, app_token, table_id)
    except Exception as e:  # noqa: BLE001
        result["error"] = "读取已有打卡记录失败: %s" % e
        logger.warning(result["error"])
        return result
    todo = [r for r in rows if (r["date"], r["name"]) not in existing]
    result["skipped"] = len(rows) - len(todo)
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        payload = {
            "records": [
                {
                    "fields": {
                        FIELDS["date"]: r["date"],
                        FIELDS["name"]: r["name"],
                        FIELDS["weekday"]: _weekday(r["date"]),
                        FIELDS["source"]: "人脸识别",
                    }
                }
                for r in batch
            ]
        }
        try:
            client.post(
                "/bitable/v1/apps/%s/tables/%s/records/batch_create"
                % (app_token, table_id),
                payload,
            )
            result["created"] += len(batch)
        except Exception as e:  # noqa: BLE001
            result["error"] = "批量写入失败: %s" % e
            logger.warning("checkin sync batch failed: %s", e)
            break
    logger.info(
        "checkin sync done: scanned=%s created=%s skipped=%s error=%s",
        result["scanned"], result["created"], result["skipped"], result["error"],
    )
    return result
