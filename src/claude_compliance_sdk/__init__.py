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
from claude_compliance_sdk._internal.rate_limit import RateLimitSnapshot
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
    LocalSessionsRetentionUnavailableError,
    LocalSessionsUnavailableError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from claude_compliance_sdk.resources.activities import Activity
from claude_compliance_sdk.resources.chats import Chat, ChatMessagesPage, Message
from claude_compliance_sdk.resources.files import File
from claude_compliance_sdk.resources.generated_files import GeneratedFile
from claude_compliance_sdk.resources.groups import Group, GroupMember
from claude_compliance_sdk.resources.local_sessions import (
    LocalSession,
    LocalSessionMessage,
    LocalSessionTranscript,
    SessionUser,
)
from claude_compliance_sdk.resources.organizations import (
    ComplianceApiKey,
    Organization,
    OrganizationSettings,
    User,
)
from claude_compliance_sdk.resources.project_documents import (
    ProjectDocument,
    ProjectDocumentMetadata,
)
from claude_compliance_sdk.resources.projects import (
    Project,
    ProjectAttachment,
    ProjectCollaborator,
    ProjectDetail,
)
from claude_compliance_sdk.resources.remote_sessions import (
    RemoteSession,
    RemoteSessionMessage,
    RemoteSessionTranscript,
)
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
    "ComplianceApiKey",
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
    "LocalSession",
    "LocalSessionMessage",
    "LocalSessionTranscript",
    "LocalSessionsRetentionUnavailableError",
    "LocalSessionsUnavailableError",
    "Message",
    "NotFoundError",
    "OffsetPage",
    "Organization",
    "OrganizationSettings",
    "Permission",
    "PermissionDeniedError",
    "Project",
    "ProjectAttachment",
    "ProjectCollaborator",
    "ProjectDetail",
    "ProjectDocument",
    "ProjectDocumentMetadata",
    "RateLimitError",
    "RateLimitSnapshot",
    "RemoteSession",
    "RemoteSessionMessage",
    "RemoteSessionTranscript",
    "Role",
    "SessionUser",
    "User",
    "__version__",
]
