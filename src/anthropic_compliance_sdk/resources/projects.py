"""Projects resource group.

Wraps the ``/v1/compliance/apps/projects`` and per-project endpoints —
list, get, delete, and list-attachments. A project delete returns 409
if chats are still attached; the SDK surfaces that as a
``ComplianceConflictError``. Methods land in Phase 3.
"""

from anthropic_compliance_sdk._internal.base_transport import BaseAsyncTransport, BaseTransport


class Projects:
    """Synchronous client for compliance project metadata and attachments."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport


class AsyncProjects:
    """Asynchronous client for compliance project metadata and attachments."""

    def __init__(self, transport: BaseAsyncTransport) -> None:
        self._transport = transport
