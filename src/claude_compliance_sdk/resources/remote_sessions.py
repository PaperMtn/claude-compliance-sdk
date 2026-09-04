"""Remote Sessions resource group.

Remote sessions are Cowork sessions started on claude.ai web or mobile,
which run in the cloud in Anthropic-managed environments. Sessions that
run on users' own machines are a separate family — see
`local_sessions`.

Wraps two endpoints, both read-only. There is deliberately no
retrieve-one method: the API exposes a list and a transcript, but no
``GET /sessions/remote/{id}``.

* ``GET /v1/compliance/apps/sessions/remote`` — page of session
  metadata. Exposed via `list` and `iter`.
* ``GET /v1/compliance/apps/sessions/remote/{id}/messages`` — one
  session's transcript. Exposed via `list_messages` and
  `iter_messages`.

Requires a Compliance Access Key with ``read:compliance_user_data``.
Admin API keys are rejected with 403.

These endpoints count against a second request budget on top of the
shared Compliance API rate limit, so a 429 here can arrive well below
600 requests per minute.

Example:
    ```python
    from claude_compliance_sdk import ComplianceClient

    with ComplianceClient(api_key="sk-ant-api01-...") as client:
        for session in client.remote_sessions.iter(
            created_at_gte="2026-06-01T00:00:00Z",
        ):
            if session.status == "pending":
                continue  # No transcript until provisioning completes.
            transcript = client.remote_sessions.list_messages(session.id)
            print(session.id, len(transcript.messages.data))
    ```
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Mapping

from claude_compliance_sdk._internal.pagination import (
    OffsetPage,
    iter_all_offset_async,
    iter_all_offset_sync,
)
from claude_compliance_sdk._internal.parsing import parse_with_extra
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport
from claude_compliance_sdk.resources.local_sessions import SessionUser

# Module-level alias for the `list` builtin — see resources/activities.py
# for the rationale.
StrList = list[str]

REMOTE_SESSIONS_PATH = "/v1/compliance/apps/sessions/remote"

MAX_USER_IDS = 10
MAX_ORGANIZATION_IDS = 500
_REJECTED_MAX_BYTES = 0


@dataclass
class RemoteSession:
    """Metadata for one Cowork session running in the cloud.

    A session is owned by either a user or an agent, never both.

    Attributes:
        id: Session identifier (``cse_...``).
        organization_uuid: UUID of the organisation the session
            belongs to.
        created_at: When the session was created (RFC 3339, UTC).
        updated_at: When the session was last modified.
        status: Lifecycle state — ``pending``, ``active``, ``paused``,
            ``archived``, or ``failed``. A ``pending`` session has no
            transcript yet and its messages endpoint returns 404 until
            provisioning completes. Deleted sessions are never
            returned. Kept as a plain string so new states pass
            through.
        user: The owning user, or ``None`` on agent-owned sessions.
        agent_id: The owning agent (``cagt_...``), or ``None`` on
            user-owned sessions.
        started_by_user: On agent-owned sessions, the human who
            initiated the run — for example by starting a scheduled
            task. ``None`` on user-owned sessions.
        product_surface: Currently only ``cowork_remote``. ``None``
            when not recorded. Treat unrecognised values as an
            unclassified surface rather than an error.
        claude_project_id: The claude.ai project the session belongs
            to (``claude_proj_...``), or ``None``.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    organization_uuid: str
    created_at: str
    updated_at: str
    status: str
    user: SessionUser | None = None
    agent_id: str | None = None
    started_by_user: SessionUser | None = None
    product_surface: str | None = None
    claude_project_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "RemoteSession":
        """Build a `RemoteSession` from one decoded record."""
        session = parse_with_extra(cls, body)
        for attr in ("user", "started_by_user"):
            raw = body.get(attr)
            if isinstance(raw, Mapping):
                setattr(session, attr, SessionUser.from_dict(raw))
        return session


