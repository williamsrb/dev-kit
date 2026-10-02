"""Code-intelligence helpers for agentctl: source languages and Serena orphans.

`languages` counts source files by language and names the few that matter, so a
tool that needs a language list (the Serena wrapper) can pick it deterministically.
Plain text, office/PDF documents, data formats and binaries are not counted.

`orphans` finds Serena processes left behind by a client that went away: a
`serena start-mcp-server` re-parented to init, and language servers with no live
Serena server above them. Ownership comes from the SERENA_MCP_SERVER=1 marker that
bin/serena-mcp sets (inherited by every process Serena starts) or from Serena's own
install paths, so an editor's own pyright or tsserver is never matched.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentctl_common import emit, git, repo_root

# extension -> (language label, Serena language server id)
LANGUAGES: dict[str, tuple[str, str]] = {
    ".py": ("python", "python"),
    ".pyi": ("python", "python"),
    ".ts": ("typescript", "typescript"),
    ".tsx": ("typescript", "typescript"),
    ".mts": ("typescript", "typescript"),
    ".cts": ("typescript", "typescript"),
    ".js": ("javascript", "typescript"),
    ".jsx": ("javascript", "typescript"),
    ".mjs": ("javascript", "typescript"),
    ".cjs": ("javascript", "typescript"),
    ".php": ("php", "php"),
    ".java": ("java", "java"),
    ".kt": ("kotlin", "kotlin"),
    ".kts": ("kotlin", "kotlin"),
    ".cs": ("csharp", "csharp"),
    ".go": ("go", "go"),
    ".rs": ("rust", "rust"),
    ".rb": ("ruby", "ruby"),
    ".swift": ("swift", "swift"),
    ".scala": ("scala", "scala"),
    ".dart": ("dart", "dart"),
    ".lua": ("lua", "lua"),
    ".ex": ("elixir", "elixir"),
    ".exs": ("elixir", "elixir"),
    ".pl": ("perl", "perl"),
    ".sh": ("shell", "bash"),
    ".bash": ("shell", "bash"),
    ".ps1": ("powershell", "powershell"),
    ".c": ("c", "cpp"),
    ".h": ("c", "cpp"),
    ".cc": ("cpp", "cpp"),
    ".cpp": ("cpp", "cpp"),
    ".hpp": ("cpp", "cpp"),
    ".md": ("markdown", "markdown"),
    ".markdown": ("markdown", "markdown"),
}

SKIP_DIRS = frozenset({
    ".git", "node_modules", "vendor", "dist", "build", "target", "out", "coverage",
    "__pycache__", ".venv", "venv", ".tox", ".next", ".nuxt", ".gradle", ".idea",
    ".serena", "graft-out", "graphify-out",
})
MINIFIED_MARKERS = (".min.", ".bundle.", ".d.ts")


def _git_files(root: Path) -> list[str] | None:
    result = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if result.returncode != 0:
        return None
    return [path for path in result.stdout.split("\0") if path]


def _walk_files(root: Path) -> list[str]:
    found: list[str] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        base = Path(current).relative_to(root)
        found.extend(str(base / name) for name in files)
    return found


def _counted(relative: str) -> str | None:
    path = Path(relative)
    if SKIP_DIRS.intersection(path.parts[:-1]):
        return None
    name = path.name.lower()
    if any(marker in name for marker in MINIFIED_MARKERS):
        return None
    return path.suffix.lower() if path.suffix.lower() in LANGUAGES else None


def detect_languages(
    cwd: Path, *, top: int = 3, min_files: int = 3, min_share: float = 0.02
) -> dict[str, Any]:
    root = repo_root(cwd) or cwd
    files = _git_files(root)
    method = "git"
    if files is None:
        files, method = _walk_files(root), "walk"

    by_server: Counter[str] = Counter()
    by_extension: dict[str, Counter[str]] = {}
    for relative in files:
        suffix = _counted(relative)
        if suffix is None:
            continue
        label, server = LANGUAGES[suffix]
        by_server[server] += 1
        by_extension.setdefault(server, Counter())[label] += 1

    total = sum(by_server.values())
    ranked = sorted(by_server.items(), key=lambda item: (-item[1], item[0]))
    selected = [
        {
            "serena": server,
            "files": count,
            "share": round(count / total, 4),
            "kinds": dict(by_extension[server].most_common()),
        }
        for server, count in ranked
        if count >= min_files and count / total >= min_share
    ][:top]
    return {
        "root": str(root),
        "method": method,
        "source_files": total,
        "languages": selected,
        "language_servers": [entry["serena"] for entry in selected],
    }


SERENA_MARKER = b"SERENA_MCP_SERVER=1"
SERENA_SERVER_RE = re.compile(r"/serena(?:-mcp)?\s+start-mcp-server\b")
SERENA_LS_DIR = "/.serena/language_servers/"
LANGUAGE_SERVER_RE = re.compile(
    r"pyright-langserver|pyright/dist/langserver\.index\.js|typescript-language-server|tsserver\.js"
    r"|typingsInstaller\.js|marksman|intelephense|gopls|rust-analyzer|jdtls|" + re.escape(SERENA_LS_DIR)
)
REAPERS = frozenset({"systemd", "init"})
KILLABLE = frozenset({"serena", "language_server"})
ONBOARD_DIR = Path.home() / ".serena" / "onboarding"
ONBOARD_START_GRACE = 120


@dataclass(frozen=True)
class Proc:
    pid: int
    ppid: int
    comm: str
    args: str
    marked: bool
    rss_kb: int
    age_s: int


def read_processes() -> dict[int, Proc] | None:
    """Current user's processes from /proc; None where /proc is unavailable."""
    proc = Path("/proc")
    if not (proc / "self" / "stat").is_file():
        return None
    ticks, page_kb = os.sysconf("SC_CLK_TCK"), os.sysconf("SC_PAGE_SIZE") // 1024
    uptime = float((proc / "uptime").read_text().split()[0])
    uid, found = os.getuid(), {}
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            stat = (entry / "stat").read_text()
            args = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
            environ = (entry / "environ").read_bytes()
            rss_pages = int((entry / "statm").read_text().split()[1])
        except (OSError, ValueError, IndexError):
            continue
        comm = stat[stat.find("(") + 1 : stat.rfind(")")]
        fields = stat[stat.rfind(")") + 2 :].split()
        pid = int(entry.name)
        found[pid] = Proc(
            pid=pid,
            ppid=int(fields[1]),
            comm=comm,
            args=args,
            marked=SERENA_MARKER in environ.split(b"\0"),
            rss_kb=rss_pages * page_kb,
            age_s=int(uptime - int(fields[19]) / ticks),
        )
    return found


