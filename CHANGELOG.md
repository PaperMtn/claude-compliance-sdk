# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Session transcripts** — two new resource groups covering Cowork,
  Claude Code, Claude Science, and Claude for Microsoft 365:
  - `client.local_sessions` — sessions on users' machines
    (`list`, `iter`, `get`, `list_messages`, `iter_messages`).
  - `client.remote_sessions` — Cowork sessions running in
    Anthropic-managed cloud environments (`list`, `iter`,
    `list_messages`, `iter_messages`; the API exposes no retrieve-one).

  New types: `LocalSession`, `LocalSessionMessage`,
  `LocalSessionTranscript`, `RemoteSession`, `RemoteSessionMessage`,
  `RemoteSessionTranscript`, and the shared `SessionUser`. Message
  `content` blocks stay raw dicts so block types that have not shipped
  yet pass through untouched. See ADR-0005 for why the two families are
  separate groups.
- `organizations.get_settings(organization_id)` — the effective
  settings in force for one linked organisation, for attesting that
  retention windows, redaction, SSO enforcement, and the IP allowlist
  match your baseline without Console access. New types
  `OrganizationSettings` and `ComplianceApiKey`. Setting rows stay raw
  dicts keyed on `type`; there are 50+ names and the list grows. Note
  that a **missing** row means "administrators here cannot change it",
  not "off".
- `projects.list_collaborators()` / `iter_collaborators()` — the users,
  groups, organisation-wide grants, and organisation-role grants on a
  project, as a four-way union discriminated on
  `ProjectCollaborator.type`.
- `project_documents.get_metadata(document_id)` — a document's
  metadata without its body, so enumerating documents no longer means
  downloading every one. New type `ProjectDocumentMetadata`.
- `activities.list()` / `iter()` accept `exclude_activity_types` (the
  inverse of `activity_types`; the server rejects passing both) and
  `order` (`"asc"` / `"desc"`).
- `client.rate_limit_status` — the server's last reported request
  budget, read from the `anthropic-ratelimit-*` response headers, as a
  new public `RateLimitSnapshot`. Use `remaining` to pace your own
  workers: the 600 rpm budget is shared across every key under the
  parent organisation, so it accounts for traffic this client cannot
  see.
- `LocalSessionsUnavailableError` (subclass of `NotFoundError`) — the
  404 meaning "local sessions are off for this parent organisation",
  which does *not* mean a session is gone. Keep your queued IDs.
- `LocalSessionsRetentionUnavailableError` (subclass of
  `InternalServerError`) — the one local-session 503 that is not
  transient. It is excluded from retry. See ADR-0006.
- `organizations.iter()` — auto-paginating sibling to
  `organizations.list()`, matching every other paginated resource.
- `chats.list()` / `chats.iter()` accept `order_by` (`"created_at"` or
  `"updated_at"`).
- `anthropic_version` keyword on both clients, defaulting to
  `"2023-06-01"`. Pass `None` to suppress the header.
- `User.organization_role` — the built-in membership level, previously
  arriving in `extra`.
- `ProjectAttachment.md5`, `.size_bytes`, and `.updated_at` — previously
  arriving in `extra`.
- `examples/session_export.py` — export Cowork, Claude Code, and
  Claude Science transcripts over a time window, one JSON file per
  session. Handles the cases worth knowing about: unavailable message
  content is exported rather than dropped, non-transient retention
  failures skip a session instead of blocking the walk, and pending
  remote sessions are left for a later run.
- `scripts/snapshot_spec.py` and `spec-snapshots/<date>/` — committed
  markdown snapshots of the hosted docs, so upstream API changes are
  visible as a `git diff`.

### Changed

- **BREAKING:** `organizations.list()` returns `OffsetPage[Organization]`
  instead of `list[Organization]`. `GET /v1/compliance/organizations` is
  now paginated, and the old shape silently discarded every page after
  the first. Replace `for org in client.organizations.list()` with
  `client.organizations.iter()`, or read `.list().data` for a single
  page.
- **BREAKING:** the SDK now sends `anthropic-version: 2023-06-01` on
  every request, reversing the Phase-0 decision to omit it. The hosted
  docs require it and every published example sends it. See ADR-0004.
