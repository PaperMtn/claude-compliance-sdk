"""Tests for the retry policy and its integration with the transport."""

from __future__ import annotations

import random

import httpx
import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    NotFoundError,
)
from claude_compliance_sdk._internal.retry import (
    DEFAULT_BASE_DELAY,
    RETRYABLE_STATUSES,
    SAFE_METHODS,
    RetryPolicy,
)
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport


API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
PATH = "/v1/compliance/activities"


# ---------------------------------------------------------------------------
# RetryPolicy — should_retry_status
# ---------------------------------------------------------------------------


def test_retryable_statuses_match_plan() -> None:
    assert RETRYABLE_STATUSES == {429, 500, 502, 503, 504}


def test_safe_methods_set() -> None:
    assert SAFE_METHODS == {"GET", "HEAD", "OPTIONS", "DELETE"}


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retries_retryable_status_for_safe_method(status: int) -> None:
    policy = RetryPolicy(max_retries=3)
    assert policy.should_retry_status(retry_index=0, method="GET", status_code=status)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 418])
def test_does_not_retry_non_retryable_status(status: int) -> None:
    policy = RetryPolicy(max_retries=3)
    assert not policy.should_retry_status(retry_index=0, method="GET", status_code=status)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
def test_does_not_retry_5xx_for_non_idempotent_methods(method: str) -> None:
    policy = RetryPolicy(max_retries=3)
    assert not policy.should_retry_status(retry_index=0, method=method, status_code=500)


def test_does_not_retry_when_retry_index_at_max() -> None:
    policy = RetryPolicy(max_retries=2)
    assert policy.should_retry_status(retry_index=1, method="GET", status_code=500)
    assert not policy.should_retry_status(retry_index=2, method="GET", status_code=500)


def test_max_retries_zero_disables_retries() -> None:
    policy = RetryPolicy(max_retries=0)
    assert not policy.should_retry_status(retry_index=0, method="GET", status_code=500)


def test_method_check_is_case_insensitive() -> None:
    policy = RetryPolicy(max_retries=3)
    assert policy.should_retry_status(retry_index=0, method="get", status_code=500)


# ---------------------------------------------------------------------------
# RetryPolicy — should_retry_exception
# ---------------------------------------------------------------------------


def test_retries_connect_error_for_any_method() -> None:
    policy = RetryPolicy(max_retries=3)
    exc = httpx.ConnectError("dns failed")
    for method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        assert policy.should_retry_exception(retry_index=0, method=method, exc=exc)


def test_retries_read_timeout_only_for_safe_methods() -> None:
    policy = RetryPolicy(max_retries=3)
    exc = httpx.ReadTimeout("slow")
    assert policy.should_retry_exception(retry_index=0, method="GET", exc=exc)
    assert policy.should_retry_exception(retry_index=0, method="DELETE", exc=exc)
    assert not policy.should_retry_exception(retry_index=0, method="POST", exc=exc)
    assert not policy.should_retry_exception(retry_index=0, method="PUT", exc=exc)


def test_does_not_retry_other_http_errors() -> None:
    policy = RetryPolicy(max_retries=3)
    exc = httpx.HTTPError("unexpected")
    assert not policy.should_retry_exception(retry_index=0, method="GET", exc=exc)


# ---------------------------------------------------------------------------
# RetryPolicy — compute_delay
# ---------------------------------------------------------------------------


def test_compute_delay_uses_retry_after_when_supplied() -> None:
    policy = RetryPolicy(max_retries=3)
    assert policy.compute_delay(retry_index=0, retry_after=12.5) == 12.5


def test_compute_delay_clamps_negative_retry_after_to_zero() -> None:
    policy = RetryPolicy(max_retries=3)
    assert policy.compute_delay(retry_index=0, retry_after=-5.0) == 0.0


def test_compute_delay_doubles_with_retry_index() -> None:
    # With jitter disabled, the schedule is deterministic.
    policy = RetryPolicy(max_retries=10, jitter_ratio=0.0, _rng=random.Random(0))
    assert policy.compute_delay(retry_index=0) == DEFAULT_BASE_DELAY
    assert policy.compute_delay(retry_index=1) == DEFAULT_BASE_DELAY * 2
    assert policy.compute_delay(retry_index=2) == DEFAULT_BASE_DELAY * 4
    assert policy.compute_delay(retry_index=3) == DEFAULT_BASE_DELAY * 8


def test_compute_delay_caps_at_cap_delay() -> None:
    policy = RetryPolicy(
        max_retries=20, base_delay=1.0, cap_delay=8.0, jitter_ratio=0.0, _rng=random.Random(0)
    )
    # 1 * 2^10 = 1024, cap clamps to 8
    assert policy.compute_delay(retry_index=10) == 8.0


def test_compute_delay_applies_jitter_within_ratio() -> None:
    policy = RetryPolicy(max_retries=10, jitter_ratio=0.25, _rng=random.Random(0))
    # backoff = 0.5; jitter band is ±0.125
    for _ in range(100):
        d = policy.compute_delay(retry_index=0)
        assert 0.375 <= d <= 0.625


def test_compute_delay_seeded_rng_is_reproducible() -> None:
    a = RetryPolicy(max_retries=3, _rng=random.Random(42))
    b = RetryPolicy(max_retries=3, _rng=random.Random(42))
    assert a.compute_delay(retry_index=0) == b.compute_delay(retry_index=0)


# ---------------------------------------------------------------------------
# Transport integration — sync
# ---------------------------------------------------------------------------


