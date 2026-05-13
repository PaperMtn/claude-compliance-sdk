"""Tests for the sliding-window rate limiter."""

from __future__ import annotations

import pytest

from claude_compliance_sdk._internal.rate_limit import (
    WINDOW_SECONDS,
    AsyncSlidingWindowLimiter,
    SlidingWindowLimiter,
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
    monkeypatch.setattr(
        "claude_compliance_sdk._internal.rate_limit.time.sleep", clock.sleep
    )
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
