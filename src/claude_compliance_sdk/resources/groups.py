"""Groups resource group.

Wraps ``/v1/compliance/groups`` and the per-group ``/members`` endpoint
for compliance RBAC groups. Methods land in Phase 3.
"""

from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport


class Groups:
    """Synchronous client for compliance RBAC groups and members."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport


class AsyncGroups:
    """Asynchronous client for compliance RBAC groups and members."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport
