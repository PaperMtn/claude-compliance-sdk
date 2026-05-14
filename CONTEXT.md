# CONTEXT.md

The domain language, architecture, and decision history of
**claude-compliance-sdk**. Read this before designing anything new — it
exists so the project's vocabulary stays consistent across PRs and so
locked design decisions are not silently revisited.

This file is the input to architecture tools (e.g. the
`improve-codebase-architecture` skill) and to new contributors who need
to come up to speed quickly. Keep it short and precise. If a concept
needs more than a paragraph, link out to an ADR under `docs/adr/`.

---

## 1. What this SDK wraps

The **Anthropic Compliance API** is the read-side companion to Anthropic's
Claude.ai product. It lets compliance teams at Claude Enterprise
organisations export and audit user activity: who chatted with Claude,
what they sent, what Claude generated, and what files were uploaded or
produced. It is the data plane for eDiscovery, DLP, audit, and
incident-response use cases.

The SDK targets **spec revision K, dated 2026-05-04** (PDF at the repo
root). When the spec and this document disagree, the spec wins — file
an issue.

The SDK does **not** wrap the regular Anthropic Messages API; for that,
use the official `anthropic` Python SDK.

---

## 2. Domain language

These terms appear throughout the code, tests, and docs. Use them
consistently — do not invent synonyms.

### Identities

- **Organization** — a Claude Enterprise tenant. Identified by `org_uuid`.
  An API key is scoped to a single organisation.
- **User** — a human member of an organisation. The "actor" in audit
  events.
- **Role** — a named bundle of permissions inside an organisation
  (RBAC). Roles list their permissions; users hold roles.
- **Group** — a named collection of users used for permission
  assignment.

### Activity

- **Activity** — a single audit event (user login, chat created, file
  uploaded, etc.). The **Activity Feed** is the cursor-paginated list
  of activities for an organisation.
- **Actor** — the user who performed an activity.
- **Activity type** — a string enum identifying the kind of event.

### Conversations

- **Chat** — a single conversation between a user and Claude. Has an
  `id`, an owning user, and zero or more messages.
- **Message** — a single turn within a chat (user prompt, assistant
  reply, tool result). Cursor-paginated within a chat.
- **Project** — a named container that groups chats, project documents,
  and project files for a single user. Deleting a project with chats
  still attached returns `409` — the user must detach or delete the
  chats first.
- **Project document** — a plain-text reference document attached to a
  project (custom instructions, knowledge snippets). Distinct from
  project files.

### Binary content

Three distinct backends, three distinct IDs, three distinct lifecycles:

- **User file** (`claude_file_id`) — uploaded by a user as a chat
  attachment. Has metadata, eager download, and a `DELETE` endpoint.
- **Generated file** (`claude_gen_file_id`) — produced by the assistant
  inside a chat. Lives in the per-conversation **Filestore**. Has
  metadata and download. **No delete.**
- **Artifact** (`artifact_version_id`) — a versioned text artifact
  (code, markdown, structured output) emitted by Claude as part of a
  response. Download only — no metadata endpoint, no delete.

Treat these as three separate resources, not three flavours of one. The
spec, the IDs, and the lifecycles all differ.

### Auth

- **Compliance Access Key** (`sk-ant-api01-…`) — issued from Claude.ai.
  Grants access to most resources except the Activity Feed.
- **Admin Key** (`sk-ant-admin01-…`) — issued from the Anthropic
  Console. **Only valid on the Activity Feed.** All other endpoints
  reject it.

The SDK does **not** check the key prefix locally before calling an
endpoint. The server enforces. The client labels the resulting `401`
as either `InvalidAPIKeyError` (key is wrong) or
`InsufficientScopeError` (key is valid but lacks scope) by parsing
`error.message` best-effort.

### Pagination

Two styles in the spec; the SDK exposes both, plus an `.iter()` helper
on every paginated resource.

- **Cursor pagination** — used by Activity Feed, Chats, and Messages.
  Page payload includes `first_id`, `last_id`, and `has_more`. Next
  page is `?after_id=<last_id>`; previous is `?before_id=<first_id>`.
  Modelled in code as `CursorPage[T]` / `AsyncCursorPage[T]`.
- **Offset pagination** — used by everything else. Page payload
  includes an opaque `next_page` token. Modelled as `OffsetPage[T]` /
  `AsyncOffsetPage[T]`.

`GET /organizations` is **unpaginated** and errors when the result
would exceed 1,000 organisations. The SDK returns `list[Organization]`
directly and surfaces the server error untouched.

### Errors

All API errors share the same JSON shape:

```json
{ "error": { "type": "...", "message": "..." } }
```

The SDK maps status codes to a typed hierarchy rooted at
`ComplianceClientError`. Every error carries the HTTP status, the
`request_id` header, the server's `error.type`, the server's
`error.message`, and the raw body. See `exceptions.py` for the full
tree.

### Rate limiting

The server enforces **600 requests per minute per API key**. The SDK
applies a client-side sliding-window limiter at the same rate by
default (`rate_limit_rpm=600`) to smooth bursty callers, but the
limiter is not a substitute for handling 429s — those are retried by
the transport with `Retry-After` honoured over the backoff schedule.
Set `rate_limit_rpm=0` to disable the limiter and rely purely on
server enforcement.

---

## 3. Architecture

