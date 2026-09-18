#!/usr/bin/env python3
"""Post the plan's implicit-requirement tick list as a Jira ADF checkbox comment.

Creates a comment, or edits the stored ``_Comment-id:`` after backing up the
current body. Does not post when the list is empty or ``- Implicit: none``.

Usage:
    post_implicit_requirements.py --issue PROJ-1 --file ~/.agents/plans/PROJ-1/implicit.md
    post_implicit_requirements.py --issue PROJ-1 --file ~/.agents/plans/PROJ-1.md --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKBOX_RE = re.compile(r"^(\*|-)\s+\[([ xX])\]\s*(.*)$")
NONE_RE = re.compile(r"^-\s+Implicit:\s+none\s*$", re.IGNORECASE)
COMMENT_ID_RE = re.compile(r"^_Comment-id:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)
IMPLICIT_HEADING_RE = re.compile(r"^##\s+Implicit requirements\b", re.IGNORECASE)
ANY_HEADING_RE = re.compile(r"^##\s+")
AGENTCTL = Path.home() / ".agents" / "bin" / "agentctl"
BACKUP = (
    Path.home()
    / ".agents"
    / "skills"
    / "plan-task-evidence"
    / "scripts"
    / "backup-jira-comment.py"
)


def implicit_section(text: str, filename: str) -> str:
    if Path(filename).name == "implicit.md":
        return text
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if IMPLICIT_HEADING_RE.match(line):
            start = index
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if ANY_HEADING_RE.match(lines[index]):
            end = index
            break
    return "\n".join(lines[start:end])


def extract_checkboxes(section: str) -> list[str]:
    items: list[str] = []
    for line in section.splitlines():
        if NONE_RE.match(line.strip()):
            return []
        match = CHECKBOX_RE.match(line)
        if match and match.group(3).strip():
            items.append(f"- [ ] {match.group(3).strip()}")
    return items


def extract_comment_id(text: str) -> str | None:
    for line in text.splitlines():
        match = COMMENT_ID_RE.match(line.strip())
        if match:
            return match.group(1)
    return None


def comment_body(issue: str, items: list[str]) -> str:
    lines = [
        f"Tech lead — implicit requirements for {issue}.",
        "",
        "These are extras, not bugs and not blockers. Tick each item this delivery should include. Unticked items stay out of scope (follow-up).",
        "",
        *items,
    ]
    return "\n".join(lines) + "\n"


def write_comment_id(path: Path, comment_id: str) -> None:
    text = path.read_text(encoding="utf-8")
    replacement = f"_Comment-id: {comment_id}"
    if COMMENT_ID_RE.search(text):
        text = COMMENT_ID_RE.sub(replacement, text, count=1)
        if not text.endswith("\n"):
            text += "\n"
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += f"\n{replacement}\n"
    path.write_text(text, encoding="utf-8")


def run_json(command: list[str]) -> dict:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise RuntimeError(f"{' '.join(command)}: {detail}")
    return json.loads(result.stdout)


def backup_comment(issue: str, comment_id: str) -> Path:
    payload = run_json([
        str(AGENTCTL), "jira", "request", "GET",
        f"/rest/api/3/issue/{issue}/comment/{comment_id}?expand=renderedBody",
    ])
    body = payload.get("result") or {}
    rendered = body.get("renderedBody")
    raw = rendered if isinstance(rendered, str) and rendered.strip() else json.dumps(body, indent=2)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".html", delete=False
    ) as handle:
        handle.write(raw)
        temp_path = Path(handle.name)
    backup = subprocess.run(
        [
            sys.executable, str(BACKUP),
            "--issue", issue,
            "--comment-id", comment_id,
            "--body-file", str(temp_path),
            "--created", str(body.get("created") or ""),
            "--updated", str(body.get("updated") or ""),
            "--author", str((body.get("author") or {}).get("displayName") or ""),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    temp_path.unlink(missing_ok=True)
    if backup.returncode != 0:
        raise RuntimeError(backup.stderr.strip() or backup.stdout.strip() or "backup failed")
    if backup.stdout.strip().startswith("{"):
        return Path(json.loads(backup.stdout)["bodyPath"])
    return Path(".")


def post_comment(issue: str, body: str, comment_id: str | None) -> dict:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".md", delete=False
    ) as handle:
        handle.write(body)
        temp_path = Path(handle.name)
    command = [str(AGENTCTL), "jira", "comment", issue, "--body-file", str(temp_path)]
    if comment_id:
        command.extend(["--comment-id", comment_id])
    try:
        return run_json(command)
    finally:
        temp_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    path = args.file.expanduser()
    if not path.is_file():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    items = extract_checkboxes(implicit_section(text, path.name))
    comment_id = extract_comment_id(text)
    payload = {
        "issue": args.issue,
        "file": str(path),
        "items": items,
        "comment_id": comment_id,
        "posted": False,
    }
    if not items:
        payload["reason"] = "none"
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    body = comment_body(args.issue, items)
    payload["body"] = body
    if args.dry_run:
        payload["reason"] = "dry-run"
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    backup_path = None
    if comment_id:
        backup_path = backup_comment(args.issue, comment_id)
        payload["backup"] = str(backup_path)
    result = post_comment(args.issue, body, comment_id)
    new_id = result.get("id") or comment_id
    if new_id:
        write_comment_id(path, str(new_id))
    payload["posted"] = True
    payload["comment_id"] = new_id
    payload["edited"] = bool(comment_id)
    payload["jira"] = result
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2), file=sys.stderr)
        raise SystemExit(1) from exc
