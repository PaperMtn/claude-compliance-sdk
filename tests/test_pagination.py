"""Tests for the cursor and offset page primitives and their iterators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk._internal.pagination import (
    AsyncCursorPage,
    AsyncOffsetPage,
    CursorPage,
    OffsetPage,
    iter_all_cursor_async,
    iter_all_cursor_sync,
    iter_all_offset_async,
    iter_all_offset_sync,
)
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
PATH = "/v1/compliance/activities"


@dataclass
class FakeActivity:
    """Stand-in for the real Activity dataclass landing in Phase 3.1."""

    id: str
    actor: str | None = None

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "FakeActivity":
        return cls(id=body["id"], actor=body.get("actor"))


@pytest.fixture
def sync_transport() -> SyncTransport:
    transport = SyncTransport(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=30.0,
        anthropic_version="2023-06-01",
        max_retries=0,
        rate_limit_rpm=0,
    )
    yield transport
    transport.close()


@pytest.fixture
async def async_transport() -> AsyncTransport:
    transport = AsyncTransport(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=30.0,
        anthropic_version="2023-06-01",
        max_retries=0,
        rate_limit_rpm=0,
    )
    yield transport
    await transport.aclose()


# ---------------------------------------------------------------------------
# Page.from_dict
# ---------------------------------------------------------------------------


def test_cursor_page_from_dict_full_body() -> None:
    body = {
        "data": [{"id": "a"}, {"id": "b"}],
        "first_id": "a",
        "last_id": "b",
        "has_more": True,
    }
    page = CursorPage.from_dict(body, FakeActivity.from_dict)
    assert page.data == [FakeActivity(id="a"), FakeActivity(id="b")]
    assert page.first_id == "a"
    assert page.last_id == "b"
    assert page.has_more is True


def test_cursor_page_from_dict_empty_defaults() -> None:
    page = CursorPage.from_dict({}, FakeActivity.from_dict)
    assert page.data == []
    assert page.first_id is None
    assert page.last_id is None
    assert page.has_more is False


def test_cursor_page_from_dict_null_data_treated_as_empty() -> None:
    page = CursorPage.from_dict(
        {"data": None, "first_id": None, "last_id": None, "has_more": False},
        FakeActivity.from_dict,
    )
    assert page.data == []


def test_offset_page_from_dict_full_body() -> None:
    body = {"data": [{"id": "x"}], "next_page": "tok_abc"}
    page = OffsetPage.from_dict(body, FakeActivity.from_dict)
    assert page.data == [FakeActivity(id="x")]
    assert page.next_page == "tok_abc"


def test_offset_page_from_dict_no_next_page() -> None:
    page = OffsetPage.from_dict({"data": [], "next_page": None}, FakeActivity.from_dict)
    assert page.data == []
    assert page.next_page is None


def test_async_page_aliases_match_sync_classes() -> None:
    # Aliases — same dataclass, different name. Keeps async resources
    # readable without a dataclass duplication.
    assert AsyncCursorPage is CursorPage
    assert AsyncOffsetPage is OffsetPage


# ---------------------------------------------------------------------------
# Cursor iteration — sync
# ---------------------------------------------------------------------------


def test_cursor_sync_single_page(sync_transport: SyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={
            "data": [{"id": "a"}, {"id": "b"}],
            "first_id": "a",
            "last_id": "b",
            "has_more": False,
        },
    )
    items = list(iter_all_cursor_sync(sync_transport, PATH, FakeActivity.from_dict))
    assert items == [FakeActivity(id="a"), FakeActivity(id="b")]


def test_cursor_sync_multi_page_chains_after_id(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={"data": [{"id": "a"}], "first_id": "a", "last_id": "a", "has_more": True},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?after_id=a",
        json={"data": [{"id": "b"}], "first_id": "b", "last_id": "b", "has_more": True},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?after_id=b",
        json={"data": [{"id": "c"}], "first_id": "c", "last_id": "c", "has_more": False},
    )

    items = list(iter_all_cursor_sync(sync_transport, PATH, FakeActivity.from_dict))
    assert [item.id for item in items] == ["a", "b", "c"]


def test_cursor_sync_empty_page_terminates(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={"data": [], "first_id": None, "last_id": None, "has_more": False},
    )
    assert list(iter_all_cursor_sync(sync_transport, PATH, FakeActivity.from_dict)) == []


def test_cursor_sync_has_more_with_null_last_id_terminates(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    # Defensive: if server returns has_more=True but no last_id, we
    # cannot advance and must stop rather than loop forever.
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={
            "data": [{"id": "a"}],
            "first_id": "a",
            "last_id": None,
            "has_more": True,
        },
    )
    items = list(iter_all_cursor_sync(sync_transport, PATH, FakeActivity.from_dict))
    assert [item.id for item in items] == ["a"]


def test_cursor_sync_preserves_initial_params(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?limit=2&activity_type=login",
        json={"data": [{"id": "a"}], "first_id": "a", "last_id": "a", "has_more": True},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?limit=2&activity_type=login&after_id=a",
        json={"data": [{"id": "b"}], "first_id": "b", "last_id": "b", "has_more": False},
    )
    items = list(
        iter_all_cursor_sync(
            sync_transport,
            PATH,
            FakeActivity.from_dict,
            params={"limit": 2, "activity_type": "login"},
        )
    )
    assert [item.id for item in items] == ["a", "b"]


def test_cursor_sync_does_not_mutate_caller_params(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?limit=2",
        json={"data": [{"id": "a"}], "first_id": "a", "last_id": "a", "has_more": True},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?limit=2&after_id=a",
        json={"data": [{"id": "b"}], "first_id": "b", "last_id": "b", "has_more": False},
    )
    caller_params: dict[str, Any] = {"limit": 2}
    list(iter_all_cursor_sync(sync_transport, PATH, FakeActivity.from_dict, params=caller_params))
    assert caller_params == {"limit": 2}


# ---------------------------------------------------------------------------
# Offset iteration — sync
# ---------------------------------------------------------------------------


def test_offset_sync_single_page(sync_transport: SyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={"data": [{"id": "a"}, {"id": "b"}], "next_page": None},
    )
    items = list(iter_all_offset_sync(sync_transport, PATH, FakeActivity.from_dict))
    assert [item.id for item in items] == ["a", "b"]


def test_offset_sync_multi_page_chains_page_token(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={"data": [{"id": "a"}], "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?page=tok_1",
        json={"data": [{"id": "b"}], "next_page": "tok_2"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?page=tok_2",
        json={"data": [{"id": "c"}], "next_page": None},
    )
    items = list(iter_all_offset_sync(sync_transport, PATH, FakeActivity.from_dict))
    assert [item.id for item in items] == ["a", "b", "c"]


def test_offset_sync_empty_page_terminates(
    sync_transport: SyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={"data": [], "next_page": None},
    )
    assert list(iter_all_offset_sync(sync_transport, PATH, FakeActivity.from_dict)) == []


# ---------------------------------------------------------------------------
# Cursor + offset iteration — async parity
# ---------------------------------------------------------------------------


async def test_cursor_async_multi_page(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={"data": [{"id": "a"}], "first_id": "a", "last_id": "a", "has_more": True},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?after_id=a",
        json={"data": [{"id": "b"}], "first_id": "b", "last_id": "b", "has_more": False},
    )
    items = [
        item async for item in iter_all_cursor_async(async_transport, PATH, FakeActivity.from_dict)
    ]
    assert [item.id for item in items] == ["a", "b"]


async def test_offset_async_multi_page(
    async_transport: AsyncTransport, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={"data": [{"id": "a"}], "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}?page=tok_1",
        json={"data": [{"id": "b"}], "next_page": None},
    )
    items = [
        item async for item in iter_all_offset_async(async_transport, PATH, FakeActivity.from_dict)
    ]
    assert [item.id for item in items] == ["a", "b"]


async def test_cursor_async_empty(async_transport: AsyncTransport, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PATH}",
        json={"data": [], "first_id": None, "last_id": None, "has_more": False},
    )
    items = [
        item async for item in iter_all_cursor_async(async_transport, PATH, FakeActivity.from_dict)
    ]
    assert items == []
