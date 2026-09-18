#!/usr/bin/env python3
"""Check that the CLI tools required for React4XP development are on PATH.

Exits non-zero if any required command is missing.
"""

from __future__ import annotations

import shutil
import sys

REQUIRED_COMMANDS = (
    "enonic",
    "node",
    "npm",
)


def main() -> int:
    print("Checking required commands...")

    missing = False
    for cmd in REQUIRED_COMMANDS:
        path = shutil.which(cmd)
        if path:
            print(f"OK: {cmd} ({path})")
        else:
            print(f"MISSING: {cmd}")
            missing = True

    if missing:
        print("Command check failed.")
        return 1

    print("Command check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
