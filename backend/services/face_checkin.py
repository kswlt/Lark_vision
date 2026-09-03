# -*- coding: utf-8 -*-
"""
人脸打卡记录读取（由希沃端 camera_checkin.py 常驻服务写入）。

记录文件: <BASE>/data/face_checkin_YYYYMMDD.json
  {"date": "2026-09-03", "names": ["张三", "李四"]}
"""

import json
import logging
import os
from datetime import date

logger = logging.getLogger("feishu")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")


def _today_path():
    return os.path.join(DATA_DIR, "face_checkin_%s.json" % date.today().strftime("%Y%m%d"))


def read_today_checkin():
    """读取今日已人脸打卡名单。返回 {"date": "...", "names": [...]}，失败返回空名单（绝不 500）。"""
    path = _today_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                names = data.get("names") or []
                return {"date": data.get("date", date.today().isoformat()), "names": list(names)}
    except Exception as e:  # noqa: BLE001
        logger.warning("读取人脸打卡记录失败: %s", e)
    return {"date": date.today().isoformat(), "names": []}


def checked_name_set():
    """返回今日已人脸打卡姓名的 set，用于从未打卡名单中扣减。"""
    return set(read_today_checkin().get("names") or [])
