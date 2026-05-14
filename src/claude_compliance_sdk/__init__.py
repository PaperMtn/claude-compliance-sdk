"""Python SDK for the Anthropic Compliance API.

Public surface:

* :class:`ComplianceClient` — synchronous client.
* :class:`AsyncComplianceClient` — asynchronous client.
* The error hierarchy rooted at :class:`ComplianceClientError`.
* Pagination page shapes (:class:`CursorPage`, :class:`OffsetPage`,
  and their async aliases).
* :data:`__version__` — current SDK version.

The two clients expose the same resource group attributes
(``activities``, ``chats``, ``files``, ``generated_files``, ``artifacts``,
``projects``, ``project_documents``, ``organizations``, ``roles``,
``groups``) and the same method names on each group. Method bodies
land in Phase 3 (per-resource implementations).
"""

from claude_compliance_sdk._internal.pagination import (
    AsyncCursorPage,
    AsyncOffsetPage,
    CursorPage,
    OffsetPage,
)
from claude_compliance_sdk.async_client import AsyncComplianceClient
from claude_compliance_sdk.client import ComplianceClient
from claude_compliance_sdk.exceptions import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ComplianceClientError,
    ConflictError,
    InsufficientScopeError,
    InternalServerError,
    InvalidAPIKeyError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from claude_compliance_sdk.resources.activities import Activity
from claude_compliance_sdk.resources.organizations import Organization, User
from claude_compliance_sdk.resources.project_documents import ProjectDocument
from claude_compliance_sdk.resources.projects import Project, ProjectAttachment, ProjectDetail
from claude_compliance_sdk.version import __version__

__all__ = [
    "APIConnectionError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "Activity",
    "AsyncComplianceClient",
    "AsyncCursorPage",
    "AsyncOffsetPage",
    "AuthenticationError",
    "BadRequestError",
    "ComplianceClient",
    "ComplianceClientError",
    "ConflictError",
    "CursorPage",
    "InsufficientScopeError",
    "InternalServerError",
    "InvalidAPIKeyError",
    "NotFoundError",
    "OffsetPage",
    "Organization",
    "PermissionDeniedError",
    "Project",
    "ProjectAttachment",
    "ProjectDetail",
    "ProjectDocument",
    "RateLimitError",
    "User",
    "__version__",
]
