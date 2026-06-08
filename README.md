# claude-compliance-sdk

This is a community Python SDK for the **Anthropic Compliance API** — the API that lets you access Claude activity logs, chat data, and file content programmatically.

The Compliance API requires an Enterprise plan, and primary owners can enable it using the guide [here](https://support.claude.com/en/articles/13015708-access-the-compliance-api).

> **Unofficial.** This is a community-maintained project. It is not
> produced, endorsed, or supported by Anthropic.

📚 **[Read the documentation](https://papermtn.github.io/claude-compliance-sdk/)** — full API reference, generated from the source.

## Features

- Complete coverage of all Compliance API endpoints, including the Activity Feed, Chats, Messages, Files, Projects, Groups, Users, Roles, Permissions, and Organisations.
- Full sync + async parity. Every resource method is available on both `ComplianceClient` and `AsyncComplianceClient` under the same name.
- Typed responses as plain dataclasses. Unknown response fields are preserved in an `extra: dict` so a future API revision adding a field cannot break the SDK.
- Built-in retry with exponential backoff that honours `Retry-After`, plus a client-side sliding-window rate limiter that matches the server's 600 RPM cap.
- Streamed downloads with a configurable memory ceiling — switch from eager bytes to `download_to_file()` or `download_stream()` for anything larger.
- Typed exception hierarchy. Every API error maps to a catchable class — `InvalidAPIKeyError`, `InsufficientScopeError`, `NotFoundError`, `ConflictError`, `RateLimitError`, and the rest.
- Tracks the hosted [Anthropic Compliance API spec](https://platform.claude.com/docs/en/api/compliance).

## Requirements
Python 3.11+.

## Install

Install from PyPI with pip:
```bash
pip install claude-compliance-sdk
```

Or install from source:
```bash
git clone https://github.com/PaperMtn/claude-compliance-sdk.git
cd claude-compliance-sdk
python -m pip install .
```

## Documentation

Full API reference docs are available at [papermtn.github.io/claude-compliance-sdk](https://papermtn.github.io/claude-compliance-sdk/).

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

The Compliance API uses **Compliance Access Keys** (prefix
`sk-ant-api01-...`), created by your organisation's Primary Owner from
Claude.ai under **Settings → Data Management → Compliance access keys**.
At creation time the key is granted one or more of the following
scopes; the scope set is fixed for the lifetime of the key:

| Scope | Unlocks |
| --- | --- |
| `read:compliance_activities` | Activity Feed (`activities`) |
| `read:compliance_user_data` | Chats, messages, file metadata, project data, group members |
| `delete:compliance_user_data` | Deleting chats and user-uploaded files |
| `read:compliance_org_data` | Organisations, users, roles, permissions, groups |

A request that the server rejects with `401`
is surfaced as either `InvalidAPIKeyError` (the key is wrong) or
`InsufficientScopeError` (the key is valid but missing the scope the
endpoint needs).

Pass the key when constructing the client:

```python
import os

client = ComplianceClient(api_key=os.environ["ANTHROPIC_COMPLIANCE_API_KEY"])
```

Or set the environment variable and let the client read it:

```bash
export ANTHROPIC_COMPLIANCE_API_KEY=sk-ant-api01-...
```

```python
client = ComplianceClient()
```

## Pagination

Two types of pagination are used:

- **Cursor-paginated** — Activity Feed, Chats, Messages. Pages carry
  `first_id` / `last_id` / `has_more`.
- **Offset-paginated** — everything else. Pages carry `has_more` and
  an opaque `next_page` token.

Every paginated resource exposes both `.list()` (one page at a time) and `.iter()` (auto-paginate — yields items one
at a time across all pages) functions.

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

Cursor resources are identical in shape; the page contains `last_id`
and you pass it back as `after_id`.

## Downloads

Three resource groups expose binary content — user files, assistant-
generated files, and artifacts. Each provides the same three download
methods:

```python
# Into memory, bounded by max_download_bytes (default 100 MiB).
data: bytes = client.files.download("claude_file_xyz789")

# Streamed to disk — unbounded.
client.files.download_to_file("claude_file_xyz789", "/tmp/report.pdf")

# Caller-managed streaming — yields bytes; connection closes when the
# iterator is exhausted or garbage-collected.
for chunk in client.files.download_stream("claude_file_xyz789"):
    handle(chunk)
```

The `max_download_bytes` cap protects memory on the memory path only.
`download_to_file` and `download_stream` ignore the cap and always stream, so you can use them for anything larger than the cap.

```python
client = ComplianceClient(max_download_bytes=10 * 1024 * 1024)  # 10 MiB cap

try:
    data = client.files.download("claude_file_big")
except FileTooLargeError as exc:
    print(f"{exc.size_bytes} bytes > {exc.max_bytes} cap — switching to stream")
    client.files.download_to_file("claude_file_big", "big.bin")
```

User files are deletable (`.delete()`). Generated files and artifacts
are not.

## Configuration

`ComplianceClient` and `AsyncComplianceClient` accept the same kwargs:

| Kwarg | Default | What it does |
| --- | --- | --- |
| `api_key` | env `ANTHROPIC_COMPLIANCE_API_KEY` | Bearer credential. |
| `base_url` | `https://api.anthropic.com` | Override for testing. |
| `timeout` | `30.0` | Per-request timeout, seconds. |
| `max_download_bytes` | `100 * 1024 * 1024` | Eager-download cap. |
| `max_retries` | `3` | Retry attempts on 429/5xx and connect errors. `0` disables. |
| `rate_limit_rpm` | `600` | Client-side sliding-window cap matching the server. `0` disables. |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup, branch model,
coding conventions, and PR checklist. Architecture decisions worth
preserving live as numbered ADRs under [`adr/`](adr/).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
