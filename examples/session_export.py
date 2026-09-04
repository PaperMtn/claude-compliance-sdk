"""Export session transcripts from Cowork, Claude Code, and friends.

Walks the local session listing over a time window and writes each
session's transcript to a JSON file. Local sessions are the ones that
run on users' own machines: Cowork in Claude Desktop, Claude Code in
the terminal or an IDE, Claude Science, and Claude for Microsoft 365.
Pass ``--remote`` to export Cowork sessions that ran in Anthropic's
cloud instead.

Requires a **Compliance Access Key** (``sk-ant-api01-...``) with
``read:compliance_user_data``. Admin API keys return 403 here.

A few behaviours worth knowing, all of which this script handles:

* ``created_at`` on a local session is the timestamp of its *earliest
  retained* call, so it advances as older calls age out of retention.
  Deduplicate on ``id`` when re-walking over time, not on timestamps.
* A transcript can contain messages whose content is unavailable. Those
  carry a ``provenance`` of ``content_unavailable`` with a ``reason``,
  and are exported as-is rather than dropped — "we know a turn happened
  here and cannot show it" is a different claim from "nothing happened".
* Tool inputs and results are truncated to 10,000 bytes by default.
  ``--full-tools`` asks for the server maximum (about 1 MiB).
* A 404 reading "Local sessions are not available." means the endpoints
  are off for your organisation, not that a session is gone.

Usage::

    export ANTHROPIC_COMPLIANCE_ACCESS_KEY=sk-ant-api01-...

    # Every local session since a date.
    python examples/session_export.py --since 2026-07-01T00:00:00Z

    # Just Claude Code, with untruncated tool calls.
    python examples/session_export.py \\
        --since 2026-07-01T00:00:00Z \\
        --surface claude_code \\
        --full-tools

    # Cowork sessions that ran in the cloud.
    python examples/session_export.py --remote --since 2026-07-01T00:00:00Z
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from claude_compliance_sdk import (
    APIError,
    ComplianceClient,
    InsufficientScopeError,
    LocalSessionsRetentionUnavailableError,
    LocalSessionsUnavailableError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--since",
        help="Earliest session start (RFC 3339, e.g. 2026-07-01T00:00:00Z).",
    )
    parser.add_argument("--until", help="Latest session start (RFC 3339).")
    parser.add_argument(
        "--surface",
        help=(
            "Only export sessions from this product_surface, e.g. claude_code, "
            "cowork, claude_science. Filtered client-side; the API has no such filter."
        ),
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Export cloud Cowork sessions instead of local ones.",
    )
    parser.add_argument(
        "--full-tools",
        action="store_true",
        help="Request the server maximum for tool inputs and results (~1 MiB each).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("./sessions"),
        help="Output directory (created if missing).",
    )
    parser.add_argument("--limit", type=int, help="Page size for the session listing.")
    return parser.parse_args()


def _tool_cap(full: bool) -> int | None:
    """Return the byte cap to request for tool inputs and results.

    ``-1`` asks for the server maximum; ``None`` leaves the server
    default of 10,000 bytes. Worth raising if anything downstream parses
    tool arguments, because a *truncated* ``tool_use`` input is cut
    mid-document and is no longer valid JSON.
    """
    return -1 if full else None


def export_local(client: ComplianceClient, args: argparse.Namespace) -> tuple[int, int]:
    """Export local sessions. Returns (sessions, messages)."""
    sessions = messages = 0
    for session in client.local_sessions.iter(
        created_at_gte=args.since,
        created_at_lt=args.until,
        limit=args.limit,
    ):
        if args.surface and session.product_surface != args.surface:
            continue
        try:
            transcript = [
                asdict(message)
                for message in client.local_sessions.iter_messages(
                    session.id,
                    tool_use_input_max_bytes=_tool_cap(args.full_tools),
                    tool_result_max_bytes=_tool_cap(args.full_tools),
                )
            ]
        except LocalSessionsRetentionUnavailableError:
            # Depends on the organisation's retention settings, not on
            # load. Skip and retry on a later run rather than blocking.
            print(f"  skipped {session.id}: retention not evaluable", file=sys.stderr)
            continue

        payload: dict[str, Any] = {"session": asdict(session), "messages": transcript}
        (args.out_dir / f"{session.id}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        sessions += 1
        messages += len(transcript)
        unavailable = sum(
            1
            for message in transcript
            if (message.get("provenance") or {}).get("type") == "content_unavailable"
        )
        note = f" ({unavailable} unavailable)" if unavailable else ""
        print(
            f"  exported {session.id} [{session.product_surface}] "
            f"{len(transcript)} messages{note}",
            file=sys.stderr,
        )
    return sessions, messages


def export_remote(client: ComplianceClient, args: argparse.Namespace) -> tuple[int, int]:
    """Export cloud Cowork sessions. Returns (sessions, messages)."""
    sessions = messages = 0
    for session in client.remote_sessions.iter(
        created_at_gte=args.since,
        created_at_lt=args.until,
        limit=args.limit,
    ):
        if args.surface and session.product_surface != args.surface:
            continue
        if session.status == "pending":
            # Still being provisioned; its messages endpoint 404s until
            # it starts. Pick it up on a later run.
            print(f"  skipped {session.id}: pending", file=sys.stderr)
            continue

        transcript = [
            asdict(message)
            for message in client.remote_sessions.iter_messages(
                session.id,
                tool_use_input_max_bytes=_tool_cap(args.full_tools),
                tool_result_max_bytes=_tool_cap(args.full_tools),
            )
        ]
        payload: dict[str, Any] = {"session": asdict(session), "messages": transcript}
        (args.out_dir / f"{session.id}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        sessions += 1
        messages += len(transcript)
        print(
            f"  exported {session.id} {len(transcript)} messages",
            file=sys.stderr,
        )
    return sessions, messages


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        with ComplianceClient() as client:
            if args.remote:
                sessions, messages = export_remote(client, args)
            else:
                sessions, messages = export_local(client, args)
    except LocalSessionsUnavailableError:
        print(
            "Local sessions are not available for this organisation. This is "
            "not a per-session error — keep any queued IDs and retry later.",
            file=sys.stderr,
        )
        return 3
    except InsufficientScopeError as exc:
        print("Missing scope:", exc.error_message, file=sys.stderr)
        return 2
    except APIError as exc:
        print(f"API error (request-id {exc.request_id}):", exc, file=sys.stderr)
        return 1

    print(
        f"Exported {sessions} session(s), {messages} message(s) to {args.out_dir}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
