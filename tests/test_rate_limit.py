"""Tests for the sliding-window rate limiter."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest

from claude_compliance_sdk._internal.rate_limit import (
    WINDOW_SECONDS,
    AsyncSlidingWindowLimiter,
    RateLimitSnapshot,
    SlidingWindowLimiter,
    parse_rate_limit_headers,
)


class _FakeClock:
    """A monkey-patchable clock used to drive the limiter deterministically."""

    def __init__(self) -> None:
        self.now: float = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    async def async_sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    clock = _FakeClock()
    monkeypatch.setattr(
        "claude_compliance_sdk._internal.rate_limit.time.monotonic", clock.monotonic
    )
    monkeypatch.setattr("claude_compliance_sdk._internal.rate_limit.time.sleep", clock.sleep)
    monkeypatch.setattr(
        "claude_compliance_sdk._internal.rate_limit.asyncio.sleep", clock.async_sleep
    )
    return clock


# ---------------------------------------------------------------------------
# Sync limiter
# ---------------------------------------------------------------------------


def test_acquire_does_not_sleep_below_quota(fake_clock: _FakeClock) -> None:
    limiter = SlidingWindowLimiter(rpm=3)
    for _ in range(3):
        limiter.acquire()
    assert fake_clock.sleeps == []


def test_acquire_sleeps_when_quota_full(fake_clock: _FakeClock) -> None:
    limiter = SlidingWindowLimiter(rpm=2)
    limiter.acquire()
    limiter.acquire()
    limiter.acquire()  # third must wait for the first slot to slide out
    assert len(fake_clock.sleeps) == 1
    assert fake_clock.sleeps[0] == pytest.approx(WINDOW_SECONDS)


def test_acquire_drops_expired_timestamps(fake_clock: _FakeClock) -> None:
    limiter = SlidingWindowLimiter(rpm=2)
    limiter.acquire()
    limiter.acquire()
    # Skip past the window manually — the next acquire should find the
    # bucket empty and pass without sleeping.
    fake_clock.advance(WINDOW_SECONDS + 1)
    limiter.acquire()
    assert fake_clock.sleeps == []


def test_rpm_zero_disables_limiter(fake_clock: _FakeClock) -> None:
    limiter = SlidingWindowLimiter(rpm=0)
    for _ in range(1000):
        limiter.acquire()
    assert fake_clock.sleeps == []


def test_negative_rpm_disables_limiter(fake_clock: _FakeClock) -> None:
    limiter = SlidingWindowLimiter(rpm=-5)
    for _ in range(10):
        limiter.acquire()
    assert fake_clock.sleeps == []


# ---------------------------------------------------------------------------
# Async limiter
# ---------------------------------------------------------------------------


async def test_async_acquire_does_not_sleep_below_quota(fake_clock: _FakeClock) -> None:
    limiter = AsyncSlidingWindowLimiter(rpm=3)
    for _ in range(3):
        await limiter.acquire()
    assert fake_clock.sleeps == []


async def test_async_acquire_sleeps_when_quota_full(fake_clock: _FakeClock) -> None:
    limiter = AsyncSlidingWindowLimiter(rpm=2)
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()
    assert len(fake_clock.sleeps) == 1
    assert fake_clock.sleeps[0] == pytest.approx(WINDOW_SECONDS)


async def test_async_rpm_zero_disables_limiter(fake_clock: _FakeClock) -> None:
    limiter = AsyncSlidingWindowLimiter(rpm=0)
    for _ in range(1000):
        await limiter.acquire()
    assert fake_clock.sleeps == []


# ---------------------------------------------------------------------------
# Param sanity: both limiters honour the WINDOW constant
# ---------------------------------------------------------------------------


def test_window_constant_matches_spec() -> None:
    # CONTEXT.md and the Compliance API spec define the window as 60s.
    assert WINDOW_SECONDS == 60.0


# ---------------------------------------------------------------------------
# Server-reported budget (anthropic-ratelimit-* headers)
# ---------------------------------------------------------------------------


def _reset_in(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def test_parse_rate_limit_headers_reads_all_three() -> None:
    snapshot = parse_rate_limit_headers(
        {
            "anthropic-ratelimit-requests-limit": "600",
            "anthropic-ratelimit-requests-remaining": "42",
            "anthropic-ratelimit-requests-reset": "2026-04-21T14:38:25Z",
        }
    )
    assert snapshot is not None
    assert snapshot.limit == 600
    assert snapshot.remaining == 42
    assert snapshot.reset_at == datetime(2026, 4, 21, 14, 38, 25, tzinfo=timezone.utc)


def test_parse_rate_limit_headers_returns_none_when_absent() -> None:
    # Requests rejected before the rate limiter carry no such headers.
    assert parse_rate_limit_headers({"content-type": "application/json"}) is None


def test_parse_rate_limit_headers_tolerates_partial_and_garbage() -> None:
    snapshot = parse_rate_limit_headers(
        {
            "anthropic-ratelimit-requests-limit": "not-a-number",
            "anthropic-ratelimit-requests-remaining": "7",
            "anthropic-ratelimit-requests-reset": "yesterday",
        }
    )
    assert snapshot is not None
    assert snapshot.limit is None
    assert snapshot.remaining == 7
    assert snapshot.reset_at is None


def test_parse_rate_limit_headers_assumes_utc_for_naive_reset() -> None:
    snapshot = parse_rate_limit_headers(
        {"anthropic-ratelimit-requests-reset": "2026-04-21T14:38:25"}
    )
    assert snapshot is not None
    assert snapshot.reset_at == datetime(2026, 4, 21, 14, 38, 25, tzinfo=timezone.utc)


def test_observe_exposes_the_snapshot() -> None:
    limiter = SlidingWindowLimiter(rpm=600)
    assert limiter.snapshot is None
    limiter.observe(parse_rate_limit_headers({"anthropic-ratelimit-requests-remaining": "123"}))
    assert limiter.snapshot is not None
    assert limiter.snapshot.remaining == 123


def test_observe_ignores_none() -> None:
    limiter = SlidingWindowLimiter(rpm=600)
    limiter.observe(None)
    assert limiter.snapshot is None


def _exhausted(seconds_until_reset: float) -> RateLimitSnapshot | None:
    return parse_rate_limit_headers(
        {
            "anthropic-ratelimit-requests-remaining": "0",
            "anthropic-ratelimit-requests-reset": _reset_in(seconds_until_reset),
        }
    )


def test_acquire_waits_for_reset_when_budget_is_exhausted(fake_clock: _FakeClock) -> None:
    # remaining=0 means the next request is a guaranteed 429, so wait
    # for the stated reset rather than spending it to find out.
    limiter = SlidingWindowLimiter(rpm=600)
    limiter.observe(_exhausted(30))
    limiter.acquire()
    assert fake_clock.sleeps, "expected acquire to wait for the reset"
    assert 0 < sum(fake_clock.sleeps) <= 31


def test_acquire_returns_immediately_once_the_deadline_passes(fake_clock: _FakeClock) -> None:
    limiter = SlidingWindowLimiter(rpm=600)
    limiter.observe(_exhausted(30))
    limiter.acquire()
    first = len(fake_clock.sleeps)
    limiter.acquire()
    assert len(fake_clock.sleeps) == first, "deadline should be cleared after the wait"


def test_exhausted_without_a_reset_header_does_not_block(fake_clock: _FakeClock) -> None:
    # No reset time means no deadline to wait for, so fall through to
    # the local window and let the server answer with a 429 if it must.
    limiter = SlidingWindowLimiter(rpm=600)
    limiter.observe(parse_rate_limit_headers({"anthropic-ratelimit-requests-remaining": "0"}))
    limiter.acquire()
    assert fake_clock.sleeps == []


def test_acquire_does_not_wait_when_budget_remains(fake_clock: _FakeClock) -> None:
    limiter = SlidingWindowLimiter(rpm=600)
    limiter.observe(
        parse_rate_limit_headers(
            {
                "anthropic-ratelimit-requests-remaining": "500",
                "anthropic-ratelimit-requests-reset": _reset_in(30),
            }
        )
    )
    limiter.acquire()
    assert fake_clock.sleeps == []


def test_acquire_does_not_wait_when_reset_is_in_the_past(fake_clock: _FakeClock) -> None:
    limiter = SlidingWindowLimiter(rpm=600)
    limiter.observe(_exhausted(-5))
    limiter.acquire()
    assert fake_clock.sleeps == []


def test_server_budget_is_honoured_even_with_the_local_window_disabled(
    fake_clock: _FakeClock,
) -> None:
    # rpm=0 opts out of the *local* window only. The shared server
    # budget is not something a caller can opt out of.
    limiter = SlidingWindowLimiter(rpm=0)
    limiter.observe(_exhausted(10))
    limiter.acquire()
    assert fake_clock.sleeps and fake_clock.sleeps[0] > 0


async def test_async_acquire_waits_for_reset(fake_clock: _FakeClock) -> None:
    limiter = AsyncSlidingWindowLimiter(rpm=600)
    limiter.observe(_exhausted(20))
    await limiter.acquire()
    assert fake_clock.sleeps and 0 < sum(fake_clock.sleeps) <= 21


async def test_async_observe_exposes_the_snapshot() -> None:
    limiter = AsyncSlidingWindowLimiter(rpm=600)
    limiter.observe(parse_rate_limit_headers({"anthropic-ratelimit-requests-limit": "600"}))
    assert limiter.snapshot is not None
    assert limiter.snapshot.limit == 600
