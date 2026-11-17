"""The Python floor: find an interpreter that meets it, or re-exec under one.

This is the first devkit code a too-old `python3` runs (RHEL 9 ships 3.9), so
it must parse and run on 3.9: stdlib only, no 3.10+ syntax.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

MIN = (3, 12)
# `python3` first: a system that already meets the floor keeps running as today.
CANDIDATES = ("python3", "python3.13", "python3.12")
GUARD_ENV = "DEVKIT_REEXEC"
FIX = ("devkit needs Python 3.12 or newer and found none on PATH.\n"
       "  RHEL 9 and rebuilds: ./bootstrap.sh --apply, or sudo dnf install python3.12\n"
       "  then re-run; /usr/bin/python3 stays as it is.")

_PROBE = f"import sys; sys.exit(sys.version_info < {MIN})"


def meets_floor(path: str) -> bool:
    """True when the interpreter at `path` is 3.12 or newer."""
    try:
        return subprocess.run([path, "-c", _PROBE], check=False, timeout=30,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def find_python() -> str | None:
    """Absolute path of the first candidate on PATH that is 3.12 or newer."""
    for name in CANDIDATES:
        path = shutil.which(name)
        if path and meets_floor(path):
            return path
    return None


def reexec_if_old(argv: list[str]) -> None:
    """No-op on 3.12+. Otherwise exec argv under a newer interpreter, or exit 2."""
    if sys.version_info >= MIN:
        return
    found = None if os.environ.get(GUARD_ENV) else find_python()
    if not found:
        sys.stderr.write(FIX + "\n")
        raise SystemExit(2)
    os.environ[GUARD_ENV] = "1"
    os.execv(found, [found] + list(argv))
