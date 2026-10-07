"""Codex threads.

CODEX_HOME holds each thread as a rollout file under sessions/ or
archived_sessions/, a `threads` row in state_N.sqlite that lists it, and a line
in session_index.jsonl. Rollouts are copied byte for byte. A thread's row is
copied when the target lacks it, with rollout_path rewritten to the target home;
project and section ids are local to one database and are left unset.
thread_history_1.sqlite is not copied: it is a projection of the rollouts and
Codex rebuilds it for a thread it has no state for.

The state database is versioned in its name. It is merged only when the target
has one of the same name; otherwise the files are copied and Codex indexes them
itself.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from ..common import relative_to_home
from ..errors import DevkitError
from .common import Step, backup_sqlite, files_under, plan_copy, sqlite_uri

ROLLOUT_DIRS = ("sessions", "archived_sessions")
INDEX = "session_index.jsonl"
LOCAL_COLUMNS = {"project_id", "thread_section_id", "section_position",
                 "section_entered_at_ms"}
BUMPED_COLUMNS = ("updated_at", "updated_at_ms")


def _rollouts(src: Path, dst: Path) -> Iterable[tuple[Path, Path]]:
    for name in ROLLOUT_DIRS:
        if (src / name).is_dir():
            for path in files_under(src / name):
                yield path, dst / path.relative_to(src)


def _state_db(home: Path) -> Path | None:
    def version(path: Path) -> int:
        tail = path.stem.split("_", 1)[1]
        return int(tail) if tail.isdigit() else -1
    found = sorted(home.glob("state_*.sqlite"), key=version)
    return found[-1] if found else None


def _open(path: Path, mode: str) -> sqlite3.Connection:
    return sqlite3.connect(sqlite_uri(path, mode), uri=True)


def _columns(con: sqlite3.Connection) -> dict[str, tuple]:
    return {row[1]: row for row in con.execute("pragma table_info(threads)")}


def _insert_columns(src: sqlite3.Connection, dst: sqlite3.Connection) -> list[str]:
    src_cols, dst_cols = _columns(src), _columns(dst)
    common = [c for c in dst_cols if c in src_cols and c not in LOCAL_COLUMNS]
    required = [name for name, row in dst_cols.items()
                if row[3] and row[4] is None and not row[5] and name not in common]
    if required:
        raise DevkitError(
            f"the Codex databases differ: the target needs {', '.join(required)}",
            "update both Codex installs to the same version, then re-run")
    return common


def _check_schema(src_db: Path, dst_db: Path) -> None:
    source, target = _open(src_db, "ro"), _open(dst_db, "ro")
    try:
        _insert_columns(source, target)
    finally:
        target.close()
        source.close()


def _threads(db: Path) -> dict[str, tuple[str, int]]:
    con = _open(db, "ro")
    try:
        return {row[0]: (row[1], row[2])
                for row in con.execute("select id, rollout_path, updated_at from threads")}
    finally:
        con.close()


def _index_ids(path: Path) -> dict[str, str]:
    lines = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                lines[json.loads(line)["id"]] = line
            except (ValueError, KeyError):
                continue
    return lines


def _apply_threads(src_db: Path, dst_db: Path, src: Path, dst: Path,
                   new: list[str], newer: list[str]) -> None:
    backup_sqlite(dst_db)
    source, target = _open(src_db, "ro"), _open(dst_db, "rw")
    try:
        columns = _insert_columns(source, target)
        bumped = [c for c in BUMPED_COLUMNS if c in columns]
        marks = ", ".join("?" * len(columns))
        path_at = columns.index("rollout_path")
        with target:
            for thread_id in new:
                row = list(source.execute(
                    f"select {', '.join(columns)} from threads where id=?", (thread_id,)).fetchone())
                row[path_at] = str(dst) + row[path_at][len(str(src)):]
                target.execute(f"insert into threads ({', '.join(columns)}) values ({marks})", row)
            for thread_id in newer:
                values = source.execute(
                    f"select {', '.join(bumped)} from threads where id=?", (thread_id,)).fetchone()
                target.execute(
                    f"update threads set {', '.join(c + '=?' for c in bumped)} where id=?",
                    (*values, thread_id))
    finally:
        target.close()
        source.close()


def _append_index(src: Path, dst: Path, missing: list[str]) -> None:
    lines = _index_ids(src / INDEX)
    target = dst / INDEX
    current = target.read_text(encoding="utf-8") if target.is_file() else ""
    if current and not current.endswith("\n"):
        current += "\n"
    partial = target.with_name(target.name + ".devkit-partial")
    partial.write_text(current + "".join(lines[i] + "\n" for i in missing), encoding="utf-8")
    os.replace(partial, target)


def plan(src: Path, dst: Path) -> list[Step]:
    steps: list[Step] = []
    rollouts = plan_copy("Codex rollouts", _rollouts(src, dst))
    if rollouts.new + rollouts.newer + rollouts.unchanged:
        steps.append(rollouts.step())

    src_db = _state_db(src)
    if src_db:
        dst_db = dst / src_db.name
        if not dst_db.is_file():
            print(f"note: {relative_to_home(dst_db)} does not exist yet; the rollouts are "
                  f"copied and Codex indexes them when it first starts there.")
        else:
            have, theirs = _threads(src_db), _threads(dst_db)
            new = [t for t, (path, _u) in have.items() if t not in theirs
                   and path.startswith(str(src) + "/") and Path(path).is_file()]
            newer = [t for t, (_p, updated) in have.items()
                     if t in theirs and updated > theirs[t][1]]
            if new or newer:
                _check_schema(src_db, dst_db)
                steps.append(Step(
                    f"Codex threads: {len(new)} new, {len(newer)} newer in {src_db.name} "
                    f"(backed up first, {dst_db.stat().st_size / 1e6:.1f} MB)",
                    lambda: _apply_threads(src_db, dst_db, src, dst, new, newer)))

    missing = [i for i in _index_ids(src / INDEX) if i not in _index_ids(dst / INDEX)]
    if missing:
        steps.append(Step(f"Codex session index: {len(missing)} entries added",
                          lambda: _append_index(src, dst, missing)))
    return steps
