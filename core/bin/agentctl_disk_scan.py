#!/usr/bin/env python3
"""Standalone disk scanner for `agentctl disk`.

Walks one disk and stores raw facts in a SQLite cache. Standard library only, so
the root-owned copy that the install script places under /usr/local/lib can run
without the rest of the harness. Never writes outside its cache directory.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SCANNER_VERSION = "1"
MIN_DIR_BYTES = 100_000_000
MIN_FILE_BYTES = 50_000_000
UNREADABLE_CAP = 500
PROGRESS_EVERY = 20_000

REAL_FSTYPES = {"btrfs", "xfs", "vfat", "f2fs", "ntfs", "ntfs3", "fuseblk", "exfat", "nfs", "nfs4"}
MANIFESTS = {
    "package.json", "Cargo.toml", "pyproject.toml", "pom.xml", "build.gradle",
    "build.gradle.kts", "go.mod", "composer.json", "Gemfile", "CMakeLists.txt",
}
REGEN_NAMES = {"node_modules", ".venv", "venv", "__pycache__"}
INHERIT_KINDS = {"trash", "cache", "regenerable", "download", "log", "tmp"}
HOME_CACHE_PREFIXES = (
    (".cache",), (".npm", "_cacache"), (".gradle", "caches"), (".cargo", "registry"),
    (".m2", "repository"),
)
CONFIG_CACHE_NAMES = {"Cache", "CachedData", "GPUCache", "Code Cache"}

_SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE run(id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, status TEXT,
  files_seen INTEGER, dirs_seen INTEGER, bytes_seen INTEGER, unreadable_count INTEGER,
  non_utf8_skipped INTEGER, duration_s REAL);
CREATE TABLE unreadable(path TEXT, errno INTEGER);
CREATE TABLE dirs(path TEXT PRIMARY KEY, bytes INTEGER, files INTEGER, newest_mtime REAL,
  newest_mtime_excl_regen REAL, kind TEXT);
CREATE TABLE files(path TEXT PRIMARY KEY, bytes INTEGER, mtime REAL, atime REAL, kind TEXT);
"""


class ScanError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def human(num: float) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1000 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1000
    return f"{value:.1f} TB"


# --- mountinfo -----------------------------------------------------------

def _unescape(field: str) -> str:
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def parse_mountinfo(text: str) -> list[dict[str, str]]:
    mounts: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if "-" not in parts[6:]:
            continue
        sep = parts.index("-", 6)
        if len(parts) < sep + 3:
            continue
        mounts.append({
            "dev": parts[2],
            "root": _unescape(parts[3]),
            "mount": _unescape(parts[4]),
            "fstype": parts[sep + 1],
            "device": _unescape(parts[sep + 2]),
        })
    return mounts


def real_mounts(mounts: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        m for m in mounts
        if (m["fstype"].startswith("ext") or m["fstype"] in REAL_FSTYPES)
    ]


def read_mountinfo() -> list[dict[str, str]]:
    # AGENTCTL_DISK_MOUNTINFO lets tests describe a fake disk layout.
    source = os.environ.get("AGENTCTL_DISK_MOUNTINFO") or "/proc/self/mountinfo"
    return parse_mountinfo(Path(source).read_text(encoding="utf-8", errors="replace"))


def mount_for_path(path: str, mounts: list[dict[str, str]]) -> dict[str, str] | None:
    best: dict[str, str] | None = None
    for mount in mounts:
        point = mount["mount"]
        inside = path == point or point == "/" or path.startswith(point.rstrip("/") + "/")
        if inside and (best is None or len(point) >= len(best["mount"])):
            best = mount
    return best


# --- classification ------------------------------------------------------

def home_of(path: str) -> str | None:
    env_home = os.environ.get("HOME", "").rstrip("/")
    if env_home and (path == env_home or path.startswith(env_home + "/")):
        return env_home
    parts = Path(path).parts
    if len(parts) >= 3 and parts[:2] == ("/", "home"):
        return "/home/" + parts[2]
    if len(parts) >= 2 and parts[:2] == ("/", "root"):
        return "/root"
    return None


def classify_path(path: str, name: str, is_dir: bool, own_names: set[str], parent_names: set[str],
                  parent_kind: str) -> str:
    """First match wins. Descendants of trash/cache/regenerable/... inherit the kind."""
    kind = _classify_by_path(path, name, is_dir, own_names, parent_names)
    if kind in ("other", "appdata", "project") and parent_kind in INHERIT_KINDS:
        return parent_kind
    return kind


