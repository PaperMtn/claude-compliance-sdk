"""Download helpers shared by Files, GeneratedFiles, and Artifacts.

The three Files-trio resource groups have identical download
ergonomics — eager bytes, stream-to-disk, caller-managed streaming —
so this module centralises the patterns rather than letting each
resource reimplement them.

Three pairs of helpers are exposed (one sync, one async each):

* ``download_eager_*`` — read the response in full into memory,
  bounded by ``max_download_bytes``. Raises
  :class:`~claude_compliance_sdk.FileTooLargeError` if the body's
  ``Content-Length`` (or the streamed byte total when the header is
  absent) exceeds the cap.
* ``download_to_file_*`` — stream the response to a local path.
  Unbounded — the cap exists to protect memory, not disk.
* ``download_stream_*`` — yield response chunks to the caller; the
  generator owns connection cleanup on exhaustion or close.

All helpers issue ``transport.request("GET", path, stream=True)`` so
the response body is left undrained until the helper itself iterates.
Errors from the server (non-2xx) raise their usual
:class:`~claude_compliance_sdk.APIError` subclass inside
``request()`` — the helpers never see an error response.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Union

import httpx

from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport
from claude_compliance_sdk.exceptions import FileTooLargeError

PathLike = Union[str, os.PathLike[str]]


# ---------------------------------------------------------------------------
# Sync helpers
# ---------------------------------------------------------------------------


def download_eager_sync(
    transport: SyncTransport,
    path: str,
    *,
    max_download_bytes: int,
) -> bytes:
    """Fetch the full response body, bounded by ``max_download_bytes``."""
    response = transport.request("GET", path, stream=True)
    try:
        _enforce_content_length(response, max_download_bytes)
        return _read_bounded_sync(response, max_download_bytes)
    finally:
        response.close()


def download_to_file_sync(
    transport: SyncTransport,
    path: str,
    *,
    dest: PathLike,
) -> None:
    """Stream the response body to ``dest`` (unbounded)."""
    response = transport.request("GET", path, stream=True)
    try:
        with open(dest, "wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
    finally:
        response.close()


def download_stream_sync(
    transport: SyncTransport,
    path: str,
) -> Iterator[bytes]:
    """Yield response chunks to the caller (connection auto-closes)."""
    response = transport.request("GET", path, stream=True)
    try:
        yield from response.iter_bytes()
    finally:
        response.close()


# ---------------------------------------------------------------------------
# Async helpers
# ---------------------------------------------------------------------------


async def download_eager_async(
    transport: AsyncTransport,
    path: str,
    *,
    max_download_bytes: int,
) -> bytes:
    """Async analogue of :func:`download_eager_sync`."""
    response = await transport.request("GET", path, stream=True)
    try:
        _enforce_content_length(response, max_download_bytes)
        return await _read_bounded_async(response, max_download_bytes)
    finally:
        await response.aclose()


async def download_to_file_async(
    transport: AsyncTransport,
    path: str,
    *,
    dest: PathLike,
) -> None:
    """Async analogue of :func:`download_to_file_sync`."""
    response = await transport.request("GET", path, stream=True)
    try:
        with open(dest, "wb") as handle:
            async for chunk in response.aiter_bytes():
                handle.write(chunk)
    finally:
        await response.aclose()


async def download_stream_async(
    transport: AsyncTransport,
    path: str,
) -> AsyncIterator[bytes]:
    """Async analogue of :func:`download_stream_sync`."""
    response = await transport.request("GET", path, stream=True)
    try:
        async for chunk in response.aiter_bytes():
            yield chunk
    finally:
        await response.aclose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enforce_content_length(response: httpx.Response, max_download_bytes: int) -> None:
    raw = response.headers.get("content-length")
    if raw is None:
        return
    try:
        size = int(raw)
    except ValueError:
        return
    if size > max_download_bytes:
        raise FileTooLargeError(
            f"Server reported Content-Length {size} bytes, exceeds "
            f"max_download_bytes {max_download_bytes}. Use "
            "download_to_file() or download_stream() for larger files.",
            size_bytes=size,
            max_bytes=max_download_bytes,
        )


def _read_bounded_sync(response: httpx.Response, max_download_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > max_download_bytes:
            raise FileTooLargeError(
                f"Response exceeded max_download_bytes {max_download_bytes} "
                "mid-stream (no Content-Length was sent). Use "
                "download_to_file() or download_stream() for larger files.",
                size_bytes=None,
                max_bytes=max_download_bytes,
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def _read_bounded_async(response: httpx.Response, max_download_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > max_download_bytes:
            raise FileTooLargeError(
                f"Response exceeded max_download_bytes {max_download_bytes} "
                "mid-stream (no Content-Length was sent). Use "
                "download_to_file() or download_stream() for larger files.",
                size_bytes=None,
                max_bytes=max_download_bytes,
            )
        chunks.append(chunk)
    return b"".join(chunks)
