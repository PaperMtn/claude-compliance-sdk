"""Chats resource group.

Wraps ``GET /v1/compliance/apps/chats``, the per-chat messages endpoint,
and chat deletion. Read and delete methods land in Phase 3.
"""

from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport


class Chats:
    """Synchronous client for compliance chat metadata and messages."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport


class AsyncChats:
    """Asynchronous client for compliance chat metadata and messages."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport
