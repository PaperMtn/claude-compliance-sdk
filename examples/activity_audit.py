"""Audit user activity over a time window.

Streams the Compliance API Activity Feed for the given window and
writes one NDJSON record per activity to stdout (or to ``--out``).
Optionally filters by actor user IDs and/or activity types.

Requires an **admin key** (``sk-ant-admin01-...``) — the Activity
Feed is the only endpoint admin keys can call.

Usage::

    export ANTHROPIC_COMPLIANCE_API_KEY=sk-ant-admin01-...
    python examples/activity_audit.py \\
        --since 2025-06-01T00:00:00Z \\
        --until 2025-06-30T23:59:59Z \\
        --type api_key_created \\
        --type compliance_api_accessed \\
        --out audit.ndjson
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import TextIO

from claude_compliance_sdk import (
    APIError,
    ComplianceClient,
    InsufficientScopeError,
    InvalidAPIKeyError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", required=True, help="Earliest created_at (RFC 3339).")
    parser.add_argument("--until", required=True, help="Latest created_at (RFC 3339).")
    parser.add_argument(
        "--actor",
        action="append",
        dest="actor_ids",
        help="Filter to this actor (repeatable).",
    )
    parser.add_argument(
        "--type",
        action="append",
        dest="activity_types",
        help="Filter to this activity type (repeatable).",
    )
    parser.add_argument(
        "--out",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Destination file (default: stdout).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Page size hint (max 5000).",
    )
    return parser.parse_args()


def write_records(stream: TextIO, client: ComplianceClient, args: argparse.Namespace) -> int:
    count = 0
    for activity in client.activities.iter(
        actor_ids=args.actor_ids,
        activity_types=args.activity_types,
        created_at_gte=args.since,
        created_at_lt=args.until,
        limit=args.limit,
    ):
        record = {
            "id": activity.id,
            "created_at": activity.created_at,
            "type": activity.type,
            "organization_id": activity.organization_id,
            "actor": activity.actor,
            **activity.extra,
        }
        stream.write(json.dumps(record) + "\n")
        count += 1
    return count


def main() -> int:
    args = parse_args()
    try:
        with ComplianceClient() as client:
            count = write_records(args.out, client, args)
    except InvalidAPIKeyError:
        print("API key invalid or revoked.", file=sys.stderr)
        return 2
    except InsufficientScopeError as exc:
        print(
            "API key lacks the required scope:",
            exc.error_message,
            file=sys.stderr,
        )
        return 2
    except APIError as exc:
        print(f"Server error {exc.status_code}: {exc.error_message}", file=sys.stderr)
        return 1

    print(f"Wrote {count} activities.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
