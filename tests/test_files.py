"""Tests for the Files resource group (user-uploaded files)."""

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
from claude_compliance_sdk.resources.files import FILES_PATH, File


API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
FILE_ID = "claude_file_xyz789"


SPEC_EXAMPLE_FILE: dict[str, Any] = {
    "id": "claude_file_xyz789",
    "filename": "quarterly_report.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 1048576,
    "created_at": "2024-01-15T10:30:00Z",
    "message_ids": ["claude_chat_msg_abc123"],
}


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


def test_file_from_dict() -> None:
    file_ = File.from_dict(SPEC_EXAMPLE_FILE)
    assert file_.id == "claude_file_xyz789"
    assert file_.filename == "quarterly_report.pdf"
    assert file_.mime_type == "application/pdf"
    assert file_.size_bytes == 1048576
    assert file_.message_ids == ["claude_chat_msg_abc123"]


def test_file_from_dict_null_filename() -> None:
    body = dict(SPEC_EXAMPLE_FILE)
    body["filename"] = None
    body["mime_type"] = None
    body["size_bytes"] = None
    file_ = File.from_dict(body)
    assert file_.filename is None
    assert file_.mime_type is None
    assert file_.size_bytes is None


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


# ---------------------------------------------------------------------------
# .get()
# ---------------------------------------------------------------------------


def test_get_returns_file_metadata(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{FILES_PATH}/{FILE_ID}",
        json=SPEC_EXAMPLE_FILE,
    )
    file_ = sync_client.files.get(FILE_ID)
    assert isinstance(file_, File)
    assert file_.id == FILE_ID


def test_get_404_raises_not_found(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{FILES_PATH}/{FILE_ID}",
        status_code=404,
        json={
            "error": {
                "type": "not_found_error",
                "message": (
                    "No file found with provided id, or it has already been deleted."
                ),
            }
        },
    )
    with pytest.raises(NotFoundError):
        sync_client.files.get(FILE_ID)


# ---------------------------------------------------------------------------
# .download() — eager, bounded
# ---------------------------------------------------------------------------


def _content_url() -> str:
    return f"{BASE_URL}{FILES_PATH}/{FILE_ID}/content"


def test_download_returns_bytes_within_limit(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    payload = b"hello world"
    httpx_mock.add_response(
        url=_content_url(),
        content=payload,
        headers={"content-length": str(len(payload))},
    )
    assert sync_client.files.download(FILE_ID) == payload


def test_download_rejects_oversize_via_content_length(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_content_url(),
        content=b"x" * 100,  # body itself is small
        headers={"content-length": "9999999"},  # header lies, exceeds 1024 limit
    )
    with pytest.raises(FileTooLargeError) as exc_info:
        sync_client.files.download(FILE_ID)
    assert exc_info.value.size_bytes == 9999999
    assert exc_info.value.max_bytes == 1024


def test_download_to_file_writes_bytes(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    payload = b"streaming bytes"
    httpx_mock.add_response(url=_content_url(), content=payload)
    dest = tmp_path / "out.bin"
    sync_client.files.download_to_file(FILE_ID, dest)
    assert dest.read_bytes() == payload


def test_download_to_file_unbounded(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    # Larger than max_download_bytes; download_to_file is unbounded.
    payload = b"x" * 2048
    httpx_mock.add_response(url=_content_url(), content=payload)
    dest = tmp_path / "big.bin"
    sync_client.files.download_to_file(FILE_ID, dest)
    assert dest.stat().st_size == 2048


def test_download_stream_yields_chunks(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    payload = b"abcdef"
    httpx_mock.add_response(url=_content_url(), content=payload)
    collected = b"".join(sync_client.files.download_stream(FILE_ID))
    assert collected == payload


def test_download_404_raises_not_found(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_content_url(),
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Missing."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.files.download(FILE_ID)


# ---------------------------------------------------------------------------
# .delete()
# ---------------------------------------------------------------------------


def test_delete_returns_none(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{FILES_PATH}/{FILE_ID}",
        method="DELETE",
        json={"id": FILE_ID, "type": "claude_file_deleted"},
    )
    assert sync_client.files.delete(FILE_ID) is None


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_get(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{FILES_PATH}/{FILE_ID}", json=SPEC_EXAMPLE_FILE
    )
    file_ = await async_client.files.get(FILE_ID)
    assert file_.id == FILE_ID


async def test_async_download_within_limit(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"small")
    assert await async_client.files.download(FILE_ID) == b"small"


async def test_async_download_oversize_via_content_length(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_content_url(),
        content=b"x",
        headers={"content-length": "5000"},
    )
    with pytest.raises(FileTooLargeError):
        await async_client.files.download(FILE_ID)


async def test_async_download_to_file(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    payload = b"async bytes"
    httpx_mock.add_response(url=_content_url(), content=payload)
    dest = tmp_path / "out.bin"
    await async_client.files.download_to_file(FILE_ID, dest)
    assert dest.read_bytes() == payload


async def test_async_download_stream(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    payload = b"async chunks"
    httpx_mock.add_response(url=_content_url(), content=payload)
    collected = b"".join(
        [chunk async for chunk in async_client.files.download_stream(FILE_ID)]
    )
    assert collected == payload


async def test_async_delete(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}{FILES_PATH}/{FILE_ID}",
        method="DELETE",
        json={"id": FILE_ID, "type": "claude_file_deleted"},
    )
    assert await async_client.files.delete(FILE_ID) is None
