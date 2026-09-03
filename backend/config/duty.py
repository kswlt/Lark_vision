# -*- coding: utf-8 -*-
"""
值日表 & 名单配置加载器。

名单统一存放在 config/team_roster.json，直接编辑人名即可，
接口按缓存（值日 2 分钟 / 未打卡 2 分钟）自动热更新，保存后无需重启。
"""

import json
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
_CONFIG = os.path.join(_BASE, "config", "team_roster.json")


def load_roster():
    """读取 team_roster.json，失败时返回空字典（绝不抛错）。"""
    try:
        with open(_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def get_duty_roster():
    """值日轮值名单（顺序轮值，每天一人）。"""
    return load_roster().get("duty_roster") or ["待定"]


def get_duty_start():
    """轮值起始日期（该日为名单第 1 人）。"""
    return load_roster().get("duty_start") or "2026-09-01"


def get_unchecked_monitor():
    """未打卡监控名单：首页滚动只提醒名单内成员。"""
    return load_roster().get("unchecked_monitor") or []


# 兼容旧引用（sources.py 历史 import）
DUTY_ROSTER = get_duty_roster()
DUTY_START = get_duty_start()
UNCHECKED_MONITOR = get_unchecked_monitor()
