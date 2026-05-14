"""Tests for the GeneratedFiles resource group (assistant tool outputs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import (
    AsyncComplianceClient,
    ComplianceClient,
    FileTooLargeError,
    NotFoundError,
)
from claude_compliance_sdk.resources.generated_files import (
    GENERATED_FILES_PATH,
    GeneratedFile,
)


API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
GEN_FILE_ID = "claude_gen_file_abc123"


SPEC_EXAMPLE_GENERATED_FILE: dict[str, Any] = {
    "id": "claude_gen_file_abc123",
    "filename": "data_analysis.xlsx",
    "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "size_bytes": 524288,
    "created_at": "2024-01-15T10:30:00Z",
    "claude_chat_id": "claude_chat_xyz789",
}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


def test_generated_file_from_dict() -> None:
    f = GeneratedFile.from_dict(SPEC_EXAMPLE_GENERATED_FILE)
    assert f.id == "claude_gen_file_abc123"
    assert f.filename == "data_analysis.xlsx"
    assert f.claude_chat_id == "claude_chat_xyz789"
    assert f.size_bytes == 524288


def test_generated_file_from_dict_nullable_fields() -> None:
    body = dict(SPEC_EXAMPLE_GENERATED_FILE)
    body["mime_type"] = None
    body["size_bytes"] = None
    body["created_at"] = None
    f = GeneratedFile.from_dict(body)
    assert f.mime_type is None
    assert f.size_bytes is None
    assert f.created_at is None


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
        max_download_bytes=1024,
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
        max_download_bytes=1024,
    )
    yield client
    await client.aclose()


def _content_url() -> str:
    return f"{BASE_URL}{GENERATED_FILES_PATH}/{GEN_FILE_ID}/content"


# ---------------------------------------------------------------------------
# Methods
# ---------------------------------------------------------------------------


def test_get_returns_metadata(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GENERATED_FILES_PATH}/{GEN_FILE_ID}",
        json=SPEC_EXAMPLE_GENERATED_FILE,
    )
    f = sync_client.generated_files.get(GEN_FILE_ID)
    assert f.id == GEN_FILE_ID
    assert f.claude_chat_id == "claude_chat_xyz789"


def test_get_404_raises_not_found(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GENERATED_FILES_PATH}/{GEN_FILE_ID}",
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Missing."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.generated_files.get(GEN_FILE_ID)


def test_download_returns_bytes(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"spreadsheet bytes")
    assert sync_client.generated_files.download(GEN_FILE_ID) == b"spreadsheet bytes"


def test_download_rejects_oversize(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_content_url(),
        content=b"x",
        headers={"content-length": "9999"},
    )
    with pytest.raises(FileTooLargeError):
        sync_client.generated_files.download(GEN_FILE_ID)


def test_download_to_file(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"x" * 5000)
    dest = tmp_path / "gen.xlsx"
    sync_client.generated_files.download_to_file(GEN_FILE_ID, dest)
    assert dest.stat().st_size == 5000


def test_download_stream(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"chunked")
    collected = b"".join(sync_client.generated_files.download_stream(GEN_FILE_ID))
    assert collected == b"chunked"


def test_no_delete_method() -> None:
    # Spec explicitly excludes DELETE for generated files; make sure the
    # resource doesn't accidentally expose one.
    sync_client_attrs = dir(ComplianceClient(api_key=API_KEY).generated_files)
    assert "delete" not in sync_client_attrs


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_get(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{GENERATED_FILES_PATH}/{GEN_FILE_ID}",
        json=SPEC_EXAMPLE_GENERATED_FILE,
    )
    f = await async_client.generated_files.get(GEN_FILE_ID)
    assert f.filename == "data_analysis.xlsx"


async def test_async_download(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"async bytes")
    assert await async_client.generated_files.download(GEN_FILE_ID) == b"async bytes"


async def test_async_download_stream(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"async chunks")
    collected = b"".join(
        [chunk async for chunk in async_client.generated_files.download_stream(GEN_FILE_ID)]
    )
    assert collected == b"async chunks"


async def test_async_download_to_file(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    payload = b"async bytes to disk"
    httpx_mock.add_response(url=_content_url(), content=payload)
    dest = tmp_path / "out.xlsx"
    await async_client.generated_files.download_to_file(GEN_FILE_ID, dest)
    assert dest.read_bytes() == payload
