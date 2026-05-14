"""Tests for the shared download helpers in ``_internal/downloads.py``.

The resource-level tests exercise the happy paths via real
:class:`SyncTransport` / :class:`AsyncTransport`. This file covers
the bounded-read fallback for responses that omit ``Content-Length``,
which is awkward to reach through ``pytest-httpx`` (it auto-sets the
header whenever a body is supplied).
"""

from __future__ import annotations

from typing import Iterator

import httpx
import pytest

from claude_compliance_sdk import FileTooLargeError
from claude_compliance_sdk._internal.downloads import (
    _enforce_content_length,
    _read_bounded_async,
    _read_bounded_sync,
)


class _FakeSyncStreamResponse:
    """Drop-in stub for httpx.Response covering only what _read_bounded_sync uses."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def iter_bytes(self) -> Iterator[bytes]:
        yield from self._chunks


def test_read_bounded_sync_returns_bytes_under_limit() -> None:
    response = _FakeSyncStreamResponse([b"abc", b"def"])
    assert _read_bounded_sync(response, max_download_bytes=100) == b"abcdef"  # type: ignore[arg-type]


def test_read_bounded_sync_raises_mid_stream_above_limit() -> None:
    response = _FakeSyncStreamResponse([b"a" * 600, b"b" * 600])  # 1200 > 1000
    with pytest.raises(FileTooLargeError) as exc_info:
        _read_bounded_sync(response, max_download_bytes=1000)  # type: ignore[arg-type]
    assert exc_info.value.size_bytes is None
    assert exc_info.value.max_bytes == 1000
    assert "mid-stream" in str(exc_info.value)


class _FakeAsyncStreamResponse:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


async def test_read_bounded_async_returns_bytes_under_limit() -> None:
    response = _FakeAsyncStreamResponse([b"hi", b"there"])
    result = await _read_bounded_async(response, max_download_bytes=100)  # type: ignore[arg-type]
    assert result == b"hithere"


async def test_read_bounded_async_raises_mid_stream_above_limit() -> None:
    response = _FakeAsyncStreamResponse([b"x" * 600, b"y" * 600])
    with pytest.raises(FileTooLargeError) as exc_info:
        await _read_bounded_async(response, max_download_bytes=1000)  # type: ignore[arg-type]
    assert exc_info.value.size_bytes is None
    assert exc_info.value.max_bytes == 1000


# ---------------------------------------------------------------------------
# _enforce_content_length defensive paths
# ---------------------------------------------------------------------------


class _FakeHeadersResponse:
    """Minimal stand-in exposing only ``.headers`` for header-lookup tests."""

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


def test_enforce_content_length_noop_when_header_missing() -> None:
    response = _FakeHeadersResponse({})
    # Should not raise.
    _enforce_content_length(response, max_download_bytes=10)  # type: ignore[arg-type]


def test_enforce_content_length_noop_when_header_unparseable() -> None:
    response = _FakeHeadersResponse({"content-length": "not-an-integer"})
    _enforce_content_length(response, max_download_bytes=10)  # type: ignore[arg-type]


def test_enforce_content_length_raises_when_header_exceeds_limit() -> None:
    response = _FakeHeadersResponse({"content-length": "5000"})
    with pytest.raises(FileTooLargeError) as exc_info:
        _enforce_content_length(response, max_download_bytes=1000)  # type: ignore[arg-type]
    assert exc_info.value.size_bytes == 5000
