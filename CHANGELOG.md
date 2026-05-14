# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project scaffolding: Poetry configuration, dependency pinning, tooling
  config (Black, isort, Pylint, mypy, pre-commit), src/tests layout, and
  documentation skeleton.
- Exception hierarchy (`claude_compliance_sdk.exceptions`) rooted at
  `ComplianceClientError`. HTTP errors under `APIError` cover 400, 401
  (split into `InvalidAPIKeyError` / `InsufficientScopeError` by
  best-effort message parse), 403, 404, 409, 429 (carries
  `retry_after`), other 4xx via `APIStatusError`, and 5xx via
  `InternalServerError`. Transport errors are `APIConnectionError` and
  `APITimeoutError`. `APIError.from_response(...)` builds the right
  subclass from a status code, response headers, and decoded body. All
  classes are re-exported from `claude_compliance_sdk`.
- HTTP transport (`SyncTransport`, `AsyncTransport` in
  `claude_compliance_sdk._internal.transport`) backed by `httpx`. Single
  `request()` entry point per transport handles header injection
  (`x-api-key`, `anthropic-version`, SDK `User-Agent`), error mapping
  via `APIError.from_response`, `request_id` propagation, and
  streaming responses for the upcoming download helpers.
  `ComplianceClient` and `AsyncComplianceClient` now construct the real
  transports and their `close()` / `aclose()` delegate accordingly.
- Retry policy (`claude_compliance_sdk._internal.retry.RetryPolicy`)
  with exponential backoff (0.5s base, 20s cap, ±25% jitter), bounded
  by `max_retries`. Retries 429 / 500 / 502 / 503 / 504 for safe
  methods, `httpx.ConnectError` for any method, `httpx.ReadTimeout`
  only for safe methods. Honours `Retry-After` on 429 over the
  backoff schedule.
- Client-side rate limiter
  (`claude_compliance_sdk._internal.rate_limit.SlidingWindowLimiter`
  / `AsyncSlidingWindowLimiter`) with a 60-second sliding window
  sized by `rate_limit_rpm`. Defaults to 600 RPM to match server-side
  enforcement; `rate_limit_rpm=0` disables it.
- Pagination primitives in
  `claude_compliance_sdk._internal.pagination`: generic dataclasses
  `CursorPage[T]` and `OffsetPage[T]` plus four iteration helpers
  (`iter_all_cursor_sync`, `iter_all_cursor_async`,
  `iter_all_offset_sync`, `iter_all_offset_async`) that resources'
  `.iter()` methods will plug into in Phase 3. `CursorPage`,
  `OffsetPage`, `AsyncCursorPage`, and `AsyncOffsetPage` are
  re-exported from `claude_compliance_sdk`.
- Activities resource group (`Activities`, `AsyncActivities`) wrapping
  `GET /v1/compliance/activities`. `.list(...)` returns
  `CursorPage[Activity]`; `.iter(...)` auto-paginates. Filters cover
  `organization_ids`, `actor_ids`, `activity_types`, the four
  `created_at.*` comparators, `after_id` / `before_id`, and `limit`.
  `Activity` is a plain dataclass with type-specific fields preserved
  in `extra: dict` and re-exported from `claude_compliance_sdk`.
- Organizations resource group (`Organizations`, `AsyncOrganizations`).
  `.list()` returns `list[Organization]` for the unpaginated
  `GET /v1/compliance/organizations` endpoint; the spec's 1,000-org
  cap surfaces as `InternalServerError` rather than being papered
  over. `.list_users(org_uuid, ...)` returns `OffsetPage[User]` and
  `.iter_users(org_uuid, ...)` auto-paginates over
  `GET /v1/compliance/organizations/{org_uuid}/users`. `Organization`
  and `User` dataclasses are re-exported from `claude_compliance_sdk`.
- Projects resource group (`Projects`, `AsyncProjects`) wrapping
  `GET /v1/compliance/apps/projects` (offset-paginated `.list()` /
  `.iter()`), `GET /v1/compliance/apps/projects/{project_id}`
  (`.get()` → `ProjectDetail`),
  `DELETE /v1/compliance/apps/projects/{project_id}` (`.delete()` →
  `None`; 409 surfaces as `ConflictError` when chats are still
  attached), and
  `GET /v1/compliance/apps/projects/{project_id}/attachments`
  (`.list_attachments()` / `.iter_attachments()` returning
  `ProjectAttachment` items discriminated by ``type``
  `"project_file"` / `"project_doc"`). `Project`, `ProjectDetail`,
  and `ProjectAttachment` dataclasses are re-exported.
