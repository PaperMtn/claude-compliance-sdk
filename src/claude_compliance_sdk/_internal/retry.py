"""Retry policy for the transport layer.

Pure-data class. Decides *whether* a response or transport exception is
retryable and *how long* the caller should sleep before the next
attempt. The sleep itself is the caller's responsibility — sync
:meth:`SyncTransport.request` uses :func:`time.sleep`, async uses
:func:`asyncio.sleep` — so the same policy serves both transports.

Retry semantics follow PLAN §2.3:

* Retry on HTTP 429, 500, 502, 503, 504.
* Retry on :class:`httpx.ConnectError` for any method (the request
  never reached the server).
* Retry on :class:`httpx.ReadTimeout` only for safe methods; for
  POST/PUT/PATCH the request may have been applied server-side, so a
  blind retry could double-write.
* Backoff is ``base_delay * 2**retry_index`` capped at ``cap_delay``,
  with symmetric ``±jitter_ratio`` jitter added.
* On 429 the ``Retry-After`` header (already parsed onto
  :class:`~claude_compliance_sdk.RateLimitError`) overrides the
  backoff schedule.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE_DELAY = 0.5
DEFAULT_CAP_DELAY = 20.0
DEFAULT_JITTER_RATIO = 0.25

RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "DELETE"})


@dataclass
class RetryPolicy:
    """Decides whether and when to retry a failed request.

    Attributes:
        max_retries: Number of retries after the initial attempt. The
            total request count is at most ``max_retries + 1``. Set to
            ``0`` to disable retries entirely.
        base_delay: First backoff in seconds. Each subsequent retry
            doubles the backoff up to ``cap_delay``.
        cap_delay: Upper bound on the backoff before jitter, in
            seconds.
        jitter_ratio: Fraction of the backoff used as symmetric jitter
            (e.g. ``0.25`` → ``±25%``).
    """

    max_retries: int = 3
    base_delay: float = DEFAULT_BASE_DELAY
    cap_delay: float = DEFAULT_CAP_DELAY
    jitter_ratio: float = DEFAULT_JITTER_RATIO
    _rng: random.Random = field(default_factory=random.Random, repr=False)

    def should_retry_status(self, *, retry_index: int, method: str, status_code: int) -> bool:
        """Return ``True`` if a non-2xx response should be retried.

        Args:
            retry_index: 0-indexed number of retries already used. The
                first decision (after the initial attempt) is at
                ``retry_index=0``.
            method: HTTP method of the original request. Non-safe
                methods (POST/PUT/PATCH) are never retried on a
                response — the request may have already applied
                server-side.
            status_code: HTTP status of the response.
        """
        if retry_index >= self.max_retries:
            return False
        if method.upper() not in SAFE_METHODS:
            return False
        return status_code in RETRYABLE_STATUSES

    def should_retry_exception(self, *, retry_index: int, method: str, exc: BaseException) -> bool:
        """Return ``True`` if a transport exception should be retried.

        Connect errors are retried for any method because the request
        never reached the server. Read timeouts are retried only for
        safe methods — the request *may* have been applied.
        """
        if retry_index >= self.max_retries:
            return False
        if isinstance(exc, httpx.ConnectError):
            return True
        if isinstance(exc, httpx.ReadTimeout):
            return method.upper() in SAFE_METHODS
        return False

    def compute_delay(self, *, retry_index: int, retry_after: float | None = None) -> float:
        """Return the seconds to sleep before the next attempt.

        Args:
            retry_index: 0-indexed retry count. ``retry_index=0`` is
                the first retry, ``retry_index=1`` the second, etc.
            retry_after: If supplied, overrides the backoff schedule.
                Used to honour the server's ``Retry-After`` hint on a
                429.
        """
        if retry_after is not None:
            return max(0.0, retry_after)
        backoff = min(self.cap_delay, self.base_delay * (2**retry_index))
        jitter = backoff * self.jitter_ratio
        jittered: float = backoff + self._rng.uniform(-jitter, jitter)
        return max(0.0, jittered)
