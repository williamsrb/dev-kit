#!/usr/bin/env python3
"""Store a local copy of a Jira comment body before an in-place edit.

Jira has no revert for comment edits. Call this after fetching the current
body as HTML and before ``addOrEditJiraIssueComment`` with ``commentId``.
Do not edit if this script exits non-zero.

Usage:
    backup-jira-comment.py --issue PROJ-357 --comment-id 523467 --body-file prev.html
    backup-jira-comment.py --issue PROJ-357 --comment-id 523467 --body-file -

Exit codes: 0 = wrote backup, 2 = bad invocation, 1 = write failed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
BACKUP_ROOT = Path.home() / ".agents" / "prds"


def safe_segment(value: str) -> str:
    cleaned = SAFE_RE.sub("-", value.strip())
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError(f"unsafe path segment: {value!r}")
    return cleaned


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, help="Issue key, e.g. PROJ-357")
    parser.add_argument("--comment-id", required=True, help="Jira comment id")
    parser.add_argument(
        "--body-file",
        required=True,
        help="Path to the current comment body (HTML), or - for stdin",
    )
    parser.add_argument("--created", default="", help="Comment created timestamp")
    parser.add_argument("--updated", default="", help="Comment updated timestamp")
    parser.add_argument("--author", default="", help="Comment author display name")
    args = parser.parse_args(argv)

    if args.body_file == "-":
        body = sys.stdin.read()
    else:
        path = Path(args.body_file).expanduser()
        if not path.is_file():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 2
        body = path.read_text(encoding="utf-8")

    try:
        issue = safe_segment(args.issue)
        comment_id = safe_segment(args.comment_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    dest_dir = BACKUP_ROOT / issue / "comment-backups" / comment_id
    html_path = dest_dir / f"{stamp}.html"
    meta_path = dest_dir / f"{stamp}.meta.json"

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_text(body, encoding="utf-8")
        meta = {
            "issue": args.issue.strip(),
            "commentId": args.comment_id.strip(),
            "backedUpAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "created": args.created,
            "updated": args.updated,
            "author": args.author,
            "bodyPath": str(html_path),
            "bytes": html_path.stat().st_size,
        }
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"error: failed to write backup: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "bodyPath": str(html_path), "metaPath": str(meta_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
