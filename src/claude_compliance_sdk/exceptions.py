"""Exception hierarchy for the Anthropic Compliance SDK.

All errors raised by ``claude_compliance_sdk`` derive from
:class:`ComplianceClientError`. The tree separates HTTP failures
(everything under :class:`APIError`) from transport-level failures
(everything under :class:`APIConnectionError`) so callers can catch the
two cases independently.

The Compliance API returns errors in a single JSON shape::

    {"error": {"type": "...", "message": "..."}}

Each :class:`APIError` instance carries the HTTP status code, the
``request-id`` response header, the server's ``error.type`` and
``error.message`` parsed from the body, and the raw decoded body. Use
:meth:`APIError.from_response` from the transport layer to build the
right subclass from an HTTP response.

The 401 split is intentional. The server is the source of truth — the
client only labels a 401 as :class:`InvalidAPIKeyError` or
:class:`InsufficientScopeError` for ergonomics, by looking for ``scope``
or ``permission`` in the error message.

Example:
    >>> from claude_compliance_sdk import (
    ...     ComplianceClient,
    ...     InsufficientScopeError,
    ...     RateLimitError,
    ... )
    >>> try:
    ...     ComplianceClient(api_key="sk-ant-api01-...").activities.list()
    ... except InsufficientScopeError as exc:
    ...     print("missing scope:", exc.error_message)
    ... except RateLimitError as exc:
    ...     print("retry after", exc.retry_after, "seconds")
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

__all__ = [
    "APIConnectionError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "ComplianceClientError",
    "ConflictError",
    "InsufficientScopeError",
    "InternalServerError",
    "InvalidAPIKeyError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
]


class ComplianceClientError(Exception):
    """Base class for every error raised by the SDK.

    Catch this to handle any SDK-originated failure regardless of
    whether the cause was an HTTP response or a transport-level
    problem.
    """


# ---------------------------------------------------------------------------
# HTTP errors
# ---------------------------------------------------------------------------


class APIError(ComplianceClientError):
    """Error returned by the Compliance API as a non-2xx HTTP response.

    Attributes:
        status_code: HTTP status code from the response.
        request_id: Value of the ``request-id`` response header, if any.
            Use this when filing support tickets.
        error_type: Server-supplied ``error.type`` string (for example
            ``authentication_error``), if the body matched the expected
            shape.
        error_message: Server-supplied ``error.message`` string, if the
            body matched the expected shape.
        body: The decoded response body. Typically a ``dict``, but may
            be ``str`` or ``bytes`` if the body was not JSON.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        request_id: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code: int = status_code
        self.request_id: str | None = request_id
        self.error_type: str | None = error_type
        self.error_message: str | None = error_message
        self.body: Any = body

    @classmethod
    def from_response(
        cls,
        *,
        status_code: int,
        headers: Mapping[str, str] | None = None,
        body: Any = None,
    ) -> "APIError":
        """Build the right :class:`APIError` subclass from a response.

        Routes by status code, parses ``error.type`` / ``error.message``
        out of the body when present, lifts ``request-id`` from headers,
        and on 429 parses ``Retry-After`` into seconds.

        Args:
            status_code: HTTP status code from the response.
            headers: Response headers, case-insensitive mapping
                preferred (``httpx.Headers`` works). Used to read
                ``request-id`` and, for 429, ``Retry-After``.
            body: Decoded response body. ``dict`` is preferred so the
                ``error.type`` and ``error.message`` fields can be
                extracted; any other type is stored verbatim and the
                parsed fields stay ``None``.

        Returns:
            An :class:`APIError` subclass instance matching the status
            code. 401 is split between :class:`InvalidAPIKeyError` and
            :class:`InsufficientScopeError`; 429 returns a
            :class:`RateLimitError` with ``retry_after`` populated.
        """
        headers = headers or {}
        request_id = _lookup_header(headers, "request-id") or _lookup_header(
            headers, "x-request-id"
        )
        error_type, error_message = _extract_error_fields(body)
        summary = _format_summary(status_code, error_type, error_message)

        if status_code == 400:
            klass: type[APIError] = BadRequestError
        elif status_code == 401:
            klass = _classify_authentication(error_message)
        elif status_code == 403:
            klass = PermissionDeniedError
        elif status_code == 404:
            klass = NotFoundError
        elif status_code == 409:
            klass = ConflictError
        elif status_code == 429:
            retry_after = _parse_retry_after(_lookup_header(headers, "retry-after"))
            return RateLimitError(
                summary,
                status_code=status_code,
                request_id=request_id,
                error_type=error_type,
                error_message=error_message,
                body=body,
                retry_after=retry_after,
            )
        elif 400 <= status_code < 500:
            klass = APIStatusError
        elif 500 <= status_code < 600:
            klass = InternalServerError
        else:
            klass = APIError

        return klass(
            summary,
            status_code=status_code,
            request_id=request_id,
            error_type=error_type,
            error_message=error_message,
            body=body,
        )


