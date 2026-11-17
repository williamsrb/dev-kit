"""Claude chats.

Claude Code keeps transcripts under <config dir>/projects. Claude Desktop keeps
one index file per chat, local_*.json, under
<user data dir>/claude-code-sessions/<account>/<org>/, and only lists the folder
of the organization the profile is signed in to. So the Desktop files are
flattened into the target's own org folder; copying the tree as is would put
them where the sidebar never looks.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Iterable
from pathlib import Path

from ..common import relative_to_home
from ..errors import DevkitError
from .common import Copy, Side, Step, files_under, plan_copy, read_proc

SESSIONS = "claude-code-sessions"
INDEXEDDB = "IndexedDB"
STOCK = "stock"


def _code_files(src: Path, dst: Path) -> Iterable[tuple[Path, Path]]:
    root = src / "projects"
    for path in files_under(root):
        yield path, dst / "projects" / path.relative_to(root)


def _desktop_files(src: Path, org_dir: Path) -> Iterable[tuple[Path, Path]]:
    newest: dict[str, Path] = {}
    for path in (src / SESSIONS).glob("*/*/local_*.json"):
        known = newest.get(path.name)
        if known is None or path.stat().st_mtime > known.stat().st_mtime:
            newest[path.name] = path
    for name, path in sorted(newest.items()):
        yield path, org_dir / name


def _target_org(desktop: Path) -> Path:
    orgs = [p for p in (desktop / SESSIONS).glob("*/*") if p.is_dir()]
    if not orgs:
        raise DevkitError(
            f"{relative_to_home(desktop)} has no signed-in organization folder yet",
            "open that Desktop, sign in, start one chat, quit it, then re-run")
    return max(orgs, key=lambda p: (sum(1 for _ in p.glob("local_*.json")), p.name))


def desktop_entries(desktop: Path) -> Iterable[tuple[Path, dict]]:
    """Every Desktop index file that parses, with its decoded content."""
    for path in sorted((desktop / SESSIONS).glob("*/*/local_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            yield path, data


def transcripts(code: Path, session_id: str) -> list[Path]:
    """Every projects/*/<id>.jsonl: one session id can sit under two folders."""
    return sorted((code / "projects").glob(f"*/{session_id}.jsonl"))


def transcript_title(path: Path) -> str | None:
    """The last custom-title record, else the last ai-title record.

    Only lines holding the record type are parsed: transcripts reach hundreds
    of MB, and decoding every line would miss the finder's time target.
    """
    found: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                for kind, key in (("custom-title", "customTitle"), ("ai-title", "aiTitle")):
                    if f'"{kind}"' in line:
                        try:
                            record = json.loads(line)
                        except ValueError:
                            continue
                        if record.get("type") == kind and record.get(key):
                            found[kind] = str(record[key])
    except OSError:
        return None
    return found.get("custom-title") or found.get("ai-title")


def transcript_cwd(path: Path, limit: int = 200) -> str | None:
    """Working folder of a transcript-only session: the first record with `cwd`."""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for _, line in zip(range(limit), handle):
                if '"cwd"' in line:
                    try:
                        cwd = json.loads(line).get("cwd")
                    except ValueError:
                        continue
                    if cwd:
                        return str(cwd)
    except OSError:
        return None
    return None


def target_org(dst: Side, org: Path | None) -> Path:
    if org is None:
        return _target_org(dst.desktop)
    sessions = dst.desktop / SESSIONS
    if not org.is_dir() or org.resolve().parent.parent != sessions.resolve():
        raise DevkitError(f"{org} is not an organization folder of {dst.name}",
                          f"pass one of {relative_to_home(sessions)}/<account>/<org>")
    return org


