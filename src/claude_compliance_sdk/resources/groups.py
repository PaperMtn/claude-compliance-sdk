"""Groups resource group.

Wraps three Groups endpoints:

* ``GET /v1/compliance/groups`` — offset-paginated list of groups.
* ``GET /v1/compliance/groups/{group_id}`` — single group fetch.
* ``GET /v1/compliance/groups/{group_id}/members`` —
  offset-paginated list of users in the group.

Unlike `roles`, groups are not addressed under an organisation
path — they're top-level. The roles each group grants travel inline
on `roles` as a list of role IDs.
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

GROUPS_PATH = "/v1/compliance/groups"


@dataclass
class Group:
    """A user group defined inside an organisation.

    Attributes:
        id: Tagged group identifier.
        name: Display name.
        description: Free-form description.
        source_type: How the group was created — ``"direct"`` for
            manually-created groups, ``"scim"`` for groups pushed by
            an IdP via SCIM directory sync.
        created_at: ISO 8601 creation timestamp, or ``None`` when not
            recorded.
        updated_at: ISO 8601 last-update timestamp, or ``None``.
        roles: IDs of roles assigned to the group, or ``None`` when
            the server did not include the field.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    name: str
    description: str
    source_type: str
    created_at: str | None = None
    updated_at: str | None = None
    roles: list[str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Group":
        """Build a `Group` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class GroupMember:
    """A user's membership in a group.

    Attributes:
        user_id: Tagged user identifier.
        email: Member email address at the time of the request.
        created_at: ISO 8601 membership creation timestamp, or
            ``None`` when not recorded.
        updated_at: ISO 8601 membership last-update timestamp, or
            ``None`` when not recorded.
        extra: Any additional fields the API adds in a later revision.
    """

    user_id: str
    email: str
    created_at: str | None = None
    updated_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "GroupMember":
        """Build a `GroupMember` from one decoded record."""
        return parse_with_extra(cls, body)


def _group_path(group_id: str) -> str:
    return f"{GROUPS_PATH}/{group_id}"


def _members_path(group_id: str) -> str:
    return f"{_group_path(group_id)}/members"


def _build_offset_params(*, limit: int | None, page: str | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    if page is not None:
        params["page"] = page
    return params


class Groups:
    """Synchronous client for the Groups endpoints."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[Group]:
        """Fetch one offset-paginated page of groups.

        Args:
            limit: Maximum results per page (default 500, max 1000).
            page: Opaque pagination token from a prior response.
        """
        body = self._transport.request(
            "GET",
            GROUPS_PATH,
            params=_build_offset_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, Group.from_dict)

    def iter(
        self,
        *,
        limit: int | None = None,
    ) -> Iterator[Group]:
        """Iterate every group, auto-paginating."""
        return iter_all_offset_sync(
            self._transport,
            GROUPS_PATH,
            Group.from_dict,
            params=_build_offset_params(limit=limit, page=None),
        )

    def get(self, group_id: str) -> Group:
        """Fetch one group by ID."""
        body = self._transport.request("GET", _group_path(group_id))
        return Group.from_dict(body)

    def list_members(
        self,
        group_id: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[GroupMember]:
        """Fetch one offset-paginated page of members for a group."""
        body = self._transport.request(
            "GET",
            _members_path(group_id),
            params=_build_offset_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, GroupMember.from_dict)

    def iter_members(
        self,
        group_id: str,
        *,
        limit: int | None = None,
    ) -> Iterator[GroupMember]:
        """Iterate every member of a group, auto-paginating."""
        return iter_all_offset_sync(
            self._transport,
            _members_path(group_id),
            GroupMember.from_dict,
            params=_build_offset_params(limit=limit, page=None),
        )


class AsyncGroups:
    """Asynchronous client for the Groups endpoints."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[Group]:
        """Async analogue of `list`."""
        body = await self._transport.request(
            "GET",
            GROUPS_PATH,
            params=_build_offset_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, Group.from_dict)

    def iter(
        self,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[Group]:
        """Async analogue of `iter`."""
        return iter_all_offset_async(
            self._transport,
            GROUPS_PATH,
            Group.from_dict,
            params=_build_offset_params(limit=limit, page=None),
        )

    async def get(self, group_id: str) -> Group:
        """Async analogue of `get`."""
        body = await self._transport.request("GET", _group_path(group_id))
        return Group.from_dict(body)

    async def list_members(
        self,
        group_id: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[GroupMember]:
        """Async analogue of `list_members`."""
        body = await self._transport.request(
            "GET",
            _members_path(group_id),
            params=_build_offset_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, GroupMember.from_dict)

    def iter_members(
        self,
        group_id: str,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[GroupMember]:
        """Async analogue of `iter_members`."""
        return iter_all_offset_async(
            self._transport,
            _members_path(group_id),
            GroupMember.from_dict,
            params=_build_offset_params(limit=limit, page=None),
        )
