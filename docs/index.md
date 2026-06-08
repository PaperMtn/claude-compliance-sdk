# claude-compliance-sdk

Community Python SDK for the **Anthropic Compliance API** — the
read-side of Claude Enterprise that lets compliance teams export and
audit user activity, chats, files, projects, organisations, roles, and
groups.

!!! warning "Unofficial"
    This is a community-maintained project. It is not produced,
    endorsed, or supported by Anthropic.

The full README, including quickstart and configuration, lives in the
repository root: see [README.md][readme] on GitHub.

[readme]: https://github.com/PaperMtn/claude-compliance-sdk/blob/main/README.md

## What's here

This site is the generated API reference, built from the SDK's
Google-style docstrings. Use the navigation on the left to walk the
resource groups, page primitives, and error hierarchy.

- **[Clients](api/clients.md)** — `ComplianceClient` and
  `AsyncComplianceClient`.
- **Resources** — `Activities`, `Organizations`, `Projects`,
  `Project documents`, `Chats`, `Files`, `Generated files`,
  `Artifacts`, `Roles`, `Groups`.
- **[Pagination](api/pagination.md)** — `CursorPage` and `OffsetPage`
  shapes plus the `iter_all_*` helpers.
- **[Errors](api/exceptions.md)** — `ComplianceClientError` and the
  typed subclasses you'll catch.
- **[Examples](examples.md)** — runnable scripts for common
  compliance use cases (source under
  [`examples/`](https://github.com/PaperMtn/claude-compliance-sdk/tree/main/examples)).

## Targets

- **Spec:** tracks the hosted [Anthropic Compliance API
  spec](https://platform.claude.com/docs/en/api/compliance).
- **Python:** 3.11+.
- **Runtime deps:** `httpx` only.

## License

GPL-3.0-or-later. See the
[LICENSE](https://github.com/PaperMtn/claude-compliance-sdk/blob/main/LICENSE)
file.
