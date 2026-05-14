"""Chats resource group.

Wraps three Compliance API endpoints:

* ``GET /v1/compliance/apps/chats`` — cursor-paginated chat metadata
  list. ``user_ids[]`` is **required** and must carry 1–10 IDs; the
  SDK validates the length client-side (cheap input-shape check, per
  CONTEXT.md decision 14) and raises :class:`ValueError` outside that
  range without touching the network.
* ``GET /v1/compliance/apps/chats/{claude_chat_id}/messages`` — the
  only way to fetch a single chat. Returns the chat metadata
  alongside one cursor-paginated page of messages. Exposed via two
  methods:

  * :meth:`Chats.get` returns a :class:`ChatMessagesPage` carrying
    both the chat and the message page so callers can read either.
  * :meth:`Chats.iter_messages` drives the same endpoint with a
    custom cursor loop and yields :class:`Message` objects one at a
    time.

* ``DELETE /v1/compliance/apps/chats/{claude_chat_id}`` — destructive
  delete. The chat record persists with ``deleted_at`` populated
  (soft-delete data model) but cannot be undone. Returns ``None``.

PLAN.md described an additional ``GET /v1/compliance/apps/chats/{id}``
single-fetch endpoint; the spec (Rev K) does not expose one, so
:meth:`Chats.get` uses the messages endpoint and reads chat fields
from its response.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Mapping

from claude_compliance_sdk._internal.pagination import CursorPage
from claude_compliance_sdk._internal.parsing import parse_with_extra
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

# Module-level alias for the `list` builtin — see resources/activities.py
# for the rationale.
StrList = list[str]

CHATS_PATH = "/v1/compliance/apps/chats"

# Top-level response keys that belong to the message-page wrapper rather
# than to the chat itself. Pulled out before parsing the chat fields so
# they do not leak into ``Chat.extra``.
_MESSAGE_PAGE_KEYS = frozenset({"chat_messages", "has_more", "first_id", "last_id"})


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Chat:
    """A single chat's metadata (list shape).

    Attributes:
        id: Tagged chat identifier (``claude_chat_...``).
        name: Display name.
        created_at: RFC 3339 creation timestamp.
        updated_at: RFC 3339 last-update timestamp.
        organization_id: Owning organisation's tagged ID.
        model: Model the chat ran against (e.g. ``claude-opus-4-7``).
        href: Direct claude.ai URL for the chat.
        deleted_at: RFC 3339 deletion timestamp, or ``None`` while
            the chat is still active. The server keeps the chat
            record after a delete; this field marks it.
        organization_uuid: Organisation UUID (alternate identifier),
            or ``None`` when not provided by the spec response.
        project_id: Owning project's tagged ID, or ``None`` for
            standalone chats.
        user: Creator info (``id``, ``email_address``) or ``None``.
            Kept as a raw dict per ADR-0002.
        extra: Any additional fields the spec adds in a later revision.
    """

    id: str
    name: str
    created_at: str
    updated_at: str
    organization_id: str
    model: str
    href: str
    deleted_at: str | None = None
    organization_uuid: str | None = None
    project_id: str | None = None
    user: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Chat":
        """Build a :class:`Chat` from one decoded record.

        Strips the message-page wrapper keys before delegating to
        :func:`parse_with_extra` so the chat's :attr:`extra` does not
        carry pagination cruft when the body comes from the
        ``/messages`` endpoint.
        """
        chat_only = {k: v for k, v in body.items() if k not in _MESSAGE_PAGE_KEYS}
        return parse_with_extra(cls, chat_only)


@dataclass
class Message:
    """A single message within a chat.

    Content blocks, file attachments, and artifact references are
    stored as raw dicts per ADR-0002 — typed unions for those nested
    shapes can land later if they earn their keep.

    Attributes:
        id: Tagged message identifier (``claude_chat_msg_...``).
        role: ``"user"`` or ``"assistant"``.
        created_at: RFC 3339 creation timestamp.
        content: List of content blocks. Each block has at least a
            ``type`` discriminator (e.g. ``"text"``).
        files: User-uploaded file references attached to the message,
            or ``None`` when the message has no files.
        artifacts: Artifact references generated alongside an
            assistant message, or ``None`` when there are none.
        extra: Any additional fields the spec adds in a later revision.
    """

    id: str
    role: str
    created_at: str
    content: list[dict[str, Any]]
    files: list[dict[str, Any]] | None = None
    artifacts: list[dict[str, Any]] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Message":
        """Build a :class:`Message` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class ChatMessagesPage:
    """Result of :meth:`Chats.get` — chat metadata plus one page of messages.

    The Compliance API returns these together from a single endpoint,
    so this wrapper makes the join explicit on the SDK side rather
    than scattering pagination fields across :class:`Chat`.

    Attributes:
        chat: The chat's metadata.
        messages: One :class:`CursorPage` of :class:`Message` for the
            chat. Drive further pages by passing
            ``messages.last_id`` as ``after_id`` to the next
            :meth:`Chats.get` call.
    """

    chat: Chat
    messages: CursorPage[Message]

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "ChatMessagesPage":
        """Build a :class:`ChatMessagesPage` from the ``/messages`` response."""
        chat = Chat.from_dict(body)
        messages_body = {
            "data": body.get("chat_messages") or [],
            "has_more": body.get("has_more", False),
            "first_id": body.get("first_id"),
            "last_id": body.get("last_id"),
        }
        messages = CursorPage.from_dict(messages_body, Message.from_dict)
        return cls(chat=chat, messages=messages)