- **BREAKING:** `chats.list()` and `chats.iter()` no longer require
  `user_ids`. Omitting it queries every chat under the parent
  organisation, which is the documented way to run an incremental
  export. A supplied list is still validated to 1–10 entries. Field
  order on the `Chat` and `Project` dataclasses changed as a result of
  the nullability fixes below, which matters only if you construct them
  positionally.
- `Chat.model` is now `str | None`; the API returns `null` for legacy
  chats that never had a model recorded.
- `Chat.organization_id` and `Project.organization_id` are now optional
  and documented as deprecated by the API in favour of
  `organization_uuid`.

### Fixed

- The client now throttles on the server's reported budget. When a
  response says `anthropic-ratelimit-requests-remaining: 0`, the next
  request waits for the stated reset instead of being spent to
  discover a guaranteed 429. Honoured even when `rate_limit_rpm=0` —
  that flag opts out of the *local* window, not the shared server
  limit. See ADR-0007.
- `Retry-After` is now a **floor** on the retry delay rather than
  replacing the backoff schedule. The remote-session endpoints' second
  rate-limit budget always answers `retry-after: 1` as a *minimum*
  wait, so taking it literally retried three times in three seconds
  and exhausted the retry allowance without ever waiting long enough
  to help. A longer, realistic hint from the shared budget still
  dominates the early attempts.
- `OffsetPage.has_more` is now derived from `next_page` when the payload
  omits the field. The session endpoints return `next_page` with no
  `has_more`, so reading `.has_more` previously reported "no further
  pages" while handing back a live cursor. Auto-pagination was already
  correct — it stops on `next_page`, not `has_more`.
- A 503 whose message reports that retention overrides cannot be
  evaluated is no longer retried. It depends on organisation settings
  rather than load, so the previous behaviour spent the whole retry
  budget on a failure that fails identically every time.

### Changed

- **Documentation** — the key model is now described the right way
  round. A **Compliance Access Key** (`sk-ant-api01-...`, created in
  claude.ai) reaches every endpoint and is the primary credential; an
  **Admin API key** reaches the Activity Feed *only* and 403s
  elsewhere. Previously the README and the `activities` docstrings
  implied the Activity Feed was admin-key territory, which is
  backwards. All four live scopes are now documented, along with the
  retirement of `read:compliance_org_settings` on 2026-06-30.
- The client now reads `ANTHROPIC_COMPLIANCE_ACCESS_KEY`, the name the
  hosted docs use. The legacy `ANTHROPIC_COMPLIANCE_API_KEY` this SDK
  shipped with is still honoured as a fallback, so existing
  deployments keep working; the new name wins when both are set.
- Retry backoff defaults moved from 0.5s base / 20s cap to **1s base /
  60s cap**, matching the fallback the API documents for a 429 with no
  `Retry-After` header. Retries are correspondingly slower.

### Deprecated

- Combining `user_ids` with any `updated_at` bound on `chats.list()` /
  `chats.iter()` now raises a `DeprecationWarning`. The API rejects the
  combination with HTTP 400 after 2026-09-22; use an organisation-wide
  `order_by="updated_at"` walk instead.

### Added

