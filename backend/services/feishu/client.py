# -*- coding: utf-8 -*-
"""
飞书 OpenAPI 轻量客户端。
业务层只负责拼接路径，token 注入与错误处理都在这里。
"""
import logging

import requests

from .token import TokenManager

logger = logging.getLogger("feishu")

BASE = "https://open.feishu.cn/open-apis"


class FeishuClient(object):
    def __init__(self, app_id, app_secret):
        self._tokens = TokenManager(app_id, app_secret)

    def _headers(self):
        return {
            "Authorization": "Bearer " + self._tokens.get(),
            "Content-Type": "application/json; charset=utf-8",
        }

    def _handle(self, resp, url):
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError("Feishu API 返回非 JSON: %s" % resp.status_code)
        if data.get("code") != 0:
            logger.warning("Feishu API 错误 url=%s code=%s msg=%s", url, data.get("code"), data.get("msg"))
            raise RuntimeError("Feishu API %s -> %s: %s" % (url, data.get("code"), data.get("msg")))
        return data.get("data", {})

    def get(self, path, params=None, retries=2):
        url = BASE + path
        last_err = None
        for i in range(retries + 1):
            try:
                resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
                return self._handle(resp, url)
            except Exception as e:  # noqa: BLE001
                last_err = e
                if i < retries:
                    time_sleep(0.5 * (i + 1))
        raise last_err

    def post(self, path, payload=None, retries=2):
        url = BASE + path
        last_err = None
        for i in range(retries + 1):
            try:
                resp = requests.post(url, headers=self._headers(), json=payload or {}, timeout=15)
                return self._handle(resp, url)
            except Exception as e:  # noqa: BLE001
                last_err = e
                if i < retries:
                    time_sleep(0.5 * (i + 1))
        raise last_err


def time_sleep(sec):
    import time

    time.sleep(sec)