def _classify_by_path(path: str, name: str, is_dir: bool, own_names: set[str],
                      parent_names: set[str]) -> str:
    home = home_of(path)
    rel = Path(path).relative_to(home).parts if home and path != home and path.startswith(home + "/") else ()
    if "/.local/share/Trash" in path + "/" or "/.Trash-" in path:
        return "trash"
    if home:
        if any(rel[:len(prefix)] == prefix for prefix in HOME_CACHE_PREFIXES):
            return "cache"
        if len(rel) >= 3 and rel[0] == ".config" and rel[2] in CONFIG_CACHE_NAMES:
            return "cache"
    if path == "/var/cache" or path.startswith("/var/cache/"):
        return "cache"
    if is_dir and name in REGEN_NAMES:
        return "regenerable"
    if is_dir and name == "target" and "Cargo.toml" in parent_names:
        return "regenerable"
    if is_dir and name == "build" and parent_names & {"build.gradle", "build.gradle.kts", "pom.xml", "package.json"}:
        return "regenerable"
    if rel[:1] == ("Downloads",):
        return "download"
    if path == "/var/log" or path.startswith("/var/log/"):
        return "log"
    if path in ("/tmp", "/var/tmp") or path.startswith(("/tmp/", "/var/tmp/")):
        return "tmp"
    if is_dir and rel and not rel[0].startswith(".") and (".git" in own_names or own_names & MANIFESTS):
        return "project"
    if rel[:1] == (".config",) and len(rel) >= 2:
        return "appdata"
    if rel[:2] == (".local", "share") and len(rel) >= 3:
        return "appdata"
    if rel[:2] == (".var", "app") and len(rel) >= 3:
        return "appdata"
    return "other"


# --- walker --------------------------------------------------------------

class _Frame:
    __slots__ = ("bytes", "entries", "files", "i", "kind", "mtime", "names", "newest", "newest_x", "path")

    def __init__(self, path: str, kind: str, entries: list[os.DirEntry], mtime: float):
        self.path = path
        self.kind = kind
        self.entries = entries
        self.names = {e.name for e in entries}
        self.i = 0
        self.bytes = 0
        self.files = 0
        self.newest = 0.0
        self.newest_x = 0.0
        self.mtime = mtime


