#!/usr/bin/env python3
"""Wrap Cursor @vscode/ripgrep/bin/rg with patched tgrep, or reinstall after apt.

Canonical: ~/.agents/bin/cursor-tgrep-rg-apply.py
Root copy: /usr/local/bin/cursor-tgrep-rg-apply (not a $HOME symlink)

Subcommands: wrap (also argv0=rg), apply/install (apt path), compare-json.

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WRAPPER_VERSION = "1"
HOME = Path.home()
TGREP_BIN = Path(os.environ.get("TGREP_BIN", str(HOME / ".local" / "bin" / "tgrep")))
POOL_JSON = Path(os.environ.get("TGREP_POOL_JSON", str(HOME / ".cache" / "tgrep" / "pool.json")))
CURSOR_RG_DIR = Path(
    "/usr/share/cursor/resources/app/node_modules/@vscode/ripgrep/bin"
)
MARKER_NAME = "rg.wrapper-id"
WIDENING = {
    "--no-ignore",
    "--no-ignore-dot",
    "--no-ignore-exclude",
    "--no-ignore-global",
    "--no-ignore-parent",
    "--no-ignore-vcs",
    "--no-ignore-files",
    "--follow",
    "--binary",
    "--text",
    "-a",
    "-z",
    "--search-zip",
}
ENCODING_FLAGS = {"-E", "--encoding"}


def deny_roots() -> list[Path]:
    return [
        HOME,
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
    for denied in deny_roots()[1:]:
        try:
            if not denied.exists():
                continue
            resolved.relative_to(denied.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


def cache_id(root: Path) -> str:
    return hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]


def split_search_argv(argv: list[str]) -> tuple[list[str], str | None, list[str]]:
    if "--" in argv:
        idx = argv.index("--")
        before, after = argv[:idx], argv[idx + 1 :]
    else:
        before, after = argv, []
    files_mode = "--files" in before
    if files_mode:
        return before, None, after
    pattern = after[0] if after else None
    paths = after[1:] if after else []
    return before, pattern, paths


def has_widening_flags(argv: list[str]) -> bool:
    for i, arg in enumerate(argv):
        if arg in WIDENING or arg.startswith("--no-ignore"):
            return True
        if arg in ENCODING_FLAGS:
            return True
        if arg.startswith("--encoding="):
            return True
        if arg.startswith("-E") and arg != "-E" and not arg.startswith("--"):
            return True
        if arg == "-E" and i + 1 < len(argv):
            return True
        if arg in {"-u", "-uu", "-uuu", "--unrestricted"}:
            return True
    return False


def looks_like_named_file(cwd: Path, paths: list[str]) -> bool:
    for raw in paths:
        if raw in {".", "./"}:
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        try:
            if candidate.is_file():
                return True
        except OSError:
            continue
    return False


def resolve_root(cwd: Path, paths: list[str]) -> Path:
    if not paths:
        return cwd
    raw = paths[0]
    if raw in {".", "./"}:
        return cwd
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = cwd / candidate
    return candidate


def git_toplevel(root: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def load_pool(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def serve_ready(index_dir: Path) -> bool:
    serve = index_dir / "serve.json"
    meta = index_dir / "meta.json"
    if not serve.is_file() or not meta.is_file():
        return False
    try:
        info = json.loads(serve.read_text(encoding="utf-8"))
        meta_obj = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    pid = info.get("pid")
    if not isinstance(pid, int) or not pid_alive(pid):
        return False
    return meta_obj.get("complete") is True


def pool_index_for(root: Path, pool: dict) -> Path | None:
    servers = pool.get("servers")
    if not isinstance(servers, dict):
        return None
    resolved = str(root.resolve())
    for key, rec in servers.items():
        try:
            key_path = str(Path(key).resolve())
        except OSError:
            key_path = key
        if resolved == key_path or resolved.startswith(key_path + os.sep):
            if not isinstance(rec, dict):
                continue
            raw = rec.get("index_path")
            if not raw:
                continue
            index_dir = Path(raw)
            if serve_ready(index_dir):
                return index_dir
    # convention path even without pool row
    return None


def stock_rg(wrapper: Path) -> Path:
    env = os.environ.get("RG_STOCK")
    if env:
        return Path(env)
    return wrapper.parent / "rg.stock"


def exec_path(path: Path, argv: list[str]) -> int:
    os.execv(str(path), [str(path), *argv])
    return 127


def wrap(argv: list[str]) -> int:
    if "--tgrep-wrapper-version" in argv:
        print(WRAPPER_VERSION)
        return 0
    wrapper = Path(sys.argv[0]).resolve()
    stock = stock_rg(wrapper)
    cwd = Path(os.getcwd())
    if has_widening_flags(argv) or "-z" in argv or "--search-zip" in argv:
        return exec_path(stock, argv)
    # O1 2026-09-12: tgrep --files on a hidden index lists .git/**; stock does not.
    if "--files" in argv:
        return exec_path(stock, argv)
    _before, _pattern, paths = split_search_argv(argv)
    if looks_like_named_file(cwd, paths):
        return exec_path(stock, argv)
    root = resolve_root(cwd, paths)
    if is_denied(root):
        return exec_path(stock, argv)
    toplevel = git_toplevel(root)
    if toplevel is None:
        return exec_path(stock, argv)
    if is_denied(toplevel):
        return exec_path(stock, argv)
    pool = load_pool(POOL_JSON)
    index_dir = pool_index_for(toplevel, pool)
    if index_dir is None:
        return exec_path(stock, argv)
    if not TGREP_BIN.is_file():
        return exec_path(stock, argv)
    tgrep_argv = ["--index-path", str(index_dir), *argv]
    os.execv(str(TGREP_BIN), [str(TGREP_BIN), *tgrep_argv])
    return 127


def is_wrapper_file(path: Path) -> bool:
    try:
        head = path.read_bytes()[:80]
    except OSError:
        return False
    if head.startswith(b"\x7fELF"):
        return False
    return b"cursor-tgrep-rg" in head or head.startswith(b"#!")


def apply_cursor_rg(rg_dir: Path, source: Path, dry_run: bool) -> int:
    rg = rg_dir / "rg"
    stock = rg_dir / "rg.stock"
    marker = rg_dir / MARKER_NAME
    print(f"src={source}")
    print(f"dst={rg}")
    print(f"stock={stock}")
    if dry_run:
        return 0
    if not rg_dir.is_dir():
        print(f"skip: no {rg_dir}", file=sys.stderr)
        return 0
    if not rg.exists():
        print(f"skip: no {rg}", file=sys.stderr)
        return 0
    if not is_wrapper_file(rg):
        # Package restored stock rg. Refresh rg.stock from it, then wrap.
        shutil.copy2(rg, stock)
        stock.chmod(rg.stat().st_mode)
    elif not stock.exists():
        print("wrapper present but rg.stock missing; cannot refresh stock", file=sys.stderr)
        return 2
    shutil.copy2(source, rg)
    rg.chmod(0o755)
    marker.write_text(f"{WRAPPER_VERSION}\n", encoding="utf-8")
    print("wrapped Cursor rg")
    return 0


def compare_json(
    stock: Path,
    tgrep: Path,
    cwd: Path,
    pattern: str,
    index_path: Path | None = None,
) -> int:
    argv = [
        "--hidden",
        "--no-require-git",
        "--json",
        "--crlf",
        "--no-config",
        "--",
        pattern,
        ".",
    ]
    stock_out = subprocess.run(
        [str(stock), *argv], cwd=cwd, capture_output=True, text=True, check=False
    )
    tgrep_cmd = [str(tgrep)]
    if index_path is not None:
        tgrep_cmd.extend(["--index-path", str(index_path)])
    tgrep_cmd.extend(argv)
    tgrep_out = subprocess.run(
        tgrep_cmd, cwd=cwd, capture_output=True, text=True, check=False
    )
    if stock_out.returncode not in {0, 1} or tgrep_out.returncode not in {0, 1}:
        print("fixture command failed", file=sys.stderr)
        print(stock_out.stderr, file=sys.stderr)
        print(tgrep_out.stderr, file=sys.stderr)
        return 2

    def events(text: str) -> list[dict]:
        rows = []
        for line in text.splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    stock_events = events(stock_out.stdout)
    tgrep_events = events(tgrep_out.stdout)
    stock_types = [e.get("type") for e in stock_events]
    tgrep_types = [e.get("type") for e in tgrep_events]
    needed = {"begin", "match", "end", "summary"}
    if not needed.issubset(set(stock_types)) or not needed.issubset(set(tgrep_types)):
        print(f"missing event types stock={stock_types} tgrep={tgrep_types}", file=sys.stderr)
        return 2

    def match_keys(events: list[dict]) -> set[tuple[str, int | None]]:
        keys = set()
        for event in events:
            if event.get("type") != "match":
                continue
            data = event.get("data") or {}
            path = ((data.get("path") or {}).get("text")) or ""
            line = (data.get("line_number"))
            keys.add((path.replace("\\", "/"), line))
        return keys

    stock_keys = match_keys(stock_events)
    tgrep_keys = match_keys(tgrep_events)
    if stock_keys != tgrep_keys:
        print(f"match path/line mismatch stock={stock_keys} tgrep={tgrep_keys}", file=sys.stderr)
        return 2
    print("json fixture ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    name = Path(sys.argv[0]).name
    if "--tgrep-wrapper-version" in argv:
        print(WRAPPER_VERSION)
        return 0
    if name == "rg":
        return wrap(argv)

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=False)
    wrap_p = sub.add_parser("wrap", help="search like Cursor rg")
    wrap_p.add_argument("rg_argv", nargs=argparse.REMAINDER)
    apply_p = sub.add_parser("apply", help="install wrapper over Cursor rg")
    apply_p.add_argument("--dry-run", action="store_true")
    apply_p.add_argument("--rg-dir", type=Path, default=CURSOR_RG_DIR)
    apply_p.add_argument("--source", type=Path, default=Path(__file__).resolve())
    install_p = sub.add_parser("install", help="alias of apply")
    install_p.add_argument("--dry-run", action="store_true")
    install_p.add_argument("--rg-dir", type=Path, default=CURSOR_RG_DIR)
    install_p.add_argument("--source", type=Path, default=Path(__file__).resolve())
    cmp_p = sub.add_parser("compare-json", help="TBD-3 content JSON fixture")
    cmp_p.add_argument("--stock", type=Path, required=True)
    cmp_p.add_argument("--tgrep", type=Path, required=True)
    cmp_p.add_argument("--cwd", type=Path, required=True)
    cmp_p.add_argument("--pattern", required=True)
    cmp_p.add_argument(
        "--index-path",
        type=Path,
        default=None,
        help="one-off serve index dir (tgrep --index-path)",
    )
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    cmd = args.cmd
    if cmd == "wrap":
        rest = list(args.rg_argv)
        if rest[:1] == ["--"]:
            rest = rest[1:]
        return wrap(rest)
    if cmd in {"apply", "install"}:
        return apply_cursor_rg(args.rg_dir, args.source, args.dry_run)
    if cmd == "compare-json":
        return compare_json(
            args.stock,
            args.tgrep,
            args.cwd,
            args.pattern,
            args.index_path,
        )
    if args.dry_run:
        return apply_cursor_rg(CURSOR_RG_DIR, Path(__file__).resolve(), True)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
