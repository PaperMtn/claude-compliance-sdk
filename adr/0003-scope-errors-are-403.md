# 0003. Insufficient-scope errors are classified on 403, not 401

- **Status:** Accepted
- **Date:** 2026-06-08
- **Deciders:** @PaperMtn
- **Tags:** error-handling, auth

---

## Context

Phase 0 locked a "401 split" (CONTEXT.md decision 7): the SDK refined
every HTTP 401 into `InvalidAPIKeyError` or `InsufficientScopeError` by
sniffing `error.message` for `scope`/`permission`, and mapped every 403
to a bare `PermissionDeniedError`. `InsufficientScopeError` was a
subclass of `AuthenticationError` (401).

That decision was taken from the Rev K enablement PDF. Decision 17 later
made the **hosted spec** authoritative over the PDF, and the hosted spec
is explicit that insufficient-scope failures are returned as **HTTP 403
with `error.type: "permission_error"`** — for example:

    Missing required scopes. Got: [...] Needed: [...]

A valid key with the wrong scopes returns 403, never 401; the only
documented 401 body is an invalid or revoked key. An Admin key calling a
Compliance-Access-Key-only endpoint also returns 403.

So against the live API the 401 scope-sniff was dead code:
`InsufficientScopeError` could never be produced, and
`except InsufficientScopeError` — recommended in the README and the
exceptions docstring — silently missed every real scope error.

## Decision

**We classify scope failures on 403 and re-parent the exception.** A 401
is always `InvalidAPIKeyError`. A 403 is refined to
`InsufficientScopeError` when `error.type == "permission_error"` (or a
`scope`/`permission` hint appears in the message), and falls back to
`PermissionDeniedError` otherwise. `InsufficientScopeError` becomes a
subclass of `PermissionDeniedError` (403) so its place in the hierarchy
matches its status code.

This supersedes Phase-0 decision 7 ("401 split").

## Consequences

- **Positive:** `except InsufficientScopeError` works against the live
  API; the hierarchy agrees with the wire status; the dead 401 branch is
  gone.
- **Negative — breaking change:** `InsufficientScopeError` is no longer
  an `AuthenticationError`. Callers that caught `AuthenticationError` to
  handle scope problems must catch `PermissionDeniedError` (or
  `InsufficientScopeError`). Acceptable pre-1.0; flagged in the CHANGELOG
  and the README "Authentication" section.
- **Follow-up:** optionally parse the `Got:` / `Needed:` scope lists into
  typed attributes on `InsufficientScopeError` so callers need not
  re-read the message string. Deferred until a caller needs it.

## Alternatives considered

### Keep the 401 split, also sniff 403

- **Why it was attractive:** smaller diff; no hierarchy change.
- **Why it was rejected:** leaves `InsufficientScopeError` mis-parented
  under 401 while it is really a 403, and keeps a dead 401 branch. The
  hierarchy should match the wire status.

### Document the divergence only

- **Why it was attractive:** zero code change.
- **Why it was rejected:** the exception is advertised as catchable and
  is part of the public surface; leaving it unreachable is a correctness
  bug, not a docs gap.

## References

- Hosted spec, error handling:
  <https://platform.claude.com/docs/en/manage-claude/compliance-errors>
- Issue #8.
- Supersedes CONTEXT.md decision 7. Related:
  [ADR-0001](0001-concrete-transports-without-abstract-bases.md),
  [ADR-0002](0002-response-dataclass-parsing-via-dataclasses-fields.md).
