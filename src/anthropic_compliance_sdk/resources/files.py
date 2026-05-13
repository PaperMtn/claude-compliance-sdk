"""Files resource group (user-uploaded files).

Wraps the ``/v1/compliance/apps/chats/files/{claude_file_id}`` endpoints
for metadata, download, and deletion of user-uploaded files. Methods
land in Phase 3.
"""

from anthropic_compliance_sdk._internal.base_transport import BaseAsyncTransport, BaseTransport


class Files:
    """Synchronous client for user-uploaded compliance files."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport


class AsyncFiles:
    """Asynchronous client for user-uploaded compliance files."""

    def __init__(self, transport: BaseAsyncTransport) -> None:
        self._transport = transport
