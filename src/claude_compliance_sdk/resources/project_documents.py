"""Project documents resource group.

Wraps three endpoints for plain-text project documents (custom
instructions, reference material attached to a project):

* ``GET /v1/compliance/apps/projects/documents/{document_id}`` —
  fetch one document including its text content.
* ``GET /v1/compliance/apps/projects/documents/{document_id}/metadata``
  — fetch the same document's metadata without its body, which is what
  you want when enumerating rather than exporting.
* ``DELETE /v1/compliance/apps/projects/documents/{document_id}`` —
  hard-delete a document.

The list-of-documents view lives on the parent project — call
`list_attachments`
and filter by ``type == "project_doc"``. The discriminator returns
both binary files (``project_file``) and documents (``project_doc``)
because the API lists them on the same endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from claude_compliance_sdk._internal.parsing import parse_with_extra
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

PROJECT_DOCUMENTS_PATH = "/v1/compliance/apps/projects/documents"


@dataclass
class ProjectDocument:
    """The full content of one project document.

    Attributes:
        id: Tagged document identifier (``claude_proj_doc_...``).
        filename: Display name (e.g. ``"instructions.txt"``).
        content: Document body, as plain text.
        created_at: RFC 3339 creation timestamp.
        user: Creator info (``id``, ``email_address``) or ``None`` when
            the creator's account has been deleted. Kept as a raw dict.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    filename: str
    content: str
    created_at: str
    user: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "ProjectDocument":
        """Build a `ProjectDocument` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class ProjectDocumentMetadata:
    """One project document's metadata, without its body.

    Use this to enumerate documents cheaply. `get` returns the same
    document *with* its text, which means pulling every body just to
    read a filename or a size.

    Attributes:
        id: Tagged document identifier (``claude_proj_doc_...``).
        claude_project_id: The project the document belongs to.
        filename: Display name.
        mime_type: Always ``"text/plain"`` — project documents are
            stored as text, including ones converted from other
            formats when they were added.
        size_bytes: Size of the stored text.
        md5: Lowercase hex MD5 of the stored text.
        created_at: RFC 3339 creation timestamp.
        user: Creator info (``id``, ``email_address``) or ``None`` when
            the creator's account has been deleted. Kept as a raw dict.
        extra: Any additional fields the API adds in a later revision.
    """

    id: str
    claude_project_id: str
    filename: str
    created_at: str
    mime_type: str = "text/plain"
    size_bytes: int | None = None
    md5: str | None = None
    user: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "ProjectDocumentMetadata":
        """Build a `ProjectDocumentMetadata` from one decoded record."""
        return parse_with_extra(cls, body)


def _document_path(document_id: str) -> str:
    return f"{PROJECT_DOCUMENTS_PATH}/{document_id}"


def _metadata_path(document_id: str) -> str:
    return f"{PROJECT_DOCUMENTS_PATH}/{document_id}/metadata"


class ProjectDocuments:
    """Synchronous client for the Project Documents endpoints."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def get(self, document_id: str) -> ProjectDocument:
        """Fetch one project document, content included.

        Args:
            document_id: Tagged document identifier (e.g. the ``id``
                from an attachment with ``type == "project_doc"``).

        Raises:
            NotFoundError: When ``document_id`` does not exist or has
                already been deleted.
            APIError: For any other non-2xx response.
        """
        body = self._transport.request("GET", _document_path(document_id))
        return ProjectDocument.from_dict(body)

    def get_metadata(self, document_id: str) -> ProjectDocumentMetadata:
        """Fetch one project document's metadata, without its body.

        Args:
            document_id: Tagged document identifier.

        Raises:
            NotFoundError: When ``document_id`` does not exist or has
                already been deleted.
            APIError: For any other non-2xx response.
        """
        body = self._transport.request("GET", _metadata_path(document_id))
        return ProjectDocumentMetadata.from_dict(body)

    def delete(self, document_id: str) -> None:
        """Hard-delete a project document.

        Returns ``None`` on success; the server's confirmation payload
        is discarded.

        Raises:
            NotFoundError: When ``document_id`` does not exist.
            APIError: For any other non-2xx response.
        """
        self._transport.request("DELETE", _document_path(document_id))


class AsyncProjectDocuments:
    """Asynchronous client for the Project Documents endpoints."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def get(self, document_id: str) -> ProjectDocument:
        """Async analogue of `get`."""
        body = await self._transport.request("GET", _document_path(document_id))
        return ProjectDocument.from_dict(body)

    async def get_metadata(self, document_id: str) -> ProjectDocumentMetadata:
        """Async analogue of `get_metadata`."""
        body = await self._transport.request("GET", _metadata_path(document_id))
        return ProjectDocumentMetadata.from_dict(body)

    async def delete(self, document_id: str) -> None:
        """Async analogue of `delete`."""
        await self._transport.request("DELETE", _document_path(document_id))
