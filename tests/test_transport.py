"""Tests for the sync + async httpx transport."""

from __future__ import annotations

import platform
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InsufficientScopeError,
    InternalServerError,
    InvalidAPIKeyError,
    NotFoundError,
    RateLimitError,
)
from claude_compliance_sdk._internal.transport import (
    AsyncTransport,
    SyncTransport,
    _build_user_agent,
)
from claude_compliance_sdk.version import __version__ as _SDK_VERSION

API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
PATH = "/v1/compliance/activities"


@pytest.fixture
def sync_transport() -> SyncTransport:
    # Retries are isolated in tests/test_retry.py; the transport tests
    # use max_retries=0 so a single mocked response is enough.
    transport = SyncTransport(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=30.0,
        max_retries=0,
        rate_limit_rpm=600,
    )
    yield transport
    transport.close()


@pytest.fixture
async def async_transport() -> AsyncTransport:
    transport = AsyncTransport(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=30.0,
        max_retries=0,
        rate_limit_rpm=600,
    )
    yield transport
    await transport.aclose()


# ---------------------------------------------------------------------------
# User-Agent
# ---------------------------------------------------------------------------


def test_user_agent_format() -> None:
    ua = _build_user_agent()
    assert ua.startswith(f"claude-compliance-sdk/{_SDK_VERSION}")
    assert f"python/{platform.python_version()}" in ua
    assert f"httpx/{httpx.__version__}" in ua


# ---------------------------------------------------------------------------
# Success paths (sync + async)
# ---------------------------------------------------------------------------


def test_sync_get_returns_decoded_json(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    payload = {"data": [{"id": "act_1"}], "has_more": False}
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json=payload)
    result = sync_transport.request("GET", PATH)
    assert result == payload


async def test_async_get_returns_decoded_json(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    payload = {"data": [{"id": "act_1"}], "has_more": False}
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json=payload)
    result = await async_transport.request("GET", PATH)
    assert result == payload


