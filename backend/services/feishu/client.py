"""
飞书 OpenAPI 轻量客户端。

重试策略（v2）：
- 仅对以下情况重试：
    requests.ConnectionError / Timeout
    HTTP 429（限流）、5xx（服务端错误）、飞书业务码 99991663（访问频繁）
- 不重试：权限错误、参数错误、其它 HTTP 4xx、配置错误（避免无意义重复请求）
- 使用 exponential backoff + jitter
- 所有请求强制 timeout
业务层只负责拼接路径，token 注入与错误处理都在这里。
"""
import logging
import random
import time

import requests
from requests.exceptions import ConnectionError, Timeout

from .token import TokenManager

logger = logging.getLogger("feishu")

BASE = "https://open.feishu.cn/open-apis"
DEFAULT_TIMEOUT = 15  # 秒，所有请求强制超时
MAX_RETRIES = 2       # 最多重试 2 次（共 3 次尝试）

RETRYABLE_HTTP = {429, 500, 502, 503, 504}
RETRYABLE_FEISHU_CODES = {99991663}  # 飞书业务码：访问频繁（限流类）


class FeishuError(RuntimeError):
    """Feishu API 错误。retryable=True 表示该错误值得重试。"""

    def __init__(self, message, retryable=False, code=None):
        super().__init__(message)
        self.retryable = retryable
        self.code = code


def _should_retry(exc):
    if isinstance(exc, (ConnectionError, Timeout)):
        return True
    if isinstance(exc, FeishuError):
        return exc.retryable
    return False


def _backoff(attempt, base=0.5, cap=5.0):
    """exponential backoff + jitter。attempt 从 0 开始。"""
    delay = min(cap, base * (2 ** attempt))
    jitter = random.uniform(0, delay * 0.25)
    time.sleep(delay + jitter)


class FeishuClient:
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
            raise FeishuError(
                f"Feishu API 返回非 JSON: HTTP {resp.status_code}",
                retryable=resp.status_code in RETRYABLE_HTTP,
            ) from None
        if data.get("code") != 0:
            code = data.get("code")
            msg = data.get("msg")
            retryable = (
                resp.status_code in RETRYABLE_HTTP
                or code in RETRYABLE_FEISHU_CODES
            )
            logger.warning(
                "Feishu API 错误 url=%s http=%s code=%s msg=%s retryable=%s",
                url, resp.status_code, code, msg, retryable,
            )
            raise FeishuError(
                f"Feishu API {url} -> http={resp.status_code} code={code}: {msg}",
                retryable=retryable, code=code,
            )
        return data.get("data", {})

    def _request(self, method, path, params=None, payload=None, retries=MAX_RETRIES):
        url = BASE + path
        last_err = None
        for attempt in range(retries + 1):
            try:
                resp = requests.request(
                    method, url,
                    headers=self._headers(),
                    params=params,
                    json=payload if payload is not None else {},
                    timeout=DEFAULT_TIMEOUT,
                )
                return self._handle(resp, url)
            except Exception as e:
                last_err = e
                if attempt < retries and _should_retry(e):
                    _backoff(attempt)
                    continue
                break
        raise last_err

    def get(self, path, params=None, retries=MAX_RETRIES):
        return self._request("GET", path, params=params, retries=retries)

    def post(self, path, payload=None, retries=MAX_RETRIES):
        return self._request("POST", path, payload=payload, retries=retries)

    def put(self, path, payload=None, retries=MAX_RETRIES):
        return self._request("PUT", path, payload=payload, retries=retries)
