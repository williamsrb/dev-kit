"""`agentctl disk`: read-only disk clean-up report for an AI agent.

Filesystem findings come from a SQLite cache that agentctl_disk_scan.py writes;
package-manager findings are collected live. Nothing here deletes anything: a
finding carries a suggested command string for the operator to approve.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import sqlite3
import sys
import time
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import agentctl_disk_collectors as collectors
import agentctl_disk_scan as scanner
from agentctl_common import agents_home
from agentctl_disk_collectors import Ctx, make_finding, parse_size
from agentctl_disk_scan import mount_for_path, read_mountinfo, real_mounts

RISKS = ("safe", "review", "danger")
CACHE_CATEGORIES = ("caches", "home-regenerable", "home-stale", "trash", "downloads", "big-files", "system")
LIVE_ONLY_CATEGORIES = ("docker", "apps")
CATEGORIES = CACHE_CATEGORIES + LIVE_ONLY_CATEGORIES
DEFAULTS: dict[str, Any] = {
    "min_dir_bytes": scanner.MIN_DIR_BYTES, "min_file_bytes": scanner.MIN_FILE_BYTES, "stale_days": 180,
    "collector_timeout_s": 20, "live_min_bytes": 10_000_000, "protected_paths": [], "ignore_globs": [],
}
DEFAULT_MAX_BYTES = 16384
INDEX_CAP = 5000
INDEX_KEEP_DAYS = 30
SIZE_DRIFT = 0.05
PRIORITY = {"trash": 0, "cache": 1, "regenerable": 2, "download": 3, "log": 3, "tmp": 3, "project": 4, "appdata": 4, "other": 5}
ARCHIVE_EXT = (".deb", ".rpm", ".appimage", ".iso", ".zip", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".tar.bz2",
               ".7z", ".rar", ".exe", ".msi", ".dmg", ".run", ".snap", ".flatpak", ".img")
NATIVE_CACHE_COMMANDS = {".npm/_cacache": "npm cache clean --force", ".cache/uv": "uv cache clean",
                         ".cache/pip": "pip cache purge"}
INSTALL_SCRIPT = "~/.agents/bin/agentctl-disk-root-install.py"
REASONING = {
    "caches": "Package and application caches are rebuilt on demand, so removing them is safe; the next use is slower.",
    "home-regenerable": "Build directories in a project untouched for the stale window can be recreated from the manifest.",
    "home-stale": "Nothing in this item changed within the stale window. Confirm the work is committed or unneeded first.",
    "trash": "Emptying Trash is permanent: the items cannot be restored afterward.",
    "downloads": "Installers and archives in Downloads can usually be fetched again, but check before removing.",
    "big-files": "A large file with no known role. Only the owner can say whether it is needed.",
    "system": "System files need root to remove. Review what writes them before deleting.",
    "docker": "Docker items are listed from docker itself. Volumes hold data and removal is permanent.",
    "apps": "Package-manager leftovers; the package manager decides what is safe to remove.",
}


class DiskError(Exception):
    """User-facing disk-group failure; main() prints it as JSON."""


# --- parsers and output --------------------------------------------------

def parse_size_flag(value: str, flag: str) -> int:
    try:
        return parse_size(value)
    except ValueError:
        raise DiskError(f"{flag}: cannot parse {value!r}; accepted forms: 500M, 2GB, 2GiB") from None


def parse_duration(value: str, flag: str) -> timedelta:
    match = re.fullmatch(r"\s*(\d+)\s*([hdwmy])\s*", value)
    if not match:
        raise DiskError(f"{flag}: cannot parse {value!r}; accepted forms: 36h, 90d, 6m, 1y")
    count, unit = int(match.group(1)), match.group(2)
    return timedelta(hours=count) if unit == "h" else timedelta(days=count * {"d": 1, "w": 7, "m": 30, "y": 365}[unit])


def parse_age(value: str, flag: str, now: float | None = None) -> float:
    """Return the epoch cutoff: items last used before it match. Accepts 90d, 6m, 1y or an ISO date."""
    now = time.time() if now is None else now
    if re.fullmatch(r"\s*\d+\s*[hdwmy]\s*", value):
        return now - parse_duration(value, flag).total_seconds()
    try:
        return datetime.fromisoformat(value.strip()).astimezone().timestamp()
    except ValueError:
        raise DiskError(f"{flag}: cannot parse {value!r}; accepted forms: 90d, 6m, 1y, 2025-01-31") from None


def dumps(payload: Any, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(payload, indent=2, ensure_ascii=False)
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def out(payload: Any, pretty: bool = False) -> None:
    print(dumps(payload, pretty))


def load_config() -> dict[str, Any]:
    path = Path(os.environ.get("AGENTCTL_DISK_CONFIG") or agents_home() / "config" / "disk.toml")
    config = dict(DEFAULTS)
    if not path.is_file():
        return config
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise DiskError(f"config {path}: {exc}") from None
    for key, value in data.items():
        if key not in DEFAULTS:
            continue
        if key.endswith("_bytes") and isinstance(value, str):
            value = parse_size_flag(value, f"{path.name}:{key}")
        config[key] = value
    return config


def state_dir() -> Path:
    return Path(os.environ.get("AGENTCTL_DISK_STATE") or Path.home() / ".local" / "state" / "agentctl" / "disk")


def root_state_dir() -> Path:
    return Path(os.environ.get("AGENTCTL_DISK_ROOT_STATE") or "/var/lib/agentctl-disk")


# --- targets -------------------------------------------------------------

def disk_figures(mount: str) -> dict[str, int]:
    st = os.statvfs(mount)
    return {"size": st.f_blocks * st.f_frsize, "used": (st.f_blocks - st.f_bfree) * st.f_frsize,
            "avail": st.f_bavail * st.f_frsize}


def _target(name: str, tid: str, mount: dict[str, str], root_path: str) -> dict[str, str]:
    return {"id": tid, "name": name, "mount": mount["mount"], "device": mount["device"],
            "fstype": mount["fstype"], "root_path": root_path}


def _mount_target(mount: dict[str, str]) -> dict[str, str]:
    return _target(mount["mount"], scanner.target_id_for(mount["mount"]), mount, mount["mount"])


def resolve_target(name: str, *, mounts: list[dict[str, str]] | None = None,
                   home: str | None = None) -> dict[str, str]:
    """home | root | mount point | device path | label | plain path -> mount, device and scan root."""
    allm = mounts if mounts is not None else read_mountinfo()
    disks = real_mounts(allm)
    home = home or os.path.expanduser("~")

    def owner(path: str) -> dict[str, str]:
        found = mount_for_path(path, allm)
        if not found or found not in disks:
            raise DiskError(f"{path} is not on a disk filesystem ({found['fstype'] if found else 'unknown'}); "
                            "use home, root, a mount point or a device path")
        return found

    if name == "home":
        return _target("home", "home", owner(os.path.realpath(home)), home)
    if name == "root":
        return _target("root", "root", owner("/"), "/")
    label = Path("/dev/disk/by-label") / name
    if name.startswith("/dev/") or ("/" not in name and label.exists()):
        dev = os.path.realpath(name if name.startswith("/dev/") else label)
        hits = [m for m in disks if os.path.realpath(m["device"]) == dev]
        if not hits:
            raise DiskError(f"{name}: no mounted disk uses this device; run `agentctl disk targets`")
        if len(hits) > 1:
            raise DiskError(f"{name} has {len(hits)} mounts ({', '.join(m['mount'] for m in hits)}); "
                            "name the mount point instead")
        return _mount_target(hits[0])
    path = os.path.realpath(os.path.expanduser(name))
    if not os.path.exists(path):
        raise DiskError(f"target {name!r} not found; accepted: home, root, /mnt/data, /dev/sdb1, a directory path")
    return _mount_target(owner(path))


def scan_targets(*, mounts: list[dict[str, str]] | None = None, home: str | None = None) -> list[dict[str, str]]:
    """What `scan --all` walks: root, home when it is on its own disk, every other real mount."""
    allm = mounts if mounts is not None else read_mountinfo()
    home = home or os.path.expanduser("~")
    targets = [resolve_target("root", mounts=allm, home=home)]
    home_target = resolve_target("home", mounts=allm, home=home)
    if home_target["mount"] != "/":
        targets.append(home_target)
    for mount in real_mounts(allm):
        if mount["mount"] not in ("/", home_target["mount"]) and mount["root"] == "/":
            targets.append(_mount_target(mount))
    return targets


def list_targets(*, mounts: list[dict[str, str]] | None = None, home: str | None = None) -> list[dict[str, Any]]:
    allm = mounts if mounts is not None else read_mountinfo()
    rows = [resolve_target("home", mounts=allm, home=home), resolve_target("root", mounts=allm, home=home)]
    seen_ids = {r["id"] for r in rows}
    for mount in real_mounts(allm):
        entry = _mount_target(mount)
        if entry["id"] not in seen_ids and mount["root"] == "/":
            rows.append(entry)
            seen_ids.add(entry["id"])
    for row in rows:
        row.update(disk_figures(row["mount"]))
        row["cache"] = cache_age(row["id"])
    return rows


def _parse_ts(text: str | None) -> float | None:
    try:
        return datetime.strptime(text or "", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()
    except ValueError:
        return None


def cache_age(target_id: str) -> dict[str, Any] | None:
    best = None
    for source, directory in _cache_dirs(target_id):
        status = scanner.read_status(directory, target_id)
        finished = _parse_ts(status.get("last_ok_at"))
        if finished and (best is None or (source == "root", finished) > (best[1] == "root", best[0])):
            best = (finished, source)
    if best is None:
        return None
    return {"scanned_at": datetime.fromtimestamp(best[0], UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "age_hours": round((time.time() - best[0]) / 3600, 1), "source": best[1]}


def _cache_dirs(target_id: str) -> list[tuple[str, Path]]:
    dirs = [("user", state_dir())]
    if target_id == "root":
        dirs.append(("root", root_state_dir()))
    return dirs


# --- cache access --------------------------------------------------------

def open_caches(target: dict[str, str]) -> tuple[dict[str, Any] | None, bool]:
    """Root cache when present (it has no unreadable gap), else the user cache; plus whether a wrong-schema
    cache was seen. A nightly user-level walk of / must not hide an installed root scan."""
    found: list[dict[str, Any]] = []
    mismatch = False
    for source, directory in _cache_dirs(target["id"]):
        path = directory / f"{target['id']}.sqlite"
        try:
            if not path.exists():
                continue
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            meta = dict(con.execute("SELECT key, value FROM meta"))
            if meta.get("schema_version") != str(scanner.SCHEMA_VERSION):
                mismatch = True
                con.close()
                continue
            run = con.execute("SELECT started_at, finished_at, files_seen, dirs_seen, bytes_seen,"
                              " unreadable_count, duration_s FROM run ORDER BY id DESC LIMIT 1").fetchone()
        except (sqlite3.Error, OSError):
            continue
        found.append({"con": con, "meta": meta, "run": run, "source": source, "finished": _parse_ts(run[1]) or 0.0})
    if not found:
        return None, mismatch
    best = max(found, key=lambda c: (c["source"] == "root", c["finished"]))
    for other in found:
        if other is not best:
            other["con"].close()
    return best, mismatch


def _container_roots(path: str) -> set[str]:
    home = scanner.home_of(path)
    roots = {"/var/log", "/tmp", "/var/tmp", "/var/cache"}
    if home:
        roots |= {home + "/.cache", home + "/Downloads"}
    return roots


def _swap_files() -> set[str]:
    try:
        lines = Path(os.environ.get("AGENTCTL_DISK_SWAPS") or "/proc/swaps").read_text().splitlines()[1:]
    except OSError:
        return set()
    return {line.split()[0] for line in lines if line.split()}


def _quoted_rm(path: str, is_dir: bool, needs_sudo: bool) -> str:
    cmd = ["rm", "-rf", "--", path] if is_dir else ["rm", "--", path]
    return ("sudo " if needs_sudo else "") + " ".join(shlex.quote(p) for p in cmd)


def _writable_parent(path: str) -> bool:
    return os.access(os.path.dirname(path), os.W_OK)


def _stale_project(con: sqlite3.Connection, path: str, own_newest: float, cutoff: float) -> bool:
    for parent in Path(path).parents:
        row = con.execute("SELECT newest_mtime_excl_regen FROM dirs WHERE path=? AND kind='project'",
                          (str(parent),)).fetchone()
        if row:
            return row[0] < cutoff
    return own_newest < cutoff


def cache_findings(con: sqlite3.Connection, cfg: dict[str, Any], now: float) -> list[dict[str, Any]]:
    cutoff = now - cfg["stale_days"] * 86400
    swaps = _swap_files()
    found: list[dict[str, Any]] = []

    def add(finding: dict[str, Any], kind: str, is_dir: bool) -> None:
        finding["_prio"] = PRIORITY[kind]
        finding["_dir"] = is_dir
        found.append(finding)

    def candidate(path: str, nbytes: int, kind: str, is_dir: bool, newest: float, newest_x: float,
                  atime: float | None) -> None:
        if path in _container_roots(path):
            return
        home = scanner.home_of(path)
        parent = os.path.dirname(path)
        sudo = not _writable_parent(path)
        evidence_age = f"newest change {datetime.fromtimestamp(newest).date()}"
        name = os.path.basename(path.rstrip("/")) or path
        if kind == "trash":
            add(make_finding("trash", path, f"Trash {name}" if path.count("/") > 4 else "Trash", path, nbytes,
                             risk="review", command="gio trash --empty", last_used=newest,
                             evidence="permanent: emptied Trash cannot be restored"), "trash", is_dir)
        elif kind == "cache":
            cmd = next((c for key, c in NATIVE_CACHE_COMMANDS.items() if home and path == f"{home}/{key}"), None)
            add(make_finding("caches", path, f"Cache {name}", path, nbytes, risk="safe", regenerable=True,
                             reversible=True, command=cmd or _quoted_rm(path, is_dir, sudo), needs_sudo=sudo and not cmd,
                             last_used=newest, evidence=evidence_age), "cache", is_dir)
        elif kind == "regenerable":
            if is_dir and _stale_project(con, path, newest, cutoff):
                add(make_finding("home-regenerable", path, f"Regenerable {name} in {os.path.basename(parent)}",
                                 path, nbytes, risk="safe", regenerable=True, reversible=True,
                                 command=_quoted_rm(path, True, sudo), needs_sudo=sudo, last_used=newest,
                                 evidence=f"project idle since {datetime.fromtimestamp(newest).date()}"),
                    "regenerable", True)
        elif kind == "download":
            rel = Path(path).relative_to(home).parts if home else ()
            if is_dir and len(rel) != 2:
                return
            archive = (not is_dir) and path.lower().endswith(ARCHIVE_EXT)
            category = "downloads" if (is_dir or archive) else "big-files"
            add(make_finding(category, path, f"Download {name}", path, nbytes, risk="review",
                             command=_quoted_rm(path, is_dir, sudo), needs_sudo=sudo, last_used=newest,
                             evidence=evidence_age), "download", is_dir)
        elif kind == "project":
            if is_dir and newest_x < cutoff:
                add(make_finding("home-stale", path, f"Idle project {name}", path, nbytes, risk="review",
                                 command=_quoted_rm(path, True, sudo), needs_sudo=sudo, last_used=newest_x,
                                 verify_command=f"git -C {shlex.quote(path)} status --short; git -C "
                                                f"{shlex.quote(path)} log -1 --format=%cr",
                                 evidence=f"no change outside build dirs since {datetime.fromtimestamp(newest_x).date()}"),
                    "project", True)
        elif kind == "appdata":
            if is_dir:
                add(make_finding("home-stale", path, f"App data {name}", path, nbytes, risk="danger",
                                 last_used=newest_x, evidence="live application data; informational only"),
                    "appdata", True)
        elif kind in ("log", "tmp"):
            add(make_finding("system", path, f"{'Log' if kind == 'log' else 'Temp'} {name}", path, nbytes,
                             risk="review", regenerable=True, command=_quoted_rm(path, is_dir, sudo),
                             needs_sudo=sudo, last_used=newest, evidence=evidence_age), kind, is_dir)
        elif not is_dir and path in swaps:
            add(make_finding("big-files", path, f"Swap file {name}", path, nbytes, risk="danger",
                             last_used=newest, evidence="active swap file; informational only"), "other", False)
        elif not is_dir:
            add(make_finding("big-files", path, f"Large file {name}", path, nbytes, risk="review",
                             command=_quoted_rm(path, False, sudo), needs_sudo=sudo, last_used=newest,
                             evidence=(f"modified {datetime.fromtimestamp(newest).date()}"
                                       + (f", read {datetime.fromtimestamp(atime).date()}" if atime else ""))),
                "other", False)

    for path, nbytes, _files, newest, newest_x, kind in con.execute("SELECT * FROM dirs"):
        candidate(path, nbytes, kind, True, newest, newest_x, None)
    for path, nbytes, mtime, atime, kind in con.execute("SELECT * FROM files"):
        if kind in ("regenerable", "appdata"):
            continue
        candidate(path, nbytes, "other" if kind == "project" else kind, False, mtime, mtime, atime)
    return found


def remove_overlaps(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Highest priority wins; an ancestor and a descendant never both stay, so totals do not double count."""
    kept: list[dict[str, Any]] = []
    kept_paths: set[str] = set()
    ancestors: set[str] = set()
    for item in sorted(findings, key=lambda f: (f["_prio"], -f["bytes"], len(f["path"]), f["path"])):
        path = item["path"]
        chain = [str(p) for p in Path(path).parents]
        if path in kept_paths or path in ancestors or any(p in kept_paths for p in chain):
            continue
        kept.append(item)
        kept_paths.add(path)
        ancestors.update(chain)
    return kept


