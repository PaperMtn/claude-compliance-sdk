"""Tests for the Groups resource group."""

from __future__ import annotations

import os
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import AsyncComplianceClient, ComplianceClient, NotFoundError, OffsetPage
from claude_compliance_sdk.resources.groups import GROUPS_PATH, Group, GroupMember

API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
GROUP_ID = "group_abc123"


SPEC_EXAMPLE_GROUP: dict[str, Any] = {
    "id": "group_abc123",
    "name": "Engineering",
    "description": "All engineers.",
    "source_type": "direct",
    "created_at": "2025-05-01T09:00:00Z",
    "updated_at": "2025-06-01T09:00:00Z",
    "roles": ["role_abc123", "role_def456"],
}

SPEC_EXAMPLE_GROUP_MEMBER: dict[str, Any] = {
    "user_id": "user_abc123",
    "email": "ada@example.com",
    "created_at": "2025-05-15T10:00:00Z",
    "updated_at": "2025-05-15T10:00:00Z",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_group_from_dict() -> None:
    group = Group.from_dict(SPEC_EXAMPLE_GROUP)
    assert group.id == "group_abc123"
    assert group.name == "Engineering"
    assert group.source_type == "direct"
    assert group.roles == ["role_abc123", "role_def456"]


def test_group_from_dict_scim_source() -> None:
    body = dict(SPEC_EXAMPLE_GROUP)
    body["source_type"] = "scim"
    body["roles"] = None
    group = Group.from_dict(body)
    assert group.source_type == "scim"
    assert group.roles is None


def test_group_from_dict_null_timestamps() -> None:
    body = dict(SPEC_EXAMPLE_GROUP)
    body["created_at"] = None
    body["updated_at"] = None
    group = Group.from_dict(body)
    assert group.created_at is None
    assert group.updated_at is None


def test_group_member_from_dict() -> None:
    member = GroupMember.from_dict(SPEC_EXAMPLE_GROUP_MEMBER)
    assert member.user_id == "user_abc123"
    assert member.email == "ada@example.com"
    assert member.created_at == "2025-05-15T10:00:00Z"


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


def _members_url(suffix: str = "") -> str:
    return f"{BASE_URL}{GROUPS_PATH}/{GROUP_ID}/members{suffix}"


# ---------------------------------------------------------------------------
# .list() / .iter() / .get()
# ---------------------------------------------------------------------------


def test_list_returns_offset_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}",
        json={"data": [SPEC_EXAMPLE_GROUP], "has_more": False, "next_page": None},
    )
    page = sync_client.groups.list()
    assert isinstance(page, OffsetPage)
    assert page.data[0].id == "group_abc123"


def test_list_passes_limit_and_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}?limit=500&page=tok",
        json={"data": [], "has_more": False, "next_page": None},
    )
    sync_client.groups.list(limit=500, page="tok")
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["limit"] == "500"
    assert request.url.params["page"] == "tok"


def test_iter_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}",
        json={"data": [_group("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}?page=tok_1",
        json={"data": [_group("b")], "has_more": False, "next_page": None},
    )
    ids = [g.id for g in sync_client.groups.iter()]
    assert ids == ["a", "b"]


def test_get_returns_group(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}/{GROUP_ID}",
        json=SPEC_EXAMPLE_GROUP,
    )
    group = sync_client.groups.get(GROUP_ID)
    assert group.id == GROUP_ID


def test_get_404_raises_not_found(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}/{GROUP_ID}",
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Group not found."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.groups.get(GROUP_ID)


# ---------------------------------------------------------------------------
# .list_members() / .iter_members()
# ---------------------------------------------------------------------------


def test_list_members(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_members_url(),
        json={
            "data": [SPEC_EXAMPLE_GROUP_MEMBER],
            "has_more": False,
            "next_page": None,
        },
    )
    page = sync_client.groups.list_members(GROUP_ID)
    assert isinstance(page, OffsetPage)
    assert page.data[0].user_id == "user_abc123"


def test_iter_members_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_members_url(),
        json={
            "data": [_member("user_a")],
            "has_more": True,
            "next_page": "tok_1",
        },
    )
    httpx_mock.add_response(
        url=_members_url("?page=tok_1"),
        json={
            "data": [_member("user_b")],
            "has_more": False,
            "next_page": None,
        },
    )
    ids = [m.user_id for m in sync_client.groups.iter_members(GROUP_ID)]
    assert ids == ["user_a", "user_b"]


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_list(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}",
        json={"data": [SPEC_EXAMPLE_GROUP], "has_more": False, "next_page": None},
    )
    page = await async_client.groups.list()
    assert page.data[0].name == "Engineering"


async def test_async_iter(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}",
        json={"data": [_group("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}?page=tok_1",
        json={"data": [_group("b")], "has_more": False, "next_page": None},
    )
    ids = [g.id async for g in async_client.groups.iter()]
    assert ids == ["a", "b"]


async def test_async_get(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GROUPS_PATH}/{GROUP_ID}",
        json=SPEC_EXAMPLE_GROUP,
    )
    group = await async_client.groups.get(GROUP_ID)
    assert group.id == GROUP_ID


async def test_async_list_members(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_members_url(),
        json={
            "data": [SPEC_EXAMPLE_GROUP_MEMBER],
            "has_more": False,
            "next_page": None,
        },
    )
    page = await async_client.groups.list_members(GROUP_ID)
    assert page.data[0].email == "ada@example.com"


async def test_async_iter_members(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_members_url(),
        json={
            "data": [_member("user_a"), _member("user_b")],
            "has_more": False,
            "next_page": None,
        },
    )
    ids = [m.user_id async for m in async_client.groups.iter_members(GROUP_ID)]
    assert ids == ["user_a", "user_b"]


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_COMPLIANCE_API_KEY"),
    reason="Requires ANTHROPIC_COMPLIANCE_API_KEY.",
)
def test_integration_list_groups() -> None:
    with ComplianceClient() as client:
        page = client.groups.list(limit=5)
    assert isinstance(page, OffsetPage)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _group(id_: str) -> dict[str, Any]:
    return {**SPEC_EXAMPLE_GROUP, "id": id_}


def _member(user_id: str) -> dict[str, Any]:
    return {**SPEC_EXAMPLE_GROUP_MEMBER, "user_id": user_id}
