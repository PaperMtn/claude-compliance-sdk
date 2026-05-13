"""Asynchronous entry point for the Anthropic Compliance SDK.

Mirrors :mod:`claude_compliance_sdk.client` exactly, but every method
that performs I/O is a coroutine. The construction surface, defaults,
and resource group attributes are otherwise identical so callers can
swap one client for the other without changing call sites.
"""

import os
from types import TracebackType

from claude_compliance_sdk._internal.transport import AsyncTransport
from claude_compliance_sdk.client import (
    API_KEY_ENV_VAR,
    DEFAULT_ANTHROPIC_VERSION,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_DOWNLOAD_BYTES,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_RPM,
    DEFAULT_TIMEOUT_SECONDS,
)
from claude_compliance_sdk.resources.activities import AsyncActivities
from claude_compliance_sdk.resources.artifacts import AsyncArtifacts
from claude_compliance_sdk.resources.chats import AsyncChats
from claude_compliance_sdk.resources.files import AsyncFiles
from claude_compliance_sdk.resources.generated_files import AsyncGeneratedFiles
from claude_compliance_sdk.resources.groups import AsyncGroups
from claude_compliance_sdk.resources.organizations import AsyncOrganizations
from claude_compliance_sdk.resources.project_documents import AsyncProjectDocuments
from claude_compliance_sdk.resources.projects import AsyncProjects
from claude_compliance_sdk.resources.roles import AsyncRoles


class AsyncComplianceClient:
    """Asynchronous client for the Anthropic Compliance API.

    Construct a single client per API key and reuse it across awaits.
    Designed to be used as an async context manager so the underlying
    ``httpx.AsyncClient`` is closed cleanly on exit.

    Args:
        api_key: A Compliance Access Key (``sk-ant-api01-...``) or an
            Admin key (``sk-ant-admin01-...``). If omitted, the value
            of the ``ANTHROPIC_COMPLIANCE_API_KEY`` environment variable
            is used.
        base_url: Override the API host. Defaults to the Anthropic
            production host.
        timeout: Per-request timeout in seconds. Default 30.
        anthropic_version: Value sent in the ``anthropic-version``
            header. Defaults to ``"2023-06-01"``.
        max_download_bytes: Maximum size, in bytes, that the eager
            ``download()`` coroutines will load into memory. Larger
            files must be fetched through ``download_to_file()`` or
            ``download_stream()``. Default 100 MiB.
        max_retries: Maximum retry attempts for 429 and 5xx responses.
            Default 3. Set to ``0`` to disable retries.
        rate_limit_rpm: Proactive client-side requests-per-minute cap.
            Defaults to ``600``, matching the server-side limit.

    Raises:
        ValueError: If no API key is supplied through ``api_key`` or
            the environment variable.

    Example:
        >>> import asyncio
        >>> from claude_compliance_sdk import AsyncComplianceClient
        >>> async def main() -> None:
        ...     async with AsyncComplianceClient(api_key="sk-ant-api01-...") as client:
        ...         pass  # resource methods land in Phase 3
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        anthropic_version: str = DEFAULT_ANTHROPIC_VERSION,
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
        self.anthropic_version: str = anthropic_version
        self.max_download_bytes: int = max_download_bytes
        self.max_retries: int = max_retries
        self.rate_limit_rpm: int = rate_limit_rpm

        self._transport: AsyncTransport = AsyncTransport(
            api_key=resolved_key,
            base_url=base_url,
            timeout=timeout,
            anthropic_version=anthropic_version,
            max_retries=max_retries,
            rate_limit_rpm=rate_limit_rpm,
        )

        self.activities: AsyncActivities = AsyncActivities(self._transport)
        self.artifacts: AsyncArtifacts = AsyncArtifacts(self._transport)
        self.chats: AsyncChats = AsyncChats(self._transport)
        self.files: AsyncFiles = AsyncFiles(self._transport)
        self.generated_files: AsyncGeneratedFiles = AsyncGeneratedFiles(self._transport)
        self.groups: AsyncGroups = AsyncGroups(self._transport)
        self.organizations: AsyncOrganizations = AsyncOrganizations(self._transport)
        self.project_documents: AsyncProjectDocuments = AsyncProjectDocuments(self._transport)
        self.projects: AsyncProjects = AsyncProjects(self._transport)
        self.roles: AsyncRoles = AsyncRoles(self._transport)

    async def aclose(self) -> None:
        """Close the underlying async HTTP connection pool.

        Safe to await multiple times. After ``aclose()`` is awaited, the
        client must not be reused.
        """
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncComplianceClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()
