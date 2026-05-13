"""Project documents resource group.

Wraps ``/v1/compliance/apps/projects/documents/{document_id}`` for
fetching and deleting plain-text project documents (custom instructions,
reference material). These are distinct from binary project files;
see ``files`` and ``projects.list_attachments`` for the union shape.
Methods land in Phase 3.
"""

from claude_compliance_sdk._internal.base_transport import BaseAsyncTransport, BaseTransport


class ProjectDocuments:
    """Synchronous client for compliance project documents."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport


class AsyncProjectDocuments:
    """Asynchronous client for compliance project documents."""

    def __init__(self, transport: BaseAsyncTransport) -> None:
        self._transport = transport
