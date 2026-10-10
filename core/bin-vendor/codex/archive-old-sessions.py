#!/usr/bin/env python3
"""Archive older Codex sessions by project count or absolute age.

Reads ~/.codex/state_5.sqlite `threads`. Subagent threads are ignored (they are
not listed as workspace chats). Within each cwd the N most recent parent
threads stay active; the rest are archived via `codex archive <id>` (sets
archived=1 and moves the rollout into ~/.codex/archived_sessions/). Parents
that belong in that keep set but are already archived are restored with
`codex unarchive`.
`--older-than-days DAYS` instead archives every active parent past that age,
regardless of its cwd, and never restores sessions.

Safety:
  * Dry run by default. Nothing is written without --apply.
  * Only ever touches ~/.codex. Paths resolving outside that root are refused.
  * Sessions active in the last --min-age-minutes are never touched.
  * Refuses to run while Codex Desktop appears up, unless --force-running.

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
CODEX_HOME = (HOME / ".codex").resolve()
DEFAULT_STATE_DB = CODEX_HOME / "state_5.sqlite"
DEFAULT_BACKUP_ROOT = CODEX_HOME / "backups"

ALLOWED_ROOTS = (CODEX_HOME,)


class Refused(Exception):
    """Raised when a path falls outside the allowed roots."""


def assert_allowed(path: Path) -> Path:
    resolved = path.resolve()
    for root in ALLOWED_ROOTS:
        if resolved == root or root in resolved.parents:
            return resolved
    raise Refused(f"refusing to touch {resolved} -- outside {CODEX_HOME}")


def desktop_is_running() -> bool:
    try:
        out = subprocess.run(
            ["pgrep", "-af", "codex"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    for line in out.stdout.splitlines():
        low = line.lower()
        if "crashpad" in low or "--type=" in low:
            continue
        # Ignore this script / pgrep / one-shot CLI that is not the desktop app.
        if "archive-old-sessions" in low or "pgrep" in low:
            continue
        if "codex-desktop" in low or "/opt/codex" in low:
            return True
        if "codex" in low and "app-server" in low:
            return True
    return False


def is_subagent(thread_source: object, source: object) -> bool:
    if thread_source == "subagent":
        return True
    return isinstance(source, str) and "subagent" in source


def find_codex_bin() -> str:
    which = shutil.which("codex")
    if which:
        return which
    candidate = HOME / ".local" / "bin" / "codex"
    if candidate.is_file():
        return str(candidate)
    raise FileNotFoundError("codex CLI not found on PATH or ~/.local/bin/codex")


def load_threads(db_path: Path) -> list[dict]:
    assert_allowed(db_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"no Codex state db at {db_path}")
    uri = f"file:{db_path}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        rows = con.execute(
            """
            SELECT id, cwd, title, name, archived, archived_at,
                   COALESCE(recency_at_ms, updated_at_ms, created_at_ms, 0) AS last_activity,
                   rollout_path, thread_source, source
            FROM threads
            """
        ).fetchall()
    finally:
        con.close()

    sessions: list[dict] = []
    for row in rows:
        (
            sid,
            cwd,
            title,
            name,
            archived,
            archived_at,
            last_activity,
            rollout_path,
            thread_source,
            source,
        ) = row
        if is_subagent(thread_source, source):
            continue
        sessions.append(
            {
                "session_id": str(sid),
                "cwd": cwd or "(unknown)",
                "title": (title or name or "(untitled)").split("\n", 1)[0][:80],
                "archived": bool(archived),
                "last_activity": int(last_activity or 0),
                "rollout_path": rollout_path,
            }
        )
    return sessions


def plan(
    sessions: list[dict], keep: int, min_age_minutes: int,
    older_than_days: int | None = None,
) -> tuple[list[dict], list[dict], dict]:
    now_ms = datetime.now(tz=timezone.utc).timestamp() * 1000
    cutoff_ms = now_ms - (min_age_minutes * 60 * 1000)
    if older_than_days is not None:
        cutoff_ms = min(cutoff_ms, now_ms - (older_than_days * 24 * 60 * 60 * 1000))

    by_project: dict[str, list[dict]] = defaultdict(list)
    for s in sessions:
        by_project[s["cwd"]].append(s)

    to_archive: list[dict] = []
    to_unarchive: list[dict] = []
    summary: dict[str, dict] = {}

    for cwd, group in by_project.items():
        ranked = sorted(group, key=lambda s: s["last_activity"], reverse=True)
        kept = [] if older_than_days is not None else ranked[:keep]
        dropped = ranked if older_than_days is not None else ranked[keep:]
        restore = [] if older_than_days is not None else [s for s in kept if s["archived"]]
        # Only restore when an older *active* parent is occupying a keep slot.
        # Otherwise a workspace whose chats were all archived (including the
        # single realtime/automation leftovers) would get pulled back.
        if not any(not s["archived"] for s in dropped):
            restore = []
        to_unarchive.extend(restore)

        skipped_recent = 0
        picked: list[dict] = []
        for s in dropped:
            if s["archived"]:
                continue
            if s["last_activity"] > cutoff_ms:
                skipped_recent += 1
                continue
            to_archive.append(s)
            picked.append(s)

        summary[cwd] = {
            "active": sum(1 for s in group if not s["archived"]),
            "keep": len(kept),
            "archive": len(picked),
            "unarchive": len(restore),
            "skipped_recent": skipped_recent,
            "picked": picked,
            "restore": restore,
        }

    return to_archive, to_unarchive, summary


def apply_archive(to_archive: list[dict], codex_bin: str, backup_dir: Path) -> int:
    assert_allowed(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    manifest = backup_dir / "archived-ids.txt"
    written = 0
    failures: list[str] = []

    with manifest.open("w", encoding="utf-8") as mf:
        for item in to_archive:
            sid = item["session_id"]
            mf.write(f"{sid}\t{item['cwd']}\t{item['title']}\n")
            # Copy rollout aside before CLI moves it, when the file still exists.
            rollout = item.get("rollout_path")
            if rollout:
                src = Path(rollout)
                try:
                    assert_allowed(src)
                except Refused:
                    pass
                else:
                    if src.is_file():
                        dest = backup_dir / "rollouts" / src.name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dest)

            proc = subprocess.run(
                [codex_bin, "archive", sid],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                failures.append(f"{sid}: {proc.stderr.strip() or proc.stdout.strip() or proc.returncode}")
                continue
            written += 1

    if failures:
        (backup_dir / "failures.txt").write_text(
            "\n".join(failures) + "\n", encoding="utf-8"
        )
        print(f"  ! {len(failures)} archive call(s) failed — see {backup_dir / 'failures.txt'}", file=sys.stderr)
    return written


def apply_unarchive(to_unarchive: list[dict], codex_bin: str, backup_dir: Path) -> int:
    assert_allowed(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    manifest = backup_dir / "unarchived-ids.txt"
    written = 0
    failures: list[str] = []

    with manifest.open("w", encoding="utf-8") as mf:
        for item in to_unarchive:
            sid = item["session_id"]
            mf.write(f"{sid}\t{item['cwd']}\t{item['title']}\n")
            proc = subprocess.run(
                [codex_bin, "unarchive", sid],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                failures.append(f"{sid}: {proc.stderr.strip() or proc.stdout.strip() or proc.returncode}")
                continue
            written += 1

    if failures:
        fail_path = backup_dir / "unarchive-failures.txt"
        fail_path.write_text("\n".join(failures) + "\n", encoding="utf-8")
        print(f"  ! {len(failures)} unarchive call(s) failed — see {fail_path}", file=sys.stderr)
    return written


def stamp_of(ms: int) -> str:
    if not ms:
        return "----------"
    # Codex stores ms; tolerate accidental seconds.
    ts = ms / 1000 if ms > 10_000_000_000 else ms
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive older Codex sessions, keeping the N most recent per project.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--keep", type=int, default=5, metavar="N", help="recent sessions to keep per cwd (default: 5)")
    mode.add_argument(
        "--older-than-days", type=int, metavar="DAYS",
        help="archive every active session older than DAYS, regardless of cwd",
    )
    parser.add_argument("--apply", action="store_true", help="actually archive (default is dry run)")
    parser.add_argument("--verbose", "-v", action="store_true", help="list every session that would be archived")
    parser.add_argument("--state-db", type=Path, default=DEFAULT_STATE_DB, help=f"default: {DEFAULT_STATE_DB}")
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT, help=f"default: {DEFAULT_BACKUP_ROOT}")
    parser.add_argument(
        "--min-age-minutes",
        type=int,
        default=15,
        metavar="M",
        help="never archive a session active in the last M minutes (default: 15)",
    )
    parser.add_argument(
        "--force-running",
        action="store_true",
        help="proceed even if Codex Desktop / app-server appears to be running",
    )
    args = parser.parse_args()

    if args.keep < 0:
        print("error: --keep must be >= 0", file=sys.stderr)
        return 2
    if args.older_than_days is not None and args.older_than_days < 0:
        print("error: --older-than-days must be >= 0", file=sys.stderr)
        return 2

    try:
        state_db = assert_allowed(args.state_db)
    except Refused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        sessions = load_threads(state_db)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not sessions:
        print(f"No sessions found in {state_db}")
        return 0

    to_archive, to_unarchive, summary = plan(
        sessions, args.keep, args.min_age_minutes, args.older_than_days
    )

    already = sum(1 for s in sessions if s["archived"])
    print("Vendor:   codex")
    print(f"Store:    {state_db}")
    print(f"Parents:  {len(sessions)} ({already} already archived, subagents skipped)")
    if args.older_than_days is None:
        print(f"Keeping:  {args.keep} most recent per project\n")
    else:
        print(f"Age mode: archive active sessions older than {args.older_than_days} day(s), across all projects\n")

    for cwd in sorted(summary, key=lambda c: -summary[c]["active"]):
        row = summary[cwd]
        if row["archive"] == 0 and row["unarchive"] == 0 and row["skipped_recent"] == 0:
            continue
        bits = []
        if row["skipped_recent"]:
            label = "newer than the age limit" if args.older_than_days is not None else "too recent"
            bits.append(f"skipped {row['skipped_recent']} {label}")
        if row["unarchive"]:
            bits.append(f"restore {row['unarchive']}")
        note = f"  ({', '.join(bits)})" if bits else ""
        if args.older_than_days is None:
            print(f"  {row['active']:>3} active  keep {row['keep']:>2}  archive {row['archive']:>3}{note}  {cwd}")
        else:
            print(f"  {row['active']:>3} active  archive {row['archive']:>3}{note}  {cwd}")
        if args.verbose:
            for item in sorted(row["picked"], key=lambda i: -i["last_activity"]):
                print(f"        archive  {stamp_of(item['last_activity'])}  {item['title']}")
            for item in sorted(row["restore"], key=lambda i: -i["last_activity"]):
                print(f"        restore  {stamp_of(item['last_activity'])}  {item['title']}")

    unchanged = [
        c for c, r in summary.items()
        if r["archive"] == 0 and r["unarchive"] == 0 and r["skipped_recent"] == 0
    ]
    if unchanged:
        if args.older_than_days is None:
            print(f"\n  {len(unchanged)} project(s) at or under the limit -- unchanged.")
        else:
            print(f"\n  {len(unchanged)} project(s) with no sessions before the age limit.")

    print(f"\nTo archive: {len(to_archive)} session(s). To restore: {len(to_unarchive)} session(s).")

    if not to_archive and not to_unarchive:
        print("Nothing to do.")
        return 0

    if not args.apply:
        print("\nDRY RUN -- nothing written. Re-run with --apply to make the changes.")
        return 0

    if desktop_is_running() and not args.force_running:
        print(
            "\nerror: Codex Desktop/app-server appears to be running. Close it first, "
            "or pass --force-running to override.",
            file=sys.stderr,
        )
        return 1

    try:
        codex_bin = find_codex_bin()
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = args.backup_root / f"session-archive-{stamp}"

    try:
        restored = apply_unarchive(to_unarchive, codex_bin, backup_dir) if to_unarchive else 0
        written = apply_archive(to_archive, codex_bin, backup_dir) if to_archive else 0
    except Refused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"\nRestored {restored} session(s). Archived {written} session(s).")
    print(f"Backup:  {backup_dir}")
    print("Undo archive: codex unarchive <id>  (ids listed in archived-ids.txt)")
    ok = restored == len(to_unarchive) and written == len(to_archive)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
