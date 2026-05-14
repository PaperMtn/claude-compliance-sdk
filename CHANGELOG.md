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

### Changed

- `OffsetPage` now exposes `has_more: bool` alongside `next_page` to
  match the wire format symmetrically with `CursorPage` and to give
  callers an explicit "is there more?" flag. Backward-compatible:
  payloads that omit the field default to `False`.

[Unreleased]: https://github.com/PaperMtn/claude-compliance-sdk/compare/HEAD...HEAD
