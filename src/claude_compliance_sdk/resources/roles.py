"""Roles resource group.

Wraps the org-scoped Roles endpoints:

* ``GET /v1/compliance/organizations/{org_uuid}/roles`` — offset-
  paginated list of roles.
* ``GET /v1/compliance/organizations/{org_uuid}/roles/{role_id}`` —
  single role fetch.
* ``GET /v1/compliance/organizations/{org_uuid}/roles/{role_id}/permissions``
  — offset-paginated list of permissions attached to a role.

Every method takes ``org_uuid`` because the endpoints live under the
organisation path. Enumerate organisations via
:meth:`~claude_compliance_sdk.resources.organizations.Organizations.list`
to obtain UUIDs.
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
class Role:
    """An RBAC role defined inside an organisation.

    Attributes:
        id: Tagged role identifier.
        name: Display name.
        description: Free-form description.
        created_at: ISO 8601 creation timestamp, or ``None`` when not
            recorded.
        updated_at: ISO 8601 last-update timestamp, or ``None`` when
            not recorded.
        extra: Any additional fields the spec adds in a later revision.
    """

    id: str
    name: str
    description: str
    created_at: str | None = None
    updated_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Role":
        """Build a :class:`Role` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class Permission:
    """A single permission attached to a role.

    Permissions are flat triples of (resource type, resource id,
    action) — the role grants its holders the named action on the
    addressed resource.

    Attributes:
        resource_type: Type of resource the permission applies to
            (e.g. ``"project"``).
        resource_id: Identifier of the specific resource, or a
            wildcard when the role grants on all of them.
        action: Action permitted on the resource (e.g. ``"read"``).
        extra: Any additional fields the spec adds in a later revision.
    """

    resource_type: str
    resource_id: str
    action: str
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Permission":
        """Build a :class:`Permission` from one decoded record."""
        return parse_with_extra(cls, body)


def _roles_path(org_uuid: str) -> str:
    return f"{ORGANIZATIONS_PATH}/{org_uuid}/roles"


def _role_path(org_uuid: str, role_id: str) -> str:
    return f"{_roles_path(org_uuid)}/{role_id}"


def _permissions_path(org_uuid: str, role_id: str) -> str:
    return f"{_role_path(org_uuid, role_id)}/permissions"


def _build_offset_params(*, limit: int | None, page: str | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    if page is not None:
        params["page"] = page
    return params


class Roles:
    """Synchronous client for the Roles endpoints."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        org_uuid: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[Role]:
        """Fetch one offset-paginated page of roles in an organisation.

        Args:
            org_uuid: Organisation UUID.
            limit: Maximum results per page (default 500, max 1000).
            page: Opaque pagination token from a prior response.
        """
        body = self._transport.request(
            "GET",
            _roles_path(org_uuid),
            params=_build_offset_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, Role.from_dict)

    def iter(
        self,
        org_uuid: str,
        *,
        limit: int | None = None,
    ) -> Iterator[Role]:
        """Iterate every role in an organisation, auto-paginating."""
        return iter_all_offset_sync(
            self._transport,
            _roles_path(org_uuid),
            Role.from_dict,
            params=_build_offset_params(limit=limit, page=None),
        )

    def get(self, org_uuid: str, role_id: str) -> Role:
        """Fetch one role by ID."""
        body = self._transport.request("GET", _role_path(org_uuid, role_id))
        return Role.from_dict(body)

    def list_permissions(
        self,
        org_uuid: str,
        role_id: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[Permission]:
        """Fetch one offset-paginated page of permissions for a role."""
        body = self._transport.request(
            "GET",
            _permissions_path(org_uuid, role_id),
            params=_build_offset_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, Permission.from_dict)

    def iter_permissions(
        self,
        org_uuid: str,
        role_id: str,
        *,
        limit: int | None = None,
    ) -> Iterator[Permission]:
        """Iterate every permission on a role, auto-paginating."""
        return iter_all_offset_sync(
            self._transport,
            _permissions_path(org_uuid, role_id),
            Permission.from_dict,
            params=_build_offset_params(limit=limit, page=None),
        )


class AsyncRoles:
    """Asynchronous client for the Roles endpoints."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        org_uuid: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[Role]:
        """Async analogue of :meth:`Roles.list`."""
        body = await self._transport.request(
            "GET",
            _roles_path(org_uuid),
            params=_build_offset_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, Role.from_dict)

    def iter(
        self,
        org_uuid: str,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[Role]:
        """Async analogue of :meth:`Roles.iter`."""
        return iter_all_offset_async(
            self._transport,
            _roles_path(org_uuid),
            Role.from_dict,
            params=_build_offset_params(limit=limit, page=None),
        )

    async def get(self, org_uuid: str, role_id: str) -> Role:
        """Async analogue of :meth:`Roles.get`."""
        body = await self._transport.request("GET", _role_path(org_uuid, role_id))
        return Role.from_dict(body)

    async def list_permissions(
        self,
        org_uuid: str,
        role_id: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[Permission]:
        """Async analogue of :meth:`Roles.list_permissions`."""
        body = await self._transport.request(
            "GET",
            _permissions_path(org_uuid, role_id),
            params=_build_offset_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, Permission.from_dict)

    def iter_permissions(
        self,
        org_uuid: str,
        role_id: str,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[Permission]:
        """Async analogue of :meth:`Roles.iter_permissions`."""
        return iter_all_offset_async(
            self._transport,
            _permissions_path(org_uuid, role_id),
            Permission.from_dict,
            params=_build_offset_params(limit=limit, page=None),
        )
