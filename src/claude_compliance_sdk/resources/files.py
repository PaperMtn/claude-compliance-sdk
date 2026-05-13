"""Files resource group (user-uploaded files).

Wraps the ``/v1/compliance/apps/chats/files/{claude_file_id}`` endpoints
for metadata, download, and deletion of user-uploaded files. Methods
land in Phase 3.
"""

from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport


class Files:
    """Synchronous client for user-uploaded compliance files."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport


class AsyncFiles:
    """Asynchronous client for user-uploaded compliance files."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport
