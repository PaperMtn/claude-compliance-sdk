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

[Unreleased]: https://github.com/PaperMtn/claude-compliance-sdk/compare/HEAD...HEAD
