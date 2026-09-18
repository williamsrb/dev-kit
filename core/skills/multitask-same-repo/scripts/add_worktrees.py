#!/usr/bin/env python3
"""Create git worktrees (and branches) for a same-repo multitask batch."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"{' '.join(cmd)}: {msg}")
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="git worktree add <root>/<KEY> -b <KEY> for each task key"
    )
    parser.add_argument(
        "--repo",
        required=True,
        type=Path,
        help="Parent git repo (object store)",
    )
    parser.add_argument(
        "--root",
        required=True,
        type=Path,
        help="Multitask root directory for worktrees",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Start point for new branches (default: current HEAD of --repo)",
    )
    parser.add_argument(
        "keys",
        nargs="+",
        help="Task keys / branch names (e.g. PROJ-339 PROJ-341)",
    )
    args = parser.parse_args()

    repo = args.repo.expanduser().resolve()
    root = args.root.expanduser().resolve()

    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        # worktree checkouts have .git as a file; parent must be a real repo
        inside = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo)
        if inside != "true":
            print(f"Not a git repo: {repo}", file=sys.stderr)
            return 1

    root.mkdir(parents=True, exist_ok=True)
    base = args.base or "HEAD"

    for key in args.keys:
        path = root / key
        if path.exists():
            print(f"skip exists: {path}")
            continue
        # Prefer create branch from base; if branch exists, just attach worktree
        branches = run(["git", "branch", "--list", key], cwd=repo)
        if branches.strip():
            run(["git", "worktree", "add", str(path), key], cwd=repo)
            print(f"worktree (existing branch): {path} -> {key}")
        else:
            run(["git", "worktree", "add", "-b", key, str(path), base], cwd=repo)
            print(f"worktree (new branch): {path} -> {key} (from {base})")

    print(run(["git", "worktree", "list"], cwd=repo))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
