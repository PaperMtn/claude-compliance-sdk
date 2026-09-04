"""Local Sessions resource group.

Local sessions are the conversations your users run in Claude apps on
their own machines while signed in with a Claude Enterprise account:
Cowork in Claude Desktop, Claude Code (terminal, desktop, or IDE
extension), the Claude Science desktop app, and Claude for Microsoft
365. Sessions that run in Anthropic-managed cloud environments are a
separate family — see `remote_sessions`.

Wraps three endpoints, all read-only:

* ``GET /v1/compliance/apps/sessions/local`` — page of session
  metadata. Exposed via `list` and `iter`.
* ``GET /v1/compliance/apps/sessions/local/{id}`` — one session's
  metadata. Exposed via `get`.
* ``GET /v1/compliance/apps/sessions/local/{id}/messages`` — one
  session's transcript. Exposed via `list_messages` and
  `iter_messages`.

Requires a Compliance Access Key with ``read:compliance_user_data``.
Admin API keys are rejected with 403.

Example:
    ```python
    from claude_compliance_sdk import ComplianceClient

    with ComplianceClient(api_key="sk-ant-api01-...") as client:
        for session in client.local_sessions.iter(
            created_at_gte="2026-07-01T00:00:00Z",
        ):
            print(session.id, session.product_surface)
            for message in client.local_sessions.iter_messages(session.id):
                print("  ", message.role, message.content)
    ```
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any, Mapping

from claude_compliance_sdk._internal.pagination import (
    OffsetPage,
    iter_all_offset_async,
    iter_all_offset_sync,
)
from claude_compliance_sdk._internal.parsing import parse_with_extra
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

LOCAL_SESSIONS_PATH = "/v1/compliance/apps/sessions/local"

# `0` is the one truncation value the API rejects outright; `-1` asks
# for the server maximum and any positive count is clamped to it.
_REJECTED_MAX_BYTES = 0


@dataclass
class SessionUser:
    """A user associated with a session.

    Attributes:
        id: Tagged user identifier (``user_...``). Always set on local
            sessions, so attribution survives the account being
            deleted.
        email_address: Current email address, or ``None``. On the list
            and retrieve endpoints ``None`` means the account was
            deleted or the user is no longer in an organisation the key
            can read. On the **messages** endpoint it is *always*
            ``None`` — that endpoint does not resolve email addresses,
            so join on `id` instead of reading anything into it.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    email_address: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "SessionUser":
        """Build a `SessionUser` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class LocalSession:
    """Metadata for one session run on a user's machine.

    Attributes:
        id: Session identifier (``clls_...``). Opaque; the format may
            change without notice.
        type: Always ``"compliance_local_session"``.
        organization_uuid: UUID of the organisation the session ran in.
        user: The authenticated user at the time of the session.
        product_surface: Which product created the session —
            ``cowork``, ``claude_code``, ``claude_science``, or one of
            the ``office_agents/...`` values. ``None`` when not
            recorded. Kept as a plain string: new surfaces ship as
            coverage expands, and unrecognised values must pass
            through rather than raise.
        created_at: Timestamp of the session's earliest *retained*
            call. This advances as older calls age out of retention, so
            deduplicate on `id` rather than assuming it is stable.
        updated_at: Timestamp of the session's last retained call. On
            the list endpoint this is a lower bound and can briefly lag
            a still-active session's true last activity.
        workspace_id: Tagged workspace identifier (``wrkspc_...``), or
            ``None`` when the session had no workspace.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    organization_uuid: str
    created_at: str
    updated_at: str
    type: str = "compliance_local_session"
    user: SessionUser | None = None
    product_surface: str | None = None
    workspace_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "LocalSession":
        """Build a `LocalSession` from one decoded record."""
        session = parse_with_extra(cls, body)
        raw_user = body.get("user")
        if isinstance(raw_user, Mapping):
            session.user = SessionUser.from_dict(raw_user)
        return session


