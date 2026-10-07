"""What every agent's session sync shares: the copy rule, atomic writes, SQLite
backups, and the open-file check that says whether an app is still running.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from ..errors import DevkitError


@dataclass(frozen=True)
class Side:
    """One end of a sync. A directory is None when that agent is not installed there."""
    name: str
    desktop: Path | None
    code: Path | None
    codex: Path | None
    cursor: Path | None


@dataclass
class Step:
    """One unit of work. `line` is None when there is nothing to do."""
    line: str | None
    run: Callable[[], None]


@dataclass
class Copy:
    label: str
    todo: list[tuple[Path, Path]] = field(default_factory=list)
    new: int = 0
    newer: int = 0
    unchanged: int = 0
    size: int = 0

    def describe(self) -> str:
        return (f"{self.label}: {self.new} new, {self.newer} newer, "
                f"{self.unchanged} unchanged ({self.size / 1e6:.1f} MB to copy)")

    def step(self) -> Step:
        def run() -> None:
            for src, dst in self.todo:
                copy_atomic(src, dst)
        return Step(self.describe() if self.todo else None, run)


def plan_copy(label: str, wanted: Iterable[tuple[Path, Path]]) -> Copy:
    """Copy when the target lacks the file or the source is newer. Never the reverse."""
    copy = Copy(label)
    for src, dst in wanted:
        if not dst.is_file():
            copy.new += 1
        elif src.stat().st_mtime > dst.stat().st_mtime:
            copy.newer += 1
        else:
            copy.unchanged += 1
            continue
        copy.todo.append((src, dst))
        copy.size += src.stat().st_size
    return copy


def files_under(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            yield path


def copy_atomic(src: Path, dst: Path) -> None:
    """A cut-off copy must not look finished: copy2 stamps the mtime last."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    partial = dst.with_name(dst.name + ".devkit-partial")
    shutil.copy2(src, partial)
    os.replace(partial, dst)


def sqlite_uri(path: Path, mode: str) -> str:
    return f"file:{quote(str(path))}?mode={mode}"


def backup_sqlite(path: Path) -> Path:
    """A consistent copy beside the database, taken before the first write to it."""
    need = path.stat().st_size
    if shutil.disk_usage(path.parent).free < need * 1.1:
        raise DevkitError(f"not enough free disk to back up {path.name} ({need / 1e9:.1f} GB)",
                          "free some space, then re-run")
    backup = path.with_name(f"{path.name}.devkit-backup-{time.strftime('%Y%m%dT%H%M%S')}")
    source = sqlite3.connect(sqlite_uri(path, "ro"), uri=True)
    target = sqlite3.connect(backup)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return backup


def read_proc(path: Path) -> str:
    try:
        return path.read_bytes().decode(errors="replace")
    except OSError:
        return ""


def holders(label: str, roots: Iterable[Path],
            proc: Path = Path("/proc")) -> list[tuple[str, str]]:
    """Processes with a file open under any root: the app is still running."""
    wanted = [str(root) for root in roots]
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            links = [os.readlink(fd) for fd in (entry / "fd").iterdir()]
        except OSError:
            continue
        if any(link == root or link.startswith(root + "/")
               for link in links for root in wanted):
            found.append((label, entry.name))
    return found
