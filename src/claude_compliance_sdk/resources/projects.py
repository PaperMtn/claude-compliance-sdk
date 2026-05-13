"""Projects resource group.

Wraps the ``/v1/compliance/apps/projects`` and per-project endpoints —
list, get, delete, and list-attachments. A project delete returns 409
if chats are still attached; the SDK surfaces that as a
``ComplianceConflictError``. Methods land in Phase 3.
"""

from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport


class Projects:
    """Synchronous client for compliance project metadata and attachments."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport


class AsyncProjects:
    """Asynchronous client for compliance project metadata and attachments."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport
