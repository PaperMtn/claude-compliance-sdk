"""Tests for the Organizations resource group.

Covers Organization and User dataclasses, the offset-paginated
list() / iter() and list_users() / iter_users() pairs, and sync+async
parity throughout.

Integration test gated on a live Compliance Access Key.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import (
    AsyncComplianceClient,
    ComplianceClient,
    InternalServerError,
    NotFoundError,
    OffsetPage,
)
from claude_compliance_sdk.resources.organizations import (
    ORGANIZATIONS_PATH,
    ComplianceApiKey,
    Organization,
    OrganizationSettings,
    User,
    _build_page_params,
)
from tests.conftest import requires_live_key

API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
ORG_UUID = "abcdef01-2345-6789-abcd-0123456789ab"


SPEC_EXAMPLE_ORG: dict[str, Any] = {
    "uuid": "abcdef01-2345-6789-abcd-0123456789ab",
    "name": "Acme Compliance",
    "created_at": "2025-06-01T10:00:00Z",
}

SPEC_EXAMPLE_USER: dict[str, Any] = {
    "id": "user_abc123",
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "created_at": "2025-06-07T08:09:10Z",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_organization_from_dict_parses_known_fields() -> None:
    org = Organization.from_dict(SPEC_EXAMPLE_ORG)
    assert org.uuid == "abcdef01-2345-6789-abcd-0123456789ab"
    assert org.name == "Acme Compliance"
    assert org.created_at == "2025-06-01T10:00:00Z"
    assert org.extra == {}


def test_organization_from_dict_captures_unknown_fields_in_extra() -> None:
    body = dict(SPEC_EXAMPLE_ORG)
    body["future_field"] = "future"
    org = Organization.from_dict(body)
    assert org.extra == {"future_field": "future"}


def test_user_from_dict_parses_known_fields() -> None:
    user = User.from_dict(SPEC_EXAMPLE_USER)
    assert user.id == "user_abc123"
    assert user.full_name == "Ada Lovelace"
    assert user.email == "ada@example.com"
    assert user.created_at == "2025-06-07T08:09:10Z"
    assert user.extra == {}


def test_user_from_dict_parses_organization_role() -> None:
    # Built-in membership level; kept as a plain string because new
    # values (claude_code_user was one) ship without notice.
    user = User.from_dict({**SPEC_EXAMPLE_USER, "organization_role": "claude_code_user"})
    assert user.organization_role == "claude_code_user"
    assert "organization_role" not in user.extra


def test_user_from_dict_without_organization_role() -> None:
    body = {k: v for k, v in SPEC_EXAMPLE_USER.items() if k != "organization_role"}
    assert User.from_dict(body).organization_role is None


def test_user_from_dict_captures_unknown_fields_in_extra() -> None:
    body = dict(SPEC_EXAMPLE_USER)
    body["role"] = "admin"
    user = User.from_dict(body)
    assert user.extra == {"role": "admin"}


# ---------------------------------------------------------------------------
# _build_page_params
# ---------------------------------------------------------------------------


def test_build_page_params_drops_nones() -> None:
    assert _build_page_params(limit=None, page=None) == {}


def test_build_page_params_includes_limit_and_page() -> None:
    assert _build_page_params(limit=100, page="tok_abc") == {"limit": 100, "page": "tok_abc"}


SPEC_EXAMPLE_SETTINGS: dict[str, Any] = {
    "type": "effective_organization_settings",
    "organization_id": "91012d09-e48b-438e-a489-1bebfd8fa6f9",
    "settings": [
        {
            "name": "data_retention_periods",
            "type": "data_retention",
            "value": {"chat": {"type": "fixed", "timescale": "day", "duration": 90}},
        },
        {"name": "content_redaction_enabled", "type": "boolean", "value": True},
        {"name": "ip_allowlist_ip_ranges", "type": "string_list", "value": ["10.0.0.0/8"]},
    ],
    "api_keys": [
        {
            "type": "compliance_api_key",
            "id": "apikey_01Hx7k2mP9nQ4rS6tU8vW0xY",
            "name": "Compliance Export Key",
            "scopes": ["read:compliance_activities", "read:compliance_org_data"],
            "is_active": True,
            "created_at": "2026-03-14T09:30:00Z",
            "created_by_id": "user_01Jz3a4bC5dE6fG7hI8jK9lM",
            "expires_at": None,
        }
    ],
}


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


# ---------------------------------------------------------------------------
# .list() / .iter() — offset-paginated organizations
# ---------------------------------------------------------------------------


def test_list_returns_offset_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}",
        json={"data": [SPEC_EXAMPLE_ORG], "has_more": False, "next_page": None},
    )
    page = sync_client.organizations.list()
    assert isinstance(page, OffsetPage)
    assert len(page.data) == 1
    assert isinstance(page.data[0], Organization)
    assert page.data[0].uuid == SPEC_EXAMPLE_ORG["uuid"]
    assert page.has_more is False
    assert page.next_page is None


def test_list_empty_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}",
        json={"data": [], "has_more": False, "next_page": None},
    )
    page = sync_client.organizations.list()
    assert page.data == []
    assert page.has_more is False


def test_list_passes_limit_and_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}?limit=1000&page=tok_abc",
        json={"data": [], "has_more": False, "next_page": None},
    )
    sync_client.organizations.list(limit=1000, page="tok_abc")
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["limit"] == "1000"
    assert request.url.params["page"] == "tok_abc"


def test_list_sends_no_query_params_by_default(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}",
        json={"data": [], "has_more": False, "next_page": None},
    )
    sync_client.organizations.list()
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.query == b""


def test_iter_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    # A tenant with more organisations than one page holds. Before
    # organizations became paginated the SDK returned page one and
    # silently dropped the rest.
    second_org = {**SPEC_EXAMPLE_ORG, "uuid": "5a1b2c3d-4e5f-6789-abcd-ef0123456789"}
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}",
        json={"data": [SPEC_EXAMPLE_ORG], "has_more": True, "next_page": "tok_2"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}?page=tok_2",
        json={"data": [second_org], "has_more": False, "next_page": None},
    )
    uuids = [org.uuid for org in sync_client.organizations.iter()]
    assert uuids == [SPEC_EXAMPLE_ORG["uuid"], second_org["uuid"]]


def test_iter_empty(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}",
        json={"data": [], "has_more": False, "next_page": None},
    )
    assert list(sync_client.organizations.iter()) == []


def test_iter_carries_limit_across_pages(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}?limit=1",
        json={"data": [SPEC_EXAMPLE_ORG], "has_more": True, "next_page": "tok_2"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}?limit=1&page=tok_2",
        json={"data": [], "has_more": False, "next_page": None},
    )
    list(sync_client.organizations.iter(limit=1))
    for request in httpx_mock.get_requests():
        assert request.url.params["limit"] == "1"


# ---------------------------------------------------------------------------
# .list_users() / .iter_users() — offset-paginated users
# ---------------------------------------------------------------------------


def _users_url(suffix: str = "") -> str:
    return f"{BASE_URL}{ORGANIZATIONS_PATH}/{ORG_UUID}/users{suffix}"


def test_list_users_returns_offset_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_users_url(),
        json={"data": [SPEC_EXAMPLE_USER], "has_more": True, "next_page": "tok_1"},
    )
    page = sync_client.organizations.list_users(ORG_UUID)
    assert isinstance(page, OffsetPage)
    assert len(page.data) == 1
    assert isinstance(page.data[0], User)
    assert page.has_more is True
    assert page.next_page == "tok_1"


def test_list_users_passes_limit_and_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_users_url("?limit=250&page=tok_abc"),
        json={"data": [], "has_more": False, "next_page": None},
    )
    sync_client.organizations.list_users(ORG_UUID, limit=250, page="tok_abc")
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["limit"] == "250"
    assert request.url.params["page"] == "tok_abc"


def test_iter_users_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_users_url(),
        json={"data": [_user("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=_users_url("?page=tok_1"),
        json={"data": [_user("b"), _user("c")], "has_more": False, "next_page": None},
    )
    users = list(sync_client.organizations.iter_users(ORG_UUID))
    assert [u.id for u in users] == ["a", "b", "c"]


def test_iter_users_carries_limit_across_pages(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_users_url("?limit=2"),
        json={"data": [_user("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=_users_url("?limit=2&page=tok_1"),
        json={"data": [_user("b")], "has_more": False, "next_page": None},
    )
    users = list(sync_client.organizations.iter_users(ORG_UUID, limit=2))
    assert [u.id for u in users] == ["a", "b"]


def test_iter_users_empty(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_users_url(),
        json={"data": [], "has_more": False, "next_page": None},
    )
    assert list(sync_client.organizations.iter_users(ORG_UUID)) == []


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_list_returns_offset_page(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}",
        json={"data": [SPEC_EXAMPLE_ORG], "has_more": False, "next_page": None},
    )
    page = await async_client.organizations.list()
    assert isinstance(page, OffsetPage)
    assert len(page.data) == 1
    assert page.data[0].uuid == SPEC_EXAMPLE_ORG["uuid"]


async def test_async_iter_walks_pages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    second_org = {**SPEC_EXAMPLE_ORG, "uuid": "5a1b2c3d-4e5f-6789-abcd-ef0123456789"}
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}",
        json={"data": [SPEC_EXAMPLE_ORG], "has_more": True, "next_page": "tok_2"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{ORGANIZATIONS_PATH}?page=tok_2",
        json={"data": [second_org], "has_more": False, "next_page": None},
    )
    uuids = [org.uuid async for org in async_client.organizations.iter()]
    assert uuids == [SPEC_EXAMPLE_ORG["uuid"], second_org["uuid"]]


async def test_async_list_users(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_users_url(),
        json={"data": [SPEC_EXAMPLE_USER], "has_more": False, "next_page": None},
    )
    page = await async_client.organizations.list_users(ORG_UUID)
    assert page.has_more is False
    assert page.data[0].full_name == "Ada Lovelace"


async def test_async_iter_users_walks_pages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_users_url(),
        json={"data": [_user("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=_users_url("?page=tok_1"),
        json={"data": [_user("b")], "has_more": False, "next_page": None},
    )
    ids = [u.id async for u in async_client.organizations.iter_users(ORG_UUID)]
    assert ids == ["a", "b"]


# ---------------------------------------------------------------------------
# Integration — live API, skipped unless key set
# ---------------------------------------------------------------------------


@pytest.mark.integration
@requires_live_key
def test_integration_list_organizations() -> None:
    with ComplianceClient() as client:
        page = client.organizations.list()
        orgs = list(client.organizations.iter())
    assert isinstance(page, OffsetPage)
    for org in orgs:
        assert org.uuid
        assert org.name
        assert org.created_at


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(id_: str) -> dict[str, Any]:
    return {
        "id": id_,
        "full_name": f"User {id_}",
        "email": f"{id_}@example.com",
        "created_at": "2025-06-07T08:09:10Z",
    }


# ---------------------------------------------------------------------------
# .get_settings()
# ---------------------------------------------------------------------------


def _settings_url(org_uuid: str = "91012d09-e48b-438e-a489-1bebfd8fa6f9") -> str:
    return f"{BASE_URL}{ORGANIZATIONS_PATH}/{org_uuid}/settings"


def test_get_settings_parses_rows_and_keys(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_settings_url(), json=SPEC_EXAMPLE_SETTINGS)
    settings = sync_client.organizations.get_settings("91012d09-e48b-438e-a489-1bebfd8fa6f9")
    assert isinstance(settings, OrganizationSettings)
    # organization_id is the bare UUID here, not the org_-prefixed form
    # the same field name carries on activity and chat records.
    assert settings.organization_id == "91012d09-e48b-438e-a489-1bebfd8fa6f9"
    assert not settings.organization_id.startswith("org_")
    assert len(settings.settings) == 3
    assert isinstance(settings.api_keys[0], ComplianceApiKey)
    assert settings.api_keys[0].scopes == [
        "read:compliance_activities",
        "read:compliance_org_data",
    ]
    assert settings.api_keys[0].expires_at is None


def test_get_settings_keeps_rows_as_raw_dicts(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    # 50+ setting names exist and the list grows, so callers branch on
    # `type` rather than the SDK enumerating them.
    httpx_mock.add_response(url=_settings_url(), json=SPEC_EXAMPLE_SETTINGS)
    settings = sync_client.organizations.get_settings("91012d09-e48b-438e-a489-1bebfd8fa6f9")
    by_type = {row["type"]: row["value"] for row in settings.settings}
    assert by_type["boolean"] is True
    assert by_type["string_list"] == ["10.0.0.0/8"]
    assert by_type["data_retention"]["chat"]["duration"] == 90


def test_get_settings_tolerates_an_unknown_setting_type(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    body = {
        **SPEC_EXAMPLE_SETTINGS,
        "settings": [{"name": "future_setting", "type": "future_type", "value": {"a": 1}}],
    }
    httpx_mock.add_response(url=_settings_url(), json=body)
    settings = sync_client.organizations.get_settings("91012d09-e48b-438e-a489-1bebfd8fa6f9")
    assert settings.settings[0]["type"] == "future_type"


def test_get_settings_without_api_keys(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    body = {k: v for k, v in SPEC_EXAMPLE_SETTINGS.items() if k != "api_keys"}
    httpx_mock.add_response(url=_settings_url(), json=body)
    assert (
        sync_client.organizations.get_settings("91012d09-e48b-438e-a489-1bebfd8fa6f9").api_keys
        == []
    )


def test_get_settings_404_does_not_prove_absence(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    # Unknown org, invalid UUID, and "endpoint not enabled for your
    # parent" deliberately share one response.
    httpx_mock.add_response(
        url=_settings_url("nope"),
        status_code=404,
        json={
            "error": {
                "type": "not_found_error",
                "message": "organization `nope` not found in this organization's hierarchy",
            }
        },
    )
    with pytest.raises(NotFoundError):
        sync_client.organizations.get_settings("nope")


async def test_async_get_settings(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_settings_url(), json=SPEC_EXAMPLE_SETTINGS)
    settings = await async_client.organizations.get_settings("91012d09-e48b-438e-a489-1bebfd8fa6f9")
    assert settings.type == "effective_organization_settings"
    assert settings.api_keys[0].is_active is True
