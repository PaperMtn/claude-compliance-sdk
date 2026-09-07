"""Tests for the Remote Sessions resource group.

Fixtures are lifted from the response examples in
spec-snapshots/2026-09-04/compliance-sessions.md.

Covers the two endpoints, the user/agent ownership split, the id-filter
length caps, the transcript envelope, the pending-session 404, and
sync+async parity.

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
    NotFoundError,
    OffsetPage,
    RemoteSession,
    RemoteSessionMessage,
    SessionUser,
)
from claude_compliance_sdk.resources.remote_sessions import (
    REMOTE_SESSIONS_PATH,
    RemoteSessionTranscript,
)
from tests.conftest import requires_live_key

API_KEY = "sk-ant-api01-test"
BASE_URL = "https://api.anthropic.test"
SESSION_ID = "cse_01WpQrStUvXyZaBcDeFgHjK6"

SPEC_USER_OWNED: dict[str, Any] = {
    "id": SESSION_ID,
    "organization_uuid": "91012d09-e48b-438e-a489-1bebfd8fa6f9",
    "user": {"id": "user_01XyDMpzjS89pFZXqSFUBDr6", "email_address": "user@example.com"},
    "agent_id": None,
    "started_by_user": None,
    "status": "active",
    "created_at": "2026-07-01T17:04:05Z",
    "updated_at": "2026-07-01T18:00:41Z",
    "product_surface": "cowork_remote",
    "claude_project_id": "claude_proj_01KGp4eZNug9ri4kE35RSppq",
}

SPEC_AGENT_OWNED: dict[str, Any] = {
    "id": "cse_01TkNpRsUvWxYzAbCdEfGhJ4",
    "organization_uuid": "91012d09-e48b-438e-a489-1bebfd8fa6f9",
    "user": None,
    "agent_id": "cagt_01MnPqRsTuVwXyZaBcDeFgH8",
    "started_by_user": {
        "id": "user_01XyDMpzjS89pFZXqSFUBDr6",
        "email_address": "user@example.com",
    },
    "status": "archived",
    "created_at": "2026-06-28T09:15:22Z",
    "updated_at": "2026-06-28T09:47:10Z",
    "product_surface": "cowork_remote",
    "claude_project_id": None,
}

SPEC_EXAMPLE_MESSAGE: dict[str, Any] = {
    "id": "csev_01HjKmNpQrStUvWxYzAbCdE2",
    "role": "user",
    "created_at": "2026-07-01T17:04:05Z",
    "content": [
        {
            "type": "text",
            "text": "Summarize the customer feedback in the attached spreadsheet.",
            "truncated": False,
        }
    ],
    "sent_by_user_id": None,
    "content_unavailable": False,
}


def _messages_url(session_id: str = SESSION_ID) -> str:
    return f"{BASE_URL}{REMOTE_SESSIONS_PATH}/{session_id}/messages"


@pytest.fixture
def sync_client() -> ComplianceClient:
    client = ComplianceClient(api_key=API_KEY, base_url=BASE_URL, max_retries=0, rate_limit_rpm=0)
    yield client
    client.close()


@pytest.fixture
async def async_client() -> AsyncComplianceClient:
    client = AsyncComplianceClient(
        api_key=API_KEY, base_url=BASE_URL, max_retries=0, rate_limit_rpm=0
    )
    yield client
    await client.aclose()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_user_owned_session_nests_user() -> None:
    session = RemoteSession.from_dict(SPEC_USER_OWNED)
    assert isinstance(session.user, SessionUser)
    assert session.user.email_address == "user@example.com"
    assert session.agent_id is None
    assert session.started_by_user is None
    assert session.claude_project_id == "claude_proj_01KGp4eZNug9ri4kE35RSppq"


def test_agent_owned_session_nests_started_by_user() -> None:
    # A session is owned by either a user or an agent, never both; the
    # human who kicked off an agent run shows up in started_by_user.
    session = RemoteSession.from_dict(SPEC_AGENT_OWNED)
    assert session.user is None
    assert session.agent_id == "cagt_01MnPqRsTuVwXyZaBcDeFgH8"
    assert isinstance(session.started_by_user, SessionUser)
    assert session.started_by_user.id == "user_01XyDMpzjS89pFZXqSFUBDr6"


@pytest.mark.parametrize(
    "status", ["pending", "active", "paused", "archived", "failed", "some_future_state"]
)
def test_session_passes_through_every_status(status: str) -> None:
    assert RemoteSession.from_dict({**SPEC_USER_OWNED, "status": status}).status == status


def test_message_parses_known_fields() -> None:
    message = RemoteSessionMessage.from_dict(SPEC_EXAMPLE_MESSAGE)
    assert message.role == "user"
    assert message.content_unavailable is False
    assert message.sent_by_user_id is None
    assert message.extra == {}


def test_message_content_unavailable() -> None:
    message = RemoteSessionMessage.from_dict(
        {**SPEC_EXAMPLE_MESSAGE, "content": [], "content_unavailable": True}
    )
    assert message.content_unavailable is True
    assert message.content == []


# ---------------------------------------------------------------------------
# .list() / .iter()
# ---------------------------------------------------------------------------


def test_list_returns_offset_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{REMOTE_SESSIONS_PATH}",
        json={"data": [SPEC_USER_OWNED, SPEC_AGENT_OWNED], "next_page": None},
    )
    page = sync_client.remote_sessions.list()
    assert isinstance(page, OffsetPage)
    assert [s.id for s in page.data] == [SESSION_ID, SPEC_AGENT_OWNED["id"]]
    assert page.has_more is False


def test_list_derives_has_more_from_next_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{REMOTE_SESSIONS_PATH}",
        json={"data": [SPEC_USER_OWNED], "next_page": "page_AAEfMk9"},
    )
    assert sync_client.remote_sessions.list().has_more is True


def test_list_sends_array_filters(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=(
            f"{BASE_URL}{REMOTE_SESSIONS_PATH}"
            "?organization_ids%5B%5D=org_a&user_ids%5B%5D=u1&user_ids%5B%5D=u2"
        ),
        json={"data": [], "next_page": None},
    )
    sync_client.remote_sessions.list(organization_ids=["org_a"], user_ids=["u1", "u2"])
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params.get_list("user_ids[]") == ["u1", "u2"]


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"user_ids": []}, "between 1 and 10"),
        ({"user_ids": [f"u{i}" for i in range(11)]}, "between 1 and 10"),
        ({"organization_ids": [f"o{i}" for i in range(501)]}, "at most 500"),
    ],
)
def test_list_validates_id_filter_lengths(
    sync_client: ComplianceClient, kwargs: dict[str, Any], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        sync_client.remote_sessions.list(**kwargs)


def test_iter_validates_id_filter_lengths(sync_client: ComplianceClient) -> None:
    # iter() is a generator factory, so the guard must fire on the call
    # rather than on first iteration.
    with pytest.raises(ValueError, match="between 1 and 10"):
        sync_client.remote_sessions.iter(user_ids=[])


def test_list_passes_time_filters_and_limit(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=(
            f"{BASE_URL}{REMOTE_SESSIONS_PATH}"
            "?created_at.gte=2026-06-01T00%3A00%3A00Z"
            "&created_at.gt=2026-06-02T00%3A00%3A00Z"
            "&created_at.lte=2026-07-01T00%3A00%3A00Z"
            "&created_at.lt=2026-07-02T00%3A00%3A00Z"
            "&page=tok&limit=500"
        ),
        json={"data": [], "next_page": None},
    )
    sync_client.remote_sessions.list(
        created_at_gte="2026-06-01T00:00:00Z",
        created_at_gt="2026-06-02T00:00:00Z",
        created_at_lte="2026-07-01T00:00:00Z",
        created_at_lt="2026-07-02T00:00:00Z",
        page="tok",
        limit=500,
    )
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["created_at.gte"] == "2026-06-01T00:00:00Z"
    assert request.url.params["limit"] == "500"


def test_iter_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{REMOTE_SESSIONS_PATH}",
        json={"data": [SPEC_USER_OWNED], "next_page": "p2"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{REMOTE_SESSIONS_PATH}?page=p2",
        json={"data": [SPEC_AGENT_OWNED], "next_page": None},
    )
    ids = [s.id for s in sync_client.remote_sessions.iter()]
    assert ids == [SESSION_ID, SPEC_AGENT_OWNED["id"]]


def test_iter_empty(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{REMOTE_SESSIONS_PATH}", json={"data": [], "next_page": None}
    )
    assert list(sync_client.remote_sessions.iter()) == []


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------


def test_list_messages_splits_envelope(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json={"session": SPEC_USER_OWNED, "data": [SPEC_EXAMPLE_MESSAGE], "next_page": None},
    )
    transcript = sync_client.remote_sessions.list_messages(SESSION_ID)
    assert isinstance(transcript, RemoteSessionTranscript)
    assert transcript.session.id == SESSION_ID
    assert transcript.messages.data[0].id == SPEC_EXAMPLE_MESSAGE["id"]


def test_list_messages_passes_every_param(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=(
            f"{_messages_url()}?order=desc&page=p1&limit=1000"
            "&tool_use_input_max_bytes=-1&tool_result_max_bytes=2048"
        ),
        json={"session": SPEC_USER_OWNED, "data": [], "next_page": None},
    )
    sync_client.remote_sessions.list_messages(
        SESSION_ID,
        order="desc",
        page="p1",
        limit=1000,
        tool_use_input_max_bytes=-1,
        tool_result_max_bytes=2048,
    )
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["order"] == "desc"
    assert request.url.params["tool_result_max_bytes"] == "2048"


def test_list_messages_rejects_zero_cap(sync_client: ComplianceClient) -> None:
    with pytest.raises(ValueError, match="0 is rejected"):
        sync_client.remote_sessions.list_messages(SESSION_ID, tool_use_input_max_bytes=0)


def test_iter_messages_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    second = {**SPEC_EXAMPLE_MESSAGE, "id": "csev_01BcDeFgHjKmNpQrStUvWxY4"}
    httpx_mock.add_response(
        url=_messages_url(),
        json={"session": SPEC_USER_OWNED, "data": [SPEC_EXAMPLE_MESSAGE], "next_page": "p2"},
    )
    httpx_mock.add_response(
        url=f"{_messages_url()}?page=p2",
        json={"session": SPEC_USER_OWNED, "data": [second], "next_page": None},
    )
    ids = [m.id for m in sync_client.remote_sessions.iter_messages(SESSION_ID)]
    assert ids == [SPEC_EXAMPLE_MESSAGE["id"], second["id"]]


def test_pending_session_messages_404(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    # A pending session has no transcript yet; the caller should retry
    # once it leaves that status rather than dropping the ID.
    httpx_mock.add_response(
        url=_messages_url(),
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Remote session not found."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.remote_sessions.list_messages(SESSION_ID)


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_list(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{REMOTE_SESSIONS_PATH}",
        json={"data": [SPEC_AGENT_OWNED], "next_page": None},
    )
    page = await async_client.remote_sessions.list()
    assert page.data[0].agent_id == "cagt_01MnPqRsTuVwXyZaBcDeFgH8"


async def test_async_iter_walks_pages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{REMOTE_SESSIONS_PATH}",
        json={"data": [SPEC_USER_OWNED], "next_page": "p2"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{REMOTE_SESSIONS_PATH}?page=p2",
        json={"data": [], "next_page": None},
    )
    ids = [s.id async for s in async_client.remote_sessions.iter()]
    assert ids == [SESSION_ID]


async def test_async_validates_id_filters(async_client: AsyncComplianceClient) -> None:
    with pytest.raises(ValueError, match="between 1 and 10"):
        await async_client.remote_sessions.list(user_ids=[])


async def test_async_list_messages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json={"session": SPEC_USER_OWNED, "data": [SPEC_EXAMPLE_MESSAGE], "next_page": None},
    )
    transcript = await async_client.remote_sessions.list_messages(SESSION_ID)
    assert transcript.messages.data[0].role == "user"


async def test_async_iter_messages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json={"session": SPEC_USER_OWNED, "data": [SPEC_EXAMPLE_MESSAGE], "next_page": None},
    )
    ids = [m.id async for m in async_client.remote_sessions.iter_messages(SESSION_ID)]
    assert ids == [SPEC_EXAMPLE_MESSAGE["id"]]


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@requires_live_key
def test_integration_list_remote_sessions() -> None:
    with ComplianceClient() as client:
        page = client.remote_sessions.list(limit=1)
    assert isinstance(page, OffsetPage)
    for session in page.data:
        assert session.id.startswith("cse_")
        assert session.status
