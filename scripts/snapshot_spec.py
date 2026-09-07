#!/usr/bin/env python3
"""Snapshot the hosted Compliance API docs to committed markdown.

The hosted docs are rewritten in place: no version history, no
changelog, no way to ask what a page said six months ago. This script
pulls each relevant page as markdown into a dated directory under
``spec-snapshots/`` so that "what did Anthropic change?" becomes a
``git diff`` between two snapshots instead of a manual re-read.

Every docs URL serves markdown when ``.md`` is appended, so no HTML
parsing is involved and the output is diff-friendly as fetched.

Usage:
    python scripts/snapshot_spec.py
    python scripts/snapshot_spec.py --date 2026-09-04 --out spec-snapshots

Then commit the new directory and diff it against the previous one:
    git diff --stat spec-snapshots/2026-05-04 spec-snapshots/2026-09-04

Stdlib only, so it needs no dependencies beyond the interpreter.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DOCS_ROOT = "https://platform.claude.com/docs/en"
USER_AGENT = "claude-compliance-sdk-spec-snapshot/1.0"
REQUEST_TIMEOUT_SECONDS = 60.0
MAX_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 1.0

# Pre-commit's check-added-large-files hook rejects anything over this,
# so a page that would blow the budget has to be truncated rather than
# silently committed and rejected at the hook.
MAX_FILE_BYTES = 512 * 1024


@dataclass(frozen=True)
class Page:
    """One docs page to snapshot.

    Attributes:
        slug: Output filename stem, also the manifest key.
        path: Path under ``DOCS_ROOT``, without the ``.md`` suffix.
        truncate_at: When set, drop everything from the first line
            equal to this heading onwards. Used for reference pages
            whose per-type response schemas run to megabytes and carry
            almost no signal for us, because per-activity-type fields
            land in ``Activity.extra`` rather than on the dataclass.
        enum_param: When set, also write the sorted enum members of
            this query parameter to ``<param>.txt``, so a growing enum
            diffs as a short list rather than inside a large page.
    """

    slug: str
    path: str
    truncate_at: str | None = None
    enum_param: str | None = None


PAGES: tuple[Page, ...] = (
    # Task-oriented guide pages.
    Page("compliance-api", "manage-claude/compliance-api"),
    Page("compliance-api-access", "manage-claude/compliance-api-access"),
    Page("compliance-activity-feed", "manage-claude/compliance-activity-feed"),
    Page("compliance-content-data", "manage-claude/compliance-content-data"),
    Page("compliance-sessions", "manage-claude/compliance-sessions"),
    Page("compliance-org-data", "manage-claude/compliance-org-data"),
    Page("compliance-integration-patterns", "manage-claude/compliance-integration-patterns"),
    Page("compliance-errors", "manage-claude/compliance-errors"),
    Page("compliance-faq", "manage-claude/compliance-faq"),
    # API reference. The activities page is ~3 MB in full; everything
    # after "## Returns" is a per-type response schema for 480+
    # activity types. The query-parameter section above it carries the
    # full activity-type enum, which is the part worth diffing.
    Page(
        "api-activities",
        "api/compliance/activities/list",
        truncate_at="## Returns",
        enum_param="activity_types",
    ),
    Page("api-apps", "api/compliance/apps"),
    Page("api-organizations", "api/compliance/organizations"),
    Page("api-groups", "api/compliance/groups"),
)

TRUNCATION_NOTICE = (
    "\n\n<!-- snapshot truncated at {heading!r} by scripts/snapshot_spec.py:\n"
    "     the omitted section is the per-activity-type response schema\n"
    "     (~3 MB), which the SDK does not model. See activity-types.txt\n"
    "     for the diffable list of type names. -->\n"
)

# Matches one enum member in the rendered reference, e.g. `- `"account_deleted"``.
_ENUM_MEMBER = re.compile(r'^\s*-\s+`"([a-z0-9_]+)"`\s*$')

# Matches the start of a top-level query parameter, e.g. `- `activity_types: ...``.
_PARAM_START = re.compile(r"^-\s+`([a-z_]+)(\[\])?:")


def fetch(url: str) -> str:
    """GET a URL as text, retrying transient failures with backoff.

    Raises:
        RuntimeError: When every attempt fails.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body: bytes = response.read()
                return body.decode(charset)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == MAX_ATTEMPTS - 1:
                break
            time.sleep(RETRY_BASE_DELAY_SECONDS * (2**attempt))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def truncate(text: str, heading: str) -> str:
    """Cut ``text`` at the first line equal to ``heading``.

    Cutting on the heading rather than a line count keeps the snapshot
    stable when unrelated content above it grows.
    """
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.strip() == heading:
            kept = "".join(lines[:index]).rstrip()
            return kept + TRUNCATION_NOTICE.format(heading=heading)
    print(f"  warning: truncation marker {heading!r} not found; keeping full page", file=sys.stderr)
    return text


