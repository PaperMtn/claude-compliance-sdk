# CLAUDE.md

Instructions for Claude (and Claude Code agents) working in this repo.
Read this before making changes. Human-authored conventions and locked
design decisions live here so the model does not re-litigate them every
session.

## Project identity

This repo is **claude-compliance-sdk**, a community-maintained Python
SDK for the Anthropic Compliance API. It is published on PyPI as
`claude-compliance-sdk` and imported as `claude_compliance_sdk`.

Key facts:

- **Unofficial.** Not produced or endorsed by Anthropic.
- **Hand-written.** No code generation. Do not propose generating from
  an OpenAPI spec.
- **No Pydantic.** Plain dataclasses with an `extra: dict` for unknown
  fields. Do not introduce Pydantic, marshmallow, or any other schema
  library.
- **Slack-SDK UX parity.** When designing surfaces, mirror `slack_sdk`
  rather than the official `anthropic` SDK or any code-gen output.
- **Dependency-light.** `httpx` is the only runtime dependency. Adding
  another requires a maintainer discussion in an issue first.

## Locked design decisions

These were settled in Phase 0 (2026-05-13). Do not silently revise them.
If a task seems to require revisiting one, surface the conflict to the
maintainer first.

- **License:** GPL-3.0-or-later. All source files inherit the project
  license; do not add per-file headers unless asked.
- **401 split:** keep `InvalidAPIKeyError` and `InsufficientScopeError`
  as subclasses of `AuthenticationError`. Detect via best-effort parse
  of `error.message`. Server is the source of truth; the client only
  labels.
- **Admin-key local gate:** **skipped.** Do not pre-flight check the
  key prefix before calling admin-only endpoints. Let the server 401
  and surface that as `InvalidAPIKeyError` / `InsufficientScopeError`.
- **Auto-pagination:** exposed as a separate `.iter()` method on each
  paginated resource, not as a flag on `.list()`.
- **Coverage:** local only via `pytest-cov`. CI gates at
  `--cov-fail-under=90`. No Codecov.
- **Pre-commit hooks:** required. `.pre-commit-config.yaml` is the source
  of truth for hooks; CI runs the same checks.
