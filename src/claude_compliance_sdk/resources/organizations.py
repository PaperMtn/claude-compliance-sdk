"""Organizations resource group.

Wraps two Compliance API endpoints:

* ``GET /v1/compliance/organizations`` — offset paginated list of every
  organisation under the parent organisation. Exposed via
  `list` (one page) and `iter` (auto-paginate).
* ``GET /v1/compliance/organizations/{org_uuid}/users`` — offset
  paginated list of users in a given organisation. Exposed via
  `list_users` (one page) and
  `iter_users` (auto-paginate).
* ``GET /v1/compliance/organizations/{organization_id}/settings`` — the
  settings actually in force for one organisation. Exposed via
  `get_settings`.

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

# Module-level alias for the `list` builtin — see resources/activities.py
# for the rationale.
StrList = list[str]

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


@dataclass
class ComplianceApiKey:
    """One Compliance Access Key configured for the parent organisation.

    The secret value is never returned. Deactivated keys are included
    with ``is_active`` false so you can audit what previously had
    access.

    Attributes:
        id: Key identifier (``apikey_...``).
        name: Name given to the key at creation.
        scopes: Scopes granted to the key. Keys carrying only the
            retired ``read:compliance_org_settings`` scope remain
            listed for cleanup visibility even though it no longer
            grants anything.
        is_active: Whether the key can currently authenticate.
        created_at: RFC 3339 creation timestamp.
        created_by_id: The user who created the key, or ``None`` when
            it was created by automation or the creator's account is
            gone.
        expires_at: When the key stops authenticating, or ``None`` when
            it does not expire.
        type: Always ``"compliance_api_key"``.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    name: str
    is_active: bool
    created_at: str
    scopes: StrList = field(default_factory=list)
    created_by_id: str | None = None
    expires_at: str | None = None
    type: str = "compliance_api_key"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "ComplianceApiKey":
        """Build a `ComplianceApiKey` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class OrganizationSettings:
    """The settings in force for one organisation.

    This is the *enforced* state after regulatory restrictions, feature
    availability, organisation-type defaults, and inter-feature
    dependencies are applied, which can differ from what an
    administrator configured. It reflects the state at read time;
    nothing is snapshotted.

    A setting the organisation's administrators cannot change is
    **omitted** from `settings`. Treat a missing row as "not
    controllable here", **not** as "off" — that distinction is the
    easiest thing to get wrong about this endpoint.

    Attributes:
        organization_id: The organisation's bare UUID. Note this is
            *not* the ``org_``-prefixed form that ``organization_id``
            carries on Activity Feed, chat, and project records.
        settings: Typed setting rows, each a raw dict of ``name``,
            ``type``, and ``value``. ``type`` is one of ``boolean``,
            ``integer``, ``string``, ``string_list``,
            ``provisioning_mode``, or ``data_retention``, and
            determines the shape of ``value``. Kept as dicts: there
            are 50+ setting names and the list grows, so branch on
            ``type`` rather than expecting the SDK to enumerate them.
        api_keys: Every Compliance Access Key configured for the parent
            organisation. The same list comes back whichever linked
            organisation you query.
        type: Always ``"effective_organization_settings"``.
        extra: Any additional fields the API adds in a later revision.
    """

    organization_id: str
    settings: list[dict[str, Any]] = field(default_factory=list)
    api_keys: list[ComplianceApiKey] = field(default_factory=list)
    type: str = "effective_organization_settings"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "OrganizationSettings":
        """Build an `OrganizationSettings` from one decoded record."""
        parsed = parse_with_extra(cls, body)
        raw_keys = body.get("api_keys") or []
        parsed.api_keys = [
            ComplianceApiKey.from_dict(item) for item in raw_keys if isinstance(item, Mapping)
        ]
        return parsed


def _settings_path(organization_id: str) -> str:
    return f"{ORGANIZATIONS_PATH}/{organization_id}/settings"


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

    def get_settings(self, organization_id: str) -> OrganizationSettings:
        """Fetch the settings in force for one linked organisation.

        Use this to attest that retention windows, content redaction,
        SSO enforcement, the IP allowlist, and session-duration
        controls match your documented baseline, without needing
        administrator Console access.

        Requires ``read:compliance_org_data``. The separate
        ``read:compliance_org_settings`` scope was retired on
        2026-06-30, so a key created before then that carries only the
        old scope gets a 403 here.

        Args:
            organization_id: The organisation's bare UUID, as returned
                in ``uuid`` by `list`. Must be one of the parent's
                **linked** organisations — the parent itself is not a
                valid target.

        Returns:
            An `OrganizationSettings` describing the enforced state.
            Remember that a missing setting row means "administrators
            here cannot change it", not "off".

        Raises:
            NotFoundError: When the organisation is not one of your
                parent's linked organisations, the value is not a valid
                UUID, or the settings endpoint is not yet enabled for
                your parent organisation. These three deliberately
                share one response, so a 404 does **not** prove the
                organisation does not exist.
            InsufficientScopeError: When the key lacks
                ``read:compliance_org_data``.
            APIError: For any other non-2xx response.
        """
        body = self._transport.request("GET", _settings_path(organization_id))
        return OrganizationSettings.from_dict(body)

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

    async def get_settings(self, organization_id: str) -> OrganizationSettings:
        """Async analogue of `get_settings`."""
        body = await self._transport.request("GET", _settings_path(organization_id))
        return OrganizationSettings.from_dict(body)

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
