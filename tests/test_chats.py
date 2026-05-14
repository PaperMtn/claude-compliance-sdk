"""Tests for the Chats resource group.

Covers the Chat / Message / ChatMessagesPage dataclasses, the
client-side user_ids length validation, the cursor-paginated .list()
and .iter() over chats, the combined chat+messages .get() endpoint,
.iter_messages() driving the same endpoint, and .delete() with
sync+async parity.

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
    CursorPage,
    NotFoundError,
)
from claude_compliance_sdk.resources.chats import (
    CHATS_PATH,
    Chat,
    ChatMessagesPage,
    Message,
    _build_list_params,
    _build_messages_params,
    _validate_user_ids,
)


API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
CHAT_ID = "claude_chat_abc123"


SPEC_EXAMPLE_CHAT: dict[str, Any] = {
    "id": "claude_chat_abc123",
    "name": "Product Requirements Discussion",
    "created_at": "2025-06-07T08:09:10Z",
    "updated_at": "2025-06-07T09:10:11Z",
    "deleted_at": None,
    "organization_id": "org_abc123",
    "organization_uuid": "abcdef01-2345-6789-abcd-0123456789ab",
    "project_id": "claude_proj_xyz789",
    "model": "claude-opus-4-7",
    "user": {"id": "user_xyz456", "email_address": "user@example.com"},
    "href": "https://claude.ai/chat/abcdef01-2345-6789-abcd-ef0123456789",
}

SPEC_EXAMPLE_USER_MESSAGE: dict[str, Any] = {
    "id": "claude_chat_msg_abc123",
    "role": "user",
    "created_at": "2025-06-07T08:09:10Z",
    "content": [
        {
            "type": "text",
            "text": "Can you help me draft requirements for our new dashboard feature?",
        }
    ],
    "files": [
        {
            "id": "claude_file_xyz789",
            "filename": "dashboard_mockup_v1.pdf",
            "mime_type": "application/pdf",
        }
    ],
}

SPEC_EXAMPLE_ASSISTANT_MESSAGE: dict[str, Any] = {
    "id": "claude_chat_msg_def456",
    "role": "assistant",
    "created_at": "2025-06-07T08:09:11Z",
    "content": [{"type": "text", "text": "I'd be happy to help..."}],
    "artifacts": [
        {
            "id": "claude_artifact_abc123",
            "version_id": "claude_artifact_version_xyz789",
            "title": "Dashboard Requirements Draft",
            "artifact_type": "text/markdown",
        }
    ],
}


def _chat_with_messages(
    *messages: dict[str, Any],
    has_more: bool = False,
    first_id: str | None = None,
    last_id: str | None = None,
) -> dict[str, Any]:
    return {
        **SPEC_EXAMPLE_CHAT,
        "chat_messages": list(messages),
        "has_more": has_more,
        "first_id": first_id,
        "last_id": last_id,
    }


# ---------------------------------------------------------------------------
# _validate_user_ids
# ---------------------------------------------------------------------------


def test_validate_user_ids_accepts_1_to_10() -> None:
    for n in (1, 5, 10):
        _validate_user_ids([f"user_{i}" for i in range(n)])


def test_validate_user_ids_rejects_empty() -> None:
    with pytest.raises(ValueError, match="between 1 and 10"):
        _validate_user_ids([])


def test_validate_user_ids_rejects_more_than_10() -> None:
    with pytest.raises(ValueError, match="between 1 and 10"):
        _validate_user_ids([f"user_{i}" for i in range(11)])


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_chat_from_dict_parses_known_fields() -> None:
    chat = Chat.from_dict(SPEC_EXAMPLE_CHAT)
    assert chat.id == "claude_chat_abc123"
    assert chat.deleted_at is None
    assert chat.model == "claude-opus-4-7"
    assert chat.user == {"id": "user_xyz456", "email_address": "user@example.com"}
    assert chat.extra == {}


def test_chat_from_dict_strips_message_page_keys_from_extra() -> None:
    # When the body comes from the /messages endpoint, the page wrapper
    # fields share the same top-level dict as the chat. They must not
    # leak into Chat.extra.
    body = _chat_with_messages(SPEC_EXAMPLE_USER_MESSAGE, has_more=True, last_id="x")
    chat = Chat.from_dict(body)
    assert "chat_messages" not in chat.extra
    assert "has_more" not in chat.extra
    assert "first_id" not in chat.extra
    assert "last_id" not in chat.extra


def test_chat_from_dict_preserves_unknown_fields_in_extra() -> None:
    body = dict(SPEC_EXAMPLE_CHAT)
    body["future_field"] = "later"
    chat = Chat.from_dict(body)
    assert chat.extra == {"future_field": "later"}


def test_message_from_dict_user_message() -> None:
    message = Message.from_dict(SPEC_EXAMPLE_USER_MESSAGE)
    assert message.id == "claude_chat_msg_abc123"
    assert message.role == "user"
    assert message.content[0]["text"].startswith("Can you help me draft")
    assert message.files is not None
    assert message.files[0]["filename"] == "dashboard_mockup_v1.pdf"
    assert message.artifacts is None


def test_message_from_dict_assistant_message_with_artifacts() -> None:
    message = Message.from_dict(SPEC_EXAMPLE_ASSISTANT_MESSAGE)
    assert message.role == "assistant"
    assert message.files is None
    assert message.artifacts is not None
    assert message.artifacts[0]["title"] == "Dashboard Requirements Draft"


def test_chat_messages_page_from_dict_splits_chat_and_messages() -> None:
    body = _chat_with_messages(
        SPEC_EXAMPLE_USER_MESSAGE,
        SPEC_EXAMPLE_ASSISTANT_MESSAGE,
        has_more=True,
        first_id="first_msg",
        last_id="last_msg",
    )
    result = ChatMessagesPage.from_dict(body)
    assert isinstance(result.chat, Chat)
    assert result.chat.id == "claude_chat_abc123"
    assert isinstance(result.messages, CursorPage)
    assert len(result.messages.data) == 2
    assert result.messages.has_more is True
    assert result.messages.first_id == "first_msg"
    assert result.messages.last_id == "last_msg"


# ---------------------------------------------------------------------------
# Param builders
# ---------------------------------------------------------------------------


def test_build_list_params_includes_user_ids() -> None:
    params = _build_list_params(
        user_ids=["u1", "u2"],
        organization_ids=None,
        project_ids=None,
        created_at_gte=None,
        created_at_gt=None,
        created_at_lte=None,
        created_at_lt=None,
        updated_at_gte=None,
        updated_at_gt=None,
        updated_at_lte=None,
        updated_at_lt=None,
        after_id=None,
        before_id=None,
        limit=None,
    )
    assert params == {"user_ids[]": ["u1", "u2"]}


def test_build_list_params_full_filters() -> None:
    params = _build_list_params(
        user_ids=["u1"],
        organization_ids=["org_a"],
        project_ids=["proj_a"],
        created_at_gte="2025-01-01T00:00:00Z",
        created_at_gt=None,
        created_at_lte=None,
        created_at_lt=None,
        updated_at_gte=None,
        updated_at_gt="2025-02-01T00:00:00Z",
        updated_at_lte=None,
        updated_at_lt=None,
        after_id="cursor_abc",
        before_id=None,
        limit=50,
    )
    assert params == {
        "user_ids[]": ["u1"],
        "organization_ids[]": ["org_a"],
        "project_ids[]": ["proj_a"],
        "created_at.gte": "2025-01-01T00:00:00Z",
        "updated_at.gt": "2025-02-01T00:00:00Z",
        "after_id": "cursor_abc",
        "limit": 50,
    }


def test_build_messages_params() -> None:
    assert _build_messages_params(after_id=None, before_id=None, limit=None) == {}
    assert _build_messages_params(after_id="a", before_id=None, limit=100) == {
        "after_id": "a",
        "limit": 100,
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
# .list() and .iter()
# ---------------------------------------------------------------------------


def test_list_validates_user_ids_locally(sync_client: ComplianceClient) -> None:
    with pytest.raises(ValueError):
        sync_client.chats.list(user_ids=[])
    with pytest.raises(ValueError):
        sync_client.chats.list(user_ids=[f"u{i}" for i in range(11)])


def test_list_returns_cursor_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}?user_ids%5B%5D=u1",
        json={
            "data": [SPEC_EXAMPLE_CHAT],
            "has_more": False,
            "first_id": "claude_chat_abc123",
            "last_id": "claude_chat_abc123",
        },
    )
    page = sync_client.chats.list(user_ids=["u1"])
    assert isinstance(page, CursorPage)
    assert len(page.data) == 1
    assert isinstance(page.data[0], Chat)


def test_list_passes_filters(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=(
            f"{BASE_URL}{CHATS_PATH}"
            "?user_ids%5B%5D=u1&user_ids%5B%5D=u2"
            "&project_ids%5B%5D=proj_a"
            "&created_at.gte=2025-01-01T00:00:00Z"
            "&limit=50"
        ),
        json={"data": [], "has_more": False, "first_id": None, "last_id": None},
    )
    sync_client.chats.list(
        user_ids=["u1", "u2"],
        project_ids=["proj_a"],
        created_at_gte="2025-01-01T00:00:00Z",
        limit=50,
    )
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params.get_list("user_ids[]") == ["u1", "u2"]
    assert request.url.params.get_list("project_ids[]") == ["proj_a"]


def test_iter_walks_pages(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}?user_ids%5B%5D=u1",
        json={
            "data": [_chat("a")],
            "has_more": True,
            "first_id": "a",
            "last_id": "a",
        },
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}?user_ids%5B%5D=u1&after_id=a",
        json={
            "data": [_chat("b")],
            "has_more": False,
            "first_id": "b",
            "last_id": "b",
        },
    )
    ids = [c.id for c in sync_client.chats.iter(user_ids=["u1"])]
    assert ids == ["a", "b"]


def test_iter_validates_user_ids_locally(sync_client: ComplianceClient) -> None:
    with pytest.raises(ValueError):
        list(sync_client.chats.iter(user_ids=[]))


# ---------------------------------------------------------------------------
# .get() and .iter_messages()
# ---------------------------------------------------------------------------


def _messages_url(suffix: str = "") -> str:
    return f"{BASE_URL}{CHATS_PATH}/{CHAT_ID}/messages{suffix}"


def test_get_returns_chat_messages_page(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json=_chat_with_messages(
            SPEC_EXAMPLE_USER_MESSAGE,
            SPEC_EXAMPLE_ASSISTANT_MESSAGE,
            has_more=False,
            first_id="msg1",
            last_id="msg2",
        ),
    )
    result = sync_client.chats.get(CHAT_ID)
    assert isinstance(result, ChatMessagesPage)
    assert result.chat.id == CHAT_ID
    assert len(result.messages.data) == 2
    assert result.messages.has_more is False


def test_get_passes_cursor_params(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url("?after_id=msg_abc&limit=10"),
        json=_chat_with_messages(has_more=False),
    )
    sync_client.chats.get(CHAT_ID, after_id="msg_abc", limit=10)
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["after_id"] == "msg_abc"
    assert request.url.params["limit"] == "10"


def test_get_404_raises_not_found(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    # Verbatim from the spec's Chat Not Found example.
    httpx_mock.add_response(
        url=_messages_url(),
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Chat {id} not found."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.chats.get(CHAT_ID)


def test_iter_messages_walks_pages(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json=_chat_with_messages(
            SPEC_EXAMPLE_USER_MESSAGE,
            has_more=True,
            first_id="msg_a",
            last_id="msg_a",
        ),
    )
    httpx_mock.add_response(
        url=_messages_url("?after_id=msg_a"),
        json=_chat_with_messages(
            SPEC_EXAMPLE_ASSISTANT_MESSAGE,
            has_more=False,
            first_id="msg_b",
            last_id="msg_b",
        ),
    )
    messages = list(sync_client.chats.iter_messages(CHAT_ID))
    assert [m.id for m in messages] == [
        SPEC_EXAMPLE_USER_MESSAGE["id"],
        SPEC_EXAMPLE_ASSISTANT_MESSAGE["id"],
    ]


def test_iter_messages_empty(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json=_chat_with_messages(has_more=False),
    )
    assert list(sync_client.chats.iter_messages(CHAT_ID)) == []


# ---------------------------------------------------------------------------
# .delete()
# ---------------------------------------------------------------------------


def test_delete_returns_none(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}/{CHAT_ID}",
        method="DELETE",
        json={"id": CHAT_ID, "type": "claude_chat_deleted"},
    )
    assert sync_client.chats.delete(CHAT_ID) is None


def test_delete_404_raises_not_found(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}/{CHAT_ID}",
        method="DELETE",
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Chat not found."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.chats.delete(CHAT_ID)


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_list_validates_user_ids(
    async_client: AsyncComplianceClient,
) -> None:
    with pytest.raises(ValueError):
        await async_client.chats.list(user_ids=[])


async def test_async_list_returns_page(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}?user_ids%5B%5D=u1",
        json={
            "data": [SPEC_EXAMPLE_CHAT],
            "has_more": False,
            "first_id": "claude_chat_abc123",
            "last_id": "claude_chat_abc123",
        },
    )
    page = await async_client.chats.list(user_ids=["u1"])
    assert page.data[0].id == "claude_chat_abc123"


async def test_async_iter_walks_pages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}?user_ids%5B%5D=u1",
        json={"data": [_chat("a")], "has_more": True, "first_id": "a", "last_id": "a"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}?user_ids%5B%5D=u1&after_id=a",
        json={
            "data": [_chat("b")],
            "has_more": False,
            "first_id": "b",
            "last_id": "b",
        },
    )
    ids = [c.id async for c in async_client.chats.iter(user_ids=["u1"])]
    assert ids == ["a", "b"]


async def test_async_get_and_iter_messages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json=_chat_with_messages(
            SPEC_EXAMPLE_USER_MESSAGE,
            has_more=False,
            last_id="msg_a",
        ),
    )
    result = await async_client.chats.get(CHAT_ID)
    assert result.chat.id == CHAT_ID
    assert len(result.messages.data) == 1


async def test_async_iter_messages_walks_pages(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_messages_url(),
        json=_chat_with_messages(
            SPEC_EXAMPLE_USER_MESSAGE,
            has_more=True,
            last_id="msg_a",
        ),
    )
    httpx_mock.add_response(
        url=_messages_url("?after_id=msg_a"),
        json=_chat_with_messages(
            SPEC_EXAMPLE_ASSISTANT_MESSAGE,
            has_more=False,
            last_id="msg_b",
        ),
    )
    ids = [m.id async for m in async_client.chats.iter_messages(CHAT_ID)]
    assert ids == [
        SPEC_EXAMPLE_USER_MESSAGE["id"],
        SPEC_EXAMPLE_ASSISTANT_MESSAGE["id"],
    ]


async def test_async_delete(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{CHATS_PATH}/{CHAT_ID}",
        method="DELETE",
        json={"id": CHAT_ID, "type": "claude_chat_deleted"},
    )
    assert await async_client.chats.delete(CHAT_ID) is None


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_COMPLIANCE_API_KEY")
    or not os.environ.get("ANTHROPIC_COMPLIANCE_USER_ID"),
    reason="Requires ANTHROPIC_COMPLIANCE_API_KEY and ANTHROPIC_COMPLIANCE_USER_ID.",
)
def test_integration_list_chats() -> None:
    user_id = os.environ["ANTHROPIC_COMPLIANCE_USER_ID"]
    with ComplianceClient() as client:
        page = client.chats.list(user_ids=[user_id], limit=5)
    assert isinstance(page, CursorPage)
    for chat in page.data:
        assert chat.id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chat(id_: str) -> dict[str, Any]:
    return {**SPEC_EXAMPLE_CHAT, "id": id_}