```
claude_compliance_sdk/
├── __init__.py                 # re-exports clients, errors, page classes
├── client.py                   # ComplianceClient (sync entry point)
├── async_client.py             # AsyncComplianceClient (async entry point)
├── exceptions.py               # error hierarchy + APIError.from_response
├── version.py
├── py.typed
├── _internal/                  # not part of the public surface
│   ├── transport.py            # httpx-backed SyncTransport / AsyncTransport
│   ├── retry.py                # RetryPolicy w/ Retry-After
│   ├── rate_limit.py           # sliding-window rate limiter
│   ├── pagination.py           # CursorPage, OffsetPage, iter_all helpers
│   ├── parsing.py              # parse_with_extra for response dataclasses
│   └── downloads.py            # eager / streamed / to-file download helpers
└── resources/                  # one module per resource group
    ├── activities.py
    ├── artifacts.py
    ├── chats.py
    ├── files.py
    ├── generated_files.py
    ├── groups.py
    ├── organizations.py
    ├── project_documents.py
    ├── projects.py
    └── roles.py
```

### Layering rules

- **Resources depend on transport, not on each other.** A resource
  group never imports another resource group. If two resources need the
  same helper, it lives in `_internal/`.
- **Public clients are thin.** `ComplianceClient` and
  `AsyncComplianceClient` resolve configuration, construct the
  transport, instantiate resource groups, and own lifecycle (`close()`,
  `aclose()`). They contain no request logic of their own.
- **Sync and async share data, not I/O.** Dataclasses, pagination page
  shapes, error classes, and constants are reused across both clients.
  Anything that performs I/O is duplicated — once for `httpx.Client`,
  once for `httpx.AsyncClient`.
- **`_internal/` is private.** Names under `_internal/` are not
  considered stable. Public callers must import from
  `claude_compliance_sdk` directly.

---

## 4. Design decisions (decision log)

The decisions that shape the SDK's public surface. Locked decisions are
not silently revisited inside a PR — if you want one revisited, open an
issue first.

| #   | Decision                                                                                                                                              | Date       | Status |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ |
| 1   | License: GPL-3.0-or-later.                                                                                                                            | 2026-05-13 | locked |
| 2   | Hand-written, no code-gen.                                                                                                                            | 2026-05-13 | locked |
| 3   | Plain dataclasses, no Pydantic. Unknown response fields preserved in `extra`.                                                                         | 2026-05-13 | locked |
| 4   | UX patterned on `slack_sdk`, not the official `anthropic` SDK.                                                                                        | 2026-05-13 | locked |
| 5   | Single runtime dependency: `httpx`. New runtime deps require an issue first.                                                                          | 2026-05-13 | locked |
| 6   | Sync + async clients with identical public surface.                                                                                                   | 2026-05-13 | locked |
| 7   | 401 split into `InvalidAPIKeyError` / `InsufficientScopeError` via best-effort `error.message` parse.                                                  | 2026-05-13 | locked |
| 8   | No client-side admin-key prefix gate. Let the server 401.                                                                                              | 2026-05-13 | locked |
| 9   | Auto-pagination via a separate `.iter()` method per resource, not a `flag` on `.list()`.                                                              | 2026-05-13 | locked |
| 10  | Coverage tracked locally with `pytest-cov`. CI enforces `--cov-fail-under=90`. No Codecov.                                                            | 2026-05-13 | locked |
| 11  | Pre-commit hooks required. `.pre-commit-config.yaml` is the source of truth; CI mirrors it.                                                           | 2026-05-13 | locked |
| 12  | git-flow branch model. PRs target `develop`. Releases cut from `develop` to `main`.                                                                   | 2026-05-13 | locked |
| 13  | Three binary backends (user files / generated files / artifacts) modelled as three resource groups, not one.                                          | 2026-05-13 | locked |
| 14  | `user_ids[]` length on `GET /apps/chats` validated client-side (1–10). Other server-side rules not duplicated.                                        | 2026-05-13 | locked |
| 15  | Concrete transports without abstract bases. ABCs deleted; resources type-hint `SyncTransport` / `AsyncTransport` directly. See [ADR-0001](adr/0001-concrete-transports-without-abstract-bases.md). | 2026-05-13 | locked |
| 16  | Response dataclass parsing via `parse_with_extra(cls, body)` over `dataclasses.fields(cls)`. No per-field coercion, no nested-type recursion. See [ADR-0002](adr/0002-response-dataclass-parsing-via-dataclasses-fields.md). | 2026-05-13 | locked |

Promote any of these to a full ADR (`docs/adr/NNNN-…md`) once it acquires
a real follow-up discussion. The table is the index; the ADR is the
extended argument.

---

## 5. Spec anchors

Quick reference points lifted from the spec PDF (Rev K, 2026-05-04). If
any of these change in a future spec rev, update them here and bump the
"targets spec revision" line at the top.

- **Rate limit:** 600 requests per minute per API key.
- **Two key types:** `sk-ant-api01-` (Compliance Access — most resources)
  and `sk-ant-admin01-` (Admin — only valid on the Activity Feed).
- **Two pagination styles:** cursor (`after_id` / `before_id`) on
  Activity Feed, Chats, Messages; opaque `page` token on everything
  else.
- **`GET /apps/chats`** requires `user_ids[]`, length 1–10.
- **`DELETE /apps/projects/{id}`** returns `409` when chats are still
  attached.
- **`GET /organizations`** has no pagination; errors when the result
  would exceed 1,000 organisations.
- **Error shape:** `{"error": {"type": "...", "message": "..."}}`.
- **Request headers:** only `x-api-key` is required by the spec. The
  Messages API `anthropic-version` header is **not** used by the
  Compliance API — sending it routes the request to a different
  surface and 404s the `/v1/compliance/*` paths.
