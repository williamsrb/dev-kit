"""Cursor IDE chats.

The IDE keeps them in <user data dir>/User/globalStorage/state.vscdb: one
composerHeaders row per chat (what the sidebar lists) and cursorDiskKV rows
keyed <family>:<composerId>[:<id>] for the chat itself. A chat is copied when the
target lacks it or the source was updated later: its header row and every row of
the families below, in one transaction, after a backup of the target database.

Not copied: the content-addressed rows (agentKv:blob:*, composer.content.*) and
the per-workspace databases. Their keys name no chat, so there is no way to tell
which belong to which. A chat whose header points at a workspace the target does
not know may not list under a folder until that folder is opened there.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..common import relative_to_home
from ..errors import DevkitError
from .common import Step, backup_sqlite, sqlite_uri

GLOBAL_DB = Path("User") / "globalStorage" / "state.vscdb"
FAMILIES = ("composerData", "bubbleId", "checkpointId", "codeBlockDiff",
            "codeBlockPartialInlineDiffFates", "ofsContent", "composerVirtualRowHeights",
            "composerRootWriterDiagnostic", "messageRequestContext", "composerDraft")


def _open(path: Path, mode: str) -> sqlite3.Connection:
    return sqlite3.connect(sqlite_uri(path, mode), uri=True)


def _ranges(composer_id: str):
    """(exact key, range start, range end) per family. ';' sorts right after ':'."""
    for family in FAMILIES:
        key = f"{family}:{composer_id}"
        yield key, key + ":", key + ";"


def _headers(con: sqlite3.Connection) -> dict[str, int]:
    return {row[0]: row[1] or 0
            for row in con.execute("select composerId, lastUpdatedAt from composerHeaders")}


def _weigh(con: sqlite3.Connection, composer_ids: list[str]) -> tuple[int, int]:
    rows = size = 0
    for composer_id in composer_ids:
        for key, low, high in _ranges(composer_id):
            for query, args in (("key=?", (key,)), ("key>=? and key<?", (low, high))):
                count, weight = con.execute(
                    f"select count(*), coalesce(sum(length(value)), 0) "
                    f"from cursorDiskKV where {query}", args).fetchone()
                rows, size = rows + count, size + weight
    return rows, size


def _apply(src_db: Path, dst_db: Path, composer_ids: list[str]) -> None:
    backup_sqlite(dst_db)
    con = _open(dst_db, "rw")
    try:
        con.execute("attach database ? as src", (sqlite_uri(src_db, "ro"),))
        have = {r[1] for r in con.execute("pragma main.table_info(composerHeaders)")}
        columns = ", ".join(r[1] for r in con.execute("pragma src.table_info(composerHeaders)")
                            if r[1] in have)
        with con:
            for composer_id in composer_ids:
                con.execute(f"insert or replace into main.composerHeaders ({columns}) "
                            f"select {columns} from src.composerHeaders where composerId=?",
                            (composer_id,))
                for key, low, high in _ranges(composer_id):
                    con.execute("insert or replace into main.cursorDiskKV (key, value) "
                                "select key, value from src.cursorDiskKV where key=?", (key,))
                    con.execute("insert or replace into main.cursorDiskKV (key, value) "
                                "select key, value from src.cursorDiskKV "
                                "where key>=? and key<?", (low, high))
        con.execute("detach database src")
    finally:
        con.close()


def plan(src: Path, dst: Path) -> list[Step]:
    src_db, dst_db = src / GLOBAL_DB, dst / GLOBAL_DB
    if not src_db.is_file():
        return []
    if not dst_db.is_file():
        raise DevkitError(f"{relative_to_home(dst_db)} does not exist",
                          "launch the target Cursor once, then quit it, then re-run")
    source, target = _open(src_db, "ro"), _open(dst_db, "ro")
    try:
        mine, theirs = _headers(source), _headers(target)
        todo = [c for c, updated in mine.items() if c not in theirs or updated > theirs[c]]
        new = sum(1 for c in todo if c not in theirs)
        rows, size = _weigh(source, todo)
    finally:
        target.close()
        source.close()
    if not todo:
        return [Step(None, lambda: None)]
    line = (f"Cursor chats: {new} new, {len(todo) - new} newer, {len(mine) - len(todo)} unchanged "
            f"({rows} rows, {size / 1e6:.1f} MB; {dst_db.name} "
            f"backed up first, {dst_db.stat().st_size / 1e9:.1f} GB)")
    return [Step(line, lambda: _apply(src_db, dst_db, todo))]
