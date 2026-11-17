#!/usr/bin/env python3
"""Report PRD comments not yet checked for requirement changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

COMMENT_RE = re.compile(r"^### Comment (\S+)")
MARKER_RE = re.compile(r"^Checked through: (\S+)\s*$")


def section(lines: list[str], prefix: str, end: str = "## ") -> list[str]:
    """Lines under the first H2 starting with `prefix`, up to the next line starting with `end`."""
    out: list[str] = []
    inside = False
    for line in lines:
        if inside:
            if line.startswith(end):
                break
            out.append(line)
        elif line.startswith(prefix):
            inside = True
    return out


def check(text: str) -> dict:
    lines = text.splitlines()
    # Comment bodies may carry their own H2 headings, so only Attachments ends the Comments section.
    comment_ids = [m.group(1) for line in section(lines, "## Comments", end="## Attachments")
                   if (m := COMMENT_RE.match(line))]
    changes = section(lines, "## Requirement Changes")
    markers = [m.group(1) for line in changes if (m := MARKER_RE.match(line))]
    checked = markers[-1] if markers else None
    if checked in comment_ids:
        unchecked = comment_ids[comment_ids.index(checked) + 1:]
    else:
        unchecked = comment_ids
    return {
        "comments": comment_ids,
        "checked_through": checked,
        "unchecked": unchecked,
        "stale": bool(unchecked),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prd", type=Path)
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args()
    result = check(args.prd.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(result))
    else:
        state = "stale" if result["stale"] else "current"
        print(f"{state}: unchecked {', '.join(result['unchecked']) or 'none'}")
    return 1 if result["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())
