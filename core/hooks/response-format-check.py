#!/usr/bin/env python3
"""Claude Code Stop hook: block a reply whose marker or bullet lines are indented
with plain or non-breaking spaces instead of raw &nbsp; entities, or that uses
Markdown list syntax (-, *, 1., 1)).

Four leading spaces turn the line into a Markdown code block, so the marker list
renders as preformatted text (rules/response-formatting.mdc, Markers).

Usage: response-format-check.py   (reads Claude Code's Stop hook JSON on stdin)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

for _root in (Path(__file__).resolve().parent.parent, Path.home() / ".agents"):
    if (_root / "bin" / "agentctl_config.py").is_file():
        sys.path.insert(0, str(_root / "bin"))
        break
import agentctl_config

MARKERS = "✅⛔⚠🔹🔸👉❓🚫💡•◦▪"
KEYCAP = r"(?:[0-9]️?⃣|🔟)"
CIRCLED = "Ⓐ-Ⓩ"
BAD_INDENT = re.compile(rf"^[ \t ]+(?:[{MARKERS}{CIRCLED}]|{KEYCAP})")
FENCE = re.compile(r"^ {0,3}(```|~~~)")
LIST_SYNTAX = re.compile(r"^ {0,3}([-*]|\d+[.)])\s")
SKIPPED_LINE = re.compile(r"^\s*(\||>)")


def main() -> int:
    cfg = agentctl_config.load_quiet()
    if agentctl_config.in_factory(cfg) and ((cfg or {}).get("hooks") or {}).get("response_format_skip_factory", True):
        return 0  # headless factory worker: its reply is a report, not operator chat
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    if not isinstance(payload, dict) or payload.get("stop_hook_active"):
        return 0

    message = payload.get("last_assistant_message") or ""
    reasons = []
    offending = find_bad_lines(message)
    if offending:
        sample = "\n".join(f"  line {n}: {text[:60]!r}" for n, text in offending[:3])
        reasons.append(
            "Response formatting: marker or bullet lines are indented with spaces, tabs "
            "or U+00A0 (4 leading spaces render as a code block). Rewrite the reply with raw &nbsp; "
            "entities as the indent, outside any code span:\n" + sample
        )
    listed = find_list_syntax_lines(message)
    if listed:
        sample = "\n".join(f"  line {n}: {text[:60]!r}" for n, text in listed[:3])
        reasons.append(
            "Response formatting: no Markdown list syntax (-, *, 1., 1)). Use the bullet or marker "
            "lines from rules/response-formatting.mdc:\n" + sample
        )
    if not reasons:
        return 0
    print(json.dumps({"decision": "block", "reason": "\n".join(reasons)}))
    return 0


def prose_lines(text: str):
    """(number, line) outside fenced blocks, table rows and blockquotes."""
    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and not SKIPPED_LINE.match(line):
            yield number, line


def find_list_syntax_lines(text: str) -> list[tuple[int, str]]:
    return [(n, line) for n, line in prose_lines(text) if LIST_SYNTAX.match(line)]


def find_bad_lines(text: str) -> list[tuple[int, str]]:
    return [(n, line) for n, line in prose_lines(text) if BAD_INDENT.match(line)]


if __name__ == "__main__":
    sys.exit(main())
