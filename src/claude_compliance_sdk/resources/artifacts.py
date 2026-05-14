"""Artifacts resource group.

Wraps ``GET /v1/compliance/apps/artifacts/{artifact_version_id}/content``
for downloading versioned text artifacts (code, markdown, structured
output) that Claude generates as part of assistant responses.

Unlike :mod:`files` and :mod:`generated_files`, Artifacts has **no
metadata endpoint and no DELETE** — only the content download. The
reference metadata (``id``, ``version_id``, ``title``,
``artifact_type``) is carried inline on chat messages, so the listing
shape is part of the Chats response, not a separate Artifacts call.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

from claude_compliance_sdk._internal.downloads import (
    PathLike,
    download_eager_async,
    download_eager_sync,
    download_stream_async,
    download_stream_sync,
    download_to_file_async,
    download_to_file_sync,
)
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

ARTIFACTS_PATH = "/v1/compliance/apps/artifacts"


def _content_path(artifact_version_id: str) -> str:
    return f"{ARTIFACTS_PATH}/{artifact_version_id}/content"


class Artifacts:
    """Synchronous client for compliance artifact content."""

    def __init__(self, transport: SyncTransport, *, max_download_bytes: int) -> None:
        self._transport = transport
        self._max_download_bytes = max_download_bytes

    def download(self, artifact_version_id: str) -> bytes:
        """Eager download bounded by ``max_download_bytes``.

        Raises :class:`~claude_compliance_sdk.FileTooLargeError` when
        the content exceeds the cap. Use :meth:`download_to_file` or
        :meth:`download_stream` for larger artifacts.
        """
        return download_eager_sync(
            self._transport,
            _content_path(artifact_version_id),
            max_download_bytes=self._max_download_bytes,
        )

    def download_to_file(self, artifact_version_id: str, dest: PathLike) -> None:
        """Stream the artifact to ``dest`` (unbounded)."""
        download_to_file_sync(
            self._transport,
            _content_path(artifact_version_id),
            dest=dest,
        )

    def download_stream(self, artifact_version_id: str) -> Iterator[bytes]:
        """Yield response chunks to the caller."""
        return download_stream_sync(self._transport, _content_path(artifact_version_id))


class AsyncArtifacts:
    """Asynchronous client for compliance artifact content."""

    def __init__(self, transport: AsyncTransport, *, max_download_bytes: int) -> None:
        self._transport = transport
        self._max_download_bytes = max_download_bytes

    async def download(self, artifact_version_id: str) -> bytes:
        """Async analogue of :meth:`Artifacts.download`."""
        return await download_eager_async(
            self._transport,
            _content_path(artifact_version_id),
            max_download_bytes=self._max_download_bytes,
        )

    async def download_to_file(self, artifact_version_id: str, dest: PathLike) -> None:
        """Async analogue of :meth:`Artifacts.download_to_file`."""
        await download_to_file_async(
            self._transport,
            _content_path(artifact_version_id),
            dest=dest,
        )

    def download_stream(self, artifact_version_id: str) -> AsyncIterator[bytes]:
        """Async analogue of :meth:`Artifacts.download_stream`."""
        return download_stream_async(self._transport, _content_path(artifact_version_id))