def test_sync_empty_body_returns_none(sync_transport: SyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", status_code=204, content=b"")
    assert sync_transport.request("DELETE", PATH) is None


async def test_async_empty_body_returns_none(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", status_code=204, content=b"")
    assert await async_transport.request("DELETE", PATH) is None


def test_sync_non_json_body_returned_as_text(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", content=b"plain text")
    assert sync_transport.request("GET", PATH) == "plain text"


# ---------------------------------------------------------------------------
# Header injection
# ---------------------------------------------------------------------------


def test_sync_injects_default_headers(sync_transport: SyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={})
    sync_transport.request("GET", PATH)
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["x-api-key"] == API_KEY
    assert request.headers["user-agent"].startswith(f"claude-compliance-sdk/{_SDK_VERSION}")


def test_sync_does_not_inject_anthropic_version_header(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    # The Compliance API spec lists only x-api-key as required, and
    # production /v1/compliance/* routes 404 when the Messages-API
    # `anthropic-version` header is present. The SDK must never send
    # it by default.
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={})
    sync_transport.request("GET", PATH)
    request = httpx_mock.get_request()
    assert request is not None
    assert "anthropic-version" not in request.headers


async def test_async_injects_default_headers(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={})
    await async_transport.request("GET", PATH)
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["x-api-key"] == API_KEY
    assert "anthropic-version" not in request.headers


def test_per_request_headers_merge_over_defaults(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={})
    sync_transport.request("GET", PATH, headers={"x-trace": "trace-123"})
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["x-trace"] == "trace-123"
    assert request.headers["x-api-key"] == API_KEY


def test_query_params_serialised(sync_transport: SyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}?limit=50", json={})
    sync_transport.request("GET", PATH, params={"limit": 50})
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["limit"] == "50"


def test_json_body_sent(sync_transport: SyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={})
    sync_transport.request("POST", PATH, json={"foo": "bar"})
    request = httpx_mock.get_request()
    assert request is not None
    assert request.content == b'{"foo": "bar"}'


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,error_type,message,expected",
    [
        (400, "invalid_request_error", "Bad limit.", BadRequestError),
        (
            401,
            "authentication_error",
            "The API key provided is invalid or has been revoked.",
            InvalidAPIKeyError,
        ),
        (
            403,
            "permission_error",
            "The API key provided does not have the `read:compliance_activities` scope.",
            InsufficientScopeError,
        ),
        (404, "not_found_error", "Chat not found.", NotFoundError),
        (409, "conflict_error", "Project has attached chats.", ConflictError),
        (500, "internal_error", "Boom.", InternalServerError),
    ],
)
def test_sync_error_status_raises_typed_exception(
    sync_transport: SyncTransport,
    httpx_mock: HTTPXMock,
    status: int,
    error_type: str,
    message: str,
    expected: type[APIError],
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=status,
        json={"error": {"type": error_type, "message": message}},
        headers={"request-id": "req_xyz"},
    )
    with pytest.raises(expected) as exc_info:
        sync_transport.request("GET", PATH)
    assert exc_info.value.status_code == status
    assert exc_info.value.request_id == "req_xyz"
    assert exc_info.value.error_type == error_type
    assert exc_info.value.error_message == message


async def test_async_error_mapping(async_transport: AsyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=401,
        json={"error": {"type": "authentication_error", "message": "Invalid API key."}},
    )
    with pytest.raises(AuthenticationError):
        await async_transport.request("GET", PATH)


def test_429_carries_retry_after(sync_transport: SyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=429,
        json={"error": {"type": "rate_limit_error", "message": "Slow down."}},
        headers={"Retry-After": "7"},
    )
    with pytest.raises(RateLimitError) as exc_info:
        sync_transport.request("GET", PATH)
    assert exc_info.value.retry_after == 7.0


def test_error_with_non_json_body(sync_transport: SyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=502,
        content=b"<html>gateway down</html>",
    )
    with pytest.raises(InternalServerError) as exc_info:
        sync_transport.request("GET", PATH)
    assert exc_info.value.error_type is None
    assert exc_info.value.error_message is None
    assert exc_info.value.body == "<html>gateway down</html>"


# ---------------------------------------------------------------------------
# Transport-level failures
# ---------------------------------------------------------------------------


def test_timeout_raises_api_timeout_error(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("read timed out"))
    with pytest.raises(APITimeoutError):
        sync_transport.request("GET", PATH)


def test_connect_error_raises_api_connection_error(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_exception(httpx.ConnectError("nope"))
    with pytest.raises(APIConnectionError):
        sync_transport.request("GET", PATH)


async def test_async_timeout_raises_api_timeout_error(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("read timed out"))
    with pytest.raises(APITimeoutError):
        await async_transport.request("GET", PATH)


async def test_async_connect_error_raises_api_connection_error(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_exception(httpx.ConnectError("nope"))
    with pytest.raises(APIConnectionError):
        await async_transport.request("GET", PATH)


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


def test_sync_stream_returns_undrained_response(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", content=b"binary-blob")
    response = sync_transport.request("GET", PATH, stream=True)
    assert isinstance(response, httpx.Response)
    chunks = list(response.iter_bytes())
    assert b"".join(chunks) == b"binary-blob"
    response.close()


async def test_async_stream_returns_undrained_response(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", content=b"binary-blob")
    response = await async_transport.request("GET", PATH, stream=True)
    assert isinstance(response, httpx.Response)
    chunks = [chunk async for chunk in response.aiter_bytes()]
    assert b"".join(chunks) == b"binary-blob"
    await response.aclose()


def test_sync_stream_error_drains_before_raising(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=500,
        json={"error": {"type": "internal_error", "message": "Boom."}},
    )
    with pytest.raises(InternalServerError) as exc_info:
        sync_transport.request("GET", PATH, stream=True)
    assert exc_info.value.error_message == "Boom."


async def test_async_stream_error_drains_before_raising(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=500,
        json={"error": {"type": "internal_error", "message": "Boom."}},
    )
    with pytest.raises(InternalServerError) as exc_info:
        await async_transport.request("GET", PATH, stream=True)
    assert exc_info.value.error_message == "Boom."


# ---------------------------------------------------------------------------
# Public client wire-up
# ---------------------------------------------------------------------------


def test_public_sync_client_delegates_close_to_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from claude_compliance_sdk import ComplianceClient

    closed = {"count": 0}
    client = ComplianceClient(api_key=API_KEY)

    real_close = client._transport.close  # noqa: SLF001

    def fake_close() -> None:
        closed["count"] += 1
        real_close()

    monkeypatch.setattr(client._transport, "close", fake_close)  # noqa: SLF001
    client.close()
    assert closed["count"] == 1


async def test_public_async_client_delegates_aclose_to_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from claude_compliance_sdk import AsyncComplianceClient

    closed = {"count": 0}
    client = AsyncComplianceClient(api_key=API_KEY)

    real_aclose = client._transport.aclose  # noqa: SLF001

    async def fake_aclose() -> None:
        closed["count"] += 1
        await real_aclose()

    monkeypatch.setattr(client._transport, "aclose", fake_aclose)  # noqa: SLF001
    await client.aclose()
    assert closed["count"] == 1
