#!/usr/bin/env python3
"""devkit — install and manage isolated agent-harness profiles.

Python 3.12, standard library only. No dependency is needed to run this before
bootstrap.sh has installed anything.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devkit_cli import pyfloor

pyfloor.reexec_if_old(sys.argv)

from devkit_cli.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
