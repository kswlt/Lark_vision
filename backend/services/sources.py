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
from services.face_checkin import checked_name_set
from config.duty import get_duty_roster, get_duty_start

logger = logging.getLogger("sources")

TASKS_TTL = 45
WORKTIME_TTL = 300
UNCHECKED_TTL = 60
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
        self._refresh_lock = threading.Lock()  # 单飞：同一时刻只允许一个线程刷新飞书

    def _cached_or_refresh(self, state_name, ttl, loader):
        """
        带"单飞 + 旧缓存兜底"的数据源读取：
        - 缓存新鲜 -> 直接返回
        - 缓存过期 -> 只有一个线程真正拉飞书，其余请求立即返回旧缓存（不阻塞、不重复打飞书）
        - 无旧缓存   -> 等待刷新线程完成后返回
        """
        now = time.time()
        with self._lock:
            cur = getattr(self, state_name)
            if cur is not None and now - getattr(self, state_name + "_at") < ttl:
                return cur
        if self._refresh_lock.acquire(blocking=False):
            try:
                with self._lock:
                    cur = getattr(self, state_name)
                    if cur is not None and time.time() - getattr(self, state_name + "_at") < ttl:
                        return cur
                val = loader()
                with self._lock:
                    setattr(self, state_name, val)
                    setattr(self, state_name + "_at", time.time())
                return val
            finally:
                self._refresh_lock.release()
        # 其它线程正在刷新：返回旧缓存，避免排队挤爆 Waitress
        with self._lock:
            cur = getattr(self, state_name)
            if cur is not None:
                return cur
        # 无旧缓存（冷启动）：等待刷新线程完成，最多 10 秒，避免返回 None
        deadline = time.time() + 10
        while time.time() < deadline:
            time.sleep(0.3)
            with self._lock:
                cur = getattr(self, state_name)
                if cur is not None:
                    return cur
        with self._lock:
            cur = getattr(self, state_name)
            return cur if cur is not None else []

    @property
    def data_source(self):
        return "feishu" if self.feishu_configured else "mock"

    # ---------------- tasks ----------------
    def get_tasks(self):
        return self._cached_or_refresh("_tasks", TASKS_TTL, self._load_tasks)

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
        def loader():
            records = self._load_worktime()
            # 统一清洗：任何来源（含 mock）的异常记录都不进榜
            return [r for r in (clean_record(r) for r in records) if r]

        return self._cached_or_refresh("_worktime", WORKTIME_TTL, loader)

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
        """按名单轮值生成今日 + 未来 6 天（共 7 天）值日安排（名单热读，编辑即时生效）。"""
        from datetime import date, timedelta

        roster = get_duty_roster()
        try:
            start = date.fromisoformat(get_duty_start())
        except ValueError:
            start = date(2026, 9, 1)
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
        def loader():
            names = []
            if self.feishu_configured and self.client:
                try:
                    names = load_unchecked_today(self.client)
                except Exception as e:  # noqa: BLE001
                    logger.warning("未打卡名单获取失败: %s", e)
            # 已通过摄像头人脸识别打卡的成员，从未打卡名单中扣减
            try:
                checked = checked_name_set()
                if checked:
                    names = [n for n in names if n not in checked]
            except Exception as e:  # noqa: BLE001
                logger.warning("人脸打卡扣减失败: %s", e)
            return names

        return self._cached_or_refresh("_unchecked", UNCHECKED_TTL, loader)