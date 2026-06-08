"""Activities resource group.

Wraps ``GET /v1/compliance/activities``. The Activity Feed is the
cursor-paginated audit log for an organisation; both Compliance Access
Keys (with ``read:compliance_activities`` scope) and Admin keys can
call it. The server is the source of truth on the scope check — the
client never inspects the API key prefix.

Example:
    ```python
    from claude_compliance_sdk import ComplianceClient

    with ComplianceClient(api_key="sk-ant-admin01-...") as client:
        for activity in client.activities.iter(
            created_at_gte="2025-06-01T00:00:00Z",
            activity_types=["claude_chat_created", "api_key_created"],
        ):
            print(activity.id, activity.type)
    ```
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any, Mapping

from claude_compliance_sdk._internal.pagination import (
    CursorPage,
    iter_all_cursor_async,
    iter_all_cursor_sync,
)
from claude_compliance_sdk._internal.parsing import parse_with_extra
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

# Module-level alias for the `list` builtin. The Activities classes
# below define a `.list()` method which shadows the builtin in their
# class namespace, so any `list[str]` annotation on a sibling method
# (e.g. `.iter()`) would otherwise resolve to the method type rather
# than the generic alias. Every paginated resource group will hit this
# same shadow, so the alias stays in the file.
StrList = list[str]

ACTIVITIES_PATH = "/v1/compliance/activities"


@dataclass
class Activity:
    """A single audit event from the Compliance API activity feed.

    Per-type fields (for example ``claude_chat_id`` on a
    ``claude_chat_created`` activity) land in `extra` rather than
    on the dataclass so the SDK does not have to track the full list
    of activity types — that set grows over time.

    Attributes:
        id: Unique identifier (``activity_...``).
        created_at: When the activity occurred, RFC 3339.
        type: Activity type string (``claude_chat_created``,
            ``api_key_created``, etc.). Named ``type`` to match the wire
            format.
        organization_id: Owning organisation's tagged ID, or ``None``
            for activities not tied to an organisation (login, logout,
            Compliance API access).
        organization_uuid: Owning organisation's UUID, or ``None`` as
            above.
        actor: Raw actor payload (``UserActor``, ``ApiActor``,
            ``AdminApiKeyActor``, ``UnauthenticatedUserActor``,
            ``AnthropicActor``, ``ScimDirectorySyncActor``). Discriminate
            on ``actor["type"]``. Kept as a dict because the union grows
            over time.
        extra: Activity-type-specific fields preserved verbatim from the
            response, plus any new top-level fields the API adds later.
    """

    id: str
    created_at: str
    type: str
    organization_id: str | None = None
    organization_uuid: str | None = None
    actor: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Activity":
        """Build an `Activity` from one decoded JSON record."""
        return parse_with_extra(cls, body)


def _build_query_params(
    *,
    organization_ids: StrList | None,
    actor_ids: StrList | None,
    activity_types: StrList | None,
    created_at_gte: str | None,
    created_at_gt: str | None,
    created_at_lte: str | None,
    created_at_lt: str | None,
    after_id: str | None,
    before_id: str | None,
    limit: int | None,
) -> dict[str, Any]:
    """Serialise the Activity Feed filters into an ``httpx``-compatible dict.

    Array filters (``organization_ids[]``, ``actor_ids[]``,
    ``activity_types[]``) use a list value so httpx emits one repeat
    per item. Time filters use the dotted form (``created_at.gte`` etc.)
    the API requires. ``None`` values are dropped.
    """
    params: dict[str, Any] = {}
    for name, values in (
        ("organization_ids", organization_ids),
        ("actor_ids", actor_ids),
        ("activity_types", activity_types),
    ):
        if values:
            params[f"{name}[]"] = list(values)
    for name, value in (
        ("created_at.gte", created_at_gte),
        ("created_at.gt", created_at_gt),
        ("created_at.lte", created_at_lte),
        ("created_at.lt", created_at_lt),
        ("after_id", after_id),
        ("before_id", before_id),
    ):
        if value is not None:
            params[name] = value
    if limit is not None:
        params["limit"] = limit
    return params


class Activities:
    """Synchronous client for the Compliance API activity feed."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        organization_ids: StrList | None = None,
        actor_ids: StrList | None = None,
        activity_types: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        after_id: str | None = None,
        before_id: str | None = None,
        limit: int | None = None,
    ) -> CursorPage[Activity]:
        """Fetch a single page of activities.

        Args:
            organization_ids: Filter to activities in any of these
                organisations.
            actor_ids: Filter to activities by any of these actor user
                IDs.
            activity_types: Filter to activities of any of these types.
            created_at_gte: ``created_at >= value`` (RFC 3339).
            created_at_gt: ``created_at > value`` (RFC 3339).
            created_at_lte: ``created_at <= value`` (RFC 3339).
            created_at_lt: ``created_at < value`` (RFC 3339).
            after_id: Cursor for forward pagination (newer items).
            before_id: Cursor for backward pagination (older items).
                Mutually exclusive with ``after_id``.
            limit: Maximum results, default 100, max 5000.

        Returns:
            One `CursorPage` of `Activity` objects.

        Raises:
            InsufficientScopeError: When the API key lacks
                ``read:compliance_activities``.
            APIError: For any other non-2xx response.
        """
        params = _build_query_params(
            organization_ids=organization_ids,
            actor_ids=actor_ids,
            activity_types=activity_types,
            created_at_gte=created_at_gte,
            created_at_gt=created_at_gt,
            created_at_lte=created_at_lte,
            created_at_lt=created_at_lt,
            after_id=after_id,
            before_id=before_id,
            limit=limit,
        )
        body = self._transport.request("GET", ACTIVITIES_PATH, params=params)
        return CursorPage.from_dict(body, Activity.from_dict)

    def iter(
        self,
        *,
        organization_ids: StrList | None = None,
        actor_ids: StrList | None = None,
        activity_types: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        limit: int | None = None,
    ) -> Iterator[Activity]:
        """Iterate every matching activity, auto-paginating.

        Same filters as `list` except that ``after_id`` /
        ``before_id`` are managed by the iterator and therefore not
        accepted here.
        """
        params = _build_query_params(
            organization_ids=organization_ids,
            actor_ids=actor_ids,
            activity_types=activity_types,
            created_at_gte=created_at_gte,
            created_at_gt=created_at_gt,
            created_at_lte=created_at_lte,
            created_at_lt=created_at_lt,
            after_id=None,
            before_id=None,
            limit=limit,
        )
        return iter_all_cursor_sync(
            self._transport, ACTIVITIES_PATH, Activity.from_dict, params=dict(params)
        )


