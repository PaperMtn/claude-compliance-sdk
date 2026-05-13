"""Generated files resource group (assistant-produced files).

Wraps the ``/v1/compliance/apps/chats/generated-files/{claude_gen_file_id}``
metadata and content endpoints. Unlike user-uploaded files, generated
files have no delete endpoint and live in the per-conversation
Filestore. Methods land in Phase 3.
"""

from claude_compliance_sdk._internal.base_transport import BaseAsyncTransport, BaseTransport


class GeneratedFiles:
    """Synchronous client for assistant-produced compliance files."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport


class AsyncGeneratedFiles:
    """Asynchronous client for assistant-produced compliance files."""

    def __init__(self, transport: BaseAsyncTransport) -> None:
        self._transport = transport
