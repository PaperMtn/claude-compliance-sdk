"""Tests for the Roles resource group (org-scoped roles + permissions)."""

from __future__ import annotations

import os
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import (
    AsyncComplianceClient,
    ComplianceClient,
    NotFoundError,
    OffsetPage,
)
from claude_compliance_sdk.resources.roles import (
    ORGANIZATIONS_PATH,
    Permission,
    Role,
)


API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
ORG_UUID = "abcdef01-2345-6789-abcd-0123456789ab"
ROLE_ID = "role_abc123"


SPEC_EXAMPLE_ROLE: dict[str, Any] = {
    "id": "role_abc123",
    "name": "Compliance Reviewer",
    "description": "Read-only access to compliance data.",
    "created_at": "2025-05-01T09:00:00Z",
    "updated_at": "2025-06-01T09:00:00Z",
}

SPEC_EXAMPLE_PERMISSION: dict[str, Any] = {
    "resource_type": "project",
    "resource_id": "claude_proj_abc123",
    "action": "read",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_role_from_dict() -> None:
    role = Role.from_dict(SPEC_EXAMPLE_ROLE)
    assert role.id == "role_abc123"
    assert role.name == "Compliance Reviewer"
    assert role.description == "Read-only access to compliance data."
    assert role.created_at == "2025-05-01T09:00:00Z"


def test_role_from_dict_null_timestamps() -> None:
    body = dict(SPEC_EXAMPLE_ROLE)
    body["created_at"] = None
    body["updated_at"] = None
    role = Role.from_dict(body)
    assert role.created_at is None
    assert role.updated_at is None


def test_permission_from_dict() -> None:
    perm = Permission.from_dict(SPEC_EXAMPLE_PERMISSION)
    assert perm.resource_type == "project"
    assert perm.resource_id == "claude_proj_abc123"
    assert perm.action == "read"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sync_client() -> ComplianceClient:
    client = ComplianceClient(
        api_key=API_KEY,
        base_url=BASE_URL,
        max_retries=0,
        rate_limit_rpm=0,
    )
    yield client
    client.close()


@pytest.fixture
async def async_client() -> AsyncComplianceClient:
    client = AsyncComplianceClient(
        api_key=API_KEY,
        base_url=BASE_URL,
        max_retries=0,
        rate_limit_rpm=0,
    )
    yield client
    await client.aclose()


def _roles_url(suffix: str = "") -> str:
    return f"{BASE_URL}{ORGANIZATIONS_PATH}/{ORG_UUID}/roles{suffix}"


def _permissions_url(suffix: str = "") -> str:
    return f"{BASE_URL}{ORGANIZATIONS_PATH}/{ORG_UUID}/roles/{ROLE_ID}/permissions{suffix}"


# ---------------------------------------------------------------------------
# .list() / .iter() / .get()
# ---------------------------------------------------------------------------


def test_list_returns_offset_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_roles_url(),
        json={"data": [SPEC_EXAMPLE_ROLE], "has_more": False, "next_page": None},
    )
    page = sync_client.roles.list(ORG_UUID)
    assert isinstance(page, OffsetPage)
    assert page.data[0].id == "role_abc123"


def test_list_passes_limit_and_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_roles_url("?limit=100&page=tok"),
        json={"data": [], "has_more": False, "next_page": None},
    )
    sync_client.roles.list(ORG_UUID, limit=100, page="tok")
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["limit"] == "100"
    assert request.url.params["page"] == "tok"


def test_iter_walks_pages(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_roles_url(),
        json={"data": [_role("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=_roles_url("?page=tok_1"),
        json={"data": [_role("b")], "has_more": False, "next_page": None},
    )
    ids = [r.id for r in sync_client.roles.iter(ORG_UUID)]
    assert ids == ["a", "b"]


def test_get_returns_role(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_roles_url(f"/{ROLE_ID}"), json=SPEC_EXAMPLE_ROLE)
    role = sync_client.roles.get(ORG_UUID, ROLE_ID)
    assert role.id == ROLE_ID


def test_get_404_raises_not_found(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_roles_url(f"/{ROLE_ID}"),
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Role not found."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.roles.get(ORG_UUID, ROLE_ID)


# ---------------------------------------------------------------------------
# .list_permissions() / .iter_permissions()
# ---------------------------------------------------------------------------


def test_list_permissions(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_permissions_url(),
        json={"data": [SPEC_EXAMPLE_PERMISSION], "has_more": False, "next_page": None},
    )
    page = sync_client.roles.list_permissions(ORG_UUID, ROLE_ID)
    assert isinstance(page, OffsetPage)
    assert page.data[0].action == "read"


def test_iter_permissions_walks_pages(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_permissions_url(),
        json={
            "data": [_permission("read")],
            "has_more": True,
            "next_page": "tok_1",
        },
    )
    httpx_mock.add_response(
        url=_permissions_url("?page=tok_1"),
        json={
            "data": [_permission("write")],
            "has_more": False,
            "next_page": None,
        },
    )
    actions = [p.action for p in sync_client.roles.iter_permissions(ORG_UUID, ROLE_ID)]
    assert actions == ["read", "write"]


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_list(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_roles_url(),
        json={"data": [SPEC_EXAMPLE_ROLE], "has_more": False, "next_page": None},
    )
    page = await async_client.roles.list(ORG_UUID)
    assert page.data[0].name == "Compliance Reviewer"


async def test_async_iter(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_roles_url(),
        json={"data": [_role("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=_roles_url("?page=tok_1"),
        json={"data": [_role("b")], "has_more": False, "next_page": None},
    )
    ids = [r.id async for r in async_client.roles.iter(ORG_UUID)]
    assert ids == ["a", "b"]


async def test_async_get(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_roles_url(f"/{ROLE_ID}"), json=SPEC_EXAMPLE_ROLE)
    role = await async_client.roles.get(ORG_UUID, ROLE_ID)
    assert role.id == ROLE_ID


async def test_async_list_permissions(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_permissions_url(),
        json={"data": [SPEC_EXAMPLE_PERMISSION], "has_more": False, "next_page": None},
    )
    page = await async_client.roles.list_permissions(ORG_UUID, ROLE_ID)
    assert page.data[0].resource_type == "project"


async def test_async_iter_permissions(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_permissions_url(),
        json={
            "data": [_permission("read"), _permission("write")],
            "has_more": False,
            "next_page": None,
        },
    )
    actions = [
        p.action
        async for p in async_client.roles.iter_permissions(ORG_UUID, ROLE_ID)
    ]
    assert actions == ["read", "write"]


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_COMPLIANCE_API_KEY"),
    reason="Requires ANTHROPIC_COMPLIANCE_API_KEY.",
)
def test_integration_list_roles() -> None:
    with ComplianceClient() as client:
        orgs = client.organizations.list()
        if not orgs:
            pytest.skip("No organisations available to list roles for.")
        page = client.roles.list(orgs[0].uuid, limit=5)
    assert isinstance(page, OffsetPage)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _role(id_: str) -> dict[str, Any]:
    return {**SPEC_EXAMPLE_ROLE, "id": id_}


def _permission(action: str) -> dict[str, Any]:
    return {**SPEC_EXAMPLE_PERMISSION, "action": action}
