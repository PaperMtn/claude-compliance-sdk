# 0005. Local and remote sessions are separate resource groups

- **Status:** Accepted
- **Date:** 2026-09-04
- **Deciders:** PaperMtn
- **Tags:** resources, sessions, api-surface

---

## Context

The Compliance API exposes session transcripts through two endpoint
families, split by where the session ran. Local sessions
(`/apps/sessions/local`, IDs prefixed `clls_`) are conversations on
users' own machines: Cowork in Claude Desktop, Claude Code, Claude
Science, and Claude for Microsoft 365. Remote sessions
(`/apps/sessions/remote`, IDs prefixed `cse_`) are Cowork sessions
started on claude.ai web or mobile that run in Anthropic-managed cloud
environments.

They look like one noun — "a session" — but the two families differ in
almost every respect that shapes a method signature:

- **Endpoints.** Local has list, retrieve, and messages. Remote has list
  and messages, with **no retrieve**.
- **Filters.** Local takes only `created_at.gte`, `created_at.lt`, and
  `updated_at.gte`, with no organisation or user filter at all. Remote
  takes `organization_ids[]` (max 500), `user_ids[]` (1–10), and all
  four `created_at` comparators, with no `updated_at` filter.
- **Payloads.** Remote sessions carry `status`, `agent_id`,
  `started_by_user`, and `claude_project_id`; local sessions carry none
  of those and add `workspace_id`. Local messages carry `model` and a
  three-variant `provenance` union; remote messages carry
  `sent_by_user_id` and a flat `content_unavailable` boolean.
- **Rate limits.** Remote endpoints carry a second request budget on top
  of the shared 600 rpm; local endpoints do not.
- **Errors.** Local has two conditions with no remote equivalent (see
  [ADR-0006](0006-message-based-error-refinement-for-local-sessions.md)),
  and remote has one — a `pending` session 404ing until provisioning
  completes — with no local equivalent.

Every resource group in the SDK so far maps one-to-one onto a noun in
the API. This is the first place that mapping does not obviously hold.

## Decision

We will model local and remote sessions as two resource groups,
`client.local_sessions` and `client.remote_sessions`, each with its own
dataclasses. Only `SessionUser` is shared, because the `{id,
email_address}` shape and its null-email semantics really are identical
across both.

A single `client.sessions` group would need a method surface that is the
union of both families, where roughly half the parameters return 400
depending on which family the caller is actually hitting — a
`user_ids` filter that silently does nothing on local, an `updated_at`
filter that silently does nothing on remote, and a `get()` that only
works for one of them. Splitting makes the shapes honest: every
parameter on every method is a parameter that endpoint accepts. It also
matches how the docs present them, which is the vocabulary users will
arrive with.

## Consequences

- **Positive** — no invalid parameter combinations are reachable through
  the typed surface. Each group's docstrings describe one rate-limit
  story, one error catalogue, and one pagination contract. Adding a
  third family later (Claude Code on the web is explicitly *not* a
  remote session today) is additive.
- **Negative** — a caller who wants "every session in the org" must walk
  two groups and merge, and there is no single type to hold the result.
  Two near-identical transcript dataclasses exist where one might have
  done. Twelve resource-group attributes on the client instead of
  eleven.
- **Follow-ups** — `README.md` and the docs site need to explain the
  local/remote split up front, because "which one has my Claude Code
  sessions?" is the first question any user will have. The
  `product_surface` mapping table from the docs is the clearest answer
  and should be reproduced.

## Alternatives considered

### One `sessions` group with a `kind` parameter

- **Why it was attractive:** one entry point, one mental model, and a
  natural place for a future "all sessions" convenience method.
- **Why it was rejected:** it pushes the split from the type system into
  runtime validation. Every method would have to document which
  parameters apply to which kind, and the obvious mistakes (filtering
  local sessions by user) would fail at runtime instead of never being
  expressible.

### One group, with remote-only methods raising on local IDs

- **Why it was attractive:** the ID prefixes (`clls_` vs `cse_`) make
  dispatch trivial, so the SDK could route automatically.
- **Why it was rejected:** it makes the SDK an authority on ID formats
  that the docs explicitly call opaque and subject to change without
  notice. It also does nothing about the diverging filter sets, which is
  the larger half of the problem.

## References

- `spec-snapshots/2026-09-04/compliance-sessions.md` — the product /
  endpoint-family / `product_surface` mapping table.
- `spec-snapshots/2026-09-04/api-apps.md` — the two families' parameter
  and response schemas.
- [ADR-0006](0006-message-based-error-refinement-for-local-sessions.md)
  — the local-only error conditions.