- **Server enforces, client labels.** Cheap input-shape checks may live
  client-side (`user_ids` length 1–10 on `GET /apps/chats`). Anything
  the server already validates (scopes, key type, "cannot delete project
  with attached chats") is **not** duplicated.

For a full decision log see **CONTEXT.md** § Design decisions.

## Architecture in one paragraph

`ComplianceClient` (sync) and `AsyncComplianceClient` (async) hold a
single transport (`_internal/transport.py`) and expose ten resource
group attributes (`activities`, `chats`, `files`, `generated_files`,
`artifacts`, `projects`, `project_documents`, `organizations`, `roles`,
`groups`). Each resource group is a thin class that takes a transport
in its constructor and calls `transport.request(...)`. Pagination
helpers and download helpers live under `_internal/`. Errors live in
`exceptions.py` at package root. The two clients share dataclasses and
helpers — only the I/O layer differs.

## Branch and commit conventions

- Feature branches off `develop`. Releases cut from `develop` to `main`.
  **Never open a PR against `main`** unless explicitly told it is a
  release cut.
- Conventional Commits with optional scope:
  - `feat(transport): …`, `fix(pagination): …`, `chore: …`,
    `refactor(client): …`, `docs(readme): …`.
- Subject under 72 chars. Body is for the *why*.
- No `Co-Authored-By: Claude` trailer on commits. Maintainer
  preference — author the commit normally as the human contributor.

## Coding conventions

- **Formatting:** Black (line length 100). Never hand-format.
- **Imports:** isort with the Black profile.
- **Linting:** Pylint via `.pylintrc`. Do not disable rules inline
  without justification in a code comment.
- **Typing:** mypy strict. All public APIs have explicit type hints.
  `_internal/*` may relax this when integration with an untyped library
  forces it.
- **Naming:** snake_case for functions, variables, modules; PascalCase
  for classes; `UPPER_CASE` for module-level constants.
- **Docstrings:** Google-style on every public class and method.
  Include `Example:` blocks where they help. Internal helpers can skip
  docstrings if their name is self-explanatory.
- **Comments:** only when the *why* is non-obvious. Do not narrate
  *what* the code does. Do not reference the current task, fix, or
  callers (PR description handles that).
- **Errors:** raise from `claude_compliance_sdk.exceptions`. Never raise
  bare `Exception` or `ValueError` for HTTP failures. `ValueError` is
  acceptable for input-shape violations (e.g. `user_ids` length).
  Transport code maps non-2xx responses via
  `APIError.from_response(status_code=..., headers=..., body=...)` so
  the status-code routing and 401 split stay in one place.
- **HTTP I/O:** resources never touch `httpx` directly. They call
  `self._transport.request(method, path, params=..., json=...,
  headers=..., stream=...)` and let the transport handle headers,
  rate limit, retry, and error mapping. New transport-layer concerns
  go in `_internal/`, not in resource modules.
- **Pagination:** every paginated `.list()` returns a `CursorPage[T]`
  or `OffsetPage[T]`. The sibling `.iter()` method delegates to
  `iter_all_cursor_*` / `iter_all_offset_*` from
  `_internal/pagination.py` — do not reimplement the loop per resource.
- **The `list` shadowing trick:** a resource method named `.list()`
  shadows the `list` builtin in the class namespace, which breaks
  `list[str]` annotations on sibling methods (`.iter()` and friends).
  Define a module-level alias near the top of each paginated resource
  file (`StrList = list[str]`, etc.) and use it for those parameter
  types. The first occurrence (and the rationale) lives in
  `resources/activities.py`.
- **Response dataclasses:** every resource response type (`Activity`,
  `Chat`, `Project`, …) defines its known top-level fields and an
  `extra: dict[str, Any] = field(default_factory=dict)`. The
  `from_dict` classmethod is a one-liner that delegates to
  `parse_with_extra(cls, body)` from `_internal/parsing.py` — do not
  maintain a parallel `_KNOWN_FIELDS` frozenset; the helper derives
  the known set from `dataclasses.fields(cls)`.
- **List vs Detail shapes:** when the spec returns a richer payload
  on `.get()` than on `.list()` (see `ComplianceProject` vs
  `ComplianceProjectDetail`), model both — the list class with the
  shallow fields, and a `<Name>Detail` subclass that inherits via
  dataclass inheritance and adds the extra fields with defaults.
  `parse_with_extra` works on either class because it derives the
  known set from `dataclasses.fields()` (which includes inherited
  fields).
- **Delete operations** return `None`. The server's confirmation
  payload (`{"id": ..., "type": "..._deleted"}`) is discarded;
  success is signalled by no exception being raised. Errors raise
  the usual `APIError` subclasses (`NotFoundError`, `ConflictError`,
  …).
- **Download endpoints** route through the shared helpers in
  `_internal/downloads.py`: `download_eager_*` for the bounded
  eager read (raises `FileTooLargeError` past `max_download_bytes`),
  `download_to_file_*` for streamed-to-disk (unbounded — the cap
  protects memory, not disk), `download_stream_*` for caller-managed
  chunk iteration. Resources that need them take a
  `max_download_bytes` constructor kwarg; the public clients pass
  the config through.

## Testing conventions

- Unit tests use `pytest-httpx`. Build fixtures from real response shapes
  (see the spec PDF at the repo root).
- Async tests under `pytest-asyncio` `auto` mode — no decorator needed.
- Integration tests marked `@pytest.mark.integration` and skipped in CI.
- Every public method gets:
  1. A happy-path test.
  2. An error-mapping test for the most likely failure mode.
  3. An async-parity test (parametrize over sync + async clients).
- Pagination methods additionally test empty page and multi-page iteration.
- Coverage gate is 90 %. Do not lower it.

## Things to do without being asked

- Update `CHANGELOG.md` under `[Unreleased]` whenever you add, change,
  remove, or fix a public surface.
- **After every PLAN.md section is completed, update `CONTRIBUTING.md`,
  `CONTEXT.md`, and this file (`CLAUDE.md`) with anything relevant
  before opening the PR.** Specifically:
  - **CONTRIBUTING.md** — new dev-workflow step, tool, test convention,
    or PR-checklist item.
  - **CONTEXT.md** — new domain term, architecture move, layering rule,
    or decision (goes into the decision-log table).
  - **CLAUDE.md** — new locked decision, agent-do/don't, or pointer to
    a new file/location.
- Promote any decision that gained a real follow-up discussion into a
  numbered ADR under `docs/adr/` (use `docs/adr/0000-template.md`).
- Run `pre-commit run --all-files` before declaring work done.
- Run `pytest --cov --cov-fail-under=90` and `mypy src/claude_compliance_sdk`
  before declaring work done.

## Things to ask about, not assume

- Adding a runtime dependency.
- Bumping the minimum supported Python version.
- Changing a public surface name once it has shipped.
- Promoting a Phase-0 decision summary in CONTEXT.md to a full ADR.
- Anything that touches CI release workflows or PyPI publishing.

## Where to look

- **CONTEXT.md** — domain language, architecture, decision log, spec
  anchors. Read this before designing anything new.
- **PLAN.md** — phased implementation plan and current progress.
- **CONTRIBUTING.md** — contributor-facing version of the conventions
  in this file (use that one when explaining to humans).
- **`2026-05-04 Anthropic Compliance API docs.pdf`** — the spec
  (Rev K). Authoritative when CONTEXT.md and the spec disagree.
- **`docs/adr/`** — architecture decisions worth preserving past a
  single PR. (Empty at the time of writing; populate as decisions
  crystallise.)
