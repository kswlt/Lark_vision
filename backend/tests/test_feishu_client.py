"""FeishuClient 重试策略测试：只重试可重试错误，指数退避 + jitter。"""
from unittest import mock

import pytest
from requests.exceptions import ConnectionError, Timeout

from services.feishu.client import (
    DEFAULT_TIMEOUT,
    FeishuClient,
    FeishuError,
    _should_retry,
)


def _resp(status, payload):
    r = mock.Mock()
    r.status_code = status
    r.json.return_value = payload
    return r


@pytest.fixture()
def client():
    c = FeishuClient("app_id", "app_secret")
    # 避免真实请求 token API：token 获取不属于本测试范围
    mock.patch.object(c._tokens, "get", return_value="fake-token").start()
    return c


@pytest.fixture(autouse=True)
def _cleanup_patches():
    yield
    mock.patch.stopall()


def test_should_retry_matrix():
    assert _should_retry(ConnectionError("x"))
    assert _should_retry(Timeout("x"))
    assert _should_retry(FeishuError("x", retryable=True))
    assert not _should_retry(FeishuError("x", retryable=False))
    assert not _should_retry(ValueError("x"))
    assert not _should_retry(RuntimeError("x"))


def test_http_403_not_retried(client):
    """权限/参数错误（4xx 非 429）不重试，只请求 1 次。"""
    with mock.patch("services.feishu.client.requests.request",
                    return_value=_resp(403, {"code": 99991661, "msg": "permission denied"})) as m:
        with pytest.raises(FeishuError) as ei:
            client.get("/x")
        assert m.call_count == 1
        assert ei.value.retryable is False


def test_http_429_retried_then_success(client):
    """429 限流重试，最终成功。"""
    responses = [
        _resp(429, {"code": 99991663, "msg": "rate limit"}),
        _resp(429, {"code": 99991663, "msg": "rate limit"}),
        _resp(200, {"code": 0, "data": {"ok": 1}}),
    ]
    with mock.patch("services.feishu.client.requests.request", side_effect=responses) as m:
        data = client.get("/x")
        assert m.call_count == 3
        assert data == {"ok": 1}


def test_http_500_retried(client):
    responses = [
        _resp(500, {}),
        _resp(200, {"code": 0, "data": {}}),
    ]
    with mock.patch("services.feishu.client.requests.request", side_effect=responses) as m:
        client.get("/x")
        assert m.call_count == 2


def test_connection_error_retried(client):
    responses = [ConnectionError("net down"), _resp(200, {"code": 0, "data": {}})]
    with mock.patch("services.feishu.client.requests.request", side_effect=responses) as m:
        client.get("/x")
        assert m.call_count == 2


def test_timeout_retried(client):
    responses = [Timeout("slow"), _resp(200, {"code": 0, "data": {}})]
    with mock.patch("services.feishu.client.requests.request", side_effect=responses) as m:
        client.get("/x")
        assert m.call_count == 2


def test_feishu_business_error_retryable_code(client):
    """飞书业务码 99991663（访问频繁）视为可重试。"""
    responses = [
        _resp(200, {"code": 99991663, "msg": "too frequent"}),
        _resp(200, {"code": 0, "data": {}}),
    ]
    with mock.patch("services.feishu.client.requests.request", side_effect=responses) as m:
        client.get("/x")
        assert m.call_count == 2


def test_all_requests_have_timeout(client):
    """所有请求必须带 timeout（强制超时，防挂死）。"""
    with mock.patch("services.feishu.client.requests.request",
                    return_value=_resp(200, {"code": 0, "data": {}})) as m:
        client.get("/x")
        client.post("/y", payload={"a": 1})
        client.put("/z", payload={})
        for call in m.call_args_list:
            assert call.kwargs.get("timeout") == DEFAULT_TIMEOUT
