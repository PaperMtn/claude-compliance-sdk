# Contributing to claude-compliance-sdk

Thanks for your interest. This SDK is hand-written and community-maintained
— it is **not** produced or endorsed by Anthropic. Pull requests, bug
reports, and design discussion are all welcome.

## Project ground rules

These shape every contribution. They are not negotiable inside a PR — open
an issue first if you want one revisited.

- **Hand-written, no code-gen.** The SDK is curated by hand. We do not
  generate clients from an OpenAPI spec, and PRs that introduce code-gen
  tooling will be closed.
- **No Pydantic, no heavy schema layer.** Models are plain dataclasses.
  Unknown response fields are preserved in an `extra: dict` rather than
  dropped, so the SDK does not break when the API adds fields.
- **Slack-SDK UX parity.** When in doubt about naming, ergonomics, or
  pagination shape, look at how `slack_sdk` does it and follow.
- **Server enforces, client labels.** Validation that the server already
  performs (scopes, key types, business rules like "cannot delete a
  project with attached chats") is not duplicated client-side. The client
  catches the server's error and re-raises it as a typed exception. Only
  cheap input-shape checks (e.g. "list must be 1–10 items") happen
  locally.
- **Sync and async parity.** Every public method on `ComplianceClient`
  has an equivalent on `AsyncComplianceClient`. They share dataclasses
  and pagination helpers — only the I/O layer differs. New methods land
  on both clients in the same PR.
- **Dependency-light.** Runtime deps are `httpx` only. Adding another
  runtime dependency requires discussion in an issue first.

## Development setup

```bash
# Clone and enter the project.
git clone https://github.com/PaperMtn/claude-compliance-sdk.git
cd claude-compliance-sdk

# Install Poetry (https://python-poetry.org/) if you do not have it.
# Then install runtime + dev dependencies into a virtualenv.
poetry install

# Activate the virtualenv for the rest of the session.
poetry shell

# Install the pre-commit hooks. Required — CI runs the same checks.
pre-commit install
```

Python 3.11, 3.12, and 3.13 are supported. Use the lowest version you can
when developing so you do not accidentally rely on a newer-version feature.

## Branch model

This project uses a git-flow-style model:

- `main` tracks released versions only. Tags (`v0.1.0`, `v0.2.0`, …) are
  cut from `main`.
- `develop` is the integration branch. All feature work targets `develop`.
- Feature branches are named `feat/<slug>`, fixes `fix/<slug>`, chores
  `chore/<slug>`, refactors `refactor/<slug>`, docs `docs/<slug>`.

**PRs target `develop`, not `main`.** Releases are cut from `develop` to
`main` by the maintainer.

## Commit messages

Conventional Commits, with optional scope:

```
feat(transport): add httpx-backed sync transport with retry policy
fix(pagination): handle empty cursor page on Activity Feed
chore: bump black to 24.10
refactor(client): collapse duplicate config validation
docs(readme): add pagination example
```

The scope, when present, is the area of code touched (`transport`,
`pagination`, `client`, `activities`, etc.). Keep the subject under 72
characters. Reserve the body for the *why* — the *what* is in the diff.

## Coding style

Tooling is configured in `pyproject.toml` and `.pylintrc`. Pre-commit runs
all of these on every commit:

- **Black** — formatter, 100-char line length. Black owns formatting; do
  not hand-format around it.
- **isort** — import sorting, Black profile.
- **Pylint** — uses `.pylintrc`. Rules that fight Black or duplicate mypy
  are already disabled.
- **mypy** — strict mode (`disallow_untyped_defs`, `strict_optional`,
  `warn_unused_ignores`, etc.). All public APIs must have explicit type
  hints. Internal modules under `_internal/` may relax this when needed.

Other conventions:

- Docstrings on every public class and method. Google style. Include an
  `Example:` block where it helps.
- Snake-case for functions, variables, modules. PascalCase for classes.
  `UPPER_CASE` for module-level constants.
- Internal modules live under `claude_compliance_sdk._internal.*` and are
  not part of the public API. Anything importable directly from
  `claude_compliance_sdk` is a stability promise.
- Comments only when the *why* is non-obvious. Do not narrate the *what*
  — well-named identifiers already do that.
- Avoid abstractions that exist for a single caller. Three similar lines
  are better than a premature helper.
- Raise from `claude_compliance_sdk.exceptions`. Never raise bare
  `Exception` or `ValueError` for HTTP failures. `ValueError` is fine
  for input-shape violations (e.g. `user_ids` length checks).

## Testing

```bash
# Full test suite, parallel-friendly.
poetry run pytest

# Skip integration tests (default in CI).
poetry run pytest -m "not integration"

# Coverage report. Must stay >= 90%.
poetry run pytest --cov --cov-fail-under=90

# Type-check the public package.
poetry run mypy src/claude_compliance_sdk
```

Conventions:

- Unit tests use `pytest-httpx` to mock the API. Build fixtures from real
  response shapes (see the spec PDF in the repo root) rather than
  inventing them.
- Async tests use `pytest-asyncio` in `auto` mode — just write
  `async def test_…` and it works.
- Integration tests are marked `@pytest.mark.integration` and require
  `ANTHROPIC_COMPLIANCE_API_KEY` to be set. They are skipped in CI and
  only run locally against the live API.
- Coverage gate is 90 %. We run coverage locally — we do not publish to
  Codecov.
- Test every error mapping. The most common bug in HTTP SDKs is mis-mapped
  status codes.

## Documentation

- Update **CHANGELOG.md** under the `[Unreleased]` section in the same PR
  as the code change. Follow the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
  format: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.
- Update **README.md** if you add or rename a public surface.
- Update **CONTEXT.md** if you introduce a new domain concept or change
  how an existing one is modelled.
- Architecture decisions worth preserving go under `adr/` as a
  numbered ADR (`0001-some-decision.md`). Phase-0 decisions are summarised
  in **CONTEXT.md**; promote them to ADRs once they have a real follow-up
  discussion.
- The API reference site is built with mkdocs-material and
  mkdocstrings — `poetry run mkdocs serve` to preview locally; CI
  builds in `--strict` mode so missing nav targets and unresolved
  references fail the build.

## Pull request checklist

Before opening a PR:

- [ ] Targets `develop`, not `main`.
- [ ] Pre-commit hooks pass locally (`pre-commit run --all-files`).
- [ ] Tests pass with coverage ≥ 90 %.
- [ ] Mypy is clean.
- [ ] CHANGELOG updated under `[Unreleased]`.
- [ ] Sync and async parity preserved for any new public method.
- [ ] No new runtime dependency (or if one is genuinely needed, discussed
      in an issue first).
- [ ] Docstrings on new public surfaces.
- [ ] Commit subjects follow the Conventional Commits format above.

## Reporting bugs

Open an issue on
[GitHub Issues](https://github.com/PaperMtn/claude-compliance-sdk/issues).
Include:

- SDK version (`python -c "import claude_compliance_sdk; print(claude_compliance_sdk.__version__)"`).
- Python version.
- A minimal reproduction. If it hits the live API, redact the API key and
  any organisation/user IDs.
- The full traceback, including the `request_id` from the exception when
  available — that lets the maintainer cross-reference server-side logs
  if needed.

## License

By contributing, you agree that your contributions will be licensed under
the [GPL-3.0-or-later](LICENSE) license that covers the project.