class BadRequestError(APIError):
    """HTTP 400 — request was malformed or violated input constraints."""


class AuthenticationError(APIError):
    """HTTP 401 — base class for authentication failures.

    The SDK refines a 401 into :class:`InvalidAPIKeyError` or
    :class:`InsufficientScopeError` by inspecting ``error.message``.
    Catch this class to handle either case uniformly.
    """


class InvalidAPIKeyError(AuthenticationError):
    """HTTP 401 where the API key itself is invalid or revoked."""


class InsufficientScopeError(AuthenticationError):
    """HTTP 401 where the key is valid but lacks a required scope."""


class PermissionDeniedError(APIError):
    """HTTP 403 — the caller is authenticated but not permitted."""


class NotFoundError(APIError):
    """HTTP 404 — the addressed resource does not exist."""


class ConflictError(APIError):
    """HTTP 409 — request conflicts with current server state.

    Raised, for example, when deleting a project that still has chats
    attached.
    """


class RateLimitError(APIError):
    """HTTP 429 — the server-side rate limit (600 RPM) was exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying, parsed from the
            ``Retry-After`` response header. ``None`` when the server
            did not supply one. HTTP-date values are converted to a
            non-negative seconds delta from the current time.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        request_id: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        body: Any = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            request_id=request_id,
            error_type=error_type,
            error_message=error_message,
            body=body,
        )
        self.retry_after: float | None = retry_after


class APIStatusError(APIError):
    """A 4xx status code outside the explicitly modelled set."""


class InternalServerError(APIError):
    """HTTP 5xx — the server failed to handle the request."""


# ---------------------------------------------------------------------------
# Transport errors
# ---------------------------------------------------------------------------


class APIConnectionError(ComplianceClientError):
    """The request could not reach the server or the response was lost.

    Wraps DNS failures, TCP/TLS errors, and any other transport-level
    fault raised by the underlying HTTP client.
    """


class APITimeoutError(APIConnectionError):
    """The request exceeded the configured per-request timeout."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lookup_header(headers: Mapping[str, str], name: str) -> str | None:
    # httpx.Headers is case-insensitive; plain dicts are not, so retry
    # the Title-Case variant for callers passing a raw dict.
    value = headers.get(name)
    if value is not None:
        return value
    return headers.get(name.title())


def _extract_error_fields(body: Any) -> tuple[str | None, str | None]:
    if not isinstance(body, dict):
        return None, None
    error_obj = body.get("error")
    if not isinstance(error_obj, dict):
        return None, None
    error_type = error_obj.get("type")
    error_message = error_obj.get("message")
    return (
        error_type if isinstance(error_type, str) else None,
        error_message if isinstance(error_message, str) else None,
    )


def _classify_authentication(error_message: str | None) -> type[AuthenticationError]:
    if error_message is None:
        return InvalidAPIKeyError
    lowered = error_message.lower()
    if "scope" in lowered or "permission" in lowered:
        return InsufficientScopeError
    return InvalidAPIKeyError


def _format_summary(
    status_code: int,
    error_type: str | None,
    error_message: str | None,
) -> str:
    parts = [f"HTTP {status_code}"]
    if error_type:
        parts.append(error_type)
    if error_message:
        return f"{' '.join(parts)}: {error_message}"
    return " ".join(parts)


def _parse_retry_after(raw: str | None) -> float | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        return None
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    delta = (target - datetime.now(tz=timezone.utc)).total_seconds()
    return max(0.0, delta)
