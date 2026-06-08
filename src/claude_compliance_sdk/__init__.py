"""Python SDK for the Anthropic Compliance API.

Public surface:

* `ComplianceClient` — synchronous client.
* `AsyncComplianceClient` — asynchronous client.
* The error hierarchy rooted at `ComplianceClientError`.
* Pagination page shapes (`CursorPage`, `OffsetPage`,
  and their async aliases).
* `__version__` — current SDK version.

The two clients expose the same resource group attributes
(``activities``, ``chats``, ``files``, ``generated_files``, ``artifacts``,
``projects``, ``project_documents``, ``organizations``, ``roles``,
``groups``) and the same method names on each group.
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
    FileTooLargeError,
    InsufficientScopeError,
    InternalServerError,
    InvalidAPIKeyError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from claude_compliance_sdk.resources.activities import Activity
from claude_compliance_sdk.resources.chats import Chat, ChatMessagesPage, Message
from claude_compliance_sdk.resources.files import File
from claude_compliance_sdk.resources.generated_files import GeneratedFile
from claude_compliance_sdk.resources.groups import Group, GroupMember
from claude_compliance_sdk.resources.organizations import Organization, User
from claude_compliance_sdk.resources.project_documents import ProjectDocument
from claude_compliance_sdk.resources.projects import Project, ProjectAttachment, ProjectDetail
from claude_compliance_sdk.resources.roles import Permission, Role
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
    "Chat",
    "ChatMessagesPage",
    "ComplianceClient",
    "ComplianceClientError",
    "ConflictError",
    "CursorPage",
    "File",
    "FileTooLargeError",
    "GeneratedFile",
    "Group",
    "GroupMember",
    "InsufficientScopeError",
    "InternalServerError",
    "InvalidAPIKeyError",
    "Message",
    "NotFoundError",
    "OffsetPage",
    "Organization",
    "Permission",
    "PermissionDeniedError",
    "Project",
    "ProjectAttachment",
    "ProjectDetail",
    "ProjectDocument",
    "RateLimitError",
    "Role",
    "User",
    "__version__",
]
