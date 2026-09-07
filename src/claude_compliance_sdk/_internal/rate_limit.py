"""Client-side rate limiter for the transport layer.

Sliding-window over a 60-second period, sized by ``rate_limit_rpm``.
Defaults to 600 requests per minute to match the documented
server-side limit, smoothing bursty callers so they do not have
to choose between hitting a 429 and writing their own pacing layer.
This limiter is **not** a substitute for handling 429s — the server
remains the source of truth, and rare bursts can still trip its
counter ahead of ours.

Two classes are exposed, one per concurrency model, since they need
different lock primitives:

* `SlidingWindowLimiter` uses `Lock`.
* `AsyncSlidingWindowLimiter` uses `Lock`.

Both expose the same `acquire` semantics — block (sync) or
suspend (async) until a slot is free, then record the timestamp.

Setting ``rpm`` to ``0`` or a negative value disables the limiter; its
`acquire` becomes a no-op so test transports and integrations
that want pure server enforcement can opt out. Note that ``0`` disables
only the *local* window; observed server headers are still honoured,
because those describe a limit the caller cannot opt out of.

On top of the local window, the limiter consumes the server's
``anthropic-ratelimit-*`` response headers. The real budget is shared
across every key under a parent organisation, so a local counter can
never see the whole picture — but once the server reports zero
remaining, waiting for the stated reset beats spending a request to
discover the 429.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Deque, Mapping

WINDOW_SECONDS = 60.0

LIMIT_HEADER = "anthropic-ratelimit-requests-limit"
REMAINING_HEADER = "anthropic-ratelimit-requests-remaining"
RESET_HEADER = "anthropic-ratelimit-requests-reset"


@dataclass(frozen=True)
class RateLimitSnapshot:
    """The server's view of the shared request budget, as last seen.

    Read off the ``anthropic-ratelimit-*`` headers, which the API
    returns on every authenticated response. The budget is shared
    across every key under the parent organisation and across every
    ``/v1/compliance/*`` endpoint, so ``remaining`` reflects other
    clients' traffic too.

    Attributes:
        limit: The per-minute request budget, or ``None`` when the
            header was absent.
        remaining: Requests left in the current window, or ``None``.
            Watch this to slow down before hitting a 429.
        reset_at: When the window resets and the budget is restored,
            or ``None``.
        observed_at: `monotonic` reading from when this
            was captured, for working out how stale it is.
    """

    limit: int | None = None
    remaining: int | None = None
    reset_at: datetime | None = None
    observed_at: float = 0.0


def _parse_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw.strip())
    except (AttributeError, ValueError):
        return None


def _parse_reset(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def parse_rate_limit_headers(headers: Mapping[str, Any]) -> RateLimitSnapshot | None:
    """Build a `RateLimitSnapshot` from response headers.

    Returns ``None`` when none of the three headers is present, which
    is the case for responses rejected before the rate limiter — an
    unrecognised key, for example.
    """
    limit = _parse_int(headers.get(LIMIT_HEADER))
    remaining = _parse_int(headers.get(REMAINING_HEADER))
    reset_at = _parse_reset(headers.get(RESET_HEADER))
    if limit is None and remaining is None and reset_at is None:
        return None
    return RateLimitSnapshot(
        limit=limit,
        remaining=remaining,
        reset_at=reset_at,
        observed_at=time.monotonic(),
    )


def _exhausted_deadline(snapshot: RateLimitSnapshot) -> float | None:
    """Return a monotonic deadline to wait until, if the budget is spent.

    Converted to monotonic at observation time on purpose: comparing a
    stored wall-clock timestamp later would be at the mercy of clock
    adjustments.
    """
    if snapshot.remaining is None or snapshot.remaining > 0:
        return None
    if snapshot.reset_at is None:
        return None
    seconds = (snapshot.reset_at - datetime.now(timezone.utc)).total_seconds()
    if seconds <= 0:
        return None
    return time.monotonic() + seconds


class SlidingWindowLimiter:
    """Synchronous sliding-window limiter.

    Args:
        rpm: Maximum number of `acquire` calls allowed in any
            rolling 60-second window. ``rpm <= 0`` disables the
            limiter.
    """

    def __init__(self, rpm: int) -> None:
        self._rpm: int = rpm
        self._timestamps: Deque[float] = deque()
        self._lock: threading.Lock = threading.Lock()
        self._snapshot: RateLimitSnapshot | None = None
        self._exhausted_until: float | None = None

    @property
    def snapshot(self) -> RateLimitSnapshot | None:
        """The most recent server-reported budget, if one was seen."""
        return self._snapshot

    def observe(self, snapshot: RateLimitSnapshot | None) -> None:
        """Record the server's reported budget from a response.

        When the server says nothing is left, the reset time becomes a
        deadline that `acquire` waits for.
        """
        if snapshot is None:
            return
        with self._lock:
            self._snapshot = snapshot
            deadline = _exhausted_deadline(snapshot)
            if deadline is not None:
                self._exhausted_until = deadline

    def _server_wait(self) -> float:
        """Seconds still to wait on a server-reported exhausted budget."""
        with self._lock:
            if self._exhausted_until is None:
                return 0.0
            remaining = self._exhausted_until - time.monotonic()
            if remaining <= 0:
                self._exhausted_until = None
                return 0.0
            return remaining

    def acquire(self) -> None:
        """Block until the server budget and local window both allow a slot."""
        while True:
            wait = self._server_wait()
            if wait <= 0:
                break
            time.sleep(wait)
        if self._rpm <= 0:
            return
        while True:
            with self._lock:
                now = time.monotonic()
                cutoff = now - WINDOW_SECONDS
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._rpm:
                    self._timestamps.append(now)
                    return
                wait = (self._timestamps[0] + WINDOW_SECONDS) - now
            time.sleep(max(0.0, wait))


class AsyncSlidingWindowLimiter:
    """Asynchronous mirror of `SlidingWindowLimiter`."""

    def __init__(self, rpm: int) -> None:
        self._rpm: int = rpm
        self._timestamps: Deque[float] = deque()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._snapshot: RateLimitSnapshot | None = None
        self._exhausted_until: float | None = None

    @property
    def snapshot(self) -> RateLimitSnapshot | None:
        """The most recent server-reported budget, if one was seen."""
        return self._snapshot

    def observe(self, snapshot: RateLimitSnapshot | None) -> None:
        """Record the server's reported budget from a response.

        Deliberately synchronous and lock-free: it is a single
        assignment pair called from the response path, and making it a
        coroutine would force every caller to await mid-request for no
        added safety.
        """
        if snapshot is None:
            return
        self._snapshot = snapshot
        deadline = _exhausted_deadline(snapshot)
        if deadline is not None:
            self._exhausted_until = deadline

    def _server_wait(self) -> float:
        if self._exhausted_until is None:
            return 0.0
        remaining = self._exhausted_until - time.monotonic()
        if remaining <= 0:
            self._exhausted_until = None
            return 0.0
        return remaining

    async def acquire(self) -> None:
        """Suspend until the server budget and local window both allow a slot."""
        while True:
            wait = self._server_wait()
            if wait <= 0:
                break
            await asyncio.sleep(wait)
        if self._rpm <= 0:
            return
        while True:
            async with self._lock:
                now = time.monotonic()
                cutoff = now - WINDOW_SECONDS
                while self._timestamps and self._timestamps[0] <= cutoff:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._rpm:
                    self._timestamps.append(now)
                    return
                wait = (self._timestamps[0] + WINDOW_SECONDS) - now
            await asyncio.sleep(max(0.0, wait))
