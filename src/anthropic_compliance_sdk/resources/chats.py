"""Chats resource group.

Wraps ``GET /v1/compliance/apps/chats``, the per-chat messages endpoint,
and chat deletion. Read and delete methods land in Phase 3.
"""

from anthropic_compliance_sdk._internal.base_transport import BaseAsyncTransport, BaseTransport


class Chats:
    """Synchronous client for compliance chat metadata and messages."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport


class AsyncChats:
    """Asynchronous client for compliance chat metadata and messages."""

    def __init__(self, transport: BaseAsyncTransport) -> None:
        self._transport = transport
