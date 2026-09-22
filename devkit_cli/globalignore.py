"""The kit's ignore patterns, in the user's global git ignore file.

The harness leaves regenerable output in whatever repo it works in: graft's
graph, graphify's output, agentctl's raw security reports. One global block
keeps all of it out of every repo, so no tool has to edit a repo's .gitignore.
The wrappers export GRAFT_NO_GITIGNORE and GRAFT_NO_IGNORE for the same reason.

devkit-uninstall.sh removes the block by its BEGIN and END lines, so keep them
identical to the copies in uninstaller.SCRIPT.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .common import Plan

BEGIN = "# Added by devkit: regenerable harness output, any depth."
END = "# End of devkit block."
PATTERNS = (
    "graft",
    "graft/",
    "!**/skills/graft",
    "!**/skills/graft/",
    "!**/skills/graft/**",
    "!**/hooks/graft",
    "!**/hooks/graft/",
    "!**/hooks/graft/**",
    ".graft",
    ".graft/",
    "graphify-out",
    "graphify-out/",
    ".security-local",
    ".security-local/",
)


def target(home: Path) -> Path:
    """The file git reads for this home: core.excludesFile, else git's default."""
    try:
        configured = subprocess.run(
            ["git", "config", "--global", "--get", "core.excludesFile"],
            capture_output=True, text=True, check=False,
            env={**os.environ, "HOME": str(home)},
        ).stdout.strip()
    except FileNotFoundError:
        configured = ""
    if not configured:
        return Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config") / "git" / "ignore"
    if configured.startswith("~/"):
        return home / configured[2:]
    path = Path(configured)
    return path if path.is_absolute() else home / path


def ensure(home: Path, plan: Plan) -> None:
    """Append the block unless it, or every one of its patterns, is already there.

    All-or-nothing on purpose: the negations only work after `graft`, so
    appending just the missing lines could re-ignore skills/graft.
    """
    path = target(home)
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    lines = {line.strip() for line in current.splitlines()}
    if BEGIN in lines or all(pattern in lines for pattern in PATTERNS):
        return
    plan.record(f"append {path} (global git ignore)")
    if not plan.apply:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    gap = "" if not current else "\n" if current.endswith("\n") else "\n\n"
    path.write_text(current + gap + "\n".join((BEGIN, *PATTERNS, END)) + "\n",
                    encoding="utf-8")
