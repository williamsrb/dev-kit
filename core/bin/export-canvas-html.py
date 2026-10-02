#!/usr/bin/env python3
"""PATH wrapper for the Cursor canvas → HTML exporter."""

from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPT = (
    Path.home()
    / ".agents"
    / "skills-vendor"
    / "cursor"
    / "export-canvas-html"
    / "scripts"
    / "export_canvas.py"
)

if not SCRIPT.is_file():
    sys.stderr.write(f"export-canvas-html: missing {SCRIPT}\n")
    sys.exit(127)

os.execv(sys.executable, [sys.executable, str(SCRIPT), *sys.argv[1:]])
