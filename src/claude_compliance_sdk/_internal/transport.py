"""HTTP transport for the Compliance SDK.

Two concrete classes — :class:`SyncTransport` and :class:`AsyncTransport`
— wrap :class:`httpx.Client` and :class:`httpx.AsyncClient` respectively.
Each exposes a single ``request()`` entry point used by every resource
group, with header injection, error mapping, and ``request_id`` lift
handled in one place so resources stay thin.

Retry and rate-limit hooks land in Phase 2.3 and 2.4. For now the
transport sends a single request per call. ``max_retries`` and
``rate_limit_rpm`` are accepted in ``__init__`` so the public client
config can flow through unchanged when those layers wire in.
"""

from __future__ import annotations

import platform
from typing import Any, Mapping

import httpx

from claude_compliance_sdk._internal.base_transport import (
    BaseAsyncTransport,
    BaseTransport,
)
from claude_compliance_sdk.exceptions import (
    APIConnectionError,
    APIError,
    APITimeoutError,
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


def _raise_for_error(response: httpx.Response) -> None:
    raise APIError.from_response(
        status_code=response.status_code,
        headers=response.headers,
        body=_decode_body(response),
    )


class SyncTransport(BaseTransport):
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
        max_retries: Accepted now; consumed by the retry layer in Phase
            2.3. Stored as :attr:`max_retries`.
        rate_limit_rpm: Accepted now; consumed by the rate-limit layer
            in Phase 2.4. Stored as :attr:`rate_limit_rpm`.
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
            APIError: On any non-2xx response. The subclass mirrors the
                status code.
            APITimeoutError: When the request exceeds ``timeout``.
            APIConnectionError: On any other transport-level failure.
        """
        request = self._client.build_request(
            method, path, params=params, json=json, headers=headers
        )
        try:
            response = self._client.send(request, stream=stream)
        except httpx.TimeoutException as exc:
            raise APITimeoutError(f"Request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise APIConnectionError(f"Connection failed: {exc}") from exc

        if response.is_error:
            # The error path needs the body, so any streaming response
            # must be drained before we can decode it.
            if stream:
                response.read()
                response.close()
            _raise_for_error(response)

        if stream:
            return response
        return _decode_body(response)

    def close(self) -> None:
        """Shut the underlying ``httpx.Client`` connection pool."""
        self._client.close()


class AsyncTransport(BaseAsyncTransport):
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
        request = self._client.build_request(
            method, path, params=params, json=json, headers=headers
        )
        try:
            response = await self._client.send(request, stream=stream)
        except httpx.TimeoutException as exc:
            raise APITimeoutError(f"Request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise APIConnectionError(f"Connection failed: {exc}") from exc

        if response.is_error:
            if stream:
                await response.aread()
                await response.aclose()
            _raise_for_error(response)

        if stream:
            return response
        return _decode_body(response)

    async def aclose(self) -> None:
        """Shut the underlying ``httpx.AsyncClient`` connection pool."""
        await self._client.aclose()
