"""Claude chats.

Claude Code keeps transcripts under <config dir>/projects. Claude Desktop keeps
one index file per chat, local_*.json, under
<user data dir>/claude-code-sessions/<account>/<org>/, and only lists the folder
of the organization the profile is signed in to. So the Desktop files are
flattened into the target's own org folder; copying the tree as is would put
them where the sidebar never looks.
"""

from __future__ import annotations

import os
import shutil
import time
from collections.abc import Iterable
from pathlib import Path

from ..common import relative_to_home
from ..errors import DevkitError
from .common import Side, Step, files_under, plan_copy, read_proc

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