def restat(findings: list[dict[str, Any]], scanned_at: float) -> tuple[list[dict[str, Any]], int]:
    """Drop vanished paths and flag size drift. Directories flag drift when touched after the scan."""
    live, dropped = [], 0
    for item in findings:
        try:
            st = os.lstat(item["path"])
        except FileNotFoundError:
            dropped += 1
            continue
        except OSError:
            live.append(item)
            continue
        if item["_dir"]:
            drift = st.st_mtime > scanned_at
        else:
            drift = abs(st.st_blocks * 512 - item["bytes"]) > SIZE_DRIFT * max(item["bytes"], 1)
        if drift:
            item["size_drift"] = True
        live.append(item)
    return live, dropped


# --- report --------------------------------------------------------------

def _filters(args: argparse.Namespace) -> dict[str, Any]:
    found = {"min_size": args.min_size, "older_than": args.older_than, "category": args.category,
             "max_risk": args.max_risk, "path_prefix": args.path_prefix, "sort": args.sort}
    return {k: v for k, v in found.items() if v is not None and not (k == "max_risk" and v == "review")
            and not (k == "sort" and v == "size")}


def _report_command(target: str, args: argparse.Namespace, offset: int) -> str:
    parts = ["agentctl", "disk", "report", target]
    flags = {"--min-size": args.min_size, "--older-than": args.older_than, "--category": args.category,
             "--max-risk": args.max_risk if args.max_risk != "review" else None,
             "--path-prefix": args.path_prefix, "--sort": args.sort if args.sort != "size" else None,
             "--limit": args.limit if args.limit != 25 else None, "--offset": offset}
    for flag, value in flags.items():
        if value is not None:
            parts += [flag, shlex.quote(str(value))]
    return " ".join(parts)