def plan_one(src: Side, dst: Side, session_id: str, org: Path | None = None) -> Copy:
    """One session: its transcripts, their sidecar folders and its Desktop index file."""
    found = transcripts(src.code, session_id)
    indexes = [p for p, data in desktop_entries(src.desktop)
               if data.get("cliSessionId") == session_id]
    if not found and not indexes:
        raise DevkitError(f"session {session_id} is not on {src.name}",
                          "'devkit profile session-find --title ...' lists ids")
    root = src.code / "projects"
    wanted: list[tuple[Path, Path]] = []
    for transcript in found:
        wanted.append((transcript, dst.code / "projects" / transcript.relative_to(root)))
        sidecar = transcript.with_suffix("")
        for path in files_under(sidecar) if sidecar.is_dir() else ():
            wanted.append((path, dst.code / "projects" / path.relative_to(root)))
    if indexes:
        newest = max(indexes, key=lambda p: p.stat().st_mtime)
        wanted.append((newest, target_org(dst, org) / newest.name))
    return plan_copy(f"session {session_id}", wanted)


def _accounts(desktop: Path) -> set[str]:
    return {p.name for p in (desktop / SESSIONS).glob("*") if p.is_dir()}


def _replace_indexeddb(src: Path, dst: Path) -> None:
    if dst.exists():
        dst.rename(dst.with_name(f"{INDEXEDDB}.devkit-backup-{time.strftime('%Y%m%dT%H%M%S')}"))
    shutil.copytree(src, dst, symlinks=True)


def plan(src: Side, dst: Side, only: str | None, indexeddb: bool) -> list[Step]:
    steps: list[Step] = []
    if only != "desktop" and (src.code / "projects").is_dir():
        steps.append(plan_copy("Claude Code transcripts", _code_files(src.code, dst.code)).step())
    if only != "code" and any((src.desktop / SESSIONS).glob("*/*/local_*.json")):
        org_dir = _target_org(dst.desktop)
        if not _accounts(src.desktop) <= _accounts(dst.desktop):
            print(f"note: {src.name} and {dst.name} are signed in to different accounts; "
                  f"the copied Claude chats will show up under {dst.name}'s account.")
        steps.append(plan_copy("Claude Desktop chats", _desktop_files(src.desktop, org_dir)).step())
    if indexeddb:
        source_db = src.desktop / INDEXEDDB
        if not source_db.is_dir():
            raise DevkitError(f"{relative_to_home(source_db)} does not exist",
                              "drop --indexeddb, or pick a source that has Desktop web history")
        target_db = dst.desktop / INDEXEDDB
        steps.append(Step(
            f"replace {relative_to_home(target_db)} from {relative_to_home(source_db)} "
            f"(old one kept as a backup)",
            lambda: _replace_indexeddb(source_db, target_db)))
    return steps


def running(side: Side, desktop: bool, code: bool,
            proc: Path = Path("/proc")) -> list[tuple[str, str]]:
    """Processes that hold the side's Desktop or Code data open.

    Code is matched on comm `claude` only: every child of a Claude session
    inherits CLAUDE_CONFIG_DIR, devkit itself included. A stock Desktop is its
    main process: the forks' Chromium children carry no --user-data-dir either.
    Chromium rewrites its argv into one space-joined string, hence the split.
    """
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        comm = read_proc(entry / "comm").strip()
        args = read_proc(entry / "cmdline").replace("\0", " ").split()
        flags = [a for a in args if a.startswith("--user-data-dir=")]
        if desktop:
            if side.name == STOCK:
                held = (comm.startswith("claude-desktop") and not flags
                        and not any(a.startswith("--type=") for a in args))
            else:
                held = f"--user-data-dir={side.desktop}" in flags
            if held:
                found.append(("Desktop", entry.name))
        if code and comm == "claude":
            configured = next((line.split("=", 1)[1] for line in
                               read_proc(entry / "environ").split("\0")
                               if line.startswith("CLAUDE_CONFIG_DIR=")), "")
            if configured == str(side.code) or (side.name == STOCK and not configured):
                found.append(("Code", entry.name))
    return found