- `Message.generated_files` — assistant tool-use file outputs are now a
  typed field on chat messages, alongside `files` and `artifacts`,
  instead of arriving in `extra`. (#7)

### Changed

- **BREAKING:** scope failures are now classified on HTTP 403, matching
  the live API. `InsufficientScopeError` is a subclass of
  `PermissionDeniedError` (403), not `AuthenticationError` (401); a 401
  is always `InvalidAPIKeyError`. Callers that caught
  `AuthenticationError` to handle scope problems must catch
  `PermissionDeniedError` (or `InsufficientScopeError`). See ADR-0003.
  (#8)
- **Documentation** — reworked the generated API-reference site for an
  end-user audience: stripped internal references (project phases, ADR
  numbers, `CONTEXT.md` / `CLAUDE.md`, the pinned spec revision) out of
  docstrings, moved "spec" wording to "API", retired the `Rev K` pin in
  favour of tracking the hosted spec, and trimmed the pagination page to
  the public page classes. Added a prominent docs-site link to the
  README.
- **Documentation** — clarified that `rate_limit_rpm` is best-effort and
  per-client; the live API enforces 600 RPM per *parent organisation*,
  shared across all keys, which a per-client limiter cannot enforce.
  (#11)

### Removed

- Architecture decision records are no longer published to the docs
  site. They remain in the repo under `adr/` for contributors.

### Fixed

- Honour the server's `x-should-retry` response header: a retryable
  status carrying `x-should-retry: false` is no longer retried (the
  failure is deterministic and fails identically every attempt), and
  `x-should-retry: true` forces a retry — both still gated on method
  safety. (#9)
- Treat HTTP 529 (Overloaded) as transient and retry it with
  exponential backoff, alongside 502/503/504. (#10)

## [0.1.0] - 2026-05-18

Initial release. Targets Compliance API spec revision Rev K
(2026-05-04).

### Added

- **Public clients** — `ComplianceClient` (sync) and
  `AsyncComplianceClient` (async). Identical resource surface on both;
  swap one for the other and add `await` to switch styles.
- **Resource groups** covering every Rev K endpoint:
  - `activities` — cursor-paginated Activity Feed list / iter.
  - `organizations` — unpaginated org list, plus paginated users
    per org.
  - `projects` — list, get (detail), delete, and attachment listing.
  - `project_documents` — fetch document text content and delete.
  - `chats` — cursor list of chats, combined chat-with-messages
    fetch, message iteration, and delete.
  - `files` — user-uploaded file metadata, download, delete.
  - `generated_files` — assistant tool-use outputs (download only;
    not deletable per spec).
  - `artifacts` — versioned text artifacts (download only).
  - `roles` — org-scoped role list, fetch, and permissions list.
  - `groups` — group list, fetch, and member list.
- **Pagination** — `CursorPage[T]` (used by the Activity Feed, Chats,
  Messages) and `OffsetPage[T]` (everything else). Every paginated
  resource exposes both `.list()` (one page) and `.iter()`
  (auto-paginate) methods.
- **Downloads** — three resource groups (`files`, `generated_files`,
  `artifacts`) share the same trio:
  - `.download(id)` — eager, bounded by `max_download_bytes` (default
    100 MiB). Raises `FileTooLargeError` when the cap is exceeded.
  - `.download_to_file(id, path)` — streamed to disk, unbounded.
  - `.download_stream(id)` — yields chunks for caller-managed
    streaming.
- **Typed exception hierarchy** rooted at `ComplianceClientError`.
  HTTP failures under `APIError` map every documented status code to
  a typed subclass: `BadRequestError`, `InvalidAPIKeyError` /
  `InsufficientScopeError` (a best-effort split of 401),
  `PermissionDeniedError`, `NotFoundError`, `ConflictError`,
  `RateLimitError` (carrying `retry_after`), `APIStatusError`,
  `InternalServerError`. Transport-level failures live under
  `APIConnectionError` / `APITimeoutError`. Every error carries
  `status_code`, `request_id`, `error_type`, `error_message`, and
  the raw response body.
- **Resilience** — exponential-backoff retry on 429 / 5xx / connect
  errors with `Retry-After` honoured, plus a client-side
  sliding-window rate limiter sized to the server's 600 RPM cap.
  Both tunable / disable-able via `max_retries` and
  `rate_limit_rpm`.
- **Typed responses** — every response is a plain dataclass.
  Activity-type-specific fields and any future-spec additions are
  preserved in an `extra: dict` so the SDK does not break when the
  spec grows.
- **Runnable examples** — `examples/activity_audit.py`,
  `examples/ediscovery_export.py`, and `examples/file_pull.py`
  demonstrate the spec's headline compliance use cases end-to-end.
- **Documentation site** at
  [papermtn.github.io/claude-compliance-sdk](https://papermtn.github.io/claude-compliance-sdk/).

[Unreleased]: https://github.com/PaperMtn/claude-compliance-sdk/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/PaperMtn/claude-compliance-sdk/releases/tag/v0.1.0