class AsyncActivities:
    """Asynchronous client for the Compliance API activity feed."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        organization_ids: StrList | None = None,
        actor_ids: StrList | None = None,
        activity_types: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        after_id: str | None = None,
        before_id: str | None = None,
        limit: int | None = None,
    ) -> CursorPage[Activity]:
        """Async analogue of `list`."""
        params = _build_query_params(
            organization_ids=organization_ids,
            actor_ids=actor_ids,
            activity_types=activity_types,
            created_at_gte=created_at_gte,
            created_at_gt=created_at_gt,
            created_at_lte=created_at_lte,
            created_at_lt=created_at_lt,
            after_id=after_id,
            before_id=before_id,
            limit=limit,
        )
        body = await self._transport.request("GET", ACTIVITIES_PATH, params=params)
        return CursorPage.from_dict(body, Activity.from_dict)

    def iter(
        self,
        *,
        organization_ids: StrList | None = None,
        actor_ids: StrList | None = None,
        activity_types: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Activity]:
        """Async analogue of `iter`."""
        params = _build_query_params(
            organization_ids=organization_ids,
            actor_ids=actor_ids,
            activity_types=activity_types,
            created_at_gte=created_at_gte,
            created_at_gt=created_at_gt,
            created_at_lte=created_at_lte,
            created_at_lt=created_at_lt,
            after_id=None,
            before_id=None,
            limit=limit,
        )
        return iter_all_cursor_async(
            self._transport, ACTIVITIES_PATH, Activity.from_dict, params=dict(params)
        )