# ---------------------------------------------------------------------------
# Validation, paths, and param helpers
# ---------------------------------------------------------------------------


def _validate_user_ids(user_ids: Sequence[str]) -> None:
    """Enforce the spec's 1–10 length on ``user_ids[]``.

    Cheap input-shape check that runs locally; the server still
    enforces and the SDK only labels.
    """
    count = len(user_ids)
    if count < 1 or count > 10:
        raise ValueError(
            "user_ids must contain between 1 and 10 user IDs "
            f"(got {count}). The Compliance API rejects requests "
            "outside this range."
        )


def _chat_path(chat_id: str) -> str:
    return f"{CHATS_PATH}/{chat_id}"


def _messages_path(chat_id: str) -> str:
    return f"{CHATS_PATH}/{chat_id}/messages"


def _build_list_params(
    *,
    user_ids: StrList,
    organization_ids: StrList | None,
    project_ids: StrList | None,
    created_at_gte: str | None,
    created_at_gt: str | None,
    created_at_lte: str | None,
    created_at_lt: str | None,
    updated_at_gte: str | None,
    updated_at_gt: str | None,
    updated_at_lte: str | None,
    updated_at_lt: str | None,
    after_id: str | None,
    before_id: str | None,
    limit: int | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"user_ids[]": list(user_ids)}
    for name, values in (
        ("organization_ids", organization_ids),
        ("project_ids", project_ids),
    ):
        if values:
            params[f"{name}[]"] = list(values)
    for name, value in (
        ("created_at.gte", created_at_gte),
        ("created_at.gt", created_at_gt),
        ("created_at.lte", created_at_lte),
        ("created_at.lt", created_at_lt),
        ("updated_at.gte", updated_at_gte),
        ("updated_at.gt", updated_at_gt),
        ("updated_at.lte", updated_at_lte),
        ("updated_at.lt", updated_at_lt),
        ("after_id", after_id),
        ("before_id", before_id),
    ):
        if value is not None:
            params[name] = value
    if limit is not None:
        params["limit"] = limit
    return params


