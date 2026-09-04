"""Tests for the Local Sessions resource group.

Fixtures are lifted from the response examples in
spec-snapshots/2026-09-04/compliance-sessions.md.

Covers the three endpoints, the transcript envelope, the has_more
derivation for payloads that omit the field, every documented
provenance shape plus an unrecognised one, the truncation-cap guard,
the message-refined 404 and 503 mappings, and sync+async parity.

Integration test gated on ANTHROPIC_COMPLIANCE_API_KEY.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import (
    AsyncComplianceClient,
    ComplianceClient,
    LocalSession,
    LocalSessionMessage,
    LocalSessionsRetentionUnavailableError,
    LocalSessionsUnavailableError,
    NotFoundError,
    OffsetPage,
    SessionUser,
)
from claude_compliance_sdk.resources.local_sessions import (
    LOCAL_SESSIONS_PATH,
    LocalSessionTranscript,
)

API_KEY = "sk-ant-api01-test"
BASE_URL = "https://api.anthropic.test"
SESSION_ID = "clls_01HxKpLmNoPqRsTuVwXyZaBc"

SPEC_EXAMPLE_SESSION: dict[str, Any] = {
    "type": "compliance_local_session",
    "id": SESSION_ID,
    "organization_uuid": "9a1e0000-0000-0000-0000-000000000000",
    "workspace_id": "wrkspc_01SvYKoWVRVHoEbwESNvzYdR",
    "user": {"id": "user_01GpKpLmNoPqRsTuVwXyZaBc", "email_address": "engineer@example.com"},
    "product_surface": "cowork",
    "created_at": "2026-07-09T14:02:11Z",
    "updated_at": "2026-07-09T14:02:38Z",
}

SPEC_EXAMPLE_MESSAGE: dict[str, Any] = {
    "type": "compliance_local_session_message",
    "id": "clsm_01J4KpLmNoPqRsTuVwXyZaBd",
    "role": "assistant",
    "model": "claude-opus-5",
    "created_at": "2026-07-09T14:02:11Z",
    "provenance": None,
    "content": [
        {"type": "text", "text": "I'll read the test file first.", "truncated": False},
        {
            "type": "tool_use",
            "id": "toolu_01AbCdEfGhIjKlMnOpQrSt",
            "name": "Read",
            "input": '{"file_path":"tests/auth_test.py"}',
            "truncated": False,
        },
    ],
}


def _messages_url(session_id: str = SESSION_ID) -> str:
    return f"{BASE_URL}{LOCAL_SESSIONS_PATH}/{session_id}/messages"


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


def test_local_session_from_dict_parses_known_fields() -> None:
    session = LocalSession.from_dict(SPEC_EXAMPLE_SESSION)
    assert session.id == SESSION_ID
    assert session.type == "compliance_local_session"
    assert session.product_surface == "cowork"
    assert session.workspace_id == "wrkspc_01SvYKoWVRVHoEbwESNvzYdR"
    assert session.extra == {}


def test_local_session_nests_user_dataclass() -> None:
    session = LocalSession.from_dict(SPEC_EXAMPLE_SESSION)
    assert isinstance(session.user, SessionUser)
    assert session.user.id == "user_01GpKpLmNoPqRsTuVwXyZaBc"
    assert session.user.email_address == "engineer@example.com"


def test_local_session_tolerates_null_user_email_and_workspace() -> None:
    # Deleted account, or a user outside the key's reach; and a session
    # with no workspace.
    body = {
        **SPEC_EXAMPLE_SESSION,
        "workspace_id": None,
        "user": {"id": "user_01HqRsTuVwXyZaBcDeFgHiJk", "email_address": None},
    }
    session = LocalSession.from_dict(body)
    assert session.workspace_id is None
    assert session.user is not None
    assert session.user.email_address is None


def test_local_session_passes_through_unknown_product_surface() -> None:
    # The docs explicitly ask callers to tolerate surfaces that have not
    # shipped yet rather than treating them as an error.
    session = LocalSession.from_dict({**SPEC_EXAMPLE_SESSION, "product_surface": "future_app"})
    assert session.product_surface == "future_app"


def test_local_session_message_keeps_content_blocks_as_dicts() -> None:
    message = LocalSessionMessage.from_dict(SPEC_EXAMPLE_MESSAGE)
    assert message.model == "claude-opus-5"
    assert message.provenance is None
    assert message.content[0]["type"] == "text"
    # tool_use input is a JSON-encoded string on the wire, not an object.
    assert isinstance(message.content[1]["input"], str)


@pytest.mark.parametrize(
    "provenance",
    [
        {"type": "content_unavailable", "reason": "not_captured"},
        {"type": "content_unavailable", "reason": "client_aborted"},
        {"type": "content_unavailable", "reason": "cmek_key_revoked"},
        {"type": "content_unavailable", "reason": "retention_elapsed"},
        {"type": "content_unavailable", "reason": "oversize"},
        {"type": "client_asserted"},
        {"type": "synthetic_marker"},
        {"type": "some_future_type", "reason": "who_knows"},
    ],
)
def test_local_session_message_tolerates_every_provenance(provenance: dict[str, Any]) -> None:
    message = LocalSessionMessage.from_dict(
        {**SPEC_EXAMPLE_MESSAGE, "provenance": provenance, "content": [], "model": None}
    )
    assert message.provenance == provenance
    assert message.model is None


# ---------------------------------------------------------------------------
# .list() / .iter()
# ---------------------------------------------------------------------------


def test_list_returns_offset_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}",
        json={"data": [SPEC_EXAMPLE_SESSION], "next_page": None},
    )
    page = sync_client.local_sessions.list()
    assert isinstance(page, OffsetPage)
    assert page.data[0].id == SESSION_ID


def test_list_derives_has_more_without_the_field(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    # Session responses carry next_page but no has_more at all. Reading
    # has_more must not report "done" while holding a live cursor.
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}",
        json={"data": [SPEC_EXAMPLE_SESSION], "next_page": "page_AAEfQx7"},
    )
    page = sync_client.local_sessions.list()
    assert page.next_page == "page_AAEfQx7"
    assert page.has_more is True


def test_list_has_more_false_on_final_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}",
        json={"data": [], "next_page": None},
    )
    assert sync_client.local_sessions.list().has_more is False


def test_list_passes_time_filters(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=(
            f"{BASE_URL}{LOCAL_SESSIONS_PATH}"
            "?created_at.gte=2026-07-01T00%3A00%3A00Z"
            "&created_at.lt=2026-08-01T00%3A00%3A00Z"
            "&updated_at.gte=2026-07-15T00%3A00%3A00Z"
            "&limit=500"
        ),
        json={"data": [], "next_page": None},
    )
    sync_client.local_sessions.list(
        created_at_gte="2026-07-01T00:00:00Z",
        created_at_lt="2026-08-01T00:00:00Z",
        updated_at_gte="2026-07-15T00:00:00Z",
        limit=500,
    )
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["created_at.gte"] == "2026-07-01T00:00:00Z"
    assert request.url.params["created_at.lt"] == "2026-08-01T00:00:00Z"
    assert request.url.params["updated_at.gte"] == "2026-07-15T00:00:00Z"
    assert request.url.params["limit"] == "500"


def test_iter_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    second = {**SPEC_EXAMPLE_SESSION, "id": "clls_01HyLqMnOpQrStUvWxYzAbCd"}
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}",
        json={"data": [SPEC_EXAMPLE_SESSION], "next_page": "page_2"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}?page=page_2",
        json={"data": [second], "next_page": None},
    )
    ids = [s.id for s in sync_client.local_sessions.iter()]
    assert ids == [SESSION_ID, "clls_01HyLqMnOpQrStUvWxYzAbCd"]


def test_iter_empty(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}", json={"data": [], "next_page": None}
    )
    assert list(sync_client.local_sessions.iter()) == []


# ---------------------------------------------------------------------------
# .get()
# ---------------------------------------------------------------------------


def test_get_returns_session(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}/{SESSION_ID}", json=SPEC_EXAMPLE_SESSION
    )
    assert sync_client.local_sessions.get(SESSION_ID).id == SESSION_ID


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------


def test_list_messages_splits_envelope(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json={
            "session": SPEC_EXAMPLE_SESSION,
            "data": [SPEC_EXAMPLE_MESSAGE],
            "next_page": None,
        },
    )
    transcript = sync_client.local_sessions.list_messages(SESSION_ID)
    assert isinstance(transcript, LocalSessionTranscript)
    assert transcript.session.id == SESSION_ID
    assert transcript.messages.data[0].id == SPEC_EXAMPLE_MESSAGE["id"]
    assert transcript.messages.has_more is False


def test_list_messages_passes_truncation_caps(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=(
            f"{_messages_url()}?order=desc" "&tool_use_input_max_bytes=-1&tool_result_max_bytes=-1"
        ),
        json={"session": SPEC_EXAMPLE_SESSION, "data": [], "next_page": None},
    )
    sync_client.local_sessions.list_messages(
        SESSION_ID, order="desc", tool_use_input_max_bytes=-1, tool_result_max_bytes=-1
    )
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["order"] == "desc"
    assert request.url.params["tool_use_input_max_bytes"] == "-1"
    assert request.url.params["tool_result_max_bytes"] == "-1"


@pytest.mark.parametrize(
    "kwargs",
    [{"tool_use_input_max_bytes": 0}, {"tool_result_max_bytes": 0}],
)
def test_list_messages_rejects_zero_cap_before_sending(
    sync_client: ComplianceClient, kwargs: dict[str, int]
) -> None:
    # 0 is the one value the API refuses outright, so catch it locally
    # rather than spending a request on a guaranteed 400.
    with pytest.raises(ValueError, match="0 is rejected"):
        sync_client.local_sessions.list_messages(SESSION_ID, **kwargs)


def test_list_messages_accepts_a_page_token(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{_messages_url()}?page=page_abc&limit=1000",
        json={"session": SPEC_EXAMPLE_SESSION, "data": [], "next_page": None},
    )
    sync_client.local_sessions.list_messages(SESSION_ID, page="page_abc", limit=1000)
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["page"] == "page_abc"


def test_local_session_without_a_user_key() -> None:
    body = {k: v for k, v in SPEC_EXAMPLE_SESSION.items() if k != "user"}
    assert LocalSession.from_dict(body).user is None


def test_iter_messages_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    second = {**SPEC_EXAMPLE_MESSAGE, "id": "clsm_01J4KpLmNoPqRsTuVwXyZaBf"}
    httpx_mock.add_response(
        url=_messages_url(),
        json={"session": SPEC_EXAMPLE_SESSION, "data": [SPEC_EXAMPLE_MESSAGE], "next_page": "p2"},
    )
    httpx_mock.add_response(
        url=f"{_messages_url()}?page=p2",
        json={"session": SPEC_EXAMPLE_SESSION, "data": [second], "next_page": None},
    )
    ids = [m.id for m in sync_client.local_sessions.iter_messages(SESSION_ID)]
    assert ids == [SPEC_EXAMPLE_MESSAGE["id"], second["id"]]


def test_transcript_raises_on_missing_session_envelope() -> None:
    # A response without the envelope is malformed. Surfacing the
    # dataclass TypeError matches how every other resource behaves
    # rather than inventing a half-populated session.
    with pytest.raises(TypeError):
        LocalSessionTranscript.from_dict({"data": [], "next_page": None})


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


def test_local_sessions_unavailable_is_its_own_error(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    # Returned on every call including the list, and does NOT mean a
    # session is gone, so callers should keep their queued IDs.
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}",
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Local sessions are not available."}},
    )
    with pytest.raises(LocalSessionsUnavailableError):
        sync_client.local_sessions.list()


def test_ordinary_session_not_found_stays_not_found(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}/{SESSION_ID}",
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Local session not found."}},
    )
    with pytest.raises(NotFoundError) as exc_info:
        sync_client.local_sessions.get(SESSION_ID)
    assert not isinstance(exc_info.value, LocalSessionsUnavailableError)


def test_retention_override_503_is_not_retryable(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        status_code=503,
        json={
            "error": {
                "type": "overloaded_error",
                "message": (
                    "The local-sessions index cannot currently evaluate retention "
                    "overrides for this session. Try again later."
                ),
            }
        },
    )
    with pytest.raises(LocalSessionsRetentionUnavailableError) as exc_info:
        sync_client.local_sessions.list_messages(SESSION_ID)
    assert exc_info.value.retryable is False


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_list_and_iter(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}",
        json={"data": [SPEC_EXAMPLE_SESSION], "next_page": "p2"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}?page=p2",
        json={"data": [], "next_page": None},
    )
    ids = [s.id async for s in async_client.local_sessions.iter()]
    assert ids == [SESSION_ID]


async def test_async_list_returns_page(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}?limit=10",
        json={"data": [SPEC_EXAMPLE_SESSION], "next_page": None},
    )
    page = await async_client.local_sessions.list(limit=10)
    assert page.data[0].id == SESSION_ID


async def test_async_get(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}/{SESSION_ID}", json=SPEC_EXAMPLE_SESSION
    )
    assert (await async_client.local_sessions.get(SESSION_ID)).product_surface == "cowork"


async def test_async_list_messages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json={"session": SPEC_EXAMPLE_SESSION, "data": [SPEC_EXAMPLE_MESSAGE], "next_page": None},
    )
    transcript = await async_client.local_sessions.list_messages(SESSION_ID)
    assert transcript.session.id == SESSION_ID
    assert len(transcript.messages.data) == 1


async def test_async_iter_messages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json={"session": SPEC_EXAMPLE_SESSION, "data": [SPEC_EXAMPLE_MESSAGE], "next_page": None},
    )
    ids = [m.id async for m in async_client.local_sessions.iter_messages(SESSION_ID)]
    assert ids == [SPEC_EXAMPLE_MESSAGE["id"]]


async def test_async_rejects_zero_cap(async_client: AsyncComplianceClient) -> None:
    with pytest.raises(ValueError, match="0 is rejected"):
        await async_client.local_sessions.list_messages(SESSION_ID, tool_result_max_bytes=0)


async def test_async_local_sessions_unavailable(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{LOCAL_SESSIONS_PATH}",
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Local sessions are not available."}},
    )
    with pytest.raises(LocalSessionsUnavailableError):
        await async_client.local_sessions.list()


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_COMPLIANCE_API_KEY"),
    reason="requires ANTHROPIC_COMPLIANCE_API_KEY",
)
def test_integration_list_local_sessions() -> None:
    with ComplianceClient() as client:
        page = client.local_sessions.list(limit=1)
    assert isinstance(page, OffsetPage)
    for session in page.data:
        assert session.id.startswith("clls_")
        assert session.user is not None
