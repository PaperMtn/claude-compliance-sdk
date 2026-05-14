"""Tests for the Artifacts resource group (download-only)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from claude_compliance_sdk import (
    AsyncComplianceClient,
    ComplianceClient,
    FileTooLargeError,
    NotFoundError,
)
from claude_compliance_sdk.resources.artifacts import ARTIFACTS_PATH


API_KEY = "sk-ant-api01-test-key"
BASE_URL = "https://api.test.invalid"
ARTIFACT_VERSION_ID = "claude_artifact_version_xyz789"


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
    return f"{BASE_URL}{ARTIFACTS_PATH}/{ARTIFACT_VERSION_ID}/content"


# ---------------------------------------------------------------------------
# Sync methods
# ---------------------------------------------------------------------------


def test_download_returns_bytes(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"# Markdown Artifact\n\n...")
    assert sync_client.artifacts.download(ARTIFACT_VERSION_ID).startswith(b"# Markdown")


def test_download_rejects_oversize(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_content_url(),
        content=b"x",
        headers={"content-length": "99999"},
    )
    with pytest.raises(FileTooLargeError):
        sync_client.artifacts.download(ARTIFACT_VERSION_ID)


def test_download_to_file(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    # Larger than max_download_bytes — disk download is unbounded.
    httpx_mock.add_response(url=_content_url(), content=b"x" * 4096)
    dest = tmp_path / "artifact.md"
    sync_client.artifacts.download_to_file(ARTIFACT_VERSION_ID, dest)
    assert dest.stat().st_size == 4096


def test_download_stream(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"streamed")
    collected = b"".join(sync_client.artifacts.download_stream(ARTIFACT_VERSION_ID))
    assert collected == b"streamed"


def test_download_404_raises_not_found(
    sync_client: ComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=_content_url(),
        status_code=404,
        json={"error": {"type": "not_found_error", "message": "Missing."}},
    )
    with pytest.raises(NotFoundError):
        sync_client.artifacts.download(ARTIFACT_VERSION_ID)


def test_no_get_or_delete_methods() -> None:
    # Spec explicitly excludes metadata and delete endpoints for
    # artifacts; verify the resource only exposes the download trio.
    client = ComplianceClient(api_key=API_KEY)
    public = [n for n in dir(client.artifacts) if not n.startswith("_")]
    assert set(public) == {"download", "download_to_file", "download_stream"}


# ---------------------------------------------------------------------------
# Async parity
# ---------------------------------------------------------------------------


async def test_async_download(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"async artifact")
    assert (
        await async_client.artifacts.download(ARTIFACT_VERSION_ID) == b"async artifact"
    )


async def test_async_download_to_file(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock, tmp_path: Path
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"async-bytes")
    dest = tmp_path / "art.md"
    await async_client.artifacts.download_to_file(ARTIFACT_VERSION_ID, dest)
    assert dest.read_bytes() == b"async-bytes"


async def test_async_download_stream(
    async_client: AsyncComplianceClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url=_content_url(), content=b"chunked-artifact")
    collected = b"".join(
        [
            chunk
            async for chunk in async_client.artifacts.download_stream(ARTIFACT_VERSION_ID)
        ]
    )
    assert collected == b"chunked-artifact"
