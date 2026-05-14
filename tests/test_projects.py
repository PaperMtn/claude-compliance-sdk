"""Tests for the Projects resource group.

Covers Project / ProjectDetail / ProjectAttachment dataclasses, the
offset-paginated .list() + .iter(), single-fetch .get(), .delete()
with the 409→ConflictError path, and the attachments listing pair.
Sync+async parity throughout.

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
    ConflictError,
    NotFoundError,
    OffsetPage,
)
from claude_compliance_sdk.resources.projects import (
    PROJECTS_PATH,
    Project,
    ProjectAttachment,
    ProjectDetail,
    _build_attachments_params,
    _build_list_params,
)

API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
PROJECT_ID = "claude_proj_abc123"


# Spec example from the Compliance API List projects response.
SPEC_EXAMPLE_PROJECT: dict[str, Any] = {
    "id": "claude_proj_abc123",
    "name": "Q4 Product Planning",
    "created_at": "2025-06-01T10:00:00Z",
    "updated_at": "2025-06-15T14:30:00Z",
    "is_private": True,
    "organization_id": "org_abc123",
    "user": {"id": "user_xyz456", "email_address": "user@example.com"},
}

SPEC_EXAMPLE_PROJECT_DETAIL: dict[str, Any] = {
    **SPEC_EXAMPLE_PROJECT,
    "description": "Planning doc for Q4 launches.",
    "instructions": "Always cite KPIs.",
    "chats_count": 12,
    "attachments_count": 4,
}

SPEC_EXAMPLE_FILE_ATTACHMENT: dict[str, Any] = {
    "type": "project_file",
    "id": "claude_file_abcd",
    "created_at": "2025-06-02T09:00:00Z",
    "filename": "design.pdf",
    "mime_type": "application/pdf",
}

SPEC_EXAMPLE_DOC_ATTACHMENT: dict[str, Any] = {
    "type": "project_doc",
    "id": "claude_proj_doc_abcd",
    "created_at": "2025-06-03T11:00:00Z",
    "filename": "instructions.txt",
    "mime_type": "text/plain",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


def test_project_from_dict() -> None:
    project = Project.from_dict(SPEC_EXAMPLE_PROJECT)
    assert project.id == "claude_proj_abc123"
    assert project.name == "Q4 Product Planning"
    assert project.is_private is True
    assert project.organization_id == "org_abc123"
    assert project.user == {"id": "user_xyz456", "email_address": "user@example.com"}
    assert project.extra == {}


def test_project_from_dict_null_user() -> None:
    body = dict(SPEC_EXAMPLE_PROJECT)
    body["user"] = None
    project = Project.from_dict(body)
    assert project.user is None


def test_project_detail_inherits_project_fields() -> None:
    detail = ProjectDetail.from_dict(SPEC_EXAMPLE_PROJECT_DETAIL)
    assert detail.id == "claude_proj_abc123"
    assert detail.organization_id == "org_abc123"
    assert detail.description == "Planning doc for Q4 launches."
    assert detail.instructions == "Always cite KPIs."
    assert detail.chats_count == 12
    assert detail.attachments_count == 4


def test_project_detail_defaults_for_missing_extension_fields() -> None:
    # The list endpoint doesn't return description/instructions/counts;
    # if a caller mistakenly parses a list-shape payload as a Detail,
    # the dataclass defaults keep it from blowing up.
    detail = ProjectDetail.from_dict(SPEC_EXAMPLE_PROJECT)
    assert detail.description == ""
    assert detail.instructions == ""
    assert detail.chats_count == 0
    assert detail.attachments_count == 0


def test_project_attachment_from_dict_file() -> None:
    att = ProjectAttachment.from_dict(SPEC_EXAMPLE_FILE_ATTACHMENT)
    assert att.type == "project_file"
    assert att.id == "claude_file_abcd"
    assert att.mime_type == "application/pdf"


def test_project_attachment_from_dict_doc() -> None:
    att = ProjectAttachment.from_dict(SPEC_EXAMPLE_DOC_ATTACHMENT)
    assert att.type == "project_doc"
    assert att.id == "claude_proj_doc_abcd"
    assert att.mime_type == "text/plain"


# ---------------------------------------------------------------------------
# _build_list_params
# ---------------------------------------------------------------------------


def test_build_list_params_empty_when_all_none() -> None:
    assert (
        _build_list_params(
            organization_ids=None,
            user_ids=None,
            created_at_gte=None,
            created_at_gt=None,
            created_at_lte=None,
            created_at_lt=None,
            page=None,
            limit=None,
        )
        == {}
    )


def test_build_list_params_serialises_arrays_and_dotted_times() -> None:
    params = _build_list_params(
        organization_ids=["org_a", "org_b"],
        user_ids=["user_a"],
        created_at_gte="2025-01-01T00:00:00Z",
        created_at_gt=None,
        created_at_lte=None,
        created_at_lt="2025-12-31T00:00:00Z",
        page="tok_abc",
        limit=10,
    )
    assert params == {
        "organization_ids[]": ["org_a", "org_b"],
        "user_ids[]": ["user_a"],
        "created_at.gte": "2025-01-01T00:00:00Z",
        "created_at.lt": "2025-12-31T00:00:00Z",
        "page": "tok_abc",
        "limit": 10,
    }


def test_build_list_params_drops_empty_arrays() -> None:
    params = _build_list_params(
        organization_ids=[],
        user_ids=None,
        created_at_gte=None,
        created_at_gt=None,
        created_at_lte=None,
        created_at_lt=None,
        page=None,
        limit=None,
    )
    assert params == {}


def test_build_attachments_params() -> None:
    assert _build_attachments_params(limit=None, page=None) == {}
    assert _build_attachments_params(limit=25, page="tok") == {"limit": 25, "page": "tok"}


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
# .list() / .iter()
# ---------------------------------------------------------------------------


def test_list_returns_offset_page(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}",
        json={"data": [SPEC_EXAMPLE_PROJECT], "has_more": False, "next_page": None},
    )
    page = sync_client.projects.list()
    assert isinstance(page, OffsetPage)
    assert len(page.data) == 1
    assert isinstance(page.data[0], Project)


def test_list_sends_filters(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=(
            f"{BASE_URL}{PROJECTS_PATH}"
            "?organization_ids%5B%5D=org_a"
            "&user_ids%5B%5D=user_x"
            "&created_at.gte=2025-01-01T00:00:00Z"
            "&limit=50"
        ),
        json={"data": [], "has_more": False, "next_page": None},
    )
    sync_client.projects.list(
        organization_ids=["org_a"],
        user_ids=["user_x"],
        created_at_gte="2025-01-01T00:00:00Z",
        limit=50,
    )
    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params.get_list("organization_ids[]") == ["org_a"]
    assert request.url.params.get_list("user_ids[]") == ["user_x"]


def test_iter_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}",
        json={"data": [_project("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}?page=tok_1",
        json={"data": [_project("b")], "has_more": False, "next_page": None},
    )
    ids = [p.id for p in sync_client.projects.iter()]
    assert ids == ["a", "b"]


# ---------------------------------------------------------------------------
# .get()
# ---------------------------------------------------------------------------


def test_get_returns_project_detail(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}/{PROJECT_ID}",
        json=SPEC_EXAMPLE_PROJECT_DETAIL,
    )
    detail = sync_client.projects.get(PROJECT_ID)
    assert isinstance(detail, ProjectDetail)
    assert detail.chats_count == 12


def test_get_404_raises_not_found(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}/{PROJECT_ID}",
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "No project is found."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.projects.get(PROJECT_ID)


# ---------------------------------------------------------------------------
# .delete()
# ---------------------------------------------------------------------------


def test_delete_returns_none_on_success(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}/{PROJECT_ID}",
        method="DELETE",
        json={"id": PROJECT_ID, "type": "claude_project_deleted"},
    )
    assert sync_client.projects.delete(PROJECT_ID) is None


def test_delete_attached_chats_raises_conflict_error(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    # Verbatim from the spec's Conflict (409) example.
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}/{PROJECT_ID}",
        method="DELETE",
        status_code=409,
        json={
            "error": {
                "type": "conflict_error",
                "message": (
                    'The "claude_proj_01KGp4eZNug9ri4kE35RSppq" project cannot '
                    "be deleted as it has chats attached to it. Delete or "
                    "detach them first."
                ),
            }
        },
    )
    with pytest.raises(ConflictError) as exc_info:
        sync_client.projects.delete(PROJECT_ID)
    assert "chats attached" in (exc_info.value.error_message or "")


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


def _attachments_url(suffix: str = "") -> str:
    return f"{BASE_URL}{PROJECTS_PATH}/{PROJECT_ID}/attachments{suffix}"


def test_list_attachments_returns_mixed_types(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_attachments_url(),
        json={
            "data": [SPEC_EXAMPLE_FILE_ATTACHMENT, SPEC_EXAMPLE_DOC_ATTACHMENT],
            "has_more": False,
            "next_page": None,
        },
    )
    page = sync_client.projects.list_attachments(PROJECT_ID)
    assert [att.type for att in page.data] == ["project_file", "project_doc"]


def test_iter_attachments_walks_pages(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=_attachments_url(),
        json={
            "data": [SPEC_EXAMPLE_FILE_ATTACHMENT],
            "has_more": True,
            "next_page": "tok_1",
        },
    )
    httpx_mock.add_response(
        url=_attachments_url("?page=tok_1"),
        json={
            "data": [SPEC_EXAMPLE_DOC_ATTACHMENT],
            "has_more": False,
            "next_page": None,
        },
    )
    attachments = list(sync_client.projects.iter_attachments(PROJECT_ID))
    assert [att.type for att in attachments] == ["project_file", "project_doc"]


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_list_and_iter(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}",
        json={"data": [_project("a")], "has_more": True, "next_page": "tok_1"},
    )
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}?page=tok_1",
        json={"data": [_project("b")], "has_more": False, "next_page": None},
    )
    ids = [p.id async for p in async_client.projects.iter()]
    assert ids == ["a", "b"]


async def test_async_get(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}/{PROJECT_ID}",
        json=SPEC_EXAMPLE_PROJECT_DETAIL,
    )
    detail = await async_client.projects.get(PROJECT_ID)
    assert detail.chats_count == 12


async def test_async_delete_conflict(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECTS_PATH}/{PROJECT_ID}",
        method="DELETE",
        status_code=409,
        json={
            "error": {
                "type": "conflict_error",
                "message": "Project has attached chats.",
            }
        },
    )
    with pytest.raises(ConflictError):
        await async_client.projects.delete(PROJECT_ID)


async def test_async_iter_attachments(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_attachments_url(),
        json={
            "data": [SPEC_EXAMPLE_FILE_ATTACHMENT, SPEC_EXAMPLE_DOC_ATTACHMENT],
            "has_more": False,
            "next_page": None,
        },
    )
    types = [a.type async for a in async_client.projects.iter_attachments(PROJECT_ID)]
    assert types == ["project_file", "project_doc"]


# ---------------------------------------------------------------------------
# Integration — live API, skipped unless key set
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_COMPLIANCE_API_KEY"),
    reason="Requires ANTHROPIC_COMPLIANCE_API_KEY for live API access.",
)
def test_integration_list_projects() -> None:
    with ComplianceClient() as client:
        page = client.projects.list(limit=5)
    assert isinstance(page, OffsetPage)
    for project in page.data:
        assert project.id
        assert project.organization_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project(id_: str) -> dict[str, Any]:
    return {
        **SPEC_EXAMPLE_PROJECT,
        "id": id_,
    }