@dataclass
class RemoteSessionMessage:
    """One user or assistant turn in a remote session transcript.

    Attributes:
        id: Message identifier (``csev_...``).
        role: ``"user"`` or ``"assistant"``.
        created_at: A commit timestamp. Consecutive messages can share
            one or slightly invert, so preserve the returned order
            rather than re-sorting by this field.
        content: Content blocks, each a raw dict discriminated on
            ``type`` — ``text``, ``tool_use``, or ``tool_result``.
            Kept as dicts so unrecognised block types pass through. A
            ``tool_use`` block's ``input`` is a JSON-encoded *string*,
            and a truncated one is not valid JSON.
        sent_by_user_id: On agent-owned sessions, the user who sent
            this message when it is attributable. ``None`` otherwise,
            including on every assistant message.
        content_unavailable: ``True`` when the message's content could
            not be returned at all, for example because it exceeded
            size bounds.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    role: str
    created_at: str
    content: list[dict[str, Any]] = field(default_factory=list)
    sent_by_user_id: str | None = None
    content_unavailable: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "RemoteSessionMessage":
        """Build a `RemoteSessionMessage` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class RemoteSessionTranscript:
    """A page of transcript, plus the session it belongs to.

    Attributes:
        session: The session the messages belong to. On this endpoint
            its ``user.email_address``, ``started_by_user``, and
            ``claude_project_id`` are always ``None`` — read those from
            `list` instead.
        messages: One `OffsetPage` of `RemoteSessionMessage` objects.
    """

    session: RemoteSession
    messages: OffsetPage[RemoteSessionMessage]

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "RemoteSessionTranscript":
        """Split the envelope into a session and a page of messages."""
        raw_session = body.get("session")
        session = RemoteSession.from_dict(raw_session if isinstance(raw_session, Mapping) else {})
        messages = OffsetPage.from_dict(body, RemoteSessionMessage.from_dict)
        return cls(session=session, messages=messages)


def _messages_path(session_id: str) -> str:
    return f"{REMOTE_SESSIONS_PATH}/{session_id}/messages"


def _validate_id_filters(
    user_ids: Sequence[str] | None, organization_ids: Sequence[str] | None
) -> None:
    """Enforce the API's length caps on the two array filters."""
    if user_ids is not None and not 1 <= len(user_ids) <= MAX_USER_IDS:
        raise ValueError(
            f"user_ids must contain between 1 and {MAX_USER_IDS} user IDs "
            f"(got {len(user_ids)}). Pass user_ids=None to include every user."
        )
    if organization_ids is not None and len(organization_ids) > MAX_ORGANIZATION_IDS:
        raise ValueError(
            f"organization_ids accepts at most {MAX_ORGANIZATION_IDS} values "
            f"(got {len(organization_ids)})."
        )


def _validate_max_bytes(name: str, value: int | None) -> None:
    if value == _REJECTED_MAX_BYTES:
        raise ValueError(
            f"{name} must be a positive byte count or -1 for the server "
            "maximum; 0 is rejected by the Compliance API."
        )


