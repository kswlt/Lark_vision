# -*- coding: utf-8 -*-
"""
tenant_access_token 获取与内存缓存。
按飞书返回的 expire 自动刷新，避免每次请求都重新获取。
"""
import threading
import time

import requests

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"


class TokenManager(object):
    def __init__(self, app_id, app_secret):
        self._app_id = app_id
        self._app_secret = app_secret
        self._token = None
        self._expire_at = 0.0
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            now = time.time()
            # 提前 60s 刷新，避免临界失效
            if self._token and now < self._expire_at - 60:
                return self._token
            resp = requests.post(
                TOKEN_URL,
                json={"app_id": self._app_id, "app_secret": self._app_secret},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError("获取 tenant_access_token 失败: %s" % data.get("msg"))
            self._token = data["tenant_access_token"]
            expire = int(data.get("expire", 7200))
            self._expire_at = now + expire
            return self._token
