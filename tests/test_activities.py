"""Tests for the Activities resource group.

Covers the Activity dataclass parser, the query-param builder, the
``.list()`` and ``.iter()`` methods on both sync and async variants,
and the most likely error path (``InsufficientScopeError`` from the
admin-key-only-no-scope server response).

The integration test at the bottom hits the live Compliance API when
``ANTHROPIC_COMPLIANCE_API_KEY`` is set, and is skipped otherwise
(per CLAUDE.md's testing conventions).
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import (
    AsyncComplianceClient,
    ComplianceClient,
    CursorPage,
    InsufficientScopeError,
)
from claude_compliance_sdk.resources.activities import (
    ACTIVITIES_PATH,
    Activity,
    _build_query_params,
)

API_KEY = "sk-ant-admin01-test-key"
BASE_URL = "https://api.test.invalid"


# ---------------------------------------------------------------------------
# Activity.from_dict
# ---------------------------------------------------------------------------


SPEC_EXAMPLE_ACTIVITY: dict[str, Any] = {
    "id": "activity_abc123",
    "created_at": "2025-06-07T08:09:10Z",
    "organization_id": "org_abc123",
    "organization_uuid": "abcdef01-2345-6789-abcd-0123456789ab",
    "actor": {
        "type": "user_actor",
        "email_address": "user@example.com",
        "user_id": "user_xyz456",
        "ip_address": "192.0.2.34",
        "user_agent": "Mozilla/5.0...",
    },
    "type": "claude_chat_created",
    "claude_chat_id": "claude_chat_xyz789",
    "claude_project_id": None,
}


def test_from_dict_parses_known_fields() -> None:
    activity = Activity.from_dict(SPEC_EXAMPLE_ACTIVITY)
    assert activity.id == "activity_abc123"
    assert activity.created_at == "2025-06-07T08:09:10Z"
    assert activity.type == "claude_chat_created"
    assert activity.organization_id == "org_abc123"
    assert activity.organization_uuid == "abcdef01-2345-6789-abcd-0123456789ab"
    assert activity.actor == SPEC_EXAMPLE_ACTIVITY["actor"]


def test_from_dict_stashes_type_specific_fields_in_extra() -> None:
    activity = Activity.from_dict(SPEC_EXAMPLE_ACTIVITY)
    assert activity.extra == {
        "claude_chat_id": "claude_chat_xyz789",
        "claude_project_id": None,
    }


def test_from_dict_with_null_org_fields() -> None:
    body = dict(SPEC_EXAMPLE_ACTIVITY)
    body["organization_id"] = None
    body["organization_uuid"] = None
    activity = Activity.from_dict(body)
    assert activity.organization_id is None
    assert activity.organization_uuid is None


def test_from_dict_preserves_unknown_top_level_fields_in_extra() -> None:
    body = dict(SPEC_EXAMPLE_ACTIVITY)
    body["future_field"] = "something the spec adds later"
    activity = Activity.from_dict(body)
    assert activity.extra["future_field"] == "something the spec adds later"


# ---------------------------------------------------------------------------
# _build_query_params
# ---------------------------------------------------------------------------


def test_build_params_returns_empty_dict_when_all_none() -> None:
    params = _build_query_params(
        organization_ids=None,
        actor_ids=None,
        activity_types=None,
        created_at_gte=None,
        created_at_gt=None,
        created_at_lte=None,
        created_at_lt=None,
        after_id=None,
        before_id=None,
        limit=None,
    )
    assert params == {}


def test_build_params_serialises_array_filters_with_brackets() -> None:
    params = _build_query_params(
        organization_ids=["org_a", "org_b"],
        actor_ids=["user_x"],
        activity_types=["claude_chat_created"],
        created_at_gte=None,
        created_at_gt=None,
        created_at_lte=None,
        created_at_lt=None,
        after_id=None,
        before_id=None,
        limit=None,
    )
    assert params == {
        "organization_ids[]": ["org_a", "org_b"],
        "actor_ids[]": ["user_x"],
        "activity_types[]": ["claude_chat_created"],
    }


def test_build_params_drops_empty_arrays() -> None:
    params = _build_query_params(
        organization_ids=[],
        actor_ids=None,
        activity_types=None,
        created_at_gte=None,
        created_at_gt=None,
        created_at_lte=None,
        created_at_lt=None,
        after_id=None,
        before_id=None,
        limit=None,
    )
    assert params == {}


def test_build_params_uses_dotted_form_for_time_filters() -> None:
    params = _build_query_params(
        organization_ids=None,
        actor_ids=None,
        activity_types=None,
        created_at_gte="2025-01-01T00:00:00Z",
        created_at_gt="2025-01-02T00:00:00Z",
        created_at_lte="2025-12-31T23:59:59Z",
        created_at_lt="2025-12-30T00:00:00Z",
        after_id=None,
        before_id=None,
        limit=None,
    )
    assert params == {
        "created_at.gte": "2025-01-01T00:00:00Z",
        "created_at.gt": "2025-01-02T00:00:00Z",
        "created_at.lte": "2025-12-31T23:59:59Z",
        "created_at.lt": "2025-12-30T00:00:00Z",
    }


def test_build_params_includes_cursor_and_limit() -> None:
    params = _build_query_params(
        organization_ids=None,
        actor_ids=None,
        activity_types=None,
        created_at_gte=None,
        created_at_gt=None,
        created_at_lte=None,
        created_at_lt=None,
        after_id="activity_abc",
        before_id=None,
        limit=500,
    )
    assert params == {"after_id": "activity_abc", "limit": 500}


# ---------------------------------------------------------------------------
# Sync .list() / .iter()
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


def test_list_returns_cursor_page_of_activities(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}",
        json={
            "data": [SPEC_EXAMPLE_ACTIVITY],
            "has_more": True,
            "first_id": "activity_abc123",
            "last_id": "activity_abc123",
        },
    )
    page = sync_client.activities.list()
    assert isinstance(page, CursorPage)
    assert len(page.data) == 1
    assert isinstance(page.data[0], Activity)
    assert page.data[0].id == "activity_abc123"
    assert page.has_more is True
    assert page.first_id == "activity_abc123"
    assert page.last_id == "activity_abc123"


def test_list_sends_filters_as_query_params(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=(
            f"{BASE_URL}{ACTIVITIES_PATH}"
            "?actor_ids%5B%5D=user_a"
            "&actor_ids%5B%5D=user_b"
            "&activity_types%5B%5D=claude_chat_created"
            "&created_at.gte=2025-01-01T00:00:00Z"
            "&limit=50"
        ),
        json={"data": [], "has_more": False, "first_id": None, "last_id": None},
    )
    sync_client.activities.list(
        actor_ids=["user_a", "user_b"],
        activity_types=["claude_chat_created"],
        created_at_gte="2025-01-01T00:00:00Z",
        limit=50,
    )
    request = httpx_mock.get_request()
    assert request is not None
    # Repeated array params are sent as one per occurrence.
    assert request.url.params.get_list("actor_ids[]") == ["user_a", "user_b"]
    assert request.url.params.get_list("activity_types[]") == ["claude_chat_created"]
    assert request.url.params["created_at.gte"] == "2025-01-01T00:00:00Z"
    assert request.url.params["limit"] == "50"


def test_iter_walks_multiple_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}",
        json={
            "data": [_activity("a")],
            "has_more": True,
            "first_id": "a",
            "last_id": "a",
        },
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}?after_id=a",
        json={
            "data": [_activity("b"), _activity("c")],
            "has_more": False,
            "first_id": "b",
            "last_id": "c",
        },
    )
    activities = list(sync_client.activities.iter())
    assert [a.id for a in activities] == ["a", "b", "c"]


def test_iter_carries_filters_to_each_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}?activity_types%5B%5D=api_key_created&limit=10",
        json={
            "data": [_activity("a")],
            "has_more": True,
            "first_id": "a",
            "last_id": "a",
        },
    )
    httpx_mock.add_response(
        url=(
            f"{BASE_URL}{ACTIVITIES_PATH}"
            "?activity_types%5B%5D=api_key_created&limit=10&after_id=a"
        ),
        json={
            "data": [_activity("b")],
            "has_more": False,
            "first_id": "b",
            "last_id": "b",
        },
    )
    out = list(sync_client.activities.iter(activity_types=["api_key_created"], limit=10))
    assert [a.id for a in out] == ["a", "b"]


def test_iter_empty_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}",
        json={"data": [], "has_more": False, "first_id": None, "last_id": None},
    )
    assert list(sync_client.activities.iter()) == []


def test_list_propagates_insufficient_scope_error(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    # Verbatim from the spec: a Compliance Access Key without
    # read:compliance_activities calling the Activity Feed.
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}",
        status_code=401,
        json={
            "error": {
                "type": "authentication_error",
                "message": (
                    "The API key provided does not have the "
                    "`read:compliance_activities` scope required for this endpoint. "
                    "Got scopes: []."
                ),
            }
        },
    )
    with pytest.raises(InsufficientScopeError):
        sync_client.activities.list()


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_list_returns_cursor_page_of_activities(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}",
        json={
            "data": [SPEC_EXAMPLE_ACTIVITY],
            "has_more": False,
            "first_id": "activity_abc123",
            "last_id": "activity_abc123",
        },
    )
    page = await async_client.activities.list()
    assert isinstance(page, CursorPage)
    assert page.data[0].id == "activity_abc123"


async def test_async_iter_walks_multiple_pages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}",
        json={"data": [_activity("a")], "has_more": True, "first_id": "a", "last_id": "a"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}?after_id=a",
        json={
            "data": [_activity("b")],
            "has_more": False,
            "first_id": "b",
            "last_id": "b",
        },
    )
    ids = [item.id async for item in async_client.activities.iter()]
    assert ids == ["a", "b"]


async def test_async_list_propagates_insufficient_scope_error(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{ACTIVITIES_PATH}",
        status_code=401,
        json={
            "error": {
                "type": "authentication_error",
                "message": (
                    "The API key provided does not have the "
                    "`read:compliance_activities` scope required for this endpoint."
                ),
            }
        },
    )
    with pytest.raises(InsufficientScopeError):
        await async_client.activities.list()


# ---------------------------------------------------------------------------
# Integration — live API, skipped unless ANTHROPIC_COMPLIANCE_API_KEY is set
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_COMPLIANCE_API_KEY"),
    reason="Requires ANTHROPIC_COMPLIANCE_API_KEY for live API access.",
)
def test_integration_list_one_page() -> None:
    with ComplianceClient() as client:
        page = client.activities.list(limit=5)
    assert isinstance(page, CursorPage)
    # Every activity at minimum has an id, created_at, type per spec.
    for activity in page.data:
        assert activity.id
        assert activity.created_at
        assert activity.type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _activity(id_: str) -> dict[str, Any]:
    """Minimal valid Activity payload for fixture use."""
    return {
        "id": id_,
        "created_at": "2025-06-07T08:09:10Z",
        "type": "claude_chat_created",
        "organization_id": "org_test",
        "organization_uuid": "abcdef01-2345-6789-abcd-0123456789ab",
        "actor": {"type": "user_actor", "user_id": "user_test"},
    }
