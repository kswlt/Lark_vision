# -*- coding: utf-8 -*-
"""
通讯录用户信息（姓名/头像）获取 + 12 小时内存缓存。
避免每次 Dashboard 刷新都请求 30 个头像。
"""
import threading
import time
from urllib.parse import quote


class UserCache(object):
    def __init__(self, client, ttl=12 * 3600):
        self._client = client
        self._ttl = ttl
        self._cache = {}
        self._at = {}
        self._lock = threading.Lock()

    def get(self, user_id, id_type="open_id"):
        if not user_id:
            return {"name": None, "avatarUrl": None}
        now = time.time()
        with self._lock:
            if user_id in self._cache and now - self._at.get(user_id, 0) < self._ttl:
                return self._cache[user_id]
        # 缓存未命中，去飞书查询（避免长期持锁阻塞）
        info = self._fetch(user_id, id_type)
        with self._lock:
            self._cache[user_id] = info
            self._at[user_id] = now
        return info

    def _fetch(self, user_id, id_type):
        try:
            data = self._client.get(
                "/contact/v3/users/%s" % quote(user_id),
                params={"user_id_type": id_type},
            )
            user = data.get("user") or {}
            avatar = user.get("avatar") or {}
            return {
                "name": user.get("name"),
                "avatarUrl": avatar.get("avatar_72") or avatar.get("avatar_240") or user.get("avatar_url"),
            }
        except Exception as e:  # noqa: BLE001
            import logging

            logging.getLogger("feishu").warning("获取用户 %s 信息失败: %s", user_id, e)
            return {"name": None, "avatarUrl": None}
