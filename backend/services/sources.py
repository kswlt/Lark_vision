# -*- coding: utf-8 -*-
"""
数据源统一入口（显式模式，绝不自动回退 Mock）：
- DATA_SOURCE=mock  -> 演示数据（开发/开源演示，不连飞书）
- DATA_SOURCE=feishu（默认）-> 真实飞书数据
  - 飞书请求失败：返回最近一次成功缓存并标记 stale/degraded；
  - 从未成功过：返回明确空态/错误，绝不偷偷生成 Mock 数据。
带任务 45s / 工时 5min 缓存，头像 12h 缓存。
"""
import logging
import os
import threading
import time
from datetime import date, datetime, timedelta

from config.duty import get_duty_roster, get_duty_start
from data.mock_tasks import build_mock_tasks
from data.mock_worktime import build_mock_worktime
from services.face_checkin import checked_name_set
from services.feishu import FeishuClient, UserCache, list_records
from services.feishu.normalize import normalize_task
from services.feishu.worktime import (
    clean_record,
    load_from_attendance,
    load_from_bitable,
    load_unchecked_today,
)

logger = logging.getLogger("sources")

TASKS_TTL = 45
WORKTIME_TTL = 300
UNCHECKED_TTL = 60
DUTY_TTL = 120

# 显式数据源模式：mock | feishu（默认 feishu，只有显式设置 mock 才使用演示数据）
DATA_SOURCE = os.environ.get("DATA_SOURCE", "feishu").strip().lower()
if DATA_SOURCE not in ("feishu", "mock"):
    DATA_SOURCE = "feishu"


class DataSourceError(RuntimeError):
    """飞书数据源错误（不降级为 Mock 时抛出，供调用方决定 stale 回退）。"""


class DataStore:
    def __init__(self):
        self.app_id = os.environ.get("FEISHU_APP_ID", "")
        self.app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        self.app_token = os.environ.get("FEISHU_APP_TOKEN", "")
        self.table_id = os.environ.get("FEISHU_TABLE_ID", "")
        self.feishu_configured = bool(
            self.app_id and self.app_secret and self.app_token and self.table_id
        )
        self._data_source = DATA_SOURCE
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
        self._feishu_ok = True          # 最近一次飞书请求是否成功（初始假设可用）
        self._last_success_sync = 0.0   # 最近一次成功刷新时间戳

    def _mark_success(self):
        self._feishu_ok = True
        self._last_success_sync = time.time()

    def _mark_failure(self, what, exc):
        self._feishu_ok = False
        logger.error("%s 失败: %s", what, exc)

    def _cached_or_refresh(self, state_name, ttl, loader):
        """
        带"单飞 + 旧缓存兜底"的数据源读取：
        - 缓存新鲜 -> 直接返回
        - 缓存过期 -> 只有一个线程真正拉飞书，其余请求立即返回旧缓存（不阻塞、不重复打飞书）
        - 无旧缓存   -> 等待刷新线程完成后返回
        loader 抛 DataSourceError 时向上传播（由调用方决定 stale 回退）。
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
            if cur is not None:
                return cur
        raise DataSourceError("飞书数据源尚未取得任何有效数据（冷启动失败）")

    @property
    def data_source(self):
        return self._data_source

    def health_status(self):
        """返回健康状态：data_source / feishu / last_success_sync / cache_age / stale。"""
        now = time.time()
        if self._tasks_at:
            cache_age = int(now - self._tasks_at)
            stale = cache_age > TASKS_TTL or not self._feishu_ok
        else:
            cache_age = None
            stale = True
        if self.data_source == "mock":
            # mock 是显式数据源（演示/开发），视为正常而非故障，不标记 stale
            feishu = "ok"
            status = "ok"
            stale = False
            cache_age = None
        else:
            feishu = "ok" if (self._feishu_ok and not stale) else "degraded"
            status = "ok" if feishu == "ok" else "degraded"
        return {
            "status": status,
            "data_source": self.data_source,
            "feishu": feishu,
            "last_success_sync": (
                datetime.fromtimestamp(self._last_success_sync).isoformat(timespec="seconds")
                if self._last_success_sync else None
            ),
            "cache_age": cache_age,
            "stale": stale,
        }

    # ---------------- tasks ----------------
    def get_tasks(self):
        try:
            return self._cached_or_refresh("_tasks", TASKS_TTL, self._load_tasks)
        except DataSourceError:
            # 飞书不可用：有最近成功缓存则返回（health 会标 degraded），无缓存返回明确空态
            with self._lock:
                cached = self._tasks
            return cached if cached is not None else []

    def _load_tasks(self):
        if self.data_source == "mock":
            return build_mock_tasks()
        if not self.feishu_configured:
            raise DataSourceError(
                "DATA_SOURCE=feishu 但未配置 FEISHU_APP_ID / FEISHU_APP_SECRET / "
                "FEISHU_APP_TOKEN / FEISHU_TABLE_ID（请复制 backend/.env.example 为 backend/.env）"
            )
        try:
            records = list_records(self.client, self.app_token, self.table_id)
            self._mark_success()
        except Exception as e:
            self._mark_failure("飞书任务表", e)
            raise DataSourceError(f"飞书任务表读取失败: {e}") from e
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
                t["id"] = f"{p}-{counters[p]:03d}"

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
                        self._mark_success()
                        return self._enrich_avatars(recs)
                except Exception as e:
                    self._mark_failure("工时表", e)
                    logger.warning("工时表读取失败: %s", e)
        elif source == "attendance":
            if self.client:
                try:
                    today = date.today()
                    # 考勤接口要求查询区间 ≤ 30 天
                    start = (today - timedelta(days=29)).isoformat()
                    recs = load_from_attendance(self.client, start, today.isoformat())
                    if recs:
                        self._mark_success()
                        return self._enrich_avatars(recs)
                except Exception as e:
                    self._mark_failure("考勤接口", e)
                    logger.warning("考勤接口读取失败: %s", e)
        # 未配置或读取失败：
        #   显式 feishu（真实系统）-> 返回空，劳模榜显示"暂无打卡数据"，不伪造数据
        #   显式 mock -> 返回演示工时
        if self.data_source == "feishu":
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
        roster = get_duty_roster()
        if not roster:
            logger.warning("值日名单为空（duty.py / duty.yaml 未配置），返回空值日表")
            return []
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
                except Exception as e:
                    logger.warning("未打卡名单获取失败: %s", e)
            # 已通过摄像头人脸识别打卡的成员，从未打卡名单中扣减
            try:
                checked = checked_name_set()
                if checked:
                    names = [n for n in names if n not in checked]
            except Exception as e:
                logger.warning("人脸打卡扣减失败: %s", e)
            return names

        return self._cached_or_refresh("_unchecked", UNCHECKED_TTL, loader)
