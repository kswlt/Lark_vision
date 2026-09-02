# -*- coding: utf-8 -*-
"""
数据源统一入口：
- 飞书配置完整 -> 真实数据（任务表 + 可选工时表/考勤）
- 未配置 -> 完整 Mock 模式
带任务 45s / 工时 5min 缓存，头像 12h 缓存。
"""
import logging
import os
import threading
import time
from datetime import date, timedelta

from data.mock_tasks import build_mock_tasks
from data.mock_worktime import build_mock_worktime
from services.feishu import FeishuClient, UserCache, list_records
from services.feishu.normalize import normalize_task
from services.feishu.worktime import (
    clean_record,
    load_from_attendance,
    load_from_bitable,
    load_unchecked_today,
)
from config.duty import DUTY_ROSTER, DUTY_START

logger = logging.getLogger("sources")

TASKS_TTL = 45
WORKTIME_TTL = 300
UNCHECKED_TTL = 120
DUTY_TTL = 120


class DataStore(object):
    def __init__(self):
        self.app_id = os.environ.get("FEISHU_APP_ID", "")
        self.app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        self.app_token = os.environ.get("FEISHU_APP_TOKEN", "")
        self.table_id = os.environ.get("FEISHU_TABLE_ID", "")
        self.feishu_configured = bool(
            self.app_id and self.app_secret and self.app_token and self.table_id
        )
        self.client = None
        self.users = None
        if self.feishu_configured:
            self.client = FeishuClient(self.app_id, self.app_secret)
            self.users = UserCache(self.client)

        self._tasks = None
        self._tasks_at = 0.0
        self._worktime = None
        self._worktime_at = 0.0
        self._unchecked = None
        self._unchecked_at = 0.0
        self._lock = threading.Lock()

    @property
    def data_source(self):
        return "feishu" if self.feishu_configured else "mock"

    # ---------------- tasks ----------------
    def get_tasks(self):
        now = time.time()
        with self._lock:
            if self._tasks is not None and now - self._tasks_at < TASKS_TTL:
                return self._tasks
        tasks = self._load_tasks()
        with self._lock:
            self._tasks = tasks
            self._tasks_at = time.time()
        return tasks

    def _load_tasks(self):
        if not self.feishu_configured:
            return build_mock_tasks()
        try:
            records = list_records(self.client, self.app_token, self.table_id)
        except Exception as e:  # noqa: BLE001
            logger.error("飞书任务表读取失败，回退 Mock: %s", e)
            return build_mock_tasks()
        tasks = [normalize_task(r) for r in records if r.get("fields")]
        tasks = [t for t in tasks if t.get("title")]
        # 头像/姓名补齐（12h 缓存）
        for t in tasks:
            if t.get("ownerId") and not t.get("ownerAvatarUrl"):
                info = self.users.get(t["ownerId"])
                if info.get("name") and not t.get("ownerName"):
                    t["ownerName"] = info["name"]
                if info.get("avatarUrl"):
                    t["ownerAvatarUrl"] = info["avatarUrl"]
        self._assign_readable_ids(tasks)
        return tasks

    @staticmethod
    def _assign_readable_ids(tasks):
        """表格"编号"列不可靠（多为空/纯数字），为 fallback id 生成稳定可读编号：
        按组别 ALG-001 / ELE-001 / MEC-001 / OPR-001，未分组 TSK-001。
        顺序按 group + id 稳定排序，保证每次刷新编号一致。"""
        prefix_map = {"算法": "ALG", "电控": "ELE", "机械": "MEC", "运营": "OPR"}
        counters = {}
        for t in sorted(tasks, key=lambda x: (x.get("group") or "", x.get("id") or "")):
            tid = t.get("id") or ""
            # 形如 rec... 的 record_id 或纯数字占位 -> 重新编号
            if tid.startswith("rec") or tid.isdigit() or not any(ch.isalpha() for ch in tid):
                g = t.get("group") or "未指定"
                p = prefix_map.get(g, "TSK")
                counters[p] = counters.get(p, 0) + 1
                t["id"] = "%s-%03d" % (p, counters[p])

    # ---------------- worktime ----------------
    def get_worktime_records(self):
        now = time.time()
        with self._lock:
            if self._worktime is not None and now - self._worktime_at < WORKTIME_TTL:
                return self._worktime
        records = self._load_worktime()
        # 统一清洗：任何来源（含 mock）的异常记录都不进榜
        records = [r for r in (clean_record(r) for r in records) if r]
        with self._lock:
            self._worktime = records
            self._worktime_at = time.time()
        return records

    def _load_worktime(self):
        source = os.environ.get("FEISHU_WORKTIME_SOURCE", "mock").strip().lower()
        if source == "bitable":
            wt_token = os.environ.get("FEISHU_WORKTIME_APP_TOKEN", "")
            wt_table = os.environ.get("FEISHU_WORKTIME_TABLE_ID", "")
            if self.client and wt_token and wt_table:
                try:
                    recs = load_from_bitable(self.client, wt_token, wt_table)
                    if recs:
                        return self._enrich_avatars(recs)
                except Exception as e:  # noqa: BLE001
                    logger.warning("工时表读取失败: %s", e)
        elif source == "attendance":
            if self.client:
                try:
                    today = date.today()
                    # 考勤接口要求查询区间 ≤ 30 天
                    start = (today - timedelta(days=29)).isoformat()
                    recs = load_from_attendance(self.client, start, today.isoformat())
                    if recs:
                        return self._enrich_avatars(recs)
                except Exception as e:  # noqa: BLE001
                    logger.warning("考勤接口读取失败: %s", e)
        # 未配置或读取失败：
        #   已接入飞书（真实系统）-> 返回空，劳模榜显示"暂无打卡数据"，不伪造数据
        #   纯 Mock 模式 -> 返回演示工时
        if self.feishu_configured:
            logger.info("工时数据源未就绪，劳模榜返回空")
            return []
        return build_mock_worktime()

    def _enrich_avatars(self, records):
        if not self.users:
            return records
        for r in records:
            if r.get("userId") and not r.get("avatarUrl"):
                info = self.users.get(r["userId"])
                r["avatarUrl"] = info.get("avatarUrl")
                if info.get("name") and not r.get("userName"):
                    r["userName"] = info["name"]
        return records

    # ---------------- 值日表 ----------------
    def get_duty(self):
        """按 DUTY_ROSTER 轮值生成今日 + 未来 6 天（共 7 天）值日安排。"""
        from datetime import date, timedelta

        roster = DUTY_ROSTER or ["待定"]
        start = date.fromisoformat(DUTY_START)
        today = date.today()
        days = []
        for i in range(7):
            d = today + timedelta(days=i)
            idx = (d - start).days % len(roster)
            days.append(
                {
                    "date": d.isoformat(),
                    "name": roster[idx],
                    "isToday": i == 0,
                }
            )
        return days

    # ---------------- 今日未打卡 ----------------
    def get_unchecked(self):
        now = time.time()
        with self._lock:
            if self._unchecked is not None and now - self._unchecked_at < UNCHECKED_TTL:
                return self._unchecked
        names = []
        if self.feishu_configured and self.client:
            try:
                names = load_unchecked_today(self.client)
            except Exception as e:  # noqa: BLE001
                logger.warning("未打卡名单获取失败: %s", e)
        with self._lock:
            self._unchecked = names
            self._unchecked_at = time.time()
        return names
