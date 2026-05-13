"""Roles resource group.

Wraps the nested ``/organizations/{org_uuid}/roles`` endpoints — list,
get, and list-permissions. Methods land in Phase 3.
"""

from claude_compliance_sdk._internal.base_transport import BaseAsyncTransport, BaseTransport


class Roles:
    """Synchronous client for compliance RBAC roles."""

    def __init__(self, transport: BaseTransport) -> None:
        self._transport = transport


class AsyncRoles:
    """Asynchronous client for compliance RBAC roles."""

    def __init__(self, transport: BaseAsyncTransport) -> None:
        self._transport = transport
