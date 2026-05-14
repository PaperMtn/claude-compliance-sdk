# claude-compliance-sdk

A community Python SDK for the **Anthropic Compliance API** — the read
side of Claude Enterprise that lets compliance teams export and audit
user activity, chats, files, projects, organisations, roles, and
groups.

> **Unofficial.** This is a community-maintained project. It is not
> produced, endorsed, or supported by Anthropic.

- Hand-written, dependency-light (`httpx` only), `slack_sdk`-style
  ergonomics.
- Full sync + async parity — same method names on both clients.
- Typed responses (plain dataclasses, no Pydantic). Unknown response
  fields land in `extra: dict` so the SDK does not break when the spec
  grows.
- Targets spec revision **Rev K** (2026-05-04).

## Install

```
pip install claude-compliance-sdk
```

Python 3.11+.

## Quickstart

### Sync

```python
from claude_compliance_sdk import ComplianceClient

with ComplianceClient(api_key="sk-ant-admin01-...") as client:
    for activity in client.activities.iter(
        activity_types=["claude_chat_created", "api_key_created"],
        limit=100,
    ):
        print(activity.created_at, activity.type, activity.id)
```

### Async

```python
import asyncio

from claude_compliance_sdk import AsyncComplianceClient


async def main() -> None:
    async with AsyncComplianceClient(api_key="sk-ant-admin01-...") as client:
        async for activity in client.activities.iter(limit=100):
            print(activity.created_at, activity.type)


asyncio.run(main())
```

Every resource group on both clients exposes the same method names —
swap `ComplianceClient` for `AsyncComplianceClient`, sprinkle `await`,
done.

## Authentication

The Compliance API uses two distinct key types. The SDK never inspects
the prefix — the server is the source of truth; the client only labels
the resulting `401`.

| Key prefix | Issued from | What it unlocks |
| --- | --- | --- |
| `sk-ant-api01-...` | Claude.ai → Compliance access keys | Chats, files, projects, organisations, roles, groups |
| `sk-ant-admin01-...` | Claude Console → Admin keys | The Activity Feed only |

Pass the key explicitly:

```python
client = ComplianceClient(api_key="sk-ant-api01-...")
```

Or set the environment variable and let the client read it:

```bash
export ANTHROPIC_COMPLIANCE_API_KEY=sk-ant-api01-...
```

```python
client = ComplianceClient()
```

If the key is missing in both places, the constructor raises
`ValueError` immediately — no wasted network round-trip.

## Pagination

Two flavours per the spec:

- **Cursor-paginated** — Activity Feed, Chats, Messages. Pages carry
  `first_id` / `last_id` / `has_more`.
- **Offset-paginated** — everything else. Pages carry `has_more` and
  an opaque `next_page` token.

Every paginated resource exposes both `.list()` (one page at a time —
fine-grained control) and `.iter()` (auto-paginate — yields items one
at a time across however many pages it takes).

```python
# .list() — explicit page boundaries
page = client.projects.list(limit=20)
for project in page.data:
    print(project.id)
if page.has_more:
    next_page = client.projects.list(limit=20, page=page.next_page)

# .iter() — auto-paginate
for project in client.projects.iter(organization_ids=["org_abc123"]):
    print(project.id)
```

Cursor resources are identical in shape; the page carries `last_id`
and you pass it back as `after_id`.

## Error handling

Every error the SDK raises descends from
[`ComplianceClientError`](src/claude_compliance_sdk/exceptions.py).
The HTTP branch maps status codes to typed subclasses:

```python
from claude_compliance_sdk import (
    ComplianceClient,
    APIError,
    InsufficientScopeError,
    InvalidAPIKeyError,
    RateLimitError,
    ConflictError,
    NotFoundError,
)

with ComplianceClient() as client:
    try:
        client.projects.delete("claude_proj_abc123")
    except InvalidAPIKeyError:
        print("Bad API key.")
    except InsufficientScopeError as exc:
        print("Missing scope:", exc.error_message)
    except ConflictError:
        print("Project still has chats attached.")
    except RateLimitError as exc:
        print(f"Rate limited; server says wait {exc.retry_after}s.")
    except APIError as exc:
        # Catch-all for any other HTTP failure.
        print(exc.status_code, exc.error_type, exc.error_message)
        print("request-id:", exc.request_id)
```

The 401 split (`InvalidAPIKeyError` / `InsufficientScopeError`) is a
best-effort label based on the server's error message — see ADR-0001
in `docs/adr/`. Transport-level failures live under
`APIConnectionError` (and the more specific `APITimeoutError`).
Eager downloads past the size cap raise `FileTooLargeError`.

The transport retries 429 / 500 / 502 / 503 / 504 on safe methods with
exponential backoff and honours `Retry-After`. Tune via `max_retries`
on either client (set to `0` to disable).

## Downloads

Three resource groups expose binary content — user files, assistant-
generated files, and artifacts. Each provides the same trio of
methods:

```python
# Eager — into memory, bounded by max_download_bytes (default 100 MiB).
data: bytes = client.files.download("claude_file_xyz789")

# Streamed to disk — unbounded.
client.files.download_to_file("claude_file_xyz789", "/tmp/report.pdf")

# Caller-managed streaming — yields bytes; connection closes when the
# iterator is exhausted or garbage-collected.
for chunk in client.files.download_stream("claude_file_xyz789"):
    handle(chunk)
```

The `max_download_bytes` cap protects memory on the eager path only.
`download_to_file` and `download_stream` are deliberately unbounded —
use them for anything larger than the cap.

```python
client = ComplianceClient(max_download_bytes=10 * 1024 * 1024)  # 10 MiB cap

try:
    data = client.files.download("claude_file_big")
except FileTooLargeError as exc:
    print(f"{exc.size_bytes} bytes > {exc.max_bytes} cap — switching to stream")
    client.files.download_to_file("claude_file_big", "big.bin")
```

User files are deletable (`.delete()`). Generated files and artifacts
are not — the server rejects deletes on those.

## Configuration

`ComplianceClient` and `AsyncComplianceClient` accept the same kwargs:

| Kwarg | Default | What it does |
| --- | --- | --- |
| `api_key` | env `ANTHROPIC_COMPLIANCE_API_KEY` | Bearer credential. |
| `base_url` | `https://api.anthropic.com` | Override for testing. |
| `timeout` | `30.0` | Per-request timeout, seconds. |
| `anthropic_version` | `"2023-06-01"` | Value sent in the `anthropic-version` header. |
| `max_download_bytes` | `100 * 1024 * 1024` | Eager-download cap. |
| `max_retries` | `3` | Retry attempts on 429/5xx and connect errors. `0` disables. |
| `rate_limit_rpm` | `600` | Client-side sliding-window cap matching the server. `0` disables. |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup, branch model,
coding conventions, and PR checklist. Architecture decisions worth
preserving live as numbered ADRs under [`docs/adr/`](docs/adr/).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
