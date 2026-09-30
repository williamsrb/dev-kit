#!/usr/bin/env python3
"""Insert ai-title into Claude JSONL so Cursor's native importer can display real titles.

Cursor titles a Claude Code agent from JSONL only:

  aiTitle || first non-meta user prompt || "Claude Code session"

It does not read Desktop index `title` or JSONL `custom-title`. Native Claude
CLI chats often have those and no `ai-title`, so the sidebar shows the fallback.

This writes work Claude JSONL only (`~/.claude/projects`). Do not write
*_prompt.md / *_result.md.
Do not inject `_comment`. Do not toggle cursor/importClaudeCodeAgents.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional, Tuple

HOME = Path.home()
DEFAULT_PROJECTS = HOME / ".claude" / "projects"
DEFAULT_INDEX_ROOT = HOME / ".config" / "Claude" / "claude-code-sessions"
DEFAULT_STATE_DIR = HOME / ".local" / "share" / "claude-jsonl-title-backfill"
DEFAULT_LOCK = DEFAULT_STATE_DIR / "backfill.lock"
DEFAULT_LOG = DEFAULT_STATE_DIR / "backfill.log"
SCAN_LINE_CAP = 400
TITLE_MAX = 80
GENERIC_TITLES = frozenset(
    {
        "",
        ".",
        "Claude Code session",
        "[cursor] Claude Code session",
        "Untitled session",
        "Untitled",
    }
)


@dataclass
class JsonlTitles:
    session_id: str
    ai_title: str = ""
    ai_line_index: Optional[int] = None
    custom_title: str = ""


def iso_z(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def useful_title(value: object) -> str:
    text = str(value or "").strip()
    if not text or text in GENERIC_TITLES:
        return ""
    collapsed = " ".join(text.split())
    if collapsed in GENERIC_TITLES:
        return ""
    if len(collapsed) > TITLE_MAX:
        return collapsed[: TITLE_MAX - 3] + "..."
    return collapsed


def iter_org_dirs(root: Path) -> Iterator[Path]:
    if not root.is_dir():
        return
    try:
        accounts = list(root.iterdir())
    except OSError as e:
        logging.warning("skip unreadable %s: %s", root, e)
        return
    for account in accounts:
        try:
            if account.is_symlink() or not account.is_dir():
                continue
            for org in account.iterdir():
                try:
                    if org.is_symlink() or not org.is_dir():
                        continue
                    yield org
                except OSError as e:
                    logging.warning("skip %s: %s", org, e)
        except OSError as e:
            logging.warning("skip unreadable %s: %s", account, e)


def load_index_titles(root: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not root.is_dir():
        logging.warning("index root missing: %s", root)
        return out
    for org in iter_org_dirs(root):
        try:
            paths = org.glob("local_*.json")
        except OSError as e:
            logging.warning("skip unreadable %s: %s", org, e)
            continue
        for path in paths:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
                logging.warning("unreadable index %s: %s", path, e)
                continue
            if not isinstance(data, dict):
                continue
            title = useful_title(data.get("title"))
            if not title:
                continue
            for key in (data.get("cliSessionId"), data.get("sessionId"), path.stem):
                sid = str(key or "").strip()
                if sid.startswith("local_"):
                    sid = sid[len("local_") :]
                if sid and sid not in out:
                    out[sid] = title
    return out


def iter_jsonl(root: Path, session_id: Optional[str] = None) -> Iterator[Path]:
    if not root.is_dir():
        logging.warning("projects dir missing: %s", root)
        return
    try:
        paths = root.glob("*/*.jsonl")
    except OSError as e:
        logging.warning("skip unreadable %s: %s", root, e)
        return
    for path in sorted(paths):
        if path.parent.name.startswith("."):
            continue
        if session_id and path.stem != session_id:
            continue
        yield path


def scan_jsonl(path: Path) -> JsonlTitles:
    found = JsonlTitles(session_id=path.stem)
    try:
        with path.open(encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i >= SCAN_LINE_CAP:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    rec = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                sid = rec.get("sessionId")
                if isinstance(sid, str) and sid.strip() and found.session_id == path.stem:
                    found.session_id = sid.strip()
                rec_type = rec.get("type")
                if rec_type == "ai-title" and found.ai_line_index is None:
                    found.ai_title = str(rec.get("aiTitle") or rec.get("title") or "")
                    found.ai_line_index = i
                elif rec_type == "custom-title" and not found.custom_title:
                    found.custom_title = str(rec.get("customTitle") or rec.get("title") or "")
                if found.ai_line_index is not None and found.custom_title:
                    break
    except OSError as e:
        logging.warning("skip unreadable %s: %s", path, e)
    return found


def choose_title(
    scanned: JsonlTitles, index_titles: Dict[str, str], stems: Iterable[str]
) -> Tuple[str, str]:
    existing = useful_title(scanned.ai_title)
    if existing:
        return "", "unchanged"
    custom = useful_title(scanned.custom_title)
    if custom:
        return custom, "custom-title"
    for key in stems:
        index = useful_title(index_titles.get(key, ""))
        if index:
            return index, "index"
    return "", "skip-no-title"


def build_ai_title_line(session_id: str, title: str) -> str:
    rec = {"type": "ai-title", "aiTitle": title, "sessionId": session_id}
    return json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n"


def apply_ai_title(path: Path, session_id: str, title: str, ai_line_index: Optional[int]) -> None:
    text = path.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in text[:4096] else "\n"
    lines = text.splitlines()
    new_line = build_ai_title_line(session_id, title).rstrip("\n")
    if ai_line_index is not None and 0 <= ai_line_index < len(lines):
        lines[ai_line_index] = new_line
    else:
        lines.insert(0, new_line)
    body = newline.join(lines)
    if text.endswith(("\n", "\r\n")) or not text:
        body += newline
    mode = path.stat().st_mode & 0o777
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        tmp.write_text(body, encoding="utf-8", newline="")
        os.chmod(tmp, mode)
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def acquire_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EAGAIN):
            fh.close()
            raise SystemExit("another backfill is already running") from e
        raise
    fh.write(str(os.getpid()))
    fh.flush()
    return fh


def setup_logging(log_path: Path, verbose: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
        force=True,
    )


def main(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--log", type=Path, default=DEFAULT_LOG)
    p.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    p.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS)
    p.add_argument("--index-root", type=Path, default=DEFAULT_INDEX_ROOT)
    p.add_argument("--session-id", help="Backfill a single JSONL stem.")
    args = p.parse_args(list(argv) if argv is not None else None)

    setup_logging(args.log, args.verbose)
    lock_fh = acquire_lock(args.lock)
    t0 = time.time()
    wrote = failed = unchanged = skip_no_title = 0
    by_source = {"custom-title": 0, "index": 0}
    try:
        index_titles = load_index_titles(args.index_root.expanduser())
        logging.info(
            "backfill start dry_run=%s projects=%s index_titles=%d",
            args.dry_run,
            args.projects.expanduser(),
            len(index_titles),
        )
        seen = False
        for path in iter_jsonl(args.projects.expanduser(), session_id=args.session_id):
            seen = True
            scanned = scan_jsonl(path)
            sid = scanned.session_id or path.stem
            title, source = choose_title(scanned, index_titles, (sid, path.stem))
            if source == "unchanged":
                unchanged += 1
                continue
            if source == "skip-no-title":
                skip_no_title += 1
                logging.debug("SKIP no-title %s", path)
                continue
            logging.info(
                "%s %s source=%s title=%s",
                "DRY" if args.dry_run else "WRITE",
                path,
                source,
                title,
            )
            if args.dry_run:
                wrote += 1
                by_source[source] += 1
                continue
            try:
                apply_ai_title(path, sid, title, scanned.ai_line_index)
            except OSError:
                failed += 1
                logging.exception("write failed %s", path)
                continue
            wrote += 1
            by_source[source] += 1
        if args.session_id and not seen:
            logging.warning("no jsonl for session-id %s", args.session_id)
        logging.info(
            "backfill done wrote=%d custom-title=%d index=%d unchanged=%d "
            "skip-no-title=%d failed=%d elapsed=%.2fs",
            wrote,
            by_source["custom-title"],
            by_source["index"],
            unchanged,
            skip_no_title,
            failed,
            time.time() - t0,
        )
        return 1 if failed else 0
    except Exception:
        logging.exception("backfill failed")
        return 1
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fh.close()


if __name__ == "__main__":
    raise SystemExit(main())
