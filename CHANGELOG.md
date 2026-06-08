# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `Message.generated_files` — assistant tool-use file outputs are now a
  typed field on chat messages, alongside `files` and `artifacts`,
  instead of arriving in `extra`. (#7)

### Changed

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
