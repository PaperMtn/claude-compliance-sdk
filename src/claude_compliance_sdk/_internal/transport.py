"""HTTP transport for the Compliance SDK.

Two concrete classes — :class:`SyncTransport` and :class:`AsyncTransport`
— wrap :class:`httpx.Client` and :class:`httpx.AsyncClient` respectively.
Each exposes a single ``request()`` entry point used by every resource
group, with rate limiting, header injection, retry handling, error
mapping, and ``request_id`` lift handled in one place so resources
stay thin.
"""

from __future__ import annotations

import asyncio
import platform
import time
from typing import Any, Mapping

import httpx

from claude_compliance_sdk._internal.rate_limit import (
    AsyncSlidingWindowLimiter,
    SlidingWindowLimiter,
)
from claude_compliance_sdk._internal.retry import RetryPolicy
from claude_compliance_sdk.exceptions import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    RateLimitError,
)
from claude_compliance_sdk.version import __version__ as _SDK_VERSION


def _build_user_agent() -> str:
    return (
        f"claude-compliance-sdk/{_SDK_VERSION} "
        f"python/{platform.python_version()} "
        f"httpx/{httpx.__version__}"
    )


def _build_default_headers(api_key: str, anthropic_version: str) -> dict[str, str]:
    return {
        "x-api-key": api_key,
        "anthropic-version": anthropic_version,
        "User-Agent": _build_user_agent(),
    }


def _decode_body(response: httpx.Response) -> Any:
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


def _build_api_error(response: httpx.Response) -> APIError:
    return APIError.from_response(
        status_code=response.status_code,
        headers=response.headers,
        body=_decode_body(response),
    )


def _wrap_transport_exception(exc: httpx.HTTPError) -> APIConnectionError:
    if isinstance(exc, httpx.TimeoutException):
        return APITimeoutError(f"Request timed out: {exc}")
    return APIConnectionError(f"Connection failed: {exc}")