def _build_list_params(
    *,
    organization_ids: StrList | None,
    user_ids: StrList | None,
    created_at_gte: str | None,
    created_at_gt: str | None,
    created_at_lte: str | None,
    created_at_lt: str | None,
    limit: int | None,
    page: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, values in (
        ("organization_ids", organization_ids),
        ("user_ids", user_ids),
    ):
        if values is not None:
            params[f"{name}[]"] = list(values)
    for name, value in (
        ("created_at.gte", created_at_gte),
        ("created_at.gt", created_at_gt),
        ("created_at.lte", created_at_lte),
        ("created_at.lt", created_at_lt),
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


class RemoteSessions:
    """Synchronous client for the remote session endpoints."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        organization_ids: StrList | None = None,
        user_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[RemoteSession]:
        """Fetch one page of remote session metadata, newest first.

        Defaults to every organisation the key can read. There is no
        ``updated_at`` filter on this endpoint.

        Args:
            organization_ids: Up to 500 organisation identifiers
                (``org_...`` or UUID). ``None`` includes them all.
            user_ids: 1–10 user IDs. Matches the session's *owning*
                user, so setting this excludes every agent-owned
                session. ``None`` includes them all.
            created_at_gte: ``created_at >= value`` (RFC 3339).
            created_at_gt: ``created_at > value``.
            created_at_lte: ``created_at <= value``.
            created_at_lt: ``created_at < value``.
            limit: Maximum results (default 100, max 500).
            page: Opaque token from a prior response's ``next_page``.

        Returns:
            One `OffsetPage` of `RemoteSession` objects.

        Raises:
            ValueError: When ``user_ids`` or ``organization_ids`` is
                outside the API's length caps.
            RateLimitError: These endpoints carry a second budget on
                top of the shared limit, so this can arrive well below
                600 requests per minute.
            InsufficientScopeError: When the key lacks
                ``read:compliance_user_data``.
        """
        _validate_id_filters(user_ids, organization_ids)
        body = self._transport.request(
            "GET",
            REMOTE_SESSIONS_PATH,
            params=_build_list_params(
                organization_ids=organization_ids,
                user_ids=user_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                limit=limit,
                page=page,
            ),
        )
        return OffsetPage.from_dict(body, RemoteSession.from_dict)

    def iter(
        self,
        *,
        organization_ids: StrList | None = None,
        user_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        limit: int | None = None,
    ) -> Iterator[RemoteSession]:
        """Iterate every matching remote session, auto-paginating.

        Same filters as `list` except that ``page`` is managed by the
        iterator.
        """
        _validate_id_filters(user_ids, organization_ids)
        return iter_all_offset_sync(
            self._transport,
            REMOTE_SESSIONS_PATH,
            RemoteSession.from_dict,
            params=_build_list_params(
                organization_ids=organization_ids,
                user_ids=user_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                limit=limit,
                page=None,
            ),
        )

    def list_messages(
        self,
        session_id: str,
        *,
        order: str | None = None,
        limit: int | None = None,
        page: str | None = None,
        tool_use_input_max_bytes: int | None = None,
        tool_result_max_bytes: int | None = None,
    ) -> RemoteSessionTranscript:
        """Fetch one page of a remote session's transcript.

        A page can end early when the response hits its size limit, so
        a short page does **not** mean you have reached the end. Keep
        paginating until ``next_page`` is ``None``.

        Args:
            session_id: Session identifier (``cse_...``).
            order: ``"asc"`` (oldest first, the server default) or
                ``"desc"``.
            limit: Maximum messages per page (default 100, max 1000).
            page: Opaque token from a prior response's ``next_page``.
            tool_use_input_max_bytes: Truncate each tool-use input to
                this many bytes (server default 10,000). ``-1`` asks
                for the server maximum. ``0`` raises `ValueError`.
            tool_result_max_bytes: Truncate each text item inside a
                tool result the same way.

        Returns:
            A `RemoteSessionTranscript` — the session envelope plus one
            page of messages.

        Raises:
            ValueError: When either truncation cap is ``0``.
            NotFoundError: When the session is still ``pending``, does
                not exist, has been deleted, or is in an organisation
                the key cannot read.
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
        return RemoteSessionTranscript.from_dict(body)

    def iter_messages(
        self,
        session_id: str,
        *,
        order: str | None = None,
        limit: int | None = None,
        tool_use_input_max_bytes: int | None = None,
        tool_result_max_bytes: int | None = None,
    ) -> Iterator[RemoteSessionMessage]:
        """Iterate a remote session's whole transcript, auto-paginating.

        Same arguments as `list_messages` except that ``page`` is
        managed by the iterator. The session envelope is dropped.
        """
        return iter_all_offset_sync(
            self._transport,
            _messages_path(session_id),
            RemoteSessionMessage.from_dict,
            params=_build_messages_params(
                order=order,
                limit=limit,
                page=None,
                tool_use_input_max_bytes=tool_use_input_max_bytes,
                tool_result_max_bytes=tool_result_max_bytes,
            ),
        )


class AsyncRemoteSessions:
    """Asynchronous client for the remote session endpoints."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        organization_ids: StrList | None = None,
        user_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[RemoteSession]:
        """Async analogue of `list`."""
        _validate_id_filters(user_ids, organization_ids)
        body = await self._transport.request(
            "GET",
            REMOTE_SESSIONS_PATH,
            params=_build_list_params(
                organization_ids=organization_ids,
                user_ids=user_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                limit=limit,
                page=page,
            ),
        )
        return OffsetPage.from_dict(body, RemoteSession.from_dict)

    def iter(
        self,
        *,
        organization_ids: StrList | None = None,
        user_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[RemoteSession]:
        """Async analogue of `iter`."""
        _validate_id_filters(user_ids, organization_ids)
        return iter_all_offset_async(
            self._transport,
            REMOTE_SESSIONS_PATH,
            RemoteSession.from_dict,
            params=_build_list_params(
                organization_ids=organization_ids,
                user_ids=user_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                limit=limit,
                page=None,
            ),
        )

    async def list_messages(
        self,
        session_id: str,
        *,
        order: str | None = None,
        limit: int | None = None,
        page: str | None = None,
        tool_use_input_max_bytes: int | None = None,
        tool_result_max_bytes: int | None = None,
    ) -> RemoteSessionTranscript:
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
        return RemoteSessionTranscript.from_dict(body)

    def iter_messages(
        self,
        session_id: str,
        *,
        order: str | None = None,
        limit: int | None = None,
        tool_use_input_max_bytes: int | None = None,
        tool_result_max_bytes: int | None = None,
    ) -> AsyncIterator[RemoteSessionMessage]:
        """Async analogue of `iter_messages`."""
        return iter_all_offset_async(
            self._transport,
            _messages_path(session_id),
            RemoteSessionMessage.from_dict,
            params=_build_messages_params(
                order=order,
                limit=limit,
                page=None,
                tool_use_input_max_bytes=tool_use_input_max_bytes,
                tool_result_max_bytes=tool_result_max_bytes,
            ),
        )
