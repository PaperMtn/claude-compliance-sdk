"""Artifacts resource group.

Wraps ``GET /v1/compliance/apps/artifacts/{artifact_version_id}/content``
for downloading versioned text artifacts (code, markdown, etc.) that
Claude generates or updates in chat responses. Methods land in Phase 3.
"""

from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport


class Artifacts:
    """Synchronous client for compliance artifact content."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport


class AsyncArtifacts:
    """Asynchronous client for compliance artifact content."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport
