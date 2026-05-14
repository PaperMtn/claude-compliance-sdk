"""Projects resource group.

Wraps four endpoints under ``/v1/compliance/apps/projects``:

* ``GET /v1/compliance/apps/projects`` — offset-paginated project list.
  Exposed via :meth:`Projects.list` (one page) and
  :meth:`Projects.iter` (auto-paginate).
* ``GET /v1/compliance/apps/projects/{project_id}`` — single fetch
  returning the richer :class:`ProjectDetail` shape.
* ``DELETE /v1/compliance/apps/projects/{project_id}`` — hard delete.
  Returns 409 / :class:`~claude_compliance_sdk.ConflictError` when the
  project still has chats attached. The SDK does not pre-check; the
  server is the source of truth.
* ``GET /v1/compliance/apps/projects/{project_id}/attachments`` —
  offset-paginated list of files and documents attached to a project.

Project document content lives on a sibling resource group,
:class:`~claude_compliance_sdk.resources.project_documents.ProjectDocuments`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any, Mapping

from claude_compliance_sdk._internal.pagination import (
    OffsetPage,
    iter_all_offset_async,
    iter_all_offset_sync,
)
from claude_compliance_sdk._internal.parsing import parse_with_extra
from claude_compliance_sdk._internal.transport import AsyncTransport, SyncTransport

# Module-level alias for the `list` builtin — see the same comment in
# resources/activities.py for why this is needed on every paginated
# resource that defines a `.list()` method.
StrList = list[str]

PROJECTS_PATH = "/v1/compliance/apps/projects"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Project:
    """A single Compliance API project (list-shape).

    Use :meth:`Projects.get` to fetch the richer :class:`ProjectDetail`.

    Attributes:
        id: Tagged project identifier (``claude_proj_...``).
        name: Project name.
        created_at: RFC 3339 creation timestamp.
        updated_at: RFC 3339 last-update timestamp.
        organization_id: Owning organisation's tagged ID.
        is_private: ``True`` when the project is visible only to the
            creator and specified collaborators.
        user: Creator info (``id``, ``email_address``) or ``None`` when
            the creator's account has been deleted. Kept as a raw dict
            per ADR-0002 (no nested-type recursion).
        extra: Any additional fields the spec adds in a later revision.
    """

    id: str
    name: str
    created_at: str
    updated_at: str
    organization_id: str
    is_private: bool
    user: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Project":
        """Build a :class:`Project` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class ProjectDetail(Project):
    """Detail view of a project, returned by :meth:`Projects.get`.

    Inherits every :class:`Project` field and adds four counts /
    text fields that the list endpoint omits.

    Attributes:
        description: Free-form project description.
        instructions: Project's custom instructions / prompt.
        chats_count: Number of chats inside the project.
        attachments_count: Number of files + documents attached.
    """

    description: str = ""
    instructions: str = ""
    chats_count: int = 0
    attachments_count: int = 0

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "ProjectDetail":
        """Build a :class:`ProjectDetail` from one decoded record."""
        return parse_with_extra(cls, body)


@dataclass
class ProjectAttachment:
    """An attachment on a project — either a binary file or a doc.

    Discriminate on :attr:`type`:

    * ``"project_file"`` — binary file. Download via the Files resource
      (Phase 3.5) using :attr:`id` as ``claude_file_id``.
    * ``"project_doc"`` — plain-text document. Fetch contents via
      :meth:`~claude_compliance_sdk.resources.project_documents.ProjectDocuments.get`
      using :attr:`id` as the document ID.

    Attributes:
        type: Discriminator string. ``"project_file"`` or
            ``"project_doc"``.
        id: Attachment identifier (``claude_file_...`` or
            ``claude_proj_doc_...``).
        created_at: RFC 3339 creation timestamp.
        filename: Display name.
        mime_type: MIME type. ``"text/plain"`` for project docs;
            otherwise whatever the user uploaded.
        extra: Any additional fields the spec adds in a later revision.
    """

    type: str
    id: str
    created_at: str
    filename: str
    mime_type: str
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "ProjectAttachment":
        """Build a :class:`ProjectAttachment` from one decoded record."""
        return parse_with_extra(cls, body)


# ---------------------------------------------------------------------------
# Query-param builders + paths
# ---------------------------------------------------------------------------