def _build_messages_params(
    *,
    after_id: str | None,
    before_id: str | None,
    limit: int | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if after_id is not None:
        params["after_id"] = after_id
    if before_id is not None:
        params["before_id"] = before_id
    if limit is not None:
        params["limit"] = limit
    return params


# ---------------------------------------------------------------------------
# Resource classes
# ---------------------------------------------------------------------------


class Chats:
    """Synchronous client for the Chats endpoints."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        user_ids: StrList,
        organization_ids: StrList | None = None,
        project_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        updated_at_gte: str | None = None,
        updated_at_gt: str | None = None,
        updated_at_lte: str | None = None,
        updated_at_lt: str | None = None,
        after_id: str | None = None,
        before_id: str | None = None,
        limit: int | None = None,
    ) -> CursorPage[Chat]:
        """Fetch one cursor-paginated page of chats.

        Args:
            user_ids: **Required.** 1–10 user IDs to filter on. The
                spec rejects requests outside this range; the SDK
                raises :class:`ValueError` locally before sending.
            organization_ids: Optional org filter.
            project_ids: Optional project filter.
            created_at_gte/gt/lte/lt: RFC 3339 creation-time
                comparators.
            updated_at_gte/gt/lte/lt: RFC 3339 last-update
                comparators.
            after_id: Cursor for forward pagination.
            before_id: Cursor for backward pagination. Mutually
                exclusive with ``after_id``.
            limit: Maximum results, default 100, max 1000.

        Raises:
            ValueError: When ``user_ids`` is empty or longer than 10.
        """
        _validate_user_ids(user_ids)
        body = self._transport.request(
            "GET",
            CHATS_PATH,
            params=_build_list_params(
                user_ids=user_ids,
                organization_ids=organization_ids,
                project_ids=project_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                updated_at_gte=updated_at_gte,
                updated_at_gt=updated_at_gt,
                updated_at_lte=updated_at_lte,
                updated_at_lt=updated_at_lt,
                after_id=after_id,
                before_id=before_id,
                limit=limit,
            ),
        )
        return CursorPage.from_dict(body, Chat.from_dict)

    def iter(
        self,
        *,
        user_ids: StrList,
        organization_ids: StrList | None = None,
        project_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        updated_at_gte: str | None = None,
        updated_at_gt: str | None = None,
        updated_at_lte: str | None = None,
        updated_at_lt: str | None = None,
        limit: int | None = None,
    ) -> Iterator[Chat]:
        """Iterate every matching chat, auto-paginating.

        Same filters as :meth:`list` except that ``after_id`` /
        ``before_id`` are managed by the iterator.

        Raises:
            ValueError: When ``user_ids`` is empty or longer than 10.
        """
        _validate_user_ids(user_ids)
        after_id: str | None = None
        while True:
            page = self.list(
                user_ids=user_ids,
                organization_ids=organization_ids,
                project_ids=project_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                updated_at_gte=updated_at_gte,
                updated_at_gt=updated_at_gt,
                updated_at_lte=updated_at_lte,
                updated_at_lt=updated_at_lt,
                after_id=after_id,
                limit=limit,
            )
            yield from page.data
            if not page.has_more or page.last_id is None:
                return
            after_id = page.last_id

    def get(
        self,
        chat_id: str,
        *,
        after_id: str | None = None,
        before_id: str | None = None,
        limit: int | None = None,
    ) -> ChatMessagesPage:
        """Fetch one chat's metadata + a page of its messages.

        The Compliance API returns chat metadata and a message page
        from a single endpoint; the SDK exposes them together via
        :class:`ChatMessagesPage`.

        Args:
            chat_id: Tagged chat identifier (``claude_chat_...``).
            after_id: Cursor for forward pagination of messages.
            before_id: Cursor for backward pagination of messages.
            limit: Maximum messages on the returned page. When
                omitted, the server returns the full message set in
                one response.
        """
        body = self._transport.request(
            "GET",
            _messages_path(chat_id),
            params=_build_messages_params(after_id=after_id, before_id=before_id, limit=limit),
        )
        return ChatMessagesPage.from_dict(body)

    def iter_messages(
        self,
        chat_id: str,
        *,
        limit: int | None = None,
    ) -> Iterator[Message]:
        """Iterate every message in a chat, auto-paginating.

        Args:
            chat_id: Tagged chat identifier.
            limit: Per-page maximum (max 1000 per spec). Omit to let
                the server return the full set in one response.
        """
        after_id: str | None = None
        while True:
            result = self.get(chat_id, after_id=after_id, limit=limit)
            yield from result.messages.data
            if not result.messages.has_more or result.messages.last_id is None:
                return
            after_id = result.messages.last_id

    def delete(self, chat_id: str) -> None:
        """Delete a chat (per spec: marks ``deleted_at`` and is irreversible).

        Returns ``None`` on success; the server's confirmation payload
        is discarded.
        """
        self._transport.request("DELETE", _chat_path(chat_id))


class AsyncChats:
    """Asynchronous client for the Chats endpoints."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        user_ids: StrList,
        organization_ids: StrList | None = None,
        project_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        updated_at_gte: str | None = None,
        updated_at_gt: str | None = None,
        updated_at_lte: str | None = None,
        updated_at_lt: str | None = None,
        after_id: str | None = None,
        before_id: str | None = None,
        limit: int | None = None,
    ) -> CursorPage[Chat]:
        """Async analogue of :meth:`Chats.list`."""
        _validate_user_ids(user_ids)
        body = await self._transport.request(
            "GET",
            CHATS_PATH,
            params=_build_list_params(
                user_ids=user_ids,
                organization_ids=organization_ids,
                project_ids=project_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                updated_at_gte=updated_at_gte,
                updated_at_gt=updated_at_gt,
                updated_at_lte=updated_at_lte,
                updated_at_lt=updated_at_lt,
                after_id=after_id,
                before_id=before_id,
                limit=limit,
            ),
        )
        return CursorPage.from_dict(body, Chat.from_dict)

    async def iter(
        self,
        *,
        user_ids: StrList,
        organization_ids: StrList | None = None,
        project_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        updated_at_gte: str | None = None,
        updated_at_gt: str | None = None,
        updated_at_lte: str | None = None,
        updated_at_lt: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Chat]:
        """Async analogue of :meth:`Chats.iter`."""
        _validate_user_ids(user_ids)
        after_id: str | None = None
        while True:
            page = await self.list(
                user_ids=user_ids,
                organization_ids=organization_ids,
                project_ids=project_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                updated_at_gte=updated_at_gte,
                updated_at_gt=updated_at_gt,
                updated_at_lte=updated_at_lte,
                updated_at_lt=updated_at_lt,
                after_id=after_id,
                limit=limit,
            )
            for chat in page.data:
                yield chat
            if not page.has_more or page.last_id is None:
                return
            after_id = page.last_id

    async def get(
        self,
        chat_id: str,
        *,
        after_id: str | None = None,
        before_id: str | None = None,
        limit: int | None = None,
    ) -> ChatMessagesPage:
        """Async analogue of :meth:`Chats.get`."""
        body = await self._transport.request(
            "GET",
            _messages_path(chat_id),
            params=_build_messages_params(after_id=after_id, before_id=before_id, limit=limit),
        )
        return ChatMessagesPage.from_dict(body)

    async def iter_messages(
        self,
        chat_id: str,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[Message]:
        """Async analogue of :meth:`Chats.iter_messages`."""
        after_id: str | None = None
        while True:
            result = await self.get(chat_id, after_id=after_id, limit=limit)
            for message in result.messages.data:
                yield message
            if not result.messages.has_more or result.messages.last_id is None:
                return
            after_id = result.messages.last_id

    async def delete(self, chat_id: str) -> None:
        """Async analogue of :meth:`Chats.delete`."""
        await self._transport.request("DELETE", _chat_path(chat_id))
