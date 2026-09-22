#!/usr/bin/env python3
"""Create <REPO>-multitask/<SLUG> worktree on branch SLUG from the start checkout's current branch tip."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MULTITASK_SUFFIX = "-multitask"
# Testing/integration deploy line — may contain non-approved merges. Never a feature base.
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


def branch_name_of_ref(repo: Path, ref: str) -> str | None:
    """Best-effort short branch name for ref (local or remote), else None."""
    raw = ref.strip()
    for prefix in ("refs/heads/", "refs/remotes/"):
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
            break
    raw = raw.removeprefix("remotes/")
    # origin/review → review; review → review; feature/x stays feature/x
    if "/" in raw:
        remote, rest = raw.split("/", 1)
        # treat common remote prefixes as remotes
        if remote in ("origin", "upstream") or branch_exists(repo, f"remotes/{remote}/{rest}"):
            raw = rest
    if raw and not re.fullmatch(r"[0-9a-f]{7,40}", raw):
        return raw
    # Symbolic tip of a branch?
    try:
        abbrev = run(
            ["git", "rev-parse", "--abbrev-ref", "--verify", f"{ref}^{{commit}}"],
            cwd=repo,
        )
    except RuntimeError:
        return None
    if abbrev in ("HEAD", "") or abbrev.startswith("HEAD"):
        return None
    if abbrev.startswith(("origin/", "upstream/")):
        return abbrev.split("/", 1)[1]
    return abbrev


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
    """Refuse testing-line branches (review) as worktree/feature bases."""
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
    # A raw SHA of review's tip is the same source. A named non-review branch
    # whose tip happens to match review stays allowed.
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


def current_branch_tip(start: Path) -> tuple[str, str]:
    """
    Return (branch_name, full_sha) for the start checkout's current branch tip.

    Refuses detached HEAD and forbidden testing branches (review).
    """
    branch = run(["git", "branch", "--show-current"], cwd=start)
    if not branch:
        raise RuntimeError(
            f"Start checkout is detached HEAD at {start}. Check out a development "
            "branch (not review) and retry — base is that branch's latest commit."
        )
    if branch in FORBIDDEN_BASE_BRANCHES:
        raise RuntimeError(
            f"Start checkout is on forbidden branch {branch!r} at {start}. "
            "Check out the development/integration branch you build features from "
            "(e.g. PROJ-295), then retry. Never create task worktrees from review."
        )
    sha = run(["git", "rev-parse", "refs/heads/" + branch], cwd=start)
    return branch, sha


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
            "SLUG from the start checkout's current branch tip (never review)"
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
        help=(
            "Start point for new branches (default: tip of --start's current "
            "branch). Must not be review / origin/review."
        ),
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
    base_ref, base_sha = current_branch_tip(start)
    if args.base:
        assert_base_allowed(main_repo, args.base, via="--base")
        base = args.base
        # Resolve for reporting
        try:
            base_sha = run(["git", "rev-parse", args.base], cwd=main_repo)
            named = branch_name_of_ref(main_repo, args.base)
            base_ref = named or args.base
        except RuntimeError:
            base_ref = args.base
    else:
        assert_base_allowed(main_repo, base_ref, via="current branch")
        # Prefer the branch name as start-point so logs show PROJ-295, not a bare SHA
        base = base_ref

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
                "base_sha": base_sha,
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
                    "base_sha": base_sha,
                    "worktrees": results,
                    "worktree_list": worktree_list,
                },
                indent=2,
            )
        )
    else:
        print(f"main_repo: {main_repo}")
        print(f"multitask_root: {multitask_root}")
        print(f"base: {base_ref} ({base_sha})")
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