def _build_list_params(
    *,
    organization_ids: StrList | None,
    user_ids: StrList | None,
    created_at_gte: str | None,
    created_at_gt: str | None,
    created_at_lte: str | None,
    created_at_lt: str | None,
    page: str | None,
    limit: int | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, values in (
        ("organization_ids", organization_ids),
        ("user_ids", user_ids),
    ):
        if values:
            params[f"{name}[]"] = list(values)
    for name, value in (
        ("created_at.gte", created_at_gte),
        ("created_at.gt", created_at_gt),
        ("created_at.lte", created_at_lte),
        ("created_at.lt", created_at_lt),
        ("page", page),
    ):
        if value is not None:
            params[name] = value
    if limit is not None:
        params["limit"] = limit
    return params


def _build_attachments_params(*, limit: int | None, page: str | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if limit is not None:
        params["limit"] = limit
    if page is not None:
        params["page"] = page
    return params


def _project_path(project_id: str) -> str:
    return f"{PROJECTS_PATH}/{project_id}"


def _attachments_path(project_id: str) -> str:
    return f"{PROJECTS_PATH}/{project_id}/attachments"


# ---------------------------------------------------------------------------
# Resource classes
# ---------------------------------------------------------------------------


class Projects:
    """Synchronous client for the Projects endpoints."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        organization_ids: StrList | None = None,
        user_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        page: str | None = None,
        limit: int | None = None,
    ) -> OffsetPage[Project]:
        """Fetch one offset-paginated page of projects.

        Args:
            organization_ids: Filter to projects in any of these
                organisations.
            user_ids: Filter to projects owned by any of these users.
            created_at_gte: ``created_at >= value`` (RFC 3339).
            created_at_gt: ``created_at > value`` (RFC 3339).
            created_at_lte: ``created_at <= value`` (RFC 3339).
            created_at_lt: ``created_at < value`` (RFC 3339).
            page: Opaque pagination token from a prior response.
            limit: Maximum results, default 20, max 100.
        """
        body = self._transport.request(
            "GET",
            PROJECTS_PATH,
            params=_build_list_params(
                organization_ids=organization_ids,
                user_ids=user_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                page=page,
                limit=limit,
            ),
        )
        return OffsetPage.from_dict(body, Project.from_dict)

    def iter(
        self,
        *,
        organization_ids: StrList | None = None,
        user_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        limit: int | None = None,
    ) -> Iterator[Project]:
        """Iterate every matching project, auto-paginating.

        Same filters as :meth:`list` except that ``page`` is managed
        by the iterator.
        """
        return iter_all_offset_sync(
            self._transport,
            PROJECTS_PATH,
            Project.from_dict,
            params=_build_list_params(
                organization_ids=organization_ids,
                user_ids=user_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                page=None,
                limit=limit,
            ),
        )

    def get(self, project_id: str) -> ProjectDetail:
        """Fetch the detail view of one project.

        Returns the richer :class:`ProjectDetail` (description,
        instructions, chats_count, attachments_count) in addition to
        every :class:`Project` field.

        Raises:
            NotFoundError: When ``project_id`` does not exist.
            APIError: For any other non-2xx response.
        """
        body = self._transport.request("GET", _project_path(project_id))
        return ProjectDetail.from_dict(body)

    def delete(self, project_id: str) -> None:
        """Hard-delete a project and all its associated data.

        Per spec, the project must have **no attached chats** — the
        server returns 409 / :class:`~claude_compliance_sdk.ConflictError`
        otherwise. Detach or delete the chats first.

        Returns ``None`` on success; the server's confirmation payload
        is discarded.

        Raises:
            ConflictError: When chats are still attached.
            NotFoundError: When ``project_id`` does not exist.
            APIError: For any other non-2xx response.
        """
        self._transport.request("DELETE", _project_path(project_id))

    def list_attachments(
        self,
        project_id: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[ProjectAttachment]:
        """Fetch one offset-paginated page of attachments for a project."""
        body = self._transport.request(
            "GET",
            _attachments_path(project_id),
            params=_build_attachments_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, ProjectAttachment.from_dict)

    def iter_attachments(
        self,
        project_id: str,
        *,
        limit: int | None = None,
    ) -> Iterator[ProjectAttachment]:
        """Iterate every attachment on a project, auto-paginating."""
        return iter_all_offset_sync(
            self._transport,
            _attachments_path(project_id),
            ProjectAttachment.from_dict,
            params=_build_attachments_params(limit=limit, page=None),
        )


class AsyncProjects:
    """Asynchronous client for the Projects endpoints."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        organization_ids: StrList | None = None,
        user_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        page: str | None = None,
        limit: int | None = None,
    ) -> OffsetPage[Project]:
        """Async analogue of :meth:`Projects.list`."""
        body = await self._transport.request(
            "GET",
            PROJECTS_PATH,
            params=_build_list_params(
                organization_ids=organization_ids,
                user_ids=user_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                page=page,
                limit=limit,
            ),
        )
        return OffsetPage.from_dict(body, Project.from_dict)

    def iter(
        self,
        *,
        organization_ids: StrList | None = None,
        user_ids: StrList | None = None,
        created_at_gte: str | None = None,
        created_at_gt: str | None = None,
        created_at_lte: str | None = None,
        created_at_lt: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Project]:
        """Async analogue of :meth:`Projects.iter`."""
        return iter_all_offset_async(
            self._transport,
            PROJECTS_PATH,
            Project.from_dict,
            params=_build_list_params(
                organization_ids=organization_ids,
                user_ids=user_ids,
                created_at_gte=created_at_gte,
                created_at_gt=created_at_gt,
                created_at_lte=created_at_lte,
                created_at_lt=created_at_lt,
                page=None,
                limit=limit,
            ),
        )

    async def get(self, project_id: str) -> ProjectDetail:
        """Async analogue of :meth:`Projects.get`."""
        body = await self._transport.request("GET", _project_path(project_id))
        return ProjectDetail.from_dict(body)

    async def delete(self, project_id: str) -> None:
        """Async analogue of :meth:`Projects.delete`."""
        await self._transport.request("DELETE", _project_path(project_id))

    async def list_attachments(
        self,
        project_id: str,
        *,
        limit: int | None = None,
        page: str | None = None,
    ) -> OffsetPage[ProjectAttachment]:
        """Async analogue of :meth:`Projects.list_attachments`."""
        body = await self._transport.request(
            "GET",
            _attachments_path(project_id),
            params=_build_attachments_params(limit=limit, page=page),
        )
        return OffsetPage.from_dict(body, ProjectAttachment.from_dict)

    def iter_attachments(
        self,
        project_id: str,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[ProjectAttachment]:
        """Async analogue of :meth:`Projects.iter_attachments`."""
        return iter_all_offset_async(
            self._transport,
            _attachments_path(project_id),
            ProjectAttachment.from_dict,
            params=_build_attachments_params(limit=limit, page=None),
        )