def strip_internal(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if not k.startswith("_")}


def cmd_report(args: argparse.Namespace) -> int:
    cfg = load_config()
    now = time.time()
    min_size = parse_size_flag(args.min_size, "--min-size") if args.min_size else None
    older = parse_age(args.older_than, "--older-than", now) if args.older_than else None
    max_age = parse_duration(args.max_age, "--max-age")
    categories = None
    if args.category:
        categories = {c.strip() for c in args.category.split(",") if c.strip()}
        bad = sorted(categories - set(CATEGORIES))
        if bad:
            raise DiskError(f"--category: unknown {bad[0]!r}; accepted: {', '.join(CATEGORIES)}")
    target = resolve_target(args.target)
    pretty = args.pretty
    next_hints: list[str] = []
    scan_cmd = f"agentctl disk scan {target['id'] if target['id'] in ('home', 'root') else shlex.quote(target['mount'])} --background"
    scan_started = False
    if args.refresh == "always":
        scan_started = start_scan(target, cfg).get("status") == "started"
    needs_cache = categories is None or bool(categories & set(CACHE_CATEGORIES))
    cache, mismatch = open_caches(target)
    if cache is None and needs_cache:
        status = "schema_mismatch" if mismatch else "no_cache"
        hints = [scan_cmd]
        if mismatch and target["id"] == "root":
            hints.append(f"sudo python3 {INSTALL_SCRIPT} --apply")
        out({"status": status, "target": target["id"], "mount": target["mount"],
             "message": ("cache was written by another scanner version" if mismatch else "no scan has run for this target"),
             **({"scan_started": True} if scan_started else {}), "next": hints}, pretty)
        return 0

    findings: list[dict[str, Any]] = []
    dropped = 0
    scanned_at = now
    if cache is not None:
        scanned_at = cache["finished"]
        found = remove_overlaps(cache_findings(cache["con"], cfg, now))
        if args.refresh != "never":
            found, dropped = restat(found, scanned_at)
        findings.extend(found)
    unavailable: list[dict[str, str]] = []
    if not args.no_live:
        ctx = Ctx(target=target, mounts=read_mountinfo(),
                  timeout=float(cfg["collector_timeout_s"]), live_min_bytes=int(cfg["live_min_bytes"]),
                  stale_days=int(cfg["stale_days"]))
        live, unavailable = collectors.run_collectors(ctx, categories)
        covers = tuple(c for item in live for c in item["_covers"])
        if covers:
            findings = [f for f in findings if not any(f["path"] == c or f["path"].startswith(c + "/") for c in covers)]
        findings.extend(live)
    if cache is not None:
        cache["con"].close()

    protected = [str(Path(p).expanduser()) for p in cfg["protected_paths"]]
    ignore = cfg["ignore_globs"]
    prefix = os.path.expanduser(args.path_prefix) if args.path_prefix else None
    unknown_age = 0
    filtered: list[dict[str, Any]] = []
    for item in findings:
        path = item["path"]
        if any(path == p or path.startswith(p + "/") for p in protected) or any(fnmatch.fnmatch(path, g) for g in ignore):
            continue
        if categories and item["category"] not in categories:
            continue
        if min_size is not None and item["bytes"] < min_size:
            continue
        if prefix and not path.startswith(prefix):
            continue
        if older is not None:
            if item["_ts"] is None:
                unknown_age += 1
                continue
            if item["_ts"] >= older:
                continue
        filtered.append(item)
    reclaim = {r: sum(f["bytes"] for f in filtered if f["risk"] == r) for r in RISKS}
    limit_rank = RISKS.index(args.max_risk)
    shown_set = [f for f in filtered if RISKS.index(f["risk"]) <= limit_rank]
    if args.sort == "age":
        shown_set.sort(key=lambda f: (f["_ts"] is None, f["_ts"] or 0, -f["bytes"]))
    else:
        shown_set.sort(key=lambda f: (-f["bytes"], f["path"]))
    rollup: dict[str, list[int]] = {}
    for item in shown_set:
        entry = rollup.setdefault(item["category"], [0, 0])
        entry[0] += 1
        entry[1] += item["bytes"]
    categories_out = [{"category": c, "count": v[0], "bytes": v[1]}
                      for c, v in sorted(rollup.items(), key=lambda kv: -kv[1][1])]
    write_index(target["id"], shown_set[:INDEX_CAP], now)

    figures = disk_figures(target["mount"])
    unreadable = cache["run"][5] if cache else 0
    summary: dict[str, Any] = {
        "target": target["id"], "mount": target["mount"], "device": target["device"], "disk": figures,
        "cache": ({"scanned_at": datetime.fromtimestamp(scanned_at, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "age_hours": round((now - scanned_at) / 3600, 1),
                   "stale": (now - scanned_at) > max_age.total_seconds(), "source": cache["source"]}
                  if cache else None),
        "coverage": {"unreadable_dirs": unreadable, "mode": "partial" if unreadable else "full",
                     "source": cache["source"] if cache else None},
        "reclaimable": reclaim, "excluded_unknown_age": unknown_age, "filters": _filters(args),
    }
    if dropped:
        summary["dropped_since_scan"] = dropped
    if scan_started:
        summary["scan_started"] = True
    if cache and args.refresh == "auto" and summary["cache"]["stale"]:
        next_hints.append(scan_cmd)
    if cache and target["id"] == "root" and unreadable and cache["source"] == "user":
        next_hints.append(f"python3 {INSTALL_SCRIPT}   # dry run; then: sudo python3 {INSTALL_SCRIPT} --apply")

    offset = max(0, args.offset)
    page = shown_set[offset:offset + args.limit]
    payload = fit_payload(summary, categories_out, page, len(shown_set), offset, unavailable, next_hints,
                          lambda off: _report_command(args.target, args, off), args.max_bytes, pretty)
    out(payload, pretty)
    return 0


def fit_payload(summary: dict[str, Any], categories: list[dict[str, Any]], page: list[dict[str, Any]], total: int,
                offset: int, unavailable: list[dict[str, str]], next_hints: list[str], more_cmd: Any,
                max_bytes: int, pretty: bool) -> dict[str, Any]:
    items = [strip_internal(f) for f in page]

    def build(rows: list[dict[str, Any]]) -> dict[str, Any]:
        hints = list(next_hints)
        if offset + len(rows) < total:
            hints.insert(0, more_cmd(offset + len(rows)))
        if rows:
            hints.append(f"agentctl disk explain {rows[0]['id']}")
        payload: dict[str, Any] = {"status": "ok", "summary": summary, "categories": categories, "findings": rows,
                                   "truncated": {"shown": len(rows), "total": total, "offset": offset}}
        if unavailable:
            payload["unavailable"] = unavailable
        payload["next"] = hints
        return payload

    payload = build(items)
    if len(dumps(payload, pretty).encode()) > max_bytes:
        items = [{k: v for k, v in row.items() if k not in ("evidence", "verify_command")} for row in items]
        payload = build(items)
    while items and len(dumps(payload, pretty).encode()) > max_bytes:
        items.pop()
        payload = build(items)
    return payload


# --- finding index and explain -------------------------------------------

def index_path() -> Path:
    return state_dir() / "index.sqlite"


def write_index(target_id: str, findings: list[dict[str, Any]], now: float) -> None:
    path = index_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE IF NOT EXISTS findings(id TEXT PRIMARY KEY, target TEXT, created REAL, data TEXT)")
        con.execute("DELETE FROM findings WHERE created < ?", (now - INDEX_KEEP_DAYS * 86400,))
        con.executemany("INSERT OR REPLACE INTO findings VALUES (?,?,?,?)",
                        [(f["id"], target_id, now, json.dumps(strip_internal(f))) for f in findings])
        con.commit()
        con.close()
    except (sqlite3.Error, OSError):
        return


def cmd_explain(args: argparse.Namespace) -> int:
    row = None
    try:
        con = sqlite3.connect(f"file:{index_path()}?mode=ro", uri=True)
        row = con.execute("SELECT target, data FROM findings WHERE id=?", (args.id,)).fetchone()
        con.close()
    except sqlite3.Error:
        pass
    if row is None:
        out({"status": "not_found", "id": args.id, "next": ["agentctl disk report root", "agentctl disk report home"]},
            args.pretty)
        return 0
    finding = json.loads(row[1])
    reasoning = REASONING.get(finding["category"], "")
    if finding.get("protected"):
        reasoning = "Protected: listed under /home/volumes or mounted by a container that uses such a volume. " + reasoning
    if finding["risk"] == "danger":
        reasoning += " Risk is danger, so no delete command is offered."
    out({"status": "ok", "id": args.id, "target": row[0], "finding": finding, "risk_reasoning": reasoning,
         "command": finding.get("suggested_command"), "executes": "nothing"}, args.pretty)
    return 0


# --- targets, scan, status -----------------------------------------------

def _scan_argv(target: dict[str, str], cfg: dict[str, Any], directory: Path) -> list[str]:
    return [sys.executable, "-I", str(Path(scanner.__file__).resolve()), "scan", "--target", target["root_path"],
            "--id", target["id"], "--cache-dir", str(directory), "--min-dir-bytes", str(cfg["min_dir_bytes"]),
            "--min-file-bytes", str(cfg["min_file_bytes"]), "--quiet"]


def start_scan(target: dict[str, str], cfg: dict[str, Any]) -> dict[str, Any]:
    directory = state_dir()
    directory.mkdir(parents=True, exist_ok=True)
    if not scanner.lock_is_free(directory, target["id"]):
        return {"status": "locked", "target": target["id"]}
    pid = scanner.start_background(_scan_argv(target, cfg, directory))
    return {"status": "started", "target": target["id"], "pid": pid, "next": ["agentctl disk status"]}


def cmd_targets(args: argparse.Namespace) -> int:
    out({"status": "ok", "targets": list_targets()}, args.pretty)
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    if not args.target and not args.all:
        raise DiskError("scan needs a target (home, root, a mount point) or --all")
    cfg = load_config()
    targets = scan_targets() if args.all else [resolve_target(args.target)]
    results = []
    for target in targets:
        if args.background:
            results.append(start_scan(target, cfg))
        else:
            results.append(scanner.scan_target(target["root_path"], target["id"], state_dir(),
                                               min_dir_bytes=cfg["min_dir_bytes"],
                                               min_file_bytes=cfg["min_file_bytes"]))
    failed = any(r["status"] == "failed" for r in results)
    if not (args.quiet and not failed and all(r["status"] in ("ok", "locked", "started") for r in results)):
        out({"status": "failed" if failed else results[0]["status"] if len(results) == 1 else "ok",
             "results": results}, args.pretty)
    return 1 if failed else 0


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def cmd_status(args: argparse.Namespace) -> int:
    ids = [resolve_target(args.target)["id"]] if args.target else None
    rows = []
    for source, directory in [("user", state_dir()), ("root", root_state_dir())]:
        try:
            files = sorted(directory.glob("*.status.json"))
        except OSError:
            continue
        for file in files:
            tid = file.name[:-len(".status.json")]
            if ids and tid not in ids:
                continue
            status = scanner.read_status(directory, tid)
            if status.get("state") == "running" and not _alive(status.get("pid")):
                status["state"] = "interrupted"
            rows.append({"target": tid, "source": source, **{k: v for k, v in status.items() if k != "target"}})
    out({"status": "ok", "targets": rows}, args.pretty)
    return 0


# --- parser registration -------------------------------------------------

def add_disk_parsers(group: argparse._SubParsersAction) -> None:
    def parser(name: str, help_text: str, description: str) -> argparse.ArgumentParser:
        sub = group.add_parser(name, help=help_text, description=description,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
        sub.add_argument("--pretty", action="store_true", help="Indent the JSON for reading; default is compact.")
        return sub

    targets = parser("targets", "List home, root and every real mount with size and cache age.",
                     "List scan targets with size, used, available and the age of each cache. Read-only.")
    targets.set_defaults(func=cmd_targets)

    scan = parser("scan", "Walk a disk and refresh its SQLite cache (never deletes anything).",
                  "Walk one target and write its cache atomically under a per-target lock. The walk stays on one\n"
                  "device, does not follow symlinks and opens nothing for writing outside the cache directory.\n"
                  "Target: home, root, a mount point, a device path, a label or a directory path.")
    scan.add_argument("target", nargs="?", help="home, root, a mount point, a device path or a directory.")
    scan.add_argument("--all", action="store_true", help="Scan root, home and every other real mount.")
    scan.add_argument("--background", action="store_true", help="Start the walk detached and return at once.")
    scan.add_argument("--quiet", action="store_true", help="Print nothing when the scan succeeds.")
    scan.set_defaults(func=cmd_scan)

    status = parser("status", "Show running or finished scans, start time and last result.",
                    "Read the status file of each scan target; a dead process shows as interrupted.")
    status.add_argument("target", nargs="?", help="Limit to one target.")
    status.set_defaults(func=cmd_status)

    report = parser(
        "report", "Rank clean-up opportunities on one disk as small, bounded JSON.",
        "Reads the cache for files and directories and queries docker, apt, flatpak and snap live. Findings carry\n"
        "a risk label and a suggested command string; nothing is ever deleted. With no cache the answer is\n"
        "no_cache plus the scan command to run; the report never walks the disk itself.\n"
        "Categories: " + ", ".join(CATEGORIES) + ".")
    report.add_argument("target", help="home, root, a mount point, a device path, a label or a directory.")
    report.add_argument("--min-size", help="Only findings at or above this size: 500M, 2GB, 2GiB.")
    report.add_argument("--older-than", help="Only findings last used before this: 90d, 6m, 1y or 2025-01-31.")
    report.add_argument("--category", help="Comma-separated categories to keep.")
    report.add_argument("--max-risk", choices=RISKS, default="review", help="Hide riskier findings (default review).")
    report.add_argument("--path-prefix", help="Only findings whose path starts with this.")
    report.add_argument("--sort", choices=("size", "age"), default="size", help="Largest first, or oldest first.")
    report.add_argument("--limit", type=int, default=25, help="Findings per page (default 25).")
    report.add_argument("--offset", type=int, default=0, help="Skip this many findings.")
    report.add_argument("--refresh", choices=("auto", "never", "always"), default="auto",
                        help="auto hints a rescan when stale; never skips re-stat and hints; always starts a background scan.")
    report.add_argument("--max-age", default="36h", help="Cache older than this is stale (default 36h).")
    report.add_argument("--no-live", action="store_true", help="Skip docker, apt, flatpak, snap and system collectors.")
    report.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Cap on output size (default 16384).")
    report.set_defaults(func=cmd_report)

    explain = parser("explain", "Show evidence, risk reasoning and the exact command for one finding id.",
                     "Reads the finding index written by the last report. Executes nothing.")
    explain.add_argument("id", help="Finding id from a report, such as dk_ab12cd34ef.")
    explain.set_defaults(func=cmd_explain)
