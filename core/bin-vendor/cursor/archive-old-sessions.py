#!/usr/bin/env python3
"""Archive older Cursor composer chats by workspace count or absolute age.

Groups parent composers (isSubagent=0) by workspace folder (cwd from
workspaceIdentifier.uri.fsPath, else workspaceId). Within each group the N most
recently updated stay active; the rest get isArchived=1 on the composerHeaders
table and isArchived=true inside the value JSON (and matching entries in the
ItemTable composer.composerHeaders blob when present).
`--older-than-days DAYS` instead archives every active parent past that age,
regardless of its workspace.

Safety:
  * Dry run by default. Nothing is written without --apply.
  * Only ever touches ~/.config/Cursor. Paths outside that root are refused.
  * Sessions active in the last --min-age-minutes are never touched.
  * Refuses to run while Cursor appears up, unless --force-running.
  * Backs up each modified header row (+ ItemTable slice) before writing.

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
CURSOR_CONFIG = (HOME / ".config" / "Cursor").resolve()
DEFAULT_STATE_DB = CURSOR_CONFIG / "User" / "globalStorage" / "state.vscdb"
DEFAULT_BACKUP_ROOT = HOME / ".cursor" / "backups"

ALLOWED_ROOTS = (CURSOR_CONFIG, (HOME / ".cursor").resolve())


class Refused(Exception):
    """Raised when a path falls outside the allowed roots."""


def assert_allowed(path: Path) -> Path:
    resolved = path.resolve()
    for root in ALLOWED_ROOTS:
        if resolved == root or root in resolved.parents:
            return resolved
    raise Refused(
        f"refusing to touch {resolved} -- outside {ALLOWED_ROOTS[0]} / {ALLOWED_ROOTS[1]}"
    )


def desktop_is_running() -> bool:
    try:
        out = subprocess.run(
            ["pgrep", "-af", "cursor"],
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
        if "archive-old-sessions" in low or "pgrep" in low:
            continue
        if "/usr/share/cursor/cursor" in low or "cursor --" in low:
            return True
    return False


def cwd_from_value(value: dict, workspace_id: str) -> str:
    ident = value.get("workspaceIdentifier")
    if isinstance(ident, dict):
        uri = ident.get("uri")
        if isinstance(uri, dict):
            fs_path = str(uri.get("fsPath") or "").strip()
            if fs_path:
                return fs_path
        external = ""
        if isinstance(uri, dict):
            external = str(uri.get("external") or "")
        if external.startswith("file://"):
            return external[len("file://") :]
    repos = value.get("trackedGitRepos")
    if isinstance(repos, list) and repos:
        repo = repos[0]
        if isinstance(repo, dict):
            repo_path = str(repo.get("repoPath") or "").strip()
            if repo_path:
                return repo_path
    return workspace_id or "(unknown)"


def load_sessions(db_path: Path) -> list[dict]:
    assert_allowed(db_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"no Cursor state db at {db_path}")
    uri = f"file:{db_path}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        rows = con.execute(
            """
            SELECT composerId, workspaceId, createdAt, lastUpdatedAt,
                   isArchived, isSubagent, recency, value
            FROM composerHeaders
            """
        ).fetchall()
    finally:
        con.close()

    sessions: list[dict] = []
    for row in rows:
        (
            composer_id,
            workspace_id,
            created_at,
            last_updated_at,
            is_archived,
            is_subagent,
            recency,
            value_raw,
        ) = row
        if int(is_subagent or 0):
            continue
        try:
            value = json.loads(value_raw or "{}")
        except (TypeError, json.JSONDecodeError):
            value = {}
        if not isinstance(value, dict):
            value = {}
        if value.get("isBestOfNSubcomposer") or value.get("isSubagent"):
            continue
        last_activity = int(
            recency
            or last_updated_at
            or value.get("lastUpdatedAt")
            or created_at
            or 0
        )
        sessions.append(
            {
                "session_id": str(composer_id),
                "workspace_id": str(workspace_id or ""),
                "cwd": cwd_from_value(value, str(workspace_id or "")),
                "title": str(value.get("name") or "(untitled)")[:80],
                "archived": bool(is_archived) or bool(value.get("isArchived")),
                "last_activity": last_activity,
                "value": value,
                "value_raw": value_raw or "{}",
                "created_at": created_at,
                "last_updated_at": last_updated_at,
            }
        )
    return sessions


def plan(
    sessions: list[dict], keep: int, min_age_minutes: int,
    older_than_days: int | None = None,
) -> tuple[list[dict], dict]:
    now_ms = datetime.now(tz=timezone.utc).timestamp() * 1000
    cutoff_ms = now_ms - (min_age_minutes * 60 * 1000)
    if older_than_days is not None:
        cutoff_ms = min(cutoff_ms, now_ms - (older_than_days * 24 * 60 * 60 * 1000))

    by_project: dict[str, list[dict]] = defaultdict(list)
    for s in sessions:
        by_project[s["cwd"]].append(s)

    to_archive: list[dict] = []
    summary: dict[str, dict] = {}

    for cwd, group in by_project.items():
        active = [s for s in group if not s["archived"]]
        ranked = sorted(active, key=lambda s: s["last_activity"], reverse=True)
        kept = [] if older_than_days is not None else ranked[:keep]
        dropped = ranked if older_than_days is not None else ranked[keep:]

        skipped_recent = 0
        picked: list[dict] = []
        for s in dropped:
            if s["last_activity"] > cutoff_ms:
                skipped_recent += 1
                continue
            to_archive.append(s)
            picked.append(s)

        summary[cwd] = {
            "active": len(active),
            "keep": len(kept),
            "archive": len(picked),
            "skipped_recent": skipped_recent,
            "picked": picked,
        }

    return to_archive, summary


def backup_rows(to_archive: list[dict], backup_dir: Path, db_path: Path) -> None:
    assert_allowed(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    headers_dir = backup_dir / "composerHeaders"
    headers_dir.mkdir(parents=True, exist_ok=True)
    for item in to_archive:
        payload = {
            "composerId": item["session_id"],
            "workspaceId": item["workspace_id"],
            "createdAt": item["created_at"],
            "lastUpdatedAt": item["last_updated_at"],
            "isArchived": item["archived"],
            "value": item["value"],
        }
        (headers_dir / f"{item['session_id']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Slice of ItemTable blob for the ids we will touch (full blob is small ~280KB).
    uri = f"file:{db_path}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        row = con.execute(
            "SELECT value FROM ItemTable WHERE key='composer.composerHeaders'"
        ).fetchone()
    finally:
        con.close()
    if row and row[0]:
        (backup_dir / "itemtable-composer.composerHeaders.json").write_text(
            row[0] if isinstance(row[0], str) else row[0].decode("utf-8"),
            encoding="utf-8",
        )


def apply_archive(to_archive: list[dict], db_path: Path, backup_dir: Path) -> int:
    assert_allowed(db_path)
    backup_rows(to_archive, backup_dir, db_path)

    ids = [item["session_id"] for item in to_archive]
    id_set = set(ids)

    con = sqlite3.connect(str(db_path), timeout=30)
    try:
        con.execute("PRAGMA busy_timeout=30000")
        written = 0
        for item in to_archive:
            value = dict(item["value"])
            value["isArchived"] = True
            payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            con.execute(
                """
                UPDATE composerHeaders
                SET isArchived = 1, value = ?
                WHERE composerId = ?
                """,
                (payload, item["session_id"]),
            )
            written += 1

        # Keep ItemTable blob in sync for composers it still lists.
        row = con.execute(
            "SELECT value FROM ItemTable WHERE key='composer.composerHeaders'"
        ).fetchone()
        if row and row[0]:
            raw = row[0] if isinstance(row[0], str) else row[0].decode("utf-8")
            try:
                blob = json.loads(raw)
            except json.JSONDecodeError:
                blob = None
            if isinstance(blob, dict) and isinstance(blob.get("allComposers"), list):
                changed = False
                for entry in blob["allComposers"]:
                    if not isinstance(entry, dict):
                        continue
                    cid = str(entry.get("composerId") or "")
                    if cid in id_set and not entry.get("isArchived"):
                        entry["isArchived"] = True
                        changed = True
                if changed:
                    con.execute(
                        "UPDATE ItemTable SET value = ? WHERE key = 'composer.composerHeaders'",
                        (json.dumps(blob, separators=(",", ":"), ensure_ascii=False),),
                    )

        con.commit()
    finally:
        con.close()

    return len(to_archive)


def stamp_of(ms: int) -> str:
    if not ms:
        return "----------"
    ts = ms / 1000 if ms > 10_000_000_000 else ms
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive older Cursor composer chats, keeping the N most recent per workspace.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--keep", type=int, default=5, metavar="N", help="recent chats to keep per workspace (default: 5)")
    mode.add_argument(
        "--older-than-days", type=int, metavar="DAYS",
        help="archive every active chat older than DAYS, regardless of workspace",
    )
    parser.add_argument("--apply", action="store_true", help="actually write (default is dry run)")
    parser.add_argument("--verbose", "-v", action="store_true", help="list every chat that would be archived")
    parser.add_argument("--state-db", type=Path, default=DEFAULT_STATE_DB, help=f"default: {DEFAULT_STATE_DB}")
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT, help=f"default: {DEFAULT_BACKUP_ROOT}")
    parser.add_argument(
        "--min-age-minutes",
        type=int,
        default=15,
        metavar="M",
        help="never archive a chat active in the last M minutes (default: 15)",
    )
    parser.add_argument(
        "--force-running",
        action="store_true",
        help="proceed even if Cursor appears to be running",
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
        sessions = load_sessions(state_db)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not sessions:
        print(f"No parent composers found in {state_db}")
        return 0

    to_archive, summary = plan(sessions, args.keep, args.min_age_minutes, args.older_than_days)

    already = sum(1 for s in sessions if s["archived"])
    print(f"Vendor:   cursor")
    print(f"Store:    {state_db}")
    print(f"Parents:  {len(sessions)} ({already} already archived)")
    if args.older_than_days is None:
        print(f"Keeping:  {args.keep} most recent per workspace\n")
    else:
        print(f"Age mode: archive active chats older than {args.older_than_days} day(s), across all workspaces\n")

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
            print(f"\n  {len(unchanged)} workspace(s) at or under the limit -- unchanged.")
        else:
            print(f"\n  {len(unchanged)} workspace(s) with no chats before the age limit.")

    print(f"\nTo archive: {len(to_archive)} chat(s).")

    if not to_archive:
        print("Nothing to do.")
        return 0

    if not args.apply:
        print("\nDRY RUN -- nothing written. Re-run with --apply to make the changes.")
        return 0

    if desktop_is_running() and not args.force_running:
        print(
            "\nerror: Cursor appears to be running. Close it first so it does not "
            "overwrite these rows from memory, or pass --force-running to override.",
            file=sys.stderr,
        )
        return 1

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = args.backup_root / f"session-archive-{stamp}"

    try:
        written = apply_archive(to_archive, state_db, backup_dir)
    except Refused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except sqlite3.Error as exc:
        print(f"error: sqlite write failed: {exc}", file=sys.stderr)
        return 1

    print(f"\nArchived {written} chat(s).")
    print(f"Backup:  {backup_dir}")
    print("Restore: re-apply the backed-up composerHeaders/*.json rows into state.vscdb.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
