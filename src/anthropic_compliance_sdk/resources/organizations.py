"""Organizations resource group.

Wraps ``/v1/compliance/organizations`` (list, no pagination — errors if
the result would exceed 1,000 orgs) and ``/organizations/{org_uuid}/users``
(paginated list of org members). Methods land in Phase 3.
"""

from anthropic_compliance_sdk._internal.base_transport import BaseAsyncTransport, BaseTransport


class Organizations:
    """Synchronous client for compliance organization metadata and users."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport


class AsyncOrganizations:
    """Asynchronous client for compliance organization metadata and users."""

    def __init__(self, transport: BaseAsyncTransport) -> None:
        self._transport = transport
