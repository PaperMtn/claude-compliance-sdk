"""Files resource group (user-uploaded files).

Wraps the ``/v1/compliance/apps/chats/files/{claude_file_id}``
endpoints for metadata, download, and deletion of files a user
attached to a chat.

Three resources in Phase 3.5 share the same download trio
(`download` / `download_to_file` / `download_stream`)
backed by helpers in `downloads`.
Of the three, only user-uploaded files are deletable per spec —
generated files and artifacts have no DELETE endpoint.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any, Mapping

from claude_compliance_sdk._internal.downloads import (
    PathLike,
    download_eager_async,
    download_eager_sync,
    download_stream_async,
    download_stream_sync,
    download_to_file_async,
    download_to_file_sync,
)
from claude_compliance_sdk._internal.parsing import parse_with_extra
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

FILES_PATH = "/v1/compliance/apps/chats/files"


@dataclass
class File:
    """Metadata for one user-uploaded chat file.

    Attributes:
        id: Tagged file identifier (``claude_file_...``).
        created_at: RFC 3339 creation timestamp.
        filename: Display name, or ``None`` when the upload had no
            filename set.
        mime_type: MIME type of the downloadable variant, or ``None``
            for files with no downloadable content (e.g.
            code-interpreter outputs).
        size_bytes: Size of the downloadable variant in bytes, when
            known.
        message_ids: Chat message IDs that reference this file. One
            file can be attached to multiple messages.
        extra: Any additional fields the spec adds in a later revision.
    """

    id: str
    created_at: str
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    message_ids: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "File":
        """Build a `File` from one decoded record."""
        return parse_with_extra(cls, body)


def _file_path(claude_file_id: str) -> str:
    return f"{FILES_PATH}/{claude_file_id}"


def _content_path(claude_file_id: str) -> str:
    return f"{FILES_PATH}/{claude_file_id}/content"


class Files:
    """Synchronous client for user-uploaded compliance files."""

    def __init__(self, transport: SyncTransport, *, max_download_bytes: int) -> None:
        self._transport = transport
        self._max_download_bytes = max_download_bytes

    def get(self, claude_file_id: str) -> File:
        """Fetch file metadata without downloading the bytes."""
        body = self._transport.request("GET", _file_path(claude_file_id))
        return File.from_dict(body)

    def download(self, claude_file_id: str) -> bytes:
        """Download the file's bytes in one shot.

        Bounded by the client's ``max_download_bytes`` cap; raises
        `FileTooLargeError` for anything
        larger. Use `download_to_file` or `download_stream`
        for unbounded reads.
        """
        return download_eager_sync(
            self._transport,
            _content_path(claude_file_id),
            max_download_bytes=self._max_download_bytes,
        )

    def download_to_file(self, claude_file_id: str, dest: PathLike) -> None:
        """Stream the file's bytes to ``dest`` (a path or os.PathLike).

        Unbounded — the eager cap exists to protect memory, not disk.
        """
        download_to_file_sync(
            self._transport,
            _content_path(claude_file_id),
            dest=dest,
        )

    def download_stream(self, claude_file_id: str) -> Iterator[bytes]:
        """Yield response chunks to the caller, connection auto-closes."""
        return download_stream_sync(self._transport, _content_path(claude_file_id))

    def delete(self, claude_file_id: str) -> None:
        """Permanently delete the file.

        Returns ``None`` on success; the server's confirmation payload
        is discarded.

        Raises:
            NotFoundError: When ``claude_file_id`` does not exist or
                has already been deleted.
            APIError: For any other non-2xx response.
        """
        self._transport.request("DELETE", _file_path(claude_file_id))


class AsyncFiles:
    """Asynchronous client for user-uploaded compliance files."""

    def __init__(self, transport: AsyncTransport, *, max_download_bytes: int) -> None:
        self._transport = transport
        self._max_download_bytes = max_download_bytes

    async def get(self, claude_file_id: str) -> File:
        """Async analogue of `get`."""
        body = await self._transport.request("GET", _file_path(claude_file_id))
        return File.from_dict(body)

    async def download(self, claude_file_id: str) -> bytes:
        """Async analogue of `download`."""
        return await download_eager_async(
            self._transport,
            _content_path(claude_file_id),
            max_download_bytes=self._max_download_bytes,
        )

    async def download_to_file(self, claude_file_id: str, dest: PathLike) -> None:
        """Async analogue of `download_to_file`."""
        await download_to_file_async(
            self._transport,
            _content_path(claude_file_id),
            dest=dest,
        )

    def download_stream(self, claude_file_id: str) -> AsyncIterator[bytes]:
        """Async analogue of `download_stream`."""
        return download_stream_async(self._transport, _content_path(claude_file_id))

    async def delete(self, claude_file_id: str) -> None:
        """Async analogue of `delete`."""
        await self._transport.request("DELETE", _file_path(claude_file_id))