@dataclass
class LocalSessionMessage:
    """One user or assistant turn in a local session transcript.

    Attributes:
        id: Message identifier (``clsm_...``), stable for as long as
            the turn is retained.
        role: ``"user"`` or ``"assistant"``.
        created_at: When the message was recorded. Every message
            reconstructed from the same inference call carries that
            call's timestamp, so consecutive messages often share one.
            Preserve the returned order rather than re-sorting.
        content: Content blocks, each a raw dict discriminated on
            ``type`` — ``text``, ``tool_use``, or ``tool_result``.
            Kept as dicts so block types that have not shipped yet pass
            through untouched. Note that a ``tool_use`` block's
            ``input`` is a JSON-encoded *string*, and a truncated one
            is no longer valid JSON.
        model: The model that served an assistant turn, or ``None`` on
            user messages and on any message carrying `provenance`.
        provenance: ``None`` for verified content, which is the common
            case. Otherwise a dict whose ``type`` marks the exception:
            ``content_unavailable`` (with a ``reason``),
            ``client_asserted``, or ``synthetic_marker``. Kept as a raw
            dict; tolerate unrecognised types and reasons.
        type: Always ``"compliance_local_session_message"``.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    role: str
    created_at: str
    content: list[dict[str, Any]] = field(default_factory=list)
    model: str | None = None
    provenance: dict[str, Any] | None = None
    type: str = "compliance_local_session_message"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "LocalSessionMessage":
        """Build a `LocalSessionMessage` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class LocalSessionTranscript:
    """A page of transcript, plus the session it belongs to.

    The messages endpoint returns a ``session`` envelope alongside the
    paginated ``data`` array, so the SDK exposes them together rather
    than making the caller re-fetch metadata.

    Attributes:
        session: The session the messages belong to. Its
            ``user.email_address`` is always ``None`` on this endpoint.
        messages: One `OffsetPage` of `LocalSessionMessage` objects.
    """

    session: LocalSession
    messages: OffsetPage[LocalSessionMessage]

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "LocalSessionTranscript":
        """Split the envelope into a session and a page of messages."""
        raw_session = body.get("session")
        session = LocalSession.from_dict(raw_session if isinstance(raw_session, Mapping) else {})
        messages = OffsetPage.from_dict(body, LocalSessionMessage.from_dict)
        return cls(session=session, messages=messages)


def _session_path(session_id: str) -> str:
    return f"{LOCAL_SESSIONS_PATH}/{session_id}"


def _messages_path(session_id: str) -> str:
    return f"{LOCAL_SESSIONS_PATH}/{session_id}/messages"


def _validate_max_bytes(name: str, value: int | None) -> None:
    """Reject the one truncation value the API refuses.

    Cheap input-shape check. Any positive count is valid and ``-1``
    means "server maximum"; only ``0`` is a guaranteed 400.
    """
    if value == _REJECTED_MAX_BYTES:
        raise ValueError(
            f"{name} must be a positive byte count or -1 for the server "
            "maximum; 0 is rejected by the Compliance API."
        )


