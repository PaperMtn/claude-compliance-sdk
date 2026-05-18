"""Tests for the ProjectDocuments resource group."""

from __future__ import annotations

import os
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import AsyncComplianceClient, ComplianceClient, NotFoundError
from claude_compliance_sdk.resources.project_documents import (
    PROJECT_DOCUMENTS_PATH,
    ProjectDocument,
)

API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
DOCUMENT_ID = "claude_proj_doc_abcd"


SPEC_EXAMPLE_DOCUMENT: dict[str, Any] = {
    "id": "claude_proj_doc_abcd",
    "filename": "instructions.txt",
    "content": "Always cite KPIs in summaries.",
    "created_at": "2025-06-03T11:00:00Z",
    "user": {"id": "user_xyz456", "email_address": "user@example.com"},
}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


def test_project_document_from_dict() -> None:
    doc = ProjectDocument.from_dict(SPEC_EXAMPLE_DOCUMENT)
    assert doc.id == "claude_proj_doc_abcd"
    assert doc.filename == "instructions.txt"
    assert doc.content == "Always cite KPIs in summaries."
    assert doc.created_at == "2025-06-03T11:00:00Z"
    assert doc.user == {"id": "user_xyz456", "email_address": "user@example.com"}
    assert doc.extra == {}


def test_project_document_null_user() -> None:
    body = dict(SPEC_EXAMPLE_DOCUMENT)
    body["user"] = None
    doc = ProjectDocument.from_dict(body)
    assert doc.user is None


def test_project_document_unknown_fields_in_extra() -> None:
    body = dict(SPEC_EXAMPLE_DOCUMENT)
    body["future_field"] = "later"
    doc = ProjectDocument.from_dict(body)
    assert doc.extra == {"future_field": "later"}


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
# Sync .get() / .delete()
# ---------------------------------------------------------------------------


def test_get_returns_project_document(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECT_DOCUMENTS_PATH}/{DOCUMENT_ID}",
        json=SPEC_EXAMPLE_DOCUMENT,
    )
    doc = sync_client.project_documents.get(DOCUMENT_ID)
    assert isinstance(doc, ProjectDocument)
    assert doc.content == "Always cite KPIs in summaries."


def test_get_404_raises_not_found(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    # Verbatim from the spec's Not Found (404) example.
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECT_DOCUMENTS_PATH}/{DOCUMENT_ID}",
        status_code=404,
        json={
            "error": {
                "type": "not_found_error",
                "message": (
                    "No project document found with provided id, or it has " "already been deleted."
                ),
            }
        },
    )
    with pytest.raises(NotFoundError):
        sync_client.project_documents.get(DOCUMENT_ID)


def test_delete_returns_none_on_success(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECT_DOCUMENTS_PATH}/{DOCUMENT_ID}",
        method="DELETE",
        json={"id": DOCUMENT_ID, "type": "claude_project_document_deleted"},
    )
    assert sync_client.project_documents.delete(DOCUMENT_ID) is None


def test_delete_404_raises_not_found(sync_client: ComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECT_DOCUMENTS_PATH}/{DOCUMENT_ID}",
        method="DELETE",
        status_code=404,
        json={
            "error": {
                "type": "not_found_error",
                "message": "No project document found with provided id.",
            }
        },
    )
    with pytest.raises(NotFoundError):
        sync_client.project_documents.delete(DOCUMENT_ID)


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_get(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECT_DOCUMENTS_PATH}/{DOCUMENT_ID}",
        json=SPEC_EXAMPLE_DOCUMENT,
    )
    doc = await async_client.project_documents.get(DOCUMENT_ID)
    assert doc.id == DOCUMENT_ID


async def test_async_delete(async_client: AsyncComplianceClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{PROJECT_DOCUMENTS_PATH}/{DOCUMENT_ID}",
        method="DELETE",
        json={"id": DOCUMENT_ID, "type": "claude_project_document_deleted"},
    )
    assert await async_client.project_documents.delete(DOCUMENT_ID) is None
