"""Export every chat for a set of users in an organisation.

For each chat that matches the filter, writes one JSON file under
``--out-dir`` containing the chat's metadata plus every message in
chronological order. The output is suitable for downstream
eDiscovery / legal review tooling.

Requires a **Compliance Access Key** (``sk-ant-api01-...``).

Usage::

    export ANTHROPIC_COMPLIANCE_API_KEY=sk-ant-api01-...
    python examples/ediscovery_export.py \\
        --user user_abc123 --user user_def456 \\
        --since 2025-06-01T00:00:00Z \\
        --until 2025-06-30T23:59:59Z \\
        --out-dir ./export
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from claude_compliance_sdk import APIError, Chat, ComplianceClient, InsufficientScopeError, Message


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--user",
        action="append",
        dest="user_ids",
        required=True,
        help="Actor user ID (1-10, repeatable). Required by the API.",
    )
    parser.add_argument("--since", help="Earliest created_at (RFC 3339).")
    parser.add_argument("--until", help="Latest created_at (RFC 3339).")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("./export"),
        help="Output directory (created if missing).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Per-page chat fetch size.",
    )
    return parser.parse_args()


def serialise_chat(chat: Chat) -> dict[str, Any]:
    return {
        "id": chat.id,
        "name": chat.name,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
        "deleted_at": chat.deleted_at,
        "organization_id": chat.organization_id,
        "project_id": chat.project_id,
        "model": chat.model,
        "user": chat.user,
        "href": chat.href,
    }


def serialise_message(message: Message) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "created_at": message.created_at,
        "content": message.content,
        "files": message.files,
        "artifacts": message.artifacts,
        **message.extra,
    }


def export_chat(client: ComplianceClient, chat_id: str, out_dir: Path) -> int:
    """Drive the messages cursor by hand so we can capture chat metadata.

    Returns the number of messages exported.
    """
    chat_payload: dict[str, Any] | None = None
    messages: list[dict[str, Any]] = []
    after_id: str | None = None
    while True:
        result = client.chats.get(chat_id, after_id=after_id)
        if chat_payload is None:
            chat_payload = serialise_chat(result.chat)
        messages.extend(serialise_message(m) for m in result.messages.data)
        if not result.messages.has_more or result.messages.last_id is None:
            break
        after_id = result.messages.last_id

    payload = {"chat": chat_payload, "messages": messages}
    (out_dir / f"{chat_id}.json").write_text(json.dumps(payload, indent=2))
    return len(messages)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        with ComplianceClient() as client:
            chat_count = 0
            message_count = 0
            for chat in client.chats.iter(
                user_ids=args.user_ids,
                created_at_gte=args.since,
                created_at_lt=args.until,
                limit=args.limit,
            ):
                exported = export_chat(client, chat.id, args.out_dir)
                chat_count += 1
                message_count += exported
                print(
                    f"  exported chat {chat.id} ({exported} messages)",
                    file=sys.stderr,
                )
    except InsufficientScopeError as exc:
        print("Missing scope:", exc.error_message, file=sys.stderr)
        return 2
    except APIError as exc:
        print(f"Server error {exc.status_code}: {exc.error_message}", file=sys.stderr)
        return 1

    print(
        f"Done. {chat_count} chats / {message_count} messages -> {args.out_dir}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