def _build_list_params(
    *,
    created_at_gte: str | None,
    created_at_lt: str | None,
    updated_at_gte: str | None,
    limit: int | None,
    page: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, value in (
        ("created_at.gte", created_at_gte),
        ("created_at.lt", created_at_lt),
        ("updated_at.gte", updated_at_gte),
        ("page", page),
    ):
        if value is not None:
            params[name] = value
    if limit is not None:
        params["limit"] = limit
    return params


def _build_messages_params(
    *,
    order: str | None,
    limit: int | None,
    page: str | None,
    tool_use_input_max_bytes: int | None,
    tool_result_max_bytes: int | None,
) -> dict[str, Any]:
    _validate_max_bytes("tool_use_input_max_bytes", tool_use_input_max_bytes)
    _validate_max_bytes("tool_result_max_bytes", tool_result_max_bytes)
    params: dict[str, Any] = {}
    if order is not None:
        params["order"] = order
    if page is not None:
        params["page"] = page
    for name, number in (
        ("limit", limit),
        ("tool_use_input_max_bytes", tool_use_input_max_bytes),
        ("tool_result_max_bytes", tool_result_max_bytes),
    ):
        if number is not None:
            params[name] = number
    return params


class LocalSessions:
    """Synchronous client for the local session endpoints."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        created_at_gte: str | None = None,
        created_at_lt: str | None = None,
        updated_at_gte: str | None = None,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[LocalSession]:
        """Fetch one page of local session metadata, newest first.

        The endpoint has no organisation or user filter, so bound the
        results in time instead. To poll for sessions active since a
        previous pass, use ``updated_at_gte`` set a few minutes *before*
        your last run started: a bound set to the exact previous time
        silently and permanently drops a session whose final call was
        still being indexed at that moment.

        Args:
            created_at_gte: Sessions whose first call is at or after
                this time (RFC 3339, UTC offset required).
            created_at_lt: Sessions whose first call is strictly before
                this time. When both bounds are given this must be
                strictly after ``created_at_gte``, or the API returns
                400.
            updated_at_gte: Sessions whose last call is at or after
                this time. Combines with the ``created_at`` bounds
                without changing the ordering.
            limit: Maximum results (default 100, max 500).
            page: Opaque token from a prior response's ``next_page``.
                Complete a walk within 24 hours; an older token is
                still accepted but is re-evaluated against the current
                retention boundary and can skip sessions.

        Returns:
            One `OffsetPage` of `LocalSession` objects.

        Raises:
            LocalSessionsUnavailableError: When local sessions are not
                available to the parent organisation. Keep any queued
                session IDs and retry on a later run.
            InsufficientScopeError: When the key lacks
                ``read:compliance_user_data``.
            APIError: For any other non-2xx response.
        """
        body = self._transport.request(
            "GET",
            LOCAL_SESSIONS_PATH,
            params=_build_list_params(
                created_at_gte=created_at_gte,
                created_at_lt=created_at_lt,
                updated_at_gte=updated_at_gte,
                limit=limit,
                page=page,
            ),
        )
        return OffsetPage.from_dict(body, LocalSession.from_dict)

    def iter(
        self,
        *,
        created_at_gte: str | None = None,
        created_at_lt: str | None = None,
        updated_at_gte: str | None = None,
        limit: int | None = None,
    ) -> Iterator[LocalSession]:
        """Iterate every matching local session, auto-paginating.

        Same filters as `list` except that ``page`` is managed by the
        iterator. Because ``created_at`` shifts as calls age out of
        retention, deduplicate on `id` when you re-walk over time.
        """
        return iter_all_offset_sync(
            self._transport,
            LOCAL_SESSIONS_PATH,
            LocalSession.from_dict,
            params=_build_list_params(
                created_at_gte=created_at_gte,
                created_at_lt=created_at_lt,
                updated_at_gte=updated_at_gte,
                limit=limit,
                page=None,
            ),
        )

    def get(self, session_id: str) -> LocalSession:
        """Fetch one local session's metadata, with no transcript.

        Args:
            session_id: Session identifier (``clls_...``).

        Raises:
            BadRequestError: When ``session_id`` is not a well-formed
                ``clls_`` identifier.
            LocalSessionsUnavailableError: When local sessions are not
                available to the parent organisation.
            NotFoundError: When the session is not readable by this
                key, never existed, is under zero data retention, or
                has entirely aged past retention. The API does not
                distinguish these four.
        """
        body = self._transport.request("GET", _session_path(session_id))
        return LocalSession.from_dict(body)

    def list_messages(
        self,
        session_id: str,
        *,
        order: str | None = None,
        limit: int | None = None,
        page: str | None = None,
        tool_use_input_max_bytes: int | None = None,
        tool_result_max_bytes: int | None = None,
    ) -> LocalSessionTranscript:
        """Fetch one page of a local session's transcript.

        A page can end early when the response hits its size limit, so
        a short page does **not** mean you have reached the end. Keep
        paginating until ``next_page`` is ``None``.

        Args:
            session_id: Session identifier (``clls_...``).
            order: ``"asc"`` (oldest first, the server default) or
                ``"desc"``.
            limit: Maximum messages per page (default 100, max 1000).
            page: Opaque token from a prior response's ``next_page``.
                Cursors are bound to the session *and* the sort order
                they were issued under, and expire 24 hours after the
                walk's first page.
            tool_use_input_max_bytes: Truncate each tool-use input to
                this many bytes (server default 10,000). ``-1`` asks
                for the server maximum, roughly 1 MiB. ``0`` raises
                `ValueError`.
            tool_result_max_bytes: Truncate each text item inside a
                tool result the same way.

        Returns:
            A `LocalSessionTranscript` — the session envelope plus one
            page of messages.

        Raises:
            ValueError: When either truncation cap is ``0``.
            BadRequestError: For a malformed session ID, or a ``page``
                cursor that is expired or was issued for a different
                session or sort order.
            LocalSessionsRetentionUnavailableError: When a retention
                setting could not be evaluated. Not transient — skip
                the session and retry on a later run rather than
                holding the walk open.
            NotFoundError: When every call in the session has aged past
                retention, or the session is otherwise unreadable.
        """
        body = self._transport.request(
            "GET",
            _messages_path(session_id),
            params=_build_messages_params(
                order=order,
                limit=limit,
                page=page,
                tool_use_input_max_bytes=tool_use_input_max_bytes,
                tool_result_max_bytes=tool_result_max_bytes,
            ),
        )
        return LocalSessionTranscript.from_dict(body)

    def iter_messages(
        self,
        session_id: str,
        *,
        order: str | None = None,
        limit: int | None = None,
        tool_use_input_max_bytes: int | None = None,
        tool_result_max_bytes: int | None = None,
    ) -> Iterator[LocalSessionMessage]:
        """Iterate a local session's whole transcript, auto-paginating.

        Same arguments as `list_messages` except that ``page`` is
        managed by the iterator. The session envelope is dropped; call
        `get` if you need it.
        """
        return iter_all_offset_sync(
            self._transport,
            _messages_path(session_id),
            LocalSessionMessage.from_dict,
            params=_build_messages_params(
                order=order,
                limit=limit,
                page=None,
                tool_use_input_max_bytes=tool_use_input_max_bytes,
                tool_result_max_bytes=tool_result_max_bytes,
            ),
        )


class AsyncLocalSessions:
    """Asynchronous client for the local session endpoints."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        created_at_gte: str | None = None,
        created_at_lt: str | None = None,
        updated_at_gte: str | None = None,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[LocalSession]:
        """Async analogue of `list`."""
        body = await self._transport.request(
            "GET",
            LOCAL_SESSIONS_PATH,
            params=_build_list_params(
                created_at_gte=created_at_gte,
                created_at_lt=created_at_lt,
                updated_at_gte=updated_at_gte,
                limit=limit,
                page=page,
            ),
        )
        return OffsetPage.from_dict(body, LocalSession.from_dict)

    def iter(
        self,
        *,
        created_at_gte: str | None = None,
        created_at_lt: str | None = None,
        updated_at_gte: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[LocalSession]:
        """Async analogue of `iter`."""
        return iter_all_offset_async(
            self._transport,
            LOCAL_SESSIONS_PATH,
            LocalSession.from_dict,
            params=_build_list_params(
                created_at_gte=created_at_gte,
                created_at_lt=created_at_lt,
                updated_at_gte=updated_at_gte,
                limit=limit,
                page=None,
            ),
        )

    async def get(self, session_id: str) -> LocalSession:
        """Async analogue of `get`."""
        body = await self._transport.request("GET", _session_path(session_id))
        return LocalSession.from_dict(body)

    async def list_messages(
        self,
        session_id: str,
        *,
        order: str | None = None,
        limit: int | None = None,
        page: str | None = None,
        tool_use_input_max_bytes: int | None = None,
        tool_result_max_bytes: int | None = None,
    ) -> LocalSessionTranscript:
        """Async analogue of `list_messages`."""
        body = await self._transport.request(
            "GET",
            _messages_path(session_id),
            params=_build_messages_params(
                order=order,
                limit=limit,
                page=page,
                tool_use_input_max_bytes=tool_use_input_max_bytes,
                tool_result_max_bytes=tool_result_max_bytes,
            ),
        )
        return LocalSessionTranscript.from_dict(body)

    def iter_messages(
        self,
        session_id: str,
        *,
        order: str | None = None,
        limit: int | None = None,
        tool_use_input_max_bytes: int | None = None,
        tool_result_max_bytes: int | None = None,
    ) -> AsyncIterator[LocalSessionMessage]:
        """Async analogue of `iter_messages`."""
        return iter_all_offset_async(
            self._transport,
            _messages_path(session_id),
            LocalSessionMessage.from_dict,
            params=_build_messages_params(
                order=order,
                limit=limit,
                page=None,
                tool_use_input_max_bytes=tool_use_input_max_bytes,
                tool_result_max_bytes=tool_result_max_bytes,
            ),
        )
