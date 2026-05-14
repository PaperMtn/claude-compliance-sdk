"""Download every user-uploaded file attached to a project.

Walks the project's attachments listing, filters to
``type == "project_file"`` (skipping project documents — those are
plain text and have their own endpoint), and streams each file to
disk via :meth:`Files.download_to_file`. The stream path is
unbounded by ``max_download_bytes``, so this works for large
attachments.

Requires a **Compliance Access Key** (``sk-ant-api01-...``).

Usage::

    export ANTHROPIC_COMPLIANCE_API_KEY=sk-ant-api01-...
    python docs/examples/file_pull.py \\
        --project claude_proj_abc123 \\
        --out-dir ./files
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from claude_compliance_sdk import (
    APIError,
    ComplianceClient,
    NotFoundError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", required=True, help="Project ID.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("./files"),
        help="Output directory (created if missing).",
    )
    return parser.parse_args()


def _safe_filename(attachment_id: str, filename: str | None) -> str:
    """Build a filesystem-safe destination name.

    Prefixes with the attachment ID so collisions across uploads with
    the same display name don't clobber each other.
    """
    name = filename or "unnamed"
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    return f"{attachment_id}__{safe}"


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    try:
        with ComplianceClient() as client:
            downloaded = 0
            skipped_docs = 0
            for attachment in client.projects.iter_attachments(args.project):
                if attachment.type != "project_file":
                    skipped_docs += 1
                    continue

                dest = args.out_dir / _safe_filename(attachment.id, attachment.filename)
                print(f"  -> {dest.name}", file=sys.stderr)
                client.files.download_to_file(attachment.id, dest)
                downloaded += 1
    except NotFoundError:
        print(f"Project {args.project} not found.", file=sys.stderr)
        return 2
    except APIError as exc:
        print(f"Server error {exc.status_code}: {exc.error_message}", file=sys.stderr)
        return 1

    print(
        f"Done. {downloaded} files downloaded, {skipped_docs} project docs skipped "
        f"-> {args.out_dir}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
