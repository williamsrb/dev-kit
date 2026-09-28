"""Shared primitives for agentctl command groups.

Do not put pack/merge/REST logic here. Groups import emit/run/markdown helpers
so they never import bin/agentctl (cycle).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import agentctl_jira

agents_home = agentctl_jira.agents_home

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
HEADING_QUALIFIER_RE = re.compile(r"\s*(?:\(.*\)|\[.*\]|[\u2014\u2013:-]\s.*)\s*$")


def emit(payload: Any, *, as_json: bool = True) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    elif isinstance(payload, str):
        print(payload)
    else:
        print(payload)


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    check: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            input=input_text,
            text=True,
            capture_output=True,
            check=check,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            command, returncode=124, stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\ntimed out after {timeout}s",
        )


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=cwd)


def repo_root(start: Path) -> Path | None:
    result = git(start, "rev-parse", "--show-toplevel")
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    return None


def argsafe_limit(value: int) -> int:
    return max(1, min(value, 100_000))


def section_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def section_slugs(title: str) -> list[str]:
    """Slug plus the qualifier-stripped base slug."""
    slugs = [section_slug(title)]
    base = section_slug(HEADING_QUALIFIER_RE.sub("", title))
    if base and base not in slugs:
        slugs.append(base)
    return slugs


def markdown_sections(path: Path) -> list[dict[str, Any]]:
    text_lines = path.read_text(encoding="utf-8").splitlines()
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(text_lines):
        match = HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2)))
    sections: list[dict[str, Any]] = []
    for pos, (start, level, title) in enumerate(headings):
        end = len(text_lines)
        for later_start, later_level, _ in headings[pos + 1:]:
            if later_level <= level:
                end = later_start
                break
        slugs = section_slugs(title)
        sections.append({
            "title": title,
            "slug": slugs[0],
            "slugs": slugs,
            "level": level,
            "start_line": start + 1,
            "end_line": end,
            "text": "\n".join(text_lines[start:end]).rstrip(),
        })
    return sections


def run_skill_script(script: Path, script_args: list[str], *, timeout: float | None = None) -> int:
    if not script.is_file():
        emit({"status": "error", "error": f"skill script missing: {script}"})
        return 2
    result = run([sys.executable, str(script), *script_args], timeout=timeout)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        emit({
            "status": "error",
            "error": "non-JSON output from skill script",
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:2000],
        })
        return 2
    emit(payload)
    return result.returncode
