"""Activities resource group.

Wraps ``GET /v1/compliance/activities``. Read methods land in Phase 3.
"""

from claude_compliance_sdk._internal.base_transport import BaseAsyncTransport, BaseTransport


class Activities:
    """Synchronous client for the Compliance API activity feed."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport


class AsyncActivities:
    """Asynchronous client for the Compliance API activity feed."""

    def __init__(self, transport: BaseAsyncTransport) -> None:
        self._transport = transport