def _is_server(proc: Proc) -> bool:
    return bool(SERENA_SERVER_RE.search(proc.args))


def _reaped(proc: Proc, procs: dict[int, Proc]) -> bool:
    parent = procs.get(proc.ppid)
    return proc.ppid <= 1 or (parent is not None and parent.comm in REAPERS)


def _under(proc: Proc, live: set[int], procs: dict[int, Proc]) -> bool:
    seen, pid = set(), proc.ppid
    while pid > 1 and pid not in seen:
        if pid in live:
            return True
        seen.add(pid)
        parent = procs.get(pid)
        if parent is None:
            return True
        pid = parent.ppid
    return False


def find_orphans(procs: dict[int, Proc]) -> list[dict[str, Any]]:
    live = {pid for pid, proc in procs.items() if _is_server(proc) and not _reaped(proc, procs)}
    orphans = []
    for proc in procs.values():
        owned = _is_server(proc) or proc.marked or SERENA_LS_DIR in proc.args
        if not owned or proc.pid in live or _under(proc, live, procs):
            continue
        if _is_server(proc):
            kind = "serena"
        elif LANGUAGE_SERVER_RE.search(proc.args):
            kind = "language_server"
        else:
            kind = "unknown"
        orphans.append({
            "pid": proc.pid, "ppid": proc.ppid, "kind": kind, "rss_kb": proc.rss_kb,
            "age_s": proc.age_s, "args": proc.args[:200],
        })
    return sorted(orphans, key=lambda item: item["pid"])


def _ends(pid: int) -> set[str]:
    fd_dir = Path("/proc") / str(pid) / "fd"
    try:
        names = os.listdir(fd_dir)
    except OSError:
        return set()
    pipes = set()
    for name in names:
        try:
            link = os.readlink(fd_dir / name)
        except OSError:
            continue
        if link.startswith(("pipe:", "socket:")):
            pipes.add(link)
    return pipes


