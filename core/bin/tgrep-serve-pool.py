#!/usr/bin/env python3
"""Rank, start, and cap a small tgrep serve pool.

Index dirs live at ~/.cache/tgrep/<hash-of-canonical-root>/. Never serve
$HOME, Downloads, .config, .agents, .cache, or .wine as a root.

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
POOL_JSON = Path(os.environ.get("TGREP_POOL_JSON", str(HOME / ".cache" / "tgrep" / "pool.json")))
TGREP_BIN = Path(os.environ.get("TGREP_BIN", str(HOME / ".local" / "bin" / "tgrep")))
CACHE_ROOT = HOME / ".cache" / "tgrep"
WORKSPACE_STORAGE = HOME / ".config" / "Cursor" / "User" / "workspaceStorage"
CURSOR_PROJECTS = HOME / ".cursor" / "projects"
HISTORY_ROOT = HOME / ".agents" / "history"
RANKED_CAP = 7
ENSURE_CAP = 8
WORKSPACE_RE = re.compile(r"/Workspace/[^\s\"']+")


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def deny_roots() -> list[Path]:
    return [
        HOME / "Downloads",
        HOME / ".config",
        HOME / ".cursor",
        HOME / ".agents",
        HOME / ".cache",
        HOME / ".wine",
    ]


def is_denied(root: Path) -> bool:
    try:
        resolved = root.resolve()
    except OSError:
        return True
    if resolved == HOME:
        return True
    for denied in deny_roots():
        try:
            if denied.exists() and (
                resolved == denied.resolve()
                or str(resolved).startswith(str(denied.resolve()) + os.sep)
            ):
                return True
        except OSError:
            continue
    return False


def cache_id(root: Path) -> str:
    return hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]


def git_toplevel(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return Path(result.stdout.strip()).resolve()
    except OSError:
        return None


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def load_pool() -> dict:
    if not POOL_JSON.is_file():
        return {"cap": ENSURE_CAP, "servers": {}}
    try:
        data = json.loads(POOL_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"cap": ENSURE_CAP, "servers": {}}
    if not isinstance(data, dict):
        return {"cap": ENSURE_CAP, "servers": {}}
    data.setdefault("cap", ENSURE_CAP)
    data.setdefault("servers", {})
    return data


def save_pool(pool: dict) -> None:
    POOL_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = POOL_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(pool, indent=2) + "\n", encoding="utf-8")
    tmp.replace(POOL_JSON)


def folder_from_workspace_json(path: Path) -> Path | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    folder = data.get("folder")
    if isinstance(folder, str) and folder.startswith("file://"):
        return Path(folder[len("file://") :])
    workspace = data.get("workspace")
    if isinstance(workspace, str) and workspace.startswith("file://"):
        return Path(workspace[len("file://") :])
    return None


def collect_candidates() -> list[tuple[float, Path]]:
    scored: dict[str, float] = {}

    def bump(path: Path, score: float) -> None:
        top = git_toplevel(path)
        if top is None or is_denied(top):
            return
        key = str(top)
        scored[key] = max(scored.get(key, 0.0), score)

    if WORKSPACE_STORAGE.is_dir():
        for entry in WORKSPACE_STORAGE.iterdir():
            ws = entry / "workspace.json"
            if not ws.is_file():
                continue
            folder = folder_from_workspace_json(ws)
            if folder is None:
                continue
            try:
                mtime = ws.stat().st_mtime
            except OSError:
                mtime = 0.0
            bump(folder, mtime)

    # `~/.cursor/projects/<slug>` is not a git root. Walking `git` from there
    # finds `~/.cursor` itself. Ranking uses workspace.json paths instead.

    if HISTORY_ROOT.is_dir():
        for md in HISTORY_ROOT.rglob("*.md"):
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")[:8000]
                mtime = md.stat().st_mtime
            except OSError:
                continue
            for match in WORKSPACE_RE.finditer(text):
                candidate = HOME / match.group(0).lstrip("/")
                bump(candidate, mtime)

    ranked = sorted(
        ((score, Path(path)) for path, score in scored.items()),
        key=lambda item: item[0],
        reverse=True,
    )
    return ranked


def serve_meta_complete(index_dir: Path) -> bool:
    meta = index_dir / "meta.json"
    if not meta.is_file():
        return False
    try:
        return json.loads(meta.read_text(encoding="utf-8")).get("complete") is True
    except (OSError, json.JSONDecodeError):
        return False


def start_serve(root: Path, pool: dict) -> dict | None:
    if is_denied(root):
        log(f"deny serve root {root}")
        return None
    if not TGREP_BIN.is_file():
        log(f"missing {TGREP_BIN}")
        return None
    index_dir = CACHE_ROOT / cache_id(root)
    index_dir.mkdir(parents=True, exist_ok=True)
    existing = pool.get("servers", {}).get(str(root), {})
    if isinstance(existing, dict):
        pid = existing.get("pid")
        if isinstance(pid, int) and pid_alive(pid) and (index_dir / "serve.json").is_file():
            return existing
    proc = subprocess.Popen(
        [
            str(TGREP_BIN),
            "serve",
            "--hidden",
            "--no-require-git",
            "--index-path",
            str(index_dir),
            str(root),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    serve_json = index_dir / "serve.json"
    deadline = time.time() + 15
    while time.time() < deadline:
        if serve_json.is_file():
            break
        if proc.poll() is not None:
            log(f"serve exited early for {root}")
            return None
        time.sleep(0.05)
    rec = {
        "index_path": str(index_dir),
        "pid": proc.pid,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return rec


def stop_serve(rec: dict) -> None:
    pid = rec.get("pid")
    if isinstance(pid, int) and pid_alive(pid):
        try:
            os.kill(pid, 15)
        except OSError:
            pass


def prune_orphans(pool: dict) -> None:
    servers = pool.setdefault("servers", {})
    drop = []
    for key, rec in servers.items():
        if not isinstance(rec, dict):
            drop.append(key)
            continue
        pid = rec.get("pid")
        if not isinstance(pid, int) or not pid_alive(pid):
            drop.append(key)
    for key in drop:
        servers.pop(key, None)


def cmd_rank() -> int:
    for score, path in collect_candidates()[:ENSURE_CAP]:
        print(f"{score:.0f}\t{path}")
    return 0


def cmd_status() -> int:
    pool = load_pool()
    prune_orphans(pool)
    save_pool(pool)
    print(json.dumps(pool, indent=2))
    return 0


def cmd_start_ranked() -> int:
    pool = load_pool()
    prune_orphans(pool)
    ranked = [path for _, path in collect_candidates()[:RANKED_CAP]]
    wanted = {str(path) for path in ranked}
    for key, rec in list(pool.get("servers", {}).items()):
        if key not in wanted:
            stop_serve(rec)
            pool["servers"].pop(key, None)
    for path in ranked:
        rec = start_serve(path, pool)
        if rec:
            pool.setdefault("servers", {})[str(path)] = rec
    save_pool(pool)
    return 0


def cmd_ensure(cwd: str) -> int:
    root = git_toplevel(Path(cwd))
    if root is None or is_denied(root):
        return 0
    pool = load_pool()
    prune_orphans(pool)
    servers = pool.setdefault("servers", {})
    key = str(root)
    if key in servers and isinstance(servers[key], dict):
        pid = servers[key].get("pid")
        if isinstance(pid, int) and pid_alive(pid):
            return 0
    if len(servers) >= ENSURE_CAP:
        ranked_keys = [str(path) for _, path in collect_candidates()]
        evict = None
        for existing in servers:
            if existing not in ranked_keys[:RANKED_CAP] and existing != key:
                evict = existing
                break
        if evict is None:
            # evict lowest ranked currently live
            live = [k for k in ranked_keys if k in servers]
            if live:
                evict = live[-1]
            elif servers:
                evict = next(iter(servers))
        if evict:
            stop_serve(servers[evict])
            servers.pop(evict, None)
    rec = start_serve(root, pool)
    if rec:
        servers[key] = rec
        save_pool(pool)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rank")
    sub.add_parser("status")
    sub.add_parser("start-ranked")
    ensure = sub.add_parser("ensure")
    ensure.add_argument("--cwd", default=os.getcwd())
    args = parser.parse_args(argv)
    try:
        if args.cmd == "rank":
            return cmd_rank()
        if args.cmd == "status":
            return cmd_status()
        if args.cmd == "start-ranked":
            return cmd_start_ranked()
        if args.cmd == "ensure":
            return cmd_ensure(args.cwd)
    except Exception as exc:  # noqa: BLE001 — best-effort supervisor
        log(f"tgrep-serve-pool: {exc}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
