#!/usr/bin/env python3
"""Collect daily work evidence: prompt history + git repos/commits for a given date.

Usage: collect-daily-evidence.py [YYYY-MM-DD]
Default date: today (local timezone).

Ported from collect-daily-evidence.sh — same output sections and semantics, minus the
`date -d` / `date -v` macOS-vs-Linux fork and the `find -newermt` filtering.
"""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
PROJECTS_ROOT = HOME / "Workspace" / "Projects"

MTIME_EXCLUDE_DIRS = {".git", "node_modules", "build", "dist"}
MTIME_MAX_DEPTH = 4       # matches `find -maxdepth 4`
GIT_SCAN_MAX_DEPTH = 6    # matches `find -maxdepth 6 -type d -name .git`


def git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )


def git_config(key: str) -> str:
    result = git(["config", key])
    return result.stdout.strip() if result.returncode == 0 else ""


def find_git_dirs(root: Path) -> list[Path]:
    """All directories named .git up to GIT_SCAN_MAX_DEPTH below root, sorted."""
    found: list[Path] = []
    root_depth = len(root.parts)
    for dirpath, dirnames, _ in os.walk(root):
        depth = len(Path(dirpath).parts) - root_depth
        if ".git" in dirnames and depth + 1 <= GIT_SCAN_MAX_DEPTH:
            found.append(Path(dirpath) / ".git")
        # Never recurse into a .git we found; stop descending past the max depth.
        dirnames[:] = [d for d in dirnames if d != ".git"]
        if depth + 1 >= GIT_SCAN_MAX_DEPTH:
            dirnames[:] = []
    return sorted(found, key=str)


def has_recent_mtime(repo: Path, start: float, end: float) -> bool:
    """True if any file under repo (depth<=4, excluded dirs pruned) has mtime in [start, end)."""
    repo_depth = len(repo.parts)
    for dirpath, dirnames, filenames in os.walk(repo):
        depth = len(Path(dirpath).parts) - repo_depth
        dirnames[:] = [d for d in dirnames if d not in MTIME_EXCLUDE_DIRS]
        if depth >= MTIME_MAX_DEPTH:
            dirnames[:] = []
        for name in filenames:
            try:
                mtime = (Path(dirpath) / name).stat().st_mtime
            except OSError:
                continue
            if start <= mtime < end:
                return True
    return False


def relative_to_projects(repo: Path) -> str:
    prefix = str(PROJECTS_ROOT) + os.sep
    text = str(repo)
    return text[len(prefix):] if text.startswith(prefix) else text


def main() -> int:
    date_str = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()

    try:
        day = dt.date.fromisoformat(date_str)
    except ValueError:
        print(f"Invalid date: {date_str} (expected YYYY-MM-DD)", file=sys.stderr)
        return 1

    next_day = (day + dt.timedelta(days=1)).isoformat()
    since = f"{date_str} 00:00:00"
    until = f"{next_day} 00:00:00"
    # Local-midnight window for mtime comparison.
    start_ts = dt.datetime.combine(day, dt.time.min).timestamp()
    end_ts = dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min).timestamp()

    history_dir = HOME / ".cursor" / "history" / date_str
    git_author = os.environ.get("GIT_AUTHOR") or git_config("user.email")
    git_name = os.environ.get("GIT_NAME") or git_config("user.name")

    print(f"=== HISTORY PROMPTS ({date_str}) ===")
    if history_dir.is_dir():
        prompts = sorted(str(p) for p in history_dir.glob("*_prompt.md"))
        for path in prompts:
            print(path)
        print("")
        print("--- prompt count ---")
        print(len(prompts))
    else:
        print(f"(folder missing: {history_dir})")

    print("")
    print(f"=== GIT REPOS WITH ACTIVITY ({date_str}) ===")

    for git_dir in find_git_dirs(PROJECTS_ROOT):
        repo = git_dir.parent
        if not repo.is_dir():
            continue
        rel = relative_to_projects(repo)

        commit_log = ""
        if git(["rev-parse", "--git-dir"], cwd=repo).returncode == 0:
            log = git(
                [
                    "log",
                    f"--since={since}",
                    f"--until={until}",
                    "--format=%h|%ad|%an|%ae|%s",
                    "--date=format:%H:%M",
                ],
                cwd=repo,
            )
            if log.returncode == 0:
                commit_log = log.stdout.strip("\n")
        has_commit = bool(commit_log)

        has_mtime = has_recent_mtime(repo, start_ts, end_ts)

        if has_commit or has_mtime:
            remote_res = git(["remote", "get-url", "origin"], cwd=repo)
            remote = remote_res.stdout.strip() if remote_res.returncode == 0 else "(no origin)"
            branch_res = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
            branch = branch_res.stdout.strip() if branch_res.returncode == 0 else "?"
            print("")
            print(f"REPO|{rel}|branch={branch}|remote={remote}")

            if has_commit:
                print(f"COMMITS|{rel}")
                print(commit_log)

            if has_mtime and not has_commit:
                print("NOTE|uncommitted changes or file edits today (no commits)")

    print("")
    print("=== GIT AUTHOR FILTER (for your commits) ===")
    print(f"name={git_name}")
    print(f"email={git_author}")

    print("")
    print("=== SLACK (collect via MCP — ALL workspaces) ===")
    print("Slack MCP is parked. Enable first: ~/.agents/kb/implementation/How-to-enable-playwright-mcp.md (Slack section).")
    print(f"DATE={date_str}")
    print("Each Slack MCP = a different workspace. Discover with GetMcpTools pattern=slack.")
    print("Known servers: plugin-slack-slack | user-slack-workspace-leanon (+ any others discovered)")
    print("For EACH Slack MCP server:")
    print("  Authenticate if needed: mcp_auth {} on THAT server")
    print(f'  Search 1: slack_search_public_and_private query="from:me on:{date_str}" sort=timestamp sort_dir=asc include_context=false')
    print(f'  Search 2: slack_search_public_and_private query="to:me on:{date_str}" sort=timestamp sort_dir=asc include_context=false')
    print(f'  Search 3: slack_search_public_and_private query="from:me on:{date_str} has:link example.atlassian.net" include_context=false')
    print("  Paginate each search until pagination_info reports no more pages.")
    print("  Tag hits with mcpServer id; use slack_read_thread on the SAME server for thread detail.")
    print("Do not stop after one workspace. Report per-workspace counts in the evidence appendix.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
