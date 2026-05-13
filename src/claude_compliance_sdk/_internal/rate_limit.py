"""Client-side rate limiter for the transport layer.

Sliding-window over a 60-second period, sized by ``rate_limit_rpm``.
Defaults to 600 requests per minute to match the server-side limit
documented in CONTEXT.md, smoothing bursty callers so they do not have
to choose between hitting a 429 and writing their own pacing layer.
This limiter is **not** a substitute for handling 429s — the server
remains the source of truth, and rare bursts can still trip its
counter ahead of ours.

Two classes are exposed, one per concurrency model, since they need
different lock primitives:

* :class:`SlidingWindowLimiter` uses :class:`threading.Lock`.
* :class:`AsyncSlidingWindowLimiter` uses :class:`asyncio.Lock`.

Both expose the same :meth:`acquire` semantics — block (sync) or
suspend (async) until a slot is free, then record the timestamp.

Setting ``rpm`` to ``0`` or a negative value disables the limiter; its
:meth:`acquire` becomes a no-op so test transports and integrations
that want pure server enforcement can opt out.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from typing import Deque

WINDOW_SECONDS = 60.0


class SlidingWindowLimiter:
    """Synchronous sliding-window limiter.

    Args:
        rpm: Maximum number of :meth:`acquire` calls allowed in any
            rolling 60-second window. ``rpm <= 0`` disables the
            limiter.
    """

    def __init__(self, rpm: int) -> None:
        self._rpm: int = rpm
        self._timestamps: Deque[float] = deque()
        self._lock: threading.Lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a slot in the current window is available."""
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
    """Asynchronous mirror of :class:`SlidingWindowLimiter`."""

    def __init__(self, rpm: int) -> None:
        self._rpm: int = rpm
        self._timestamps: Deque[float] = deque()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Suspend until a slot in the current window is available."""
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