- Project Documents resource group (`ProjectDocuments`,
  `AsyncProjectDocuments`) wrapping
  `GET /v1/compliance/apps/projects/documents/{document_id}`
  (`.get()` → `ProjectDocument` with full text content) and the
  matching `DELETE` (`.delete()` → `None`). `ProjectDocument` is
  re-exported.
- Chats resource group (`Chats`, `AsyncChats`) wrapping
  `GET /v1/compliance/apps/chats` (cursor-paginated `.list()` /
  `.iter()` with the full filter set; `user_ids[]` is **required**
  and validated client-side as 1–10 IDs per locked decision 14
  before the request is sent — raises `ValueError` otherwise),
  `GET /v1/compliance/apps/chats/{chat_id}/messages` (`.get()` →
  `ChatMessagesPage` with the chat metadata plus one cursor-paginated
  page of messages; `.iter_messages()` walks every message across
  pages), and `DELETE /v1/compliance/apps/chats/{chat_id}`
  (`.delete()` → `None`). `Chat`, `Message`, and `ChatMessagesPage`
  dataclasses are re-exported from `claude_compliance_sdk`.
- Files trio — three resource groups sharing the same download
  ergonomics:
  - **Files / AsyncFiles** (user uploads, deletable). `.get()` →
    `File` metadata; `.download()` → `bytes` bounded by
    `max_download_bytes`; `.download_to_file(...)` streams to disk
    unbounded; `.download_stream(...)` yields chunks to the caller;
    `.delete()` → `None`.
  - **GeneratedFiles / AsyncGeneratedFiles** (assistant tool-use
    outputs in the per-conversation Filestore, **not deletable** —
    no `DELETE` endpoint). Same `get` / `download` trio, no
    `delete`.
  - **Artifacts / AsyncArtifacts** (versioned text artifacts; **no
    metadata endpoint, not deletable** per spec). Download trio
    only — no `.get()`, no `.delete()`.
- New `_internal/downloads.py` module holding the shared
  `download_eager_*`, `download_to_file_*`, and `download_stream_*`
  helpers so the three resource modules stay thin. Eager downloads
  check `Content-Length` up-front and fall back to a streamed byte
  tally when the header is absent.
- New `FileTooLargeError` exception (subclass of
  `ComplianceClientError`) raised when an eager `.download()` would
  exceed `max_download_bytes`. Carries the configured `max_bytes`
  cap and the reported `size_bytes` when the server supplied a
  `Content-Length`. Re-exported from `claude_compliance_sdk`.
- `File` and `GeneratedFile` dataclasses are re-exported.
- Roles resource group (`Roles`, `AsyncRoles`) wrapping the
  org-scoped roles endpoints:
  `GET /v1/compliance/organizations/{org_uuid}/roles`
  (offset-paginated `.list(org_uuid, ...)` / `.iter(org_uuid, ...)`),
  `GET /v1/compliance/organizations/{org_uuid}/roles/{role_id}`
  (`.get(org_uuid, role_id)`), and
  `GET /v1/compliance/organizations/{org_uuid}/roles/{role_id}/permissions`
  (`.list_permissions(...)` / `.iter_permissions(...)`). `Role` and
  `Permission` dataclasses are re-exported.
- Groups resource group (`Groups`, `AsyncGroups`) wrapping
  `GET /v1/compliance/groups` (`.list()` / `.iter()`),
  `GET /v1/compliance/groups/{group_id}` (`.get()`), and
  `GET /v1/compliance/groups/{group_id}/members`
  (`.list_members()` / `.iter_members()`). `Group` and `GroupMember`
  dataclasses are re-exported. Group sources are tagged ``"direct"``
  for manually-created groups or ``"scim"`` for groups pushed by an
  IdP via directory sync.

### Removed

- The SDK no longer sends the `anthropic-version` request header by
  default. It was a Messages API convention we incorrectly carried
  into the Compliance transport; the Rev K spec only requires
  `x-api-key`, and production `/v1/compliance/*` paths route to a
  different surface and 404 when the version header is present.
  Removed the `anthropic_version` kwarg from `ComplianceClient` /
  `AsyncComplianceClient` and the `DEFAULT_ANTHROPIC_VERSION`
  constant. Callers who were relying on the kwarg should drop it;
  there is no functional replacement.

### Changed

- `OffsetPage` now exposes `has_more: bool` alongside `next_page` to
  match the wire format symmetrically with `CursorPage` and to give
  callers an explicit "is there more?" flag. Backward-compatible:
  payloads that omit the field default to `False`.

[Unreleased]: https://github.com/PaperMtn/claude-compliance-sdk/compare/HEAD...HEAD
