"""Generated files resource group (assistant tool-use outputs).

Wraps the
``/v1/compliance/apps/chats/generated-files/{claude_gen_file_id}``
endpoints for metadata and download of files the assistant produced
via tool use (PDFs, spreadsheets, etc.). These live in the
per-conversation Filestore — a distinct backend from user-uploaded
files — and **have no DELETE endpoint**. The server rejects any
deletion attempt.
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

GENERATED_FILES_PATH = "/v1/compliance/apps/chats/generated-files"


@dataclass
class GeneratedFile:
    """Metadata for one assistant-generated file.

    The owning chat is included on the metadata because the
    generated-file id is opaque; locate the specific message that
    produced the file by fetching messages on ``claude_chat_id`` and
    matching against the message's ``generated_files`` references.

    Attributes:
        id: Opaque generated-file id (``claude_gen_file_...``).
        filename: Display name.
        claude_chat_id: Owning chat's tagged ID.
        mime_type: MIME type as recorded by Filestore, when known.
        size_bytes: Size in bytes as recorded by Filestore, when known.
        created_at: RFC 3339 creation timestamp from Filestore, or
            ``None`` when not recorded.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    filename: str
    claude_chat_id: str
    mime_type: str | None = None
    size_bytes: int | None = None
    created_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "GeneratedFile":
        """Build a `GeneratedFile` from one decoded record."""
        return parse_with_extra(cls, body)


def _file_path(claude_gen_file_id: str) -> str:
    return f"{GENERATED_FILES_PATH}/{claude_gen_file_id}"


def _content_path(claude_gen_file_id: str) -> str:
    return f"{GENERATED_FILES_PATH}/{claude_gen_file_id}/content"


class GeneratedFiles:
    """Synchronous client for assistant-generated compliance files."""

    def __init__(self, transport: SyncTransport, *, max_download_bytes: int) -> None:
        self._transport = transport
        self._max_download_bytes = max_download_bytes

    def get(self, claude_gen_file_id: str) -> GeneratedFile:
        """Fetch metadata without downloading the bytes."""
        body = self._transport.request("GET", _file_path(claude_gen_file_id))
        return GeneratedFile.from_dict(body)

    def download(self, claude_gen_file_id: str) -> bytes:
        """Eager download bounded by ``max_download_bytes``."""
        return download_eager_sync(
            self._transport,
            _content_path(claude_gen_file_id),
            max_download_bytes=self._max_download_bytes,
        )

    def download_to_file(self, claude_gen_file_id: str, dest: PathLike) -> None:
        """Stream the file to ``dest`` (unbounded)."""
        download_to_file_sync(
            self._transport,
            _content_path(claude_gen_file_id),
            dest=dest,
        )

    def download_stream(self, claude_gen_file_id: str) -> Iterator[bytes]:
        """Yield response chunks to the caller."""
        return download_stream_sync(self._transport, _content_path(claude_gen_file_id))


class AsyncGeneratedFiles:
    """Asynchronous client for assistant-generated compliance files."""

    def __init__(self, transport: AsyncTransport, *, max_download_bytes: int) -> None:
        self._transport = transport
        self._max_download_bytes = max_download_bytes

    async def get(self, claude_gen_file_id: str) -> GeneratedFile:
        """Async analogue of `get`."""
        body = await self._transport.request("GET", _file_path(claude_gen_file_id))
        return GeneratedFile.from_dict(body)

    async def download(self, claude_gen_file_id: str) -> bytes:
        """Async analogue of `download`."""
        return await download_eager_async(
            self._transport,
            _content_path(claude_gen_file_id),
            max_download_bytes=self._max_download_bytes,
        )

    async def download_to_file(self, claude_gen_file_id: str, dest: PathLike) -> None:
        """Async analogue of `download_to_file`."""
        await download_to_file_async(
            self._transport,
            _content_path(claude_gen_file_id),
            dest=dest,
        )

    def download_stream(self, claude_gen_file_id: str) -> AsyncIterator[bytes]:
        """Async analogue of `download_stream`."""
        return download_stream_async(self._transport, _content_path(claude_gen_file_id))
