"""Synchronous entry point for the Anthropic Compliance SDK.

Exposes the ``ComplianceClient`` class: its configuration knobs and the
ten resource group attributes through which every endpoint is reached.
The request, retry, rate-limit, and pagination machinery lives in the
transport and pagination layers under ``_internal``.
"""

import os
from types import TracebackType

from claude_compliance_sdk._internal.transport import SyncTransport
from claude_compliance_sdk.resources.activities import Activities
from claude_compliance_sdk.resources.artifacts import Artifacts
from claude_compliance_sdk.resources.chats import Chats
from claude_compliance_sdk.resources.files import Files
from claude_compliance_sdk.resources.generated_files import GeneratedFiles
from claude_compliance_sdk.resources.groups import Groups
from claude_compliance_sdk.resources.organizations import Organizations
from claude_compliance_sdk.resources.project_documents import ProjectDocuments
from claude_compliance_sdk.resources.projects import Projects
from claude_compliance_sdk.resources.roles import Roles

DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
DEFAULT_MAX_RETRIES = 3
DEFAULT_RATE_LIMIT_RPM = 600

API_KEY_ENV_VAR = "ANTHROPIC_COMPLIANCE_API_KEY"


class ComplianceClient:
    """Synchronous client for the Anthropic Compliance API.

    Construct a single client per API key and reuse it across calls.
    The client holds a connection pool and a rate limiter, both of which
    need to live across requests for full benefit.

    Args:
        api_key: A Compliance Access Key (``sk-ant-api01-...``) or an
            Admin key (``sk-ant-admin01-...``). If omitted, the value
            of the ``ANTHROPIC_COMPLIANCE_API_KEY`` environment variable
            is used.
        base_url: Override the API host. Defaults to the Anthropic
            production host. Useful for testing against a recorded
            fixture server.
        timeout: Per-request timeout in seconds. Default 30.
        max_download_bytes: Maximum size, in bytes, that the eager
            ``download()`` methods will load into memory. Larger files
            must be fetched through ``download_to_file()`` or
            ``download_stream()``. Default 100 MiB.
        max_retries: Maximum retry attempts for 429 and 5xx responses.
            Default 3. Set to ``0`` to disable retries.
        rate_limit_rpm: Proactive client-side requests-per-minute cap.
            Defaults to ``600``, matching the server-side limit.

    Raises:
        ValueError: If no API key is supplied through ``api_key`` or
            the environment variable.

    Example:
        ```python
        from claude_compliance_sdk import ComplianceClient

        with ComplianceClient(api_key="sk-ant-api01-...") as client:
            for activity in client.activities.iter(limit=10):
                print(activity.id, activity.type)
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit_rpm: int = DEFAULT_RATE_LIMIT_RPM,
    ) -> None:
        resolved_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV_VAR)
        if not resolved_key:
            raise ValueError(
                "No API key provided. Pass api_key=... or set the "
                f"{API_KEY_ENV_VAR} environment variable."
            )
        self._api_key: str = resolved_key
        self.base_url: str = base_url
        self.timeout: float = timeout
        self.max_download_bytes: int = max_download_bytes
        self.max_retries: int = max_retries
        self.rate_limit_rpm: int = rate_limit_rpm

        self._transport: SyncTransport = SyncTransport(
            api_key=resolved_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            rate_limit_rpm=rate_limit_rpm,
        )

        self.activities: Activities = Activities(self._transport)
        self.artifacts: Artifacts = Artifacts(
            self._transport, max_download_bytes=max_download_bytes
        )
        self.chats: Chats = Chats(self._transport)
        self.files: Files = Files(self._transport, max_download_bytes=max_download_bytes)
        self.generated_files: GeneratedFiles = GeneratedFiles(
            self._transport, max_download_bytes=max_download_bytes
        )
        self.groups: Groups = Groups(self._transport)
        self.organizations: Organizations = Organizations(self._transport)
        self.project_documents: ProjectDocuments = ProjectDocuments(self._transport)
        self.projects: Projects = Projects(self._transport)
        self.roles: Roles = Roles(self._transport)

    def close(self) -> None:
        """Close the underlying HTTP connection pool.

        Safe to call multiple times. After ``close()`` is invoked, the
        client must not be reused.
        """
        self._transport.close()

    def __enter__(self) -> "ComplianceClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
