#!/usr/bin/env python3
"""Archive older Claude Desktop chat sessions by project count or absolute age.

Sessions are grouped by their `cwd` (project folder). Within each group the N most
recently active sessions are kept; the rest get `isArchived: true`. Archived sessions
stay on disk and remain reopenable from the app's Archived list.
`--older-than-days DAYS` instead archives every active session past that age,
regardless of its project.

Safety:
  * Dry run by default. Nothing is written without --apply.
  * Only ever touches ~/.claude and ~/.config/Claude. Any path resolving outside
    those roots is refused hard.
  * Every file it modifies is copied to a timestamped backup dir first.

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()

# The only two trees this script is allowed to modify.
ALLOWED_ROOTS = (
    (HOME / ".claude").resolve(),
    (HOME / ".config" / "Claude").resolve(),
)

DEFAULT_SESSIONS_ROOT = HOME / ".config" / "Claude" / "claude-code-sessions"
DEFAULT_BACKUP_ROOT = HOME / ".claude" / "backups"


class Refused(Exception):
    """Raised when a path falls outside the allowed roots."""


def assert_allowed(path: Path) -> Path:
    """Resolve `path` and refuse anything outside the two allowed roots."""
    resolved = path.resolve()

    for root in ALLOWED_ROOTS:
        if resolved == root or root in resolved.parents:
            return resolved

    raise Refused(
        f"refusing to touch {resolved} -- outside {ALLOWED_ROOTS[0]} and {ALLOWED_ROOTS[1]}"
    )


def desktop_is_running() -> bool:
    try:
        out = subprocess.run(
            ["pgrep", "-af", "claude-desktop"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    for line in out.stdout.splitlines():
        if "--type=" not in line and "crashpad" not in line:
            return True
    return False


def load_sessions(sessions_root: Path) -> list[dict]:
    """Read every local_*.json under sessions_root/<account>/<org>/."""
    sessions: list[dict] = []
    for path in sorted(sessions_root.glob("*/*/local_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  ! skipping unreadable {path.name}: {exc}", file=sys.stderr)
            continue
        if not isinstance(data, dict):
            continue
        sessions.append(
            {
                "path": path,
                "data": data,
                "session_id": data.get("sessionId", path.stem),
                "cwd": data.get("cwd") or "(unknown)",
                "title": data.get("title") or "(untitled)",
                "archived": bool(data.get("isArchived")),
                "last_activity": int(
                    data.get("lastActivityAt")
                    or data.get("lastFocusedAt")
                    or data.get("createdAt")
                    or 0
                ),
            }
        )
    return sessions


def plan(
    sessions: list[dict], keep: int, min_age_minutes: int,
    older_than_days: int | None = None,
) -> tuple[list[dict], dict]:
    """Decide which sessions to archive. Returns (to_archive, per_project_summary)."""
    now_ms = datetime.now(tz=timezone.utc).timestamp() * 1000
    cutoff_ms = now_ms - (min_age_minutes * 60 * 1000)
    if older_than_days is not None:
        cutoff_ms = min(cutoff_ms, now_ms - (older_than_days * 24 * 60 * 60 * 1000))

    # A session id can appear in more than one org dir; group so the same
    # conversation is kept or archived consistently across all its copies.
    by_project: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for s in sessions:
        by_project[s["cwd"]][s["session_id"]].append(s)

    to_archive: list[dict] = []
    summary: dict[str, dict] = {}

    for cwd, groups in by_project.items():
        active = {sid: copies for sid, copies in groups.items() if not all(c["archived"] for c in copies)}
        ranked = sorted(
            active.items(),
            key=lambda kv: max(c["last_activity"] for c in kv[1]),
            reverse=True,
        )
        kept = [] if older_than_days is not None else ranked[:keep]
        dropped = ranked if older_than_days is not None else ranked[keep:]

        skipped_recent = 0
        picked: list[dict] = []
        for sid, copies in dropped:
            newest = max(c["last_activity"] for c in copies)
            if newest > cutoff_ms:
                skipped_recent += 1
                continue
            for copy in copies:
                if not copy["archived"]:
                    to_archive.append(copy)
            picked.append(max(copies, key=lambda c: c["last_activity"]))

        summary[cwd] = {
            "active": len(active),
            "keep": len(kept),
            "archive": len(picked),
            "skipped_recent": skipped_recent,
            "picked": picked,
        }

    return to_archive, summary


def apply_archive(to_archive: list[dict], backup_dir: Path) -> int:
    assert_allowed(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for item in to_archive:
        path: Path = item["path"]
        assert_allowed(path)

        # Backup keeps the account/org folder structure so a restore is unambiguous.
        rel = path.relative_to(path.parents[2])
        dest = backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

        data = item["data"]
        data["isArchived"] = True
        # Match the app's own compact, single-line encoding.
        payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
        written += 1

    return written


def stamp_of(ms: int) -> str:
    if not ms:
        return "----------"
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive older Claude Desktop sessions, keeping the N most recent per project.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--keep", type=int, default=5, metavar="N",
        help="how many recent sessions to keep per project (default: 5)",
    )
    mode.add_argument(
        "--older-than-days", type=int, metavar="DAYS",
        help="archive every active session older than DAYS, regardless of project",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="actually write the changes (default is a dry run)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="list every session that would be archived, not just per-project counts",
    )
    parser.add_argument(
        "--sessions-root", type=Path, default=DEFAULT_SESSIONS_ROOT,
        help=f"session store location (default: {DEFAULT_SESSIONS_ROOT})",
    )
    parser.add_argument(
        "--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT,
        help=f"where backups are written (default: {DEFAULT_BACKUP_ROOT})",
    )
    parser.add_argument(
        "--min-age-minutes", type=int, default=15, metavar="M",
        help="never archive a session active in the last M minutes (default: 15) -- "
             "this is what protects the session you are running right now",
    )
    parser.add_argument(
        "--force-running", action="store_true",
        help="proceed even if Claude Desktop appears to be running",
    )
    args = parser.parse_args()

    if args.keep < 0:
        print("error: --keep must be >= 0", file=sys.stderr)
        return 2
    if args.older_than_days is not None and args.older_than_days < 0:
        print("error: --older-than-days must be >= 0", file=sys.stderr)
        return 2

    try:
        sessions_root = assert_allowed(args.sessions_root)
    except Refused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not sessions_root.is_dir():
        print(f"error: no session store at {sessions_root}", file=sys.stderr)
        return 2

    sessions = load_sessions(sessions_root)
    if not sessions:
        print(f"No sessions found under {sessions_root}")
        return 0

    to_archive, summary = plan(sessions, args.keep, args.min_age_minutes, args.older_than_days)

    total_files = len({s["path"] for s in sessions})
    already = sum(1 for s in sessions if s["archived"])
    print(f"Store:    {sessions_root}")
    print(f"Files:    {total_files} ({already} already archived)")
    if args.older_than_days is None:
        print(f"Keeping:  {args.keep} most recent per project\n")
    else:
        print(f"Age mode: archive active sessions older than {args.older_than_days} day(s), across all projects\n")

    for cwd in sorted(summary, key=lambda c: -summary[c]["active"]):
        row = summary[cwd]
        if row["archive"] == 0 and row["skipped_recent"] == 0:
            continue
        skipped_label = "newer than the age limit" if args.older_than_days is not None else "too recent"
        note = f"  (skipped {row['skipped_recent']} {skipped_label})" if row["skipped_recent"] else ""
        if args.older_than_days is None:
            print(f"  {row['active']:>3} active  keep {row['keep']:>2}  archive {row['archive']:>3}{note}  {cwd}")
        else:
            print(f"  {row['active']:>3} active  archive {row['archive']:>3}{note}  {cwd}")
        if args.verbose:
            for item in sorted(row["picked"], key=lambda i: -i["last_activity"]):
                print(f"        {stamp_of(item['last_activity'])}  {item['title']}")

    unchanged = [c for c, r in summary.items() if r["archive"] == 0 and r["skipped_recent"] == 0]
    if unchanged:
        if args.older_than_days is None:
            print(f"\n  {len(unchanged)} project(s) at or under the limit -- unchanged.")
        else:
            print(f"\n  {len(unchanged)} project(s) with no sessions before the age limit.")

    conversations = len({s["session_id"] for s in to_archive})
    print(f"\nTo archive: {conversations} conversation(s), {len(to_archive)} file(s) across org folders.")

    if not to_archive:
        print("Nothing to do.")
        return 0

    if not args.apply:
        print("\nDRY RUN -- nothing written. Re-run with --apply to make the changes.")
        return 0

    if desktop_is_running() and not args.force_running:
        print(
            "\nerror: Claude Desktop is running. Close it first so it does not overwrite "
            "these files from memory, or pass --force-running to override.",
            file=sys.stderr,
        )
        return 1

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = args.backup_root / f"session-archive-{stamp}"

    try:
        written = apply_archive(to_archive, backup_dir)
    except Refused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"\nArchived {written} file(s).")
    print(f"Backup:  {backup_dir}")
    print("Restore: copy the backup tree back over the session store.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
