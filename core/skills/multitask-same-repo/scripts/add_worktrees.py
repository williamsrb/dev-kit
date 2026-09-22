#!/usr/bin/env python3
"""Create git worktrees (and branches) for a same-repo multitask batch."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_BASE_BRANCHES = frozenset({"review"})
REVIEW_TIP_REFS = ("refs/heads/review", "refs/remotes/origin/review")


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


def branch_name_of_ref(repo: Path, ref: str) -> str | None:
    raw = ref.strip()
    for prefix in ("refs/heads/", "refs/remotes/"):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
            break
    raw = raw.removeprefix("remotes/")
    if "/" in raw:
        remote, rest = raw.split("/", 1)
        if remote in ("origin", "upstream"):
            raw = rest
    if raw and not re.fullmatch(r"[0-9a-f]{7,40}", raw):
        return raw
    return None


def _short_ref_name(ref: str) -> str:
    short = ref.strip()
    for prefix in ("refs/heads/", "refs/remotes/", "remotes/"):
        if short.startswith(prefix):
            short = short.removeprefix(prefix)
    if "/" in short and short.split("/", 1)[0] in ("origin", "upstream"):
        short = short.split("/", 1)[1]
    return short


def _is_forbidden_base_name(name: str) -> bool:
    short = _short_ref_name(name)
    return short in FORBIDDEN_BASE_BRANCHES or short.split("/")[-1] in FORBIDDEN_BASE_BRANCHES


def _is_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{7,40}", value))


def assert_base_allowed(repo: Path, base: str, *, via: str) -> None:
    name = branch_name_of_ref(repo, base)
    candidates = {base.strip(), name} if name else {base.strip()}
    for c in candidates:
        if c and _is_forbidden_base_name(c):
            short = _short_ref_name(c)
            raise RuntimeError(
                f"Forbidden base {base!r} ({via}): '{short}' is a testing/deploy "
                "branch and must never be the source of a task worktree or feature "
                "branch. Use the primary checkout's current development branch tip "
                "(e.g. PROJ-295), not review."
            )
    if name is not None and not _is_sha(name):
        return
    try:
        sha = run(["git", "rev-parse", "--verify", f"{base}^{{commit}}"], cwd=repo)
    except RuntimeError:
        return
    for ref in REVIEW_TIP_REFS:
        try:
            tip = run(["git", "rev-parse", "--verify", ref], cwd=repo)
        except RuntimeError:
            continue
        if sha == tip:
            raise RuntimeError(
                f"Forbidden base {base!r} ({via}): that commit is the tip of "
                f"{ref}, a testing/deploy line. Pass the development branch "
                "name (e.g. PROJ-295), not review's SHA."
            )


def current_branch_tip(repo: Path) -> tuple[str, str]:
    branch = run(["git", "branch", "--show-current"], cwd=repo)
    if not branch:
        raise RuntimeError(
            f"Repo is detached HEAD at {repo}. Check out a development branch "
            "(not review) — base is that branch's latest commit."
        )
    if branch in FORBIDDEN_BASE_BRANCHES:
        raise RuntimeError(
            f"Repo is on forbidden branch {branch!r} at {repo}. Check out the "
            "development branch you build features from (e.g. PROJ-295), then retry."
        )
    sha = run(["git", "rev-parse", "refs/heads/" + branch], cwd=repo)
    return branch, sha


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
        help=(
            "Start point for new branches (default: tip of --repo's current "
            "branch). Must not be review / origin/review."
        ),
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
    if args.base:
        assert_base_allowed(repo, args.base, via="--base")
        base = args.base
        base_ref = branch_name_of_ref(repo, args.base) or args.base
    else:
        base_ref, _sha = current_branch_tip(repo)
        assert_base_allowed(repo, base_ref, via="current branch")
        base = base_ref

    print(f"base: {base_ref} ({base})")

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