class SyncTransport:
    """Synchronous HTTP transport backed by :class:`httpx.Client`.

    Constructed once per :class:`~claude_compliance_sdk.ComplianceClient`
    and reused for the lifetime of the client. Caller is responsible for
    invoking :meth:`close` (or letting the parent client do so via its
    context manager).

    Args:
        api_key: Value sent in the ``x-api-key`` header.
        base_url: Base URL prepended to request paths.
        timeout: Per-request timeout, in seconds.
        anthropic_version: Value sent in the ``anthropic-version``
            header.
        max_retries: Maximum retries after the initial attempt. ``0``
            disables retries. Passed straight into the
            :class:`RetryPolicy`.
        rate_limit_rpm: Maximum requests per rolling 60-second window.
            ``0`` (or negative) disables the limiter. Smooths bursty
            callers; the server remains the source of truth.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float,
        anthropic_version: str,
        max_retries: int,
        rate_limit_rpm: int,
    ) -> None:
        self._client: httpx.Client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers=_build_default_headers(api_key, anthropic_version),
        )
        self.max_retries: int = max_retries
        self.rate_limit_rpm: int = rate_limit_rpm
        self._retry_policy: RetryPolicy = RetryPolicy(max_retries=max_retries)
        self._rate_limiter: SlidingWindowLimiter = SlidingWindowLimiter(rpm=rate_limit_rpm)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        stream: bool = False,
    ) -> Any:
        """Send a request and return parsed JSON or a streaming response.

        Args:
            method: HTTP method (e.g. ``"GET"``, ``"DELETE"``).
            path: Path relative to ``base_url``.
            params: Query parameters. Repeated keys (such as
                ``user_ids[]``) are supported via a list of tuples.
            json: JSON body for the request.
            headers: Per-request header overrides, merged on top of the
                client-level defaults.
            stream: When ``True``, the response is returned undrained as
                an :class:`httpx.Response` and the caller must close it.
                Used by the download helpers in Phase 3.5.

        Returns:
            The decoded JSON body as a ``dict``/``list``, ``None`` when
            the response had no body (e.g. ``204``), or an undrained
            :class:`httpx.Response` when ``stream=True``.

        Raises:
            APIError: On any non-2xx response (after retries exhausted).
                The subclass mirrors the status code.
            APITimeoutError: When the request exceeds ``timeout`` after
                retries.
            APIConnectionError: On any other transport-level failure
                after retries.
        """
        retry_index = 0
        while True:
            self._rate_limiter.acquire()
            try:
                response = self._client.send(
                    self._client.build_request(
                        method, path, params=params, json=json, headers=headers
                    ),
                    stream=stream,
                )
            except httpx.HTTPError as exc:
                if self._retry_policy.should_retry_exception(
                    retry_index=retry_index, method=method, exc=exc
                ):
                    time.sleep(self._retry_policy.compute_delay(retry_index=retry_index))
                    retry_index += 1
                    continue
                raise _wrap_transport_exception(exc) from exc

            if response.is_error:
                if stream:
                    response.read()
                    response.close()
                api_error = _build_api_error(response)
                if self._retry_policy.should_retry_status(
                    retry_index=retry_index, method=method, status_code=response.status_code
                ):
                    retry_after = (
                        api_error.retry_after if isinstance(api_error, RateLimitError) else None
                    )
                    time.sleep(
                        self._retry_policy.compute_delay(
                            retry_index=retry_index, retry_after=retry_after
                        )
                    )
                    retry_index += 1
                    continue
                raise api_error

            if stream:
                return response
            return _decode_body(response)

    def close(self) -> None:
        """Shut the underlying ``httpx.Client`` connection pool."""
        self._client.close()


class AsyncTransport:
    """Asynchronous HTTP transport backed by :class:`httpx.AsyncClient`.

    See :class:`SyncTransport` for the constructor contract and request
    semantics — this class is the async mirror.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float,
        anthropic_version: str,
        max_retries: int,
        rate_limit_rpm: int,
    ) -> None:
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers=_build_default_headers(api_key, anthropic_version),
        )
        self.max_retries: int = max_retries
        self.rate_limit_rpm: int = rate_limit_rpm
        self._retry_policy: RetryPolicy = RetryPolicy(max_retries=max_retries)
        self._rate_limiter: AsyncSlidingWindowLimiter = AsyncSlidingWindowLimiter(
            rpm=rate_limit_rpm
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        stream: bool = False,
    ) -> Any:
        """Async analogue of :meth:`SyncTransport.request`."""
        retry_index = 0
        while True:
            await self._rate_limiter.acquire()
            try:
                response = await self._client.send(
                    self._client.build_request(
                        method, path, params=params, json=json, headers=headers
                    ),
                    stream=stream,
                )
            except httpx.HTTPError as exc:
                if self._retry_policy.should_retry_exception(
                    retry_index=retry_index, method=method, exc=exc
                ):
                    await asyncio.sleep(self._retry_policy.compute_delay(retry_index=retry_index))
                    retry_index += 1
                    continue
                raise _wrap_transport_exception(exc) from exc

            if response.is_error:
                if stream:
                    await response.aread()
                    await response.aclose()
                api_error = _build_api_error(response)
                if self._retry_policy.should_retry_status(
                    retry_index=retry_index, method=method, status_code=response.status_code
                ):
                    retry_after = (
                        api_error.retry_after if isinstance(api_error, RateLimitError) else None
                    )
                    await asyncio.sleep(
                        self._retry_policy.compute_delay(
                            retry_index=retry_index, retry_after=retry_after
                        )
                    )
                    retry_index += 1
                    continue
                raise api_error

            if stream:
                return response
            return _decode_body(response)

    async def aclose(self) -> None:
        """Shut the underlying ``httpx.AsyncClient`` connection pool."""
        await self._client.aclose()
