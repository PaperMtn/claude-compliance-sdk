"""Pagination primitives for the Compliance API.

Two page shapes per the spec:

* :class:`CursorPage` — used by Activity Feed, Chats, and Messages.
  Each page payload carries ``first_id``, ``last_id``, and ``has_more``.
  Forward via ``after_id=last_id``; backward via ``before_id=first_id``.
* :class:`OffsetPage` — used by everything else paginated. Each page
  payload carries an opaque ``next_page`` token; pass it back as the
  ``page`` query parameter to fetch the next page.

Both page classes are plain dataclasses (no Pydantic, per CLAUDE.md)
parameterised over the item type ``T``. They are used identically by
sync and async resources — the iteration helpers are what differ.

The :func:`iter_all_cursor_sync` /
:func:`iter_all_cursor_async` /
:func:`iter_all_offset_sync` /
:func:`iter_all_offset_async` helpers drive a resource's ``.iter()``
method: they fetch consecutive pages, build each into a typed object
with a caller-supplied factory, and yield items one at a time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any, Callable, Generic, Mapping, TypeVar

from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

T = TypeVar("T")

ItemFactory = Callable[[Mapping[str, Any]], T]


@dataclass
class CursorPage(Generic[T]):
    """A single cursor-paginated page.

    Attributes:
        data: Decoded items from the page's ``data`` array.
        first_id: ID of the first item in the page (server-side).
            ``None`` when the page is empty.
        last_id: ID of the last item in the page. Pass as ``after_id``
            on the next request to fetch the page after this one.
        has_more: Server-supplied flag indicating whether further pages
            exist after this one.
    """

    data: list[T]
    first_id: str | None
    last_id: str | None
    has_more: bool

    @classmethod
    def from_dict(cls, body: Mapping[str, Any], item_factory: ItemFactory[T]) -> "CursorPage[T]":
        """Build a :class:`CursorPage` from a decoded response body."""
        raw_items = body.get("data") or []
        return cls(
            data=[item_factory(item) for item in raw_items],
            first_id=_str_or_none(body.get("first_id")),
            last_id=_str_or_none(body.get("last_id")),
            has_more=bool(body.get("has_more", False)),
        )


@dataclass
class OffsetPage(Generic[T]):
    """A single offset-paginated page.

    Attributes:
        data: Decoded items from the page's ``data`` array.
        next_page: Opaque pagination token returned by the server.
            Pass it as the ``page`` query parameter to fetch the next
            page. ``None`` when this is the last page.
    """

    data: list[T]
    next_page: str | None

    @classmethod
    def from_dict(cls, body: Mapping[str, Any], item_factory: ItemFactory[T]) -> "OffsetPage[T]":
        """Build an :class:`OffsetPage` from a decoded response body."""
        raw_items = body.get("data") or []
        return cls(
            data=[item_factory(item) for item in raw_items],
            next_page=_str_or_none(body.get("next_page")),
        )


# AsyncCursorPage / AsyncOffsetPage are kept as aliases of the sync
# dataclasses so async resources can type-hint a distinct name when it
# helps documentation, without duplicating the dataclass shape. The
# shape of a page does not depend on who fetched it.
AsyncCursorPage = CursorPage
AsyncOffsetPage = OffsetPage


# ---------------------------------------------------------------------------
# Iteration helpers
# ---------------------------------------------------------------------------


def iter_all_cursor_sync(
    transport: SyncTransport,
    path: str,
    item_factory: ItemFactory[T],
    *,
    params: Mapping[str, Any] | None = None,
) -> Iterator[T]:
    """Iterate every item across every cursor page, yielding one at a time.

    Args:
        transport: Transport used to issue the underlying GET requests.
        path: Path of the paginated endpoint.
        item_factory: Callable that builds a typed item from one decoded
            JSON record (the dataclasses defined per resource in Phase
            3 supply this).
        params: Initial query parameters. The helper appends
            ``after_id`` on each subsequent request without mutating the
            caller's mapping.
    """
    next_params: dict[str, Any] = dict(params or {})
    while True:
        body = transport.request("GET", path, params=next_params)
        page: CursorPage[T] = CursorPage.from_dict(body, item_factory)
        yield from page.data
        if not page.has_more or page.last_id is None:
            return
        next_params["after_id"] = page.last_id


async def iter_all_cursor_async(
    transport: AsyncTransport,
    path: str,
    item_factory: ItemFactory[T],
    *,
    params: Mapping[str, Any] | None = None,
) -> AsyncIterator[T]:
    """Async analogue of :func:`iter_all_cursor_sync`."""
    next_params: dict[str, Any] = dict(params or {})
    while True:
        body = await transport.request("GET", path, params=next_params)
        page: CursorPage[T] = CursorPage.from_dict(body, item_factory)
        for item in page.data:
            yield item
        if not page.has_more or page.last_id is None:
            return
        next_params["after_id"] = page.last_id


def iter_all_offset_sync(
    transport: SyncTransport,
    path: str,
    item_factory: ItemFactory[T],
    *,
    params: Mapping[str, Any] | None = None,
) -> Iterator[T]:
    """Iterate every item across every offset page, yielding one at a time.

    Args:
        transport: Transport used to issue the underlying GET requests.
        path: Path of the paginated endpoint.
        item_factory: Callable that builds a typed item from one decoded
            JSON record.
        params: Initial query parameters. The helper appends ``page``
            on each subsequent request without mutating the caller's
            mapping.
    """
    next_params: dict[str, Any] = dict(params or {})
    while True:
        body = transport.request("GET", path, params=next_params)
        page: OffsetPage[T] = OffsetPage.from_dict(body, item_factory)
        yield from page.data
        if page.next_page is None:
            return
        next_params["page"] = page.next_page


async def iter_all_offset_async(
    transport: AsyncTransport,
    path: str,
    item_factory: ItemFactory[T],
    *,
    params: Mapping[str, Any] | None = None,
) -> AsyncIterator[T]:
    """Async analogue of :func:`iter_all_offset_sync`."""
    next_params: dict[str, Any] = dict(params or {})
    while True:
        body = await transport.request("GET", path, params=next_params)
        page: OffsetPage[T] = OffsetPage.from_dict(body, item_factory)
        for item in page.data:
            yield item
        if page.next_page is None:
            return
        next_params["page"] = page.next_page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


__all__ = [
    "AsyncCursorPage",
    "AsyncOffsetPage",
    "CursorPage",
    "ItemFactory",
    "OffsetPage",
    "iter_all_cursor_async",
    "iter_all_cursor_sync",
    "iter_all_offset_async",
    "iter_all_offset_sync",
]
