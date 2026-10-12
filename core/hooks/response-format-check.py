#!/usr/bin/env python3
"""Claude Code Stop hook: block a reply whose marker or bullet lines are indented
with plain or non-breaking spaces instead of raw &nbsp; entities.

Four leading spaces turn the line into a Markdown code block, so the marker list
renders as preformatted text (rules/response-formatting.mdc, Markers).

Usage: response-format-check.py   (reads Claude Code's Stop hook JSON on stdin)
"""

from __future__ import annotations

import json
import re
import sys

MARKERS = "✅⛔⚠🔹🔸👉❓🚫💡•◦▪"
KEYCAP = r"(?:[0-9]️?⃣|🔟)"
CIRCLED = "Ⓐ-Ⓩ"
BAD_INDENT = re.compile(rf"^[ \t ]+(?:[{MARKERS}{CIRCLED}]|{KEYCAP})")
FENCE = re.compile(r"^ {0,3}(```|~~~)")


def main() -> int:
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return 0

    offending = find_bad_lines(payload.get("last_assistant_message") or "")
    if not offending:
        return 0

    sample = "\n".join(f"  line {n}: {text[:60]!r}" for n, text in offending[:3])
    reason = (
        "Response formatting: marker or bullet lines are indented with spaces, tabs "
        "or U+00A0 (4 leading spaces render as a code block). Rewrite the reply with raw &nbsp; "
        "entities as the indent, outside any code span:\n" + sample
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def find_bad_lines(text: str) -> list[tuple[int, str]]:
    bad = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and BAD_INDENT.match(line):
            bad.append((number, line))
    return bad


if __name__ == "__main__":
    sys.exit(main())
