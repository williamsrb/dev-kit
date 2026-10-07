"""`devkit` itself on PATH: ~/.local/bin/devkit -> <checkout>/devkit.py.

Without it the CLI only works as ./devkit from the checkout. devkit-uninstall.sh
removes the link when it points at a devkit.py, so keep that test identical to
the one in uninstaller.SCRIPT.
"""

from __future__ import annotations

import os
from pathlib import Path

from .common import Plan, repo_file

NAME = "devkit"
TARGET = "devkit.py"


def ensure(home: Path, plan: Plan) -> None:
    dest = home / ".local" / "bin" / NAME
    source = repo_file(TARGET).resolve()
    if dest.is_symlink():
        current = Path(os.readlink(dest))
        if current == source:
            return
        if current.name != TARGET:
            print(f"note: {dest} points at {current}, not devkit; left alone.")
            return
    elif dest.exists():
        print(f"note: {dest} exists and is not a devkit link; left alone.")
        return
    plan.record(f"link   {dest} -> {source}")
    if plan.apply:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.unlink(missing_ok=True)
        dest.symlink_to(source)