def extract_enum_members(text: str, param: str) -> list[str]:
    """Pull the sorted enum members of one query parameter out of a page.

    Scoped to a single parameter block on purpose. Matching enum
    members across the whole page also picks up every unrelated enum in
    the per-type response schemas (activation states, platform names,
    and so on), which inflated the activity-type list from 483 to 630
    when this was first written.

    On the activities page this yields the activity-type names, which
    are the high-signal thing to diff: new types ship without notice.
    """
    collected: list[str] = []
    in_block = False
    for line in text.splitlines():
        start = _PARAM_START.match(line)
        if start is not None:
            in_block = start.group(1) == param
            continue
        if in_block and (match := _ENUM_MEMBER.match(line)) is not None:
            collected.append(match.group(1))
    return sorted(set(collected))


def write_file(destination: Path, text: str) -> int:
    """Write ``text`` to ``destination``, returning the byte count."""
    payload = text if text.endswith("\n") else text + "\n"
    encoded = payload.encode("utf-8")
    destination.write_bytes(encoded)
    return len(encoded)


def build_manifest(rows: list[tuple[str, str, int, str]], snapshot_date: str) -> str:
    """Render the manifest table for one snapshot directory."""
    lines = [
        f"# Compliance API docs snapshot — {snapshot_date}",
        "",
        "Fetched by `scripts/snapshot_spec.py`. Each row is the page as the",
        "hosted docs served it, with `.md` appended to the documentation URL.",
        "",
        "Diff against the previous snapshot to see what Anthropic changed:",
        "",
        "```bash",
        f"git diff --stat spec-snapshots/<previous> spec-snapshots/{snapshot_date}",
        "```",
        "",
        "| File | Source | Bytes | SHA-256 |",
        "| --- | --- | --- | --- |",
    ]
    for filename, url, size, digest in rows:
        lines.append(f"| `{filename}` | <{url}> | {size:,} | `{digest[:16]}…` |")
    lines.append("")
    return "\n".join(lines)


def snapshot(out_root: Path, snapshot_date: str) -> int:
    """Fetch every page into ``out_root/snapshot_date``.

    Returns:
        Process exit code: 0 on success, 1 if any page was oversized.
    """
    out_dir = out_root / snapshot_date
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Writing snapshot to {out_dir}")

    rows: list[tuple[str, str, int, str]] = []
    oversized: list[str] = []

    for page in PAGES:
        url = f"{DOCS_ROOT}/{page.path}.md"
        print(f"  {page.slug} <- {url}")
        text = fetch(url)
        if page.truncate_at is not None:
            if page.enum_param is not None:
                members = extract_enum_members(text, page.enum_param)
                enum_size = write_file(out_dir / "activity-types.txt", "\n".join(members))
                rows.append(
                    (
                        "activity-types.txt",
                        f"{url} ({page.enum_param} enum, extracted)",
                        enum_size,
                        hashlib.sha256("\n".join(members).encode()).hexdigest(),
                    )
                )
                print(f"    extracted {len(members)} {page.enum_param} values")
            text = truncate(text, page.truncate_at)

        filename = f"{page.slug}.md"
        size = write_file(out_dir / filename, text)
        rows.append((filename, url, size, hashlib.sha256(text.encode()).hexdigest()))
        if size > MAX_FILE_BYTES:
            oversized.append(f"{filename} ({size:,} bytes)")

    write_file(out_dir / "MANIFEST.md", build_manifest(rows, snapshot_date))
    total = sum(row[2] for row in rows)
    print(f"Wrote {len(rows) + 1} files, {total:,} bytes total")

    if oversized:
        print(
            "\nERROR: these files exceed the pre-commit large-file limit "
            f"({MAX_FILE_BYTES:,} bytes) and will be rejected:",
            file=sys.stderr,
        )
        for entry in oversized:
            print(f"  {entry}", file=sys.stderr)
        print("Add a `truncate_at` for the offending page in PAGES.", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run one snapshot."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Snapshot directory name (default: today, YYYY-MM-DD).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("spec-snapshots"),
        help="Root directory for snapshots (default: spec-snapshots).",
    )
    args = parser.parse_args(argv)
    try:
        return snapshot(args.out, args.date)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
