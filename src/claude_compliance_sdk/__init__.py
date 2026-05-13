"""Python SDK for the Anthropic Compliance API.

Public surface:

* :class:`ComplianceClient` — synchronous client.
* :class:`AsyncComplianceClient` — asynchronous client.
* :data:`__version__` — current SDK version.

The two clients expose the same resource group attributes
(``activities``, ``chats``, ``files``, ``generated_files``, ``artifacts``,
``projects``, ``project_documents``, ``organizations``, ``roles``,
``groups``) and the same method names on each group. Method bodies
land in Phase 2 (core infrastructure) and Phase 3 (per-resource
implementations).
"""

from claude_compliance_sdk.async_client import AsyncComplianceClient
from claude_compliance_sdk.client import ComplianceClient
from claude_compliance_sdk.version import __version__

__all__ = [
    "AsyncComplianceClient",
    "ComplianceClient",
    "__version__",
]