def _sync_transport(max_retries: int = 3) -> SyncTransport:
    return SyncTransport(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=30.0,
        anthropic_version="2023-06-01",
        max_retries=max_retries,
        rate_limit_rpm=600,
    )


def _async_transport(max_retries: int = 3) -> AsyncTransport:
    return AsyncTransport(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=30.0,
        anthropic_version="2023-06-01",
        max_retries=max_retries,
        rate_limit_rpm=600,
    )


@pytest.fixture
def fake_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Capture every ``time.sleep`` call from transport.py and skip it."""
    calls: list[float] = []

    def fake(seconds: float) -> None:
        calls.append(seconds)

    monkeypatch.setattr("claude_compliance_sdk._internal.transport.time.sleep", fake)
    return calls


@pytest.fixture
def fake_async_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    calls: list[float] = []

    async def fake(seconds: float) -> None:
        calls.append(seconds)

    monkeypatch.setattr("claude_compliance_sdk._internal.transport.asyncio.sleep", fake)
    return calls


def test_sync_retries_500_then_succeeds(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=500,
        json={"error": {"type": "internal_error", "message": "boom"}},
    )
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={"data": []})

    transport = _sync_transport(max_retries=3)
    try:
        result = transport.request("GET", PATH)
    finally:
        transport.close()

    assert result == {"data": []}
    assert len(fake_sleep) == 1


def test_sync_exhausts_retries_then_raises(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    for _ in range(4):
        httpx_mock.add_response(
            url=f"{BASE_URL}{PATH}",
            status_code=500,
            json={"error": {"type": "internal_error", "message": "boom"}},
        )

    transport = _sync_transport(max_retries=3)
    try:
        with pytest.raises(InternalServerError):
            transport.request("GET", PATH)
    finally:
        transport.close()

    assert len(fake_sleep) == 3


def test_sync_429_uses_retry_after_over_backoff(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=429,
        json={"error": {"type": "rate_limit_error", "message": "slow"}},
        headers={"Retry-After": "9"},
    )
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={"data": []})

    transport = _sync_transport(max_retries=2)
    try:
        result = transport.request("GET", PATH)
    finally:
        transport.close()

    assert result == {"data": []}
    assert fake_sleep == [9.0]


def test_sync_does_not_retry_non_retryable_status(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "missing"}},
    )

    transport = _sync_transport(max_retries=3)
    try:
        with pytest.raises(NotFoundError):
            transport.request("GET", PATH)
    finally:
        transport.close()

    assert fake_sleep == []


def test_sync_does_not_retry_post_on_500(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=500,
        json={"error": {"type": "internal_error", "message": "boom"}},
        method="POST",
    )

    transport = _sync_transport(max_retries=3)
    try:
        with pytest.raises(InternalServerError):
            transport.request("POST", PATH, json={"x": 1})
    finally:
        transport.close()

    assert fake_sleep == []


def test_sync_retries_connect_error_then_succeeds(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    httpx_mock.add_exception(httpx.ConnectError("dns fail"))
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={"data": []})

    transport = _sync_transport(max_retries=3)
    try:
        result = transport.request("GET", PATH)
    finally:
        transport.close()

    assert result == {"data": []}
    assert len(fake_sleep) == 1


def test_sync_retries_read_timeout_for_safe_method(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("slow"))
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={"data": []})

    transport = _sync_transport(max_retries=3)
    try:
        result = transport.request("GET", PATH)
    finally:
        transport.close()

    assert result == {"data": []}


def test_sync_does_not_retry_read_timeout_for_post(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("slow"))

    transport = _sync_transport(max_retries=3)
    try:
        with pytest.raises(APITimeoutError):
            transport.request("POST", PATH, json={"x": 1})
    finally:
        transport.close()

    assert fake_sleep == []


def test_sync_exhausts_retries_on_connect_error(
    httpx_mock: HTTPXMock, fake_sleep: list[float]
) -> None:
    for _ in range(4):
        httpx_mock.add_exception(httpx.ConnectError("dns fail"))

    transport = _sync_transport(max_retries=3)
    try:
        with pytest.raises(APIConnectionError):
            transport.request("GET", PATH)
    finally:
        transport.close()

    assert len(fake_sleep) == 3


# ---------------------------------------------------------------------------
# Transport integration — async
# ---------------------------------------------------------------------------


async def test_async_retries_500_then_succeeds(
    httpx_mock: HTTPXMock, fake_async_sleep: list[float]
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=500,
        json={"error": {"type": "internal_error", "message": "boom"}},
    )
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={"data": []})

    transport = _async_transport(max_retries=3)
    try:
        result = await transport.request("GET", PATH)
    finally:
        await transport.aclose()

    assert result == {"data": []}
    assert len(fake_async_sleep) == 1


async def test_async_429_uses_retry_after(
    httpx_mock: HTTPXMock, fake_async_sleep: list[float]
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        status_code=429,
        json={"error": {"type": "rate_limit_error", "message": "slow"}},
        headers={"Retry-After": "4"},
    )
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={"data": []})

    transport = _async_transport(max_retries=2)
    try:
        result = await transport.request("GET", PATH)
    finally:
        await transport.aclose()

    assert result == {"data": []}
    assert fake_async_sleep == [4.0]


async def test_async_retries_connect_error(
    httpx_mock: HTTPXMock, fake_async_sleep: list[float]
) -> None:
    httpx_mock.add_exception(httpx.ConnectError("dns fail"))
    httpx_mock.add_response(url=f"{BASE_URL}{PATH}", json={"data": []})

    transport = _async_transport(max_retries=3)
    try:
        result = await transport.request("GET", PATH)
    finally:
        await transport.aclose()

    assert result == {"data": []}