def _storable(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def walk(root: str, *, min_dir_bytes: int = MIN_DIR_BYTES, min_file_bytes: int = MIN_FILE_BYTES,
         dev_of: Callable[[str], int] | None = None, mountpoints: set[str] | None = None,
         progress: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    """Depth-first walk of one device. Size is allocated bytes; hardlinks count once."""
    root = os.path.abspath(root)
    root_stat = os.lstat(root)
    root_dev = dev_of(root) if dev_of else root_stat.st_dev
    skip_mounts = mountpoints or set()
    dirs: list[tuple] = []
    files: list[tuple] = []
    unreadable: list[tuple[str, int]] = []
    seen_inodes: set[tuple[int, int]] = set()
    stats = {"files": 0, "dirs": 0, "non_utf8": 0, "unreadable": 0}

    def note_unreadable(path: str, code: int) -> None:
        stats["unreadable"] += 1
        if len(unreadable) < UNREADABLE_CAP and _storable(path):
            unreadable.append((path, code))

    def open_frame(path: str, name: str, mtime: float, parent_names: set[str], parent_kind: str) -> _Frame | None:
        try:
            entries = list(os.scandir(path))
        except OSError as exc:
            note_unreadable(path, exc.errno or 0)
            return None
        names = {e.name for e in entries}
        kind = classify_path(path, name, True, names, parent_names, parent_kind)
        return _Frame(path, kind, entries, mtime)

    first = open_frame(root, os.path.basename(root), root_stat.st_mtime, set(), "other")
    if first is None:
        raise ScanError(f"cannot read {root}")
    first.bytes = root_stat.st_blocks * 512
    stack = [first]
    entry_count = 0
    while stack:
        frame = stack[-1]
        if frame.i < len(frame.entries):
            entry = frame.entries[frame.i]
            frame.i += 1
            entry_count += 1
            if progress and entry_count % PROGRESS_EVERY == 0:
                progress(stats["files"], stats["dirs"])
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as exc:
                note_unreadable(entry.path, exc.errno or 0)
                continue
            decodable = _storable(entry.name)
            if not decodable:
                stats["non_utf8"] += 1
            if stat.S_ISDIR(st.st_mode):
                child_dev = dev_of(entry.path) if dev_of else st.st_dev
                if child_dev != root_dev or entry.path in skip_mounts:
                    continue
                child = open_frame(entry.path, entry.name, st.st_mtime, frame.names, frame.kind)
                if child is None:
                    frame.bytes += st.st_blocks * 512
                    continue
                child.bytes = st.st_blocks * 512
                stack.append(child)
                continue
            size = st.st_blocks * 512
            if st.st_nlink > 1:
                key = (st.st_dev, st.st_ino)
                if key in seen_inodes:
                    size = 0
                else:
                    seen_inodes.add(key)
            frame.bytes += size
            frame.files += 1
            stats["files"] += 1
            frame.newest = max(frame.newest, st.st_mtime)
            frame.newest_x = max(frame.newest_x, st.st_mtime)
            if size >= min_file_bytes and decodable and _storable(entry.path):
                files.append((entry.path, size, st.st_mtime, st.st_atime, frame.kind))
            continue
        stack.pop()
        stats["dirs"] += 1
        if frame.newest == 0.0:
            frame.newest = frame.mtime
        if frame.newest_x == 0.0:
            frame.newest_x = frame.mtime
        if frame.bytes >= min_dir_bytes and _storable(frame.path):
            dirs.append((frame.path, frame.bytes, frame.files, frame.newest, frame.newest_x, frame.kind))
        if stack:
            parent = stack[-1]
            parent.bytes += frame.bytes
            parent.files += frame.files
            parent.newest = max(parent.newest, frame.newest)
            if frame.kind not in ("regenerable", "cache"):
                parent.newest_x = max(parent.newest_x, frame.newest_x)
        else:
            stats["bytes"] = frame.bytes
    return {
        "dirs": dirs, "files": files, "unreadable": unreadable,
        "files_seen": stats["files"], "dirs_seen": stats["dirs"], "bytes_seen": stats.get("bytes", 0),
        "unreadable_count": stats["unreadable"], "non_utf8_skipped": stats["non_utf8"],
    }


# --- cache ---------------------------------------------------------------

def target_id_for(path: str) -> str:
    if path == "/":
        return "root"
    return "mnt-" + (re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-") or "root")


def write_cache(db_path: Path, result: dict[str, Any], meta: dict[str, str], started_at: str,
                duration_s: float) -> None:
    tmp = db_path.with_name(db_path.name + f".tmp{os.getpid()}")
    tmp.unlink(missing_ok=True)
    try:
        con = sqlite3.connect(tmp)
        con.executescript(_SCHEMA)
        con.executemany("INSERT INTO meta VALUES (?,?)", list(meta.items()))
        con.execute(
            "INSERT INTO run(started_at, finished_at, status, files_seen, dirs_seen, bytes_seen,"
            " unreadable_count, non_utf8_skipped, duration_s) VALUES (?,?,?,?,?,?,?,?,?)",
            (started_at, utc_now(), "ok", result["files_seen"], result["dirs_seen"], result["bytes_seen"],
             result["unreadable_count"], result["non_utf8_skipped"], round(duration_s, 2)),
        )
        con.executemany("INSERT INTO unreadable VALUES (?,?)", result["unreadable"])
        con.executemany("INSERT OR REPLACE INTO dirs VALUES (?,?,?,?,?,?)", result["dirs"])
        con.executemany("INSERT OR REPLACE INTO files VALUES (?,?,?,?,?)", result["files"])
        con.commit()
        con.close()
        os.chmod(tmp, 0o640)
        os.replace(tmp, db_path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def read_status(cache_dir: Path, target_id: str) -> dict[str, Any]:
    try:
        return json.loads((cache_dir / f"{target_id}.status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_status(cache_dir: Path, target_id: str, status: dict[str, Any]) -> None:
    path = cache_dir / f"{target_id}.status.json"
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(status, separators=(",", ":")), encoding="utf-8")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def lock_is_free(cache_dir: Path, target_id: str) -> bool:
    try:
        handle = open(cache_dir / f"{target_id}.lock", "a")  # noqa: SIM115 - closed in finally below
    except OSError:
        return True
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        return exc.errno not in (errno.EAGAIN, errno.EACCES)
    finally:
        handle.close()
    return True


def scan_target(root_path: str, target_id: str, cache_dir: Path, *, min_dir_bytes: int = MIN_DIR_BYTES,
                min_file_bytes: int = MIN_FILE_BYTES, walker: Callable[..., dict[str, Any]] = walk,
                mounts: list[dict[str, str]] | None = None) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    lock = open(cache_dir / f"{target_id}.lock", "a")  # noqa: SIM115 - held for the whole scan
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        return {"status": "locked", "target": target_id}
    started_at = utc_now()
    started = time.monotonic()
    previous = read_status(cache_dir, target_id)
    status = {k: previous[k] for k in ("last_ok_at", "last_result") if k in previous}
    status.update({"state": "running", "pid": os.getpid(), "target": target_id, "started_at": started_at})
    write_status(cache_dir, target_id, status)
    try:
        all_mounts = mounts if mounts is not None else read_mountinfo()
        mount = mount_for_path(os.path.abspath(root_path), all_mounts) or {"mount": "/", "device": ""}
        skip = {m["mount"] for m in all_mounts if m["mount"] != os.path.abspath(root_path)}

        def progress(files_seen: int, dirs_seen: int) -> None:
            write_status(cache_dir, target_id, {**status, "files_seen": files_seen, "dirs_seen": dirs_seen})

        result = walker(root_path, min_dir_bytes=min_dir_bytes, min_file_bytes=min_file_bytes,
                        mountpoints=skip, progress=progress)
        duration = time.monotonic() - started
        meta = {
            "schema_version": str(SCHEMA_VERSION), "target_id": target_id, "mount": mount["mount"],
            "device": mount.get("device", ""), "root_path": os.path.abspath(root_path),
            "scanner_version": SCANNER_VERSION,
        }
        write_cache(cache_dir / f"{target_id}.sqlite", result, meta, started_at, duration)
        summary = {
            "files_seen": result["files_seen"], "dirs_seen": result["dirs_seen"],
            "bytes_seen": result["bytes_seen"], "unreadable_count": result["unreadable_count"],
            "duration_s": round(duration, 2),
        }
        done = {"state": "finished", "target": target_id, "started_at": started_at,
                "finished_at": utc_now(), "last_ok_at": utc_now(), "last_result": summary}
        write_status(cache_dir, target_id, done)
        return {"status": "ok", "target": target_id, **summary}
    except Exception as exc:  # noqa: BLE001 - any failure must leave the old cache and report
        failed = {**{k: previous[k] for k in ("last_ok_at", "last_result") if k in previous},
                  "state": "failed", "target": target_id, "started_at": started_at,
                  "finished_at": utc_now(), "error": f"{type(exc).__name__}: {exc}"}
        write_status(cache_dir, target_id, failed)
        return {"status": "failed", "target": target_id, "error": failed["error"]}
    finally:
        lock.close()


def start_background(argv: list[str]) -> int:
    proc = subprocess.Popen(
        argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return proc.pid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentctl_disk_scan.py",
        description="Walk one disk and write a SQLite cache of sizes and ages. Read-only on the scanned disk.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Scan one target and write its cache atomically.")
    scan.add_argument("--target", required=True, help="Directory to walk, for example / or /home/me.")
    scan.add_argument("--cache-dir", required=True, type=Path, help="Directory for <id>.sqlite and status files.")
    scan.add_argument("--id", help="Cache id; default derived from --target ('/' becomes root).")
    scan.add_argument("--min-dir-bytes", type=int, default=MIN_DIR_BYTES, help="Smallest directory row stored.")
    scan.add_argument("--min-file-bytes", type=int, default=MIN_FILE_BYTES, help="Smallest file row stored.")
    scan.add_argument("--quiet", action="store_true", help="Print nothing on success.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = scan_target(args.target, args.id or target_id_for(os.path.abspath(args.target)),
                         args.cache_dir, min_dir_bytes=args.min_dir_bytes, min_file_bytes=args.min_file_bytes)
    if not (args.quiet and result["status"] in ("ok", "locked")):
        print(json.dumps(result, separators=(",", ":")))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
