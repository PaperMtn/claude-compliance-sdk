"""Organizations resource group.

Wraps two Compliance API endpoints:

* ``GET /v1/compliance/organizations`` — offset paginated list of every
  organisation under the parent organisation. Exposed via
  `list` (one page) and `iter` (auto-paginate).
* ``GET /v1/compliance/organizations/{org_uuid}/users`` — offset
  paginated list of users in a given organisation. Exposed via
  `list_users` (one page) and
  `iter_users` (auto-paginate).

Example:
    ```python
    from claude_compliance_sdk import ComplianceClient

    with ComplianceClient(api_key="sk-ant-api01-...") as client:
        for org in client.organizations.iter():
            print(org.uuid, org.name)
            for user in client.organizations.iter_users(org.uuid):
                print("  ", user.email)
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

ORGANIZATIONS_PATH = "/v1/compliance/organizations"


@dataclass
class Organization:
    """A single organisation under the parent organisation.

    Attributes:
        uuid: Stable UUID identifier (used as the path segment for
            ``/organizations/{org_uuid}/users``).
        name: Human-readable organisation name.
        created_at: RFC 3339 creation timestamp.
        extra: Any additional fields the API adds in a later revision.
    """

    uuid: str
    name: str
    created_at: str
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Organization":
        """Build an `Organization` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class User:
    """A user member of an organisation.

    Custom RBAC role and group memberships are not part of this
    payload — they come from the Roles and Groups resources.
    ``organization_role`` is a separate axis: the built-in membership
    level within this organisation.

    Attributes:
        id: Tagged user identifier (``user_...``).
        full_name: Current display name.
        email: Current email address.
        created_at: RFC 3339 account creation timestamp.
        organization_role: Built-in membership level — one of
            ``admin``, ``billing``, ``claude_code_user``, ``developer``,
            ``managed``, ``membership_admin``, ``owner``,
            ``primary_owner``, ``user``. Kept as a plain string: new
            values ship without notice.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    full_name: str
    email: str
    created_at: str
    organization_role: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "User":
        """Build a `User` from one decoded record."""
        return parse_with_extra(cls, body)


def _users_path(org_uuid: str) -> str:
    return f"{ORGANIZATIONS_PATH}/{org_uuid}/users"


def _build_page_params(*, limit: int | None, page: str | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    if page is not None:
        params["page"] = page
    return params


class Organizations:
    """Synchronous client for the Organizations endpoints."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[Organization]:
        """Fetch one offset-paginated page of organisations.

        Args:
            limit: Maximum results per page (default 1000, max 1000).
            page: Opaque pagination token from a prior response's
                ``next_page``.

        Returns:
            One `OffsetPage` of `Organization` objects, sorted by
            ``created_at`` ascending. May be empty.

        Raises:
            InsufficientScopeError: When the API key lacks
                ``read:compliance_org_data``.
            APIError: For any other non-2xx response.
        """
        body = self._transport.request(
            "GET",
            ORGANIZATIONS_PATH,
            params=_build_page_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, Organization.from_dict)

    def iter(
        self,
        *,
        limit: int | None = None,
    ) -> Iterator[Organization]:
        """Iterate every organisation under the parent, auto-paginating.

        Same arguments as `list` except that ``page`` is managed by the
        iterator and therefore not accepted here.
        """
        return iter_all_offset_sync(
            self._transport,
            ORGANIZATIONS_PATH,
            Organization.from_dict,
            params=_build_page_params(limit=limit, page=None),
        )

    def list_users(
        self,
        org_uuid: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[User]:
        """Fetch one offset-paginated page of users for an organisation.

        Args:
            org_uuid: Organisation UUID, from `list` results.
            limit: Maximum results per page (default 500, max 1000).
            page: Opaque pagination token from a prior response's
                ``next_page``.

        Returns:
            One `OffsetPage` of `User` objects.
        """
        body = self._transport.request(
            "GET",
            _users_path(org_uuid),
            params=_build_page_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, User.from_dict)

    def iter_users(
        self,
        org_uuid: str,
        *,
        limit: int | None = None,
    ) -> Iterator[User]:
        """Iterate every user in an organisation, auto-paginating.

        Same filters as `list_users` except that ``page`` is
        managed by the iterator and therefore not accepted here.
        """
        return iter_all_offset_sync(
            self._transport,
            _users_path(org_uuid),
            User.from_dict,
            params=_build_page_params(limit=limit, page=None),
        )


class AsyncOrganizations:
    """Asynchronous client for the Organizations endpoints."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[Organization]:
        """Async analogue of `list`."""
        body = await self._transport.request(
            "GET",
            ORGANIZATIONS_PATH,
            params=_build_page_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, Organization.from_dict)

    def iter(
        self,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[Organization]:
        """Async analogue of `iter`."""
        return iter_all_offset_async(
            self._transport,
            ORGANIZATIONS_PATH,
            Organization.from_dict,
            params=_build_page_params(limit=limit, page=None),
        )

    async def list_users(
        self,
        org_uuid: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[User]:
        """Async analogue of `list_users`."""
        body = await self._transport.request(
            "GET",
            _users_path(org_uuid),
            params=_build_page_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, User.from_dict)

    def iter_users(
        self,
        org_uuid: str,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[User]:
        """Async analogue of `iter_users`."""
        return iter_all_offset_async(
            self._transport,
            _users_path(org_uuid),
            User.from_dict,
            params=_build_page_params(limit=limit, page=None),
        )