def _socket_peers() -> dict[str, str] | None:
    """Unix socket inode -> peer inode, from `ss -xn`; None when ss is unavailable."""
    try:
        result = subprocess.run(["ss", "-xn"], text=True, capture_output=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    peers = {}
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 8:
            peers[f"socket:[{fields[5]}]"] = f"socket:[{fields[7]}]"
    return peers


def connected(orphans: list[dict[str, Any]], procs: dict[int, Proc]) -> set[int]:
    """Orphans whose stdin (pipe or unix socket) is still held by a non-orphan, so a client may be talking to them."""
    candidates = {orphan["pid"] for orphan in orphans}
    stdin: dict[int, str] = {}
    for pid in candidates:
        try:
            link = os.readlink(f"/proc/{pid}/fd/0")
        except OSError:
            continue
        if link.startswith(("pipe:", "socket:")):
            stdin[pid] = link
    if not stdin:
        return set()
    held = set().union(*(_ends(pid) for pid in procs if pid not in candidates))
    peers = _socket_peers() if any(link.startswith("socket:") for link in stdin.values()) else {}
    alive = set()
    for pid, link in stdin.items():
        if link.startswith("pipe:"):
            other = link
        elif peers is None:
            alive.add(pid)
            continue
        else:
            other = peers.get(link, "")
        if other in held:
            alive.add(pid)
    return alive


def stale_onboarding(state_dir: Path, procs: dict[int, Proc], now: float) -> list[dict[str, Any]]:
    """States left at starting/running by a worker that no longer exists."""
    workers = {proc.pid: proc.args for proc in procs.values() if "--run-onboarding" in proc.args}
    stale = []
    for path in sorted(state_dir.glob("*.json")):
        if path.name.endswith(".mcp.json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        status = data.get("status")
        dead_worker = status == "running" and data.get("pid") not in workers
        never_started = (
            status == "starting"
            and now - data.get("started", now) > ONBOARD_START_GRACE
            and not any(f" {data.get('root')} " in f"{args} " for args in workers.values())
        )
        if dead_worker or never_started:
            stale.append({"state": str(path), "root": data.get("root"), "status": status})
    return stale


def cmd_code_orphans(args: argparse.Namespace) -> int:
    procs = read_processes()
    if procs is None:
        emit({"status": "unsupported", "reason": "no /proc on this platform"})
        return 0
    orphans = find_orphans(procs)
    stale = stale_onboarding(args.onboarding_dir, procs, time.time())
    live_pipes = connected(orphans, procs)
    for orphan in orphans:
        orphan["connected"] = orphan["pid"] in live_pipes
    killed, fixed = [], []
    if args.kill:
        for orphan in orphans:
            if orphan["kind"] not in KILLABLE or orphan["connected"]:
                continue
            try:
                os.kill(orphan["pid"], signal.SIGTERM)
                killed.append(orphan["pid"])
            except (ProcessLookupError, PermissionError):
                pass
    if args.fix_state:
        for entry in stale:
            path = Path(entry["state"])
            data = json.loads(path.read_text(encoding="utf-8"))
            data.update(status="failed", error="worker exited without recording a result", finished=int(time.time()))
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            fixed.append(entry["state"])
    emit({
        "status": "ok",
        "orphans": orphans,
        "stale_onboarding": stale,
        "killed": killed,
        "fixed": fixed,
    })
    return 0


def cmd_code_languages(args: argparse.Namespace) -> int:
    result = detect_languages(
        args.cwd.resolve(), top=args.top, min_files=args.min_files, min_share=args.min_share
    )
    if args.serena:
        print(" ".join(result["language_servers"]))
        return 0
    emit(result)
    return 0


def add_code_parsers(group: argparse._SubParsersAction) -> None:
    languages = group.add_parser(
        "languages",
        help="Detect the most relevant source languages in a repository.",
        description=(
            "Count source files by language (git-aware, skipping vendored and generated "
            "directories) and report the top few. Plain text, documents, data formats and "
            "binaries are ignored. JavaScript and TypeScript share one Serena language server."
        ),
    )
    languages.add_argument("--cwd", type=Path, default=Path.cwd(), help="Directory inside the repository.")
    languages.add_argument("--top", type=int, default=3, help="Maximum languages to return (default 3).")
    languages.add_argument(
        "--min-files", type=int, default=3, help="Minimum files for a language to count (default 3)."
    )
    languages.add_argument(
        "--min-share", type=float, default=0.02,
        help="Minimum share of all source files for a language to count (default 0.02).",
    )
    languages.add_argument(
        "--serena", action="store_true", help="Print only the space-separated Serena language server ids."
    )
    languages.set_defaults(func=cmd_code_languages)

    orphans = group.add_parser(
        "orphans",
        help="Find Serena servers and language servers left behind by a closed client.",
        description=(
            "Report Serena processes with no live client (Linux /proc). Ownership comes from the "
            "SERENA_MCP_SERVER=1 marker set by bin/serena-mcp or from Serena's install paths. Also "
            "reports onboarding states stuck at starting/running whose worker is gone. Report-only "
            "unless --kill or --fix-state; processes of kind 'unknown', or whose stdin pipe or socket peer "
            "is still held by another process, are never killed."
        ),
    )
    orphans.add_argument("--kill", action="store_true", help="SIGTERM orphaned Serena and language-server processes.")
    orphans.add_argument("--fix-state", action="store_true", help="Mark stale onboarding states as failed.")
    orphans.add_argument(
        "--onboarding-dir", type=Path, default=ONBOARD_DIR, help="Onboarding state directory (default ~/.serena/onboarding)."
    )
    orphans.set_defaults(func=cmd_code_orphans)
