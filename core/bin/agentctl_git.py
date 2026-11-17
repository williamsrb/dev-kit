"""Git helpers for agentctl."""

from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path

from agentctl_common import emit, git, repo_root


def parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        raise ValueError(f"not an ISO 8601 datetime: {value!r}") from None
    return parsed if parsed.tzinfo else parsed.astimezone()


def head_dates(cwd: Path) -> dict[str, str]:
    out = git(cwd, "log", "-1", "--format=%aI%n%cI").stdout.split()
    return {"author": out[0], "committer": out[1]}


def cmd_git_amend_date(args: argparse.Namespace) -> int:
    cwd = args.cwd.expanduser().resolve()
    try:
        when = parse_datetime(args.datetime)
        if not repo_root(cwd):
            raise ValueError(f"{cwd} is not inside a git repository")
        if git(cwd, "rev-parse", "--verify", "HEAD").returncode != 0:
            raise ValueError("repository has no commits")
        if git(cwd, "diff", "--cached", "--quiet").returncode != 0:
            raise ValueError("refused: staged changes would be folded into the amended commit")
        pushed = git(cwd, "merge-base", "--is-ancestor", "HEAD", "@{u}").returncode == 0
        if pushed and not args.allow_pushed:
            raise ValueError("refused: HEAD is already on the upstream branch; pass --allow-pushed to rewrite it")
    except ValueError as exc:
        emit({"status": "error", "error": str(exc)})
        return 2

    before = head_dates(cwd)
    stamp = when.isoformat(timespec="seconds")
    result = subprocess.run(
        ["git", "commit", "--amend", "--no-edit", "--date", stamp],
        cwd=str(cwd), capture_output=True, text=True, check=False,
        env={**os.environ, "GIT_COMMITTER_DATE": stamp},
    )
    if result.returncode != 0:
        emit({"status": "error", "error": result.stderr.strip() or result.stdout.strip()})
        return 1
    emit({"status": "ok", "before": before, "after": head_dates(cwd), "was_pushed": pushed})
    return 0


def add_git_parsers(group) -> None:
    amend = group.add_parser(
        "amend-date",
        help="Rewrite the date of the last commit without changing its content.",
        description=(
            "Runs git commit --amend --no-edit with --date and GIT_COMMITTER_DATE set to DATETIME "
            "(ISO 8601, offset recommended). Refuses staged changes and an already pushed HEAD "
            "unless --allow-pushed."
        ),
    )
    amend.add_argument("datetime", help="ISO 8601 datetime, e.g. 2026-10-20T14:30:00-03:00.")
    amend.add_argument("-C", dest="cwd", type=Path, default=Path.cwd(), help="Repository directory.")
    amend.add_argument("--allow-pushed", action="store_true", help="Allow amending a commit already on the upstream.")
    amend.set_defaults(func=cmd_git_amend_date)
