#!/usr/bin/env python3
"""Check that the expected React4XP project structure exists.

Runs against the current working directory (the project root). Exits non-zero if any
required path is missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

REQUIRED_PATHS = (
    "src/main/resources/react4xp/entries/App.tsx",
    "src/main/resources/react4xp/componentRegistry.tsx",
    "src/main/resources/react4xp/dataFetcher.ts",
)


def main() -> int:
    print("Checking React4XP structure...")

    missing = False
    for rel in REQUIRED_PATHS:
        if Path(rel).exists():
            print(f"OK: {rel}")
        else:
            print(f"MISSING: {rel}")
            missing = True

    if Path("react4xp.config.js").is_file():
        print("OK: react4xp.config.js")
    else:
        print("INFO: react4xp.config.js not found at repository root")

    if missing:
        print("Structure check failed.")
        return 1

    print("Structure check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
