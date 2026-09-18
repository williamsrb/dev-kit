#!/usr/bin/env python3
"""Create <REPO>-multitask/<SLUG> worktree on branch SLUG from current HEAD."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MULTITASK_SUFFIX = "-multitask"


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


def validate_slug(slug: str) -> str:
    if not SLUG_RE.match(slug):
        raise RuntimeError(
            f"Invalid SLUG {slug!r}: use a Jira key or slug "
            "(letters, digits, . _ -; no path separators)"
        )
    return slug


def git_toplevel(start: Path) -> Path:
    return Path(run(["git", "rev-parse", "--show-toplevel"], cwd=start))


def main_worktree_path(repo: Path) -> Path:
    """First entry in `git worktree list --porcelain` is the primary checkout."""
    out = run(["git", "worktree", "list", "--porcelain"], cwd=repo)
    for line in out.splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree ") :])
    raise RuntimeError(f"No worktree listed for {repo}")


def resolve_layout(start: Path) -> tuple[Path, Path, str]:
    """
    Return (main_repo, multitask_root, repo_name).

    Layout:
      <parent>/REPO-NAME
      <parent>/REPO-NAME-multitask/<SLUG>
    """
    toplevel = git_toplevel(start)
    parent = toplevel.parent

    if parent.name.endswith(MULTITASK_SUFFIX):
        repo_name = parent.name[: -len(MULTITASK_SUFFIX)]
        if not repo_name:
            raise RuntimeError(f"Cannot derive REPO-NAME from {parent}")
        multitask_root = parent
        main_repo = parent.parent / repo_name
        if not main_repo.is_dir():
            # Fall back to the repo's primary worktree path
            main_repo = main_worktree_path(toplevel)
        return main_repo.resolve(), multitask_root.resolve(), repo_name

    main_repo = main_worktree_path(toplevel)
    repo_name = main_repo.name
    multitask_root = main_repo.parent / f"{repo_name}{MULTITASK_SUFFIX}"
    return main_repo.resolve(), multitask_root.resolve(), repo_name


def branch_exists(repo: Path, name: str) -> bool:
    return bool(run(["git", "branch", "--list", "--", name], cwd=repo).strip())


def current_head(start: Path) -> tuple[str, str]:
    """Return (branch_or_HEAD, full_sha) for the starting checkout."""
    sha = run(["git", "rev-parse", "HEAD"], cwd=start)
    ref = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=start)
    return ref, sha


def ensure_worktree(repo: Path, path: Path, slug: str, base: str) -> str:
    if path.exists():
        if not path.is_dir():
            raise RuntimeError(f"Path exists and is not a directory: {path}")
        # Already a linked worktree?
        try:
            top = git_toplevel(path)
            branch = run(["git", "branch", "--show-current"], cwd=path)
        except RuntimeError as exc:
            raise RuntimeError(
                f"Path exists but is not a usable git worktree: {path}"
            ) from exc
        if top.resolve() != path.resolve():
            raise RuntimeError(f"Path exists but is not a worktree root: {path}")
        if branch != slug:
            raise RuntimeError(
                f"Path exists on branch {branch!r}, expected {slug!r}: {path}"
            )
        return f"skip exists: {path} -> {slug}"

    if branch_exists(repo, slug):
        run(["git", "worktree", "add", str(path), slug], cwd=repo)
        return f"worktree (existing branch): {path} -> {slug}"

    # Never --detach: always create/check out named branch SLUG
    run(["git", "worktree", "add", "-b", slug, str(path), base], cwd=repo)
    return f"worktree (new branch): {path} -> {slug} (from {base})"


def assert_attached(path: Path, slug: str) -> None:
    branch = run(["git", "branch", "--show-current"], cwd=path)
    if not branch:
        raise RuntimeError(
            f"Worktree is detached HEAD at {path}; expected branch {slug}"
        )
    if branch != slug:
        raise RuntimeError(
            f"Worktree branch is {branch!r}, expected {slug!r}: {path}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create sibling <REPO>-multitask/<SLUG> worktree(s) on branch "
            "SLUG from the current checkout's HEAD"
        )
    )
    parser.add_argument(
        "slugs",
        nargs="+",
        help="Branch name and worktree folder (Jira key or other slug)",
    )
    parser.add_argument(
        "--start",
        type=Path,
        default=None,
        help="Directory that defines the current repo/branch (default: cwd)",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Start point for new branches (default: HEAD of --start)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print one JSON object summarizing the result",
    )
    args = parser.parse_args()

    start = (args.start or Path.cwd()).expanduser().resolve()
    slugs = [validate_slug(s) for s in args.slugs]

    main_repo, multitask_root, repo_name = resolve_layout(start)
    base_ref, base_sha = current_head(start)
    base = args.base or base_sha

    multitask_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, str]] = []
    messages: list[str] = []
    for slug in slugs:
        path = multitask_root / slug
        msg = ensure_worktree(main_repo, path, slug, base)
        assert_attached(path, slug)
        messages.append(msg)
        results.append(
            {
                "slug": slug,
                "path": str(path),
                "branch": slug,
                "base": base,
                "message": msg,
            }
        )

    worktree_list = run(["git", "worktree", "list"], cwd=main_repo)

    if args.json:
        print(
            json.dumps(
                {
                    "repo_name": repo_name,
                    "main_repo": str(main_repo),
                    "multitask_root": str(multitask_root),
                    "base_ref": base_ref,
                    "base": base,
                    "worktrees": results,
                    "worktree_list": worktree_list,
                },
                indent=2,
            )
        )
    else:
        print(f"main_repo: {main_repo}")
        print(f"multitask_root: {multitask_root}")
        print(f"base: {base_ref} ({base})")
        for msg in messages:
            print(msg)
        print(worktree_list)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
