#!/usr/bin/env python3
"""Adapts Claude Code hook payloads to history.py's schema, so Claude Code and
Cursor log into the same history directory (~/.agents/history)
using one shared script.

Usage: claude-history-adapter.py prompt|stop   (reads Claude Code's hook JSON on stdin)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HISTORY_PY = Path(__file__).with_name("history.py")


def log_error(message: str) -> None:
    """Same file and line format as history.py's log_error."""
    home = Path(os.environ.get("AGENTS_HOME") or Path.home() / ".agents").expanduser()
    log = home / "history" / ".state" / "hook-errors.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] claude-history-adapter: {message}\n")


def last_assistant_usage(transcript_path: str | None) -> dict[str, object]:
    """model and token counts from the last assistant entry of the session transcript."""
    if not transcript_path:
        return {}
    try:
        lines = Path(transcript_path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    for line in reversed(lines):
        try:
            message = json.loads(line).get("message")
        except (json.JSONDecodeError, AttributeError):
            continue
        if isinstance(message, dict) and message.get("role") == "assistant":
            usage = message.get("usage") or {}
            return {
                "model": message.get("model", ""),
                "input_tokens": usage.get("input_tokens", ""),
                "output_tokens": usage.get("output_tokens", ""),
            }
    return {}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        log_error(f"bad hook JSON ({exc})")
        sys.stdout.write("{}")
        return 0
    if not isinstance(payload, dict):
        payload = {}

    conversation_id = payload.get("session_id", "")
    generation_id = payload.get("prompt_id", "")

    if mode == "prompt":
        mapped = {
            "prompt": payload.get("prompt", ""),
            "conversation_id": conversation_id,
            "generation_id": generation_id,
            "hook_event_name": "UserPromptSubmit",
            "harness": "claude",
            "workspace_roots": [payload["cwd"]] if payload.get("cwd") else [],
        }
        history_mode = "prompt"
    else:
        mapped = {
            "text": payload.get("last_assistant_message", ""),
            "conversation_id": conversation_id,
            "generation_id": generation_id,
            "hook_event_name": "Stop",
            "harness": "claude",
            "status": "completed",
            **last_assistant_usage(payload.get("transcript_path")),
        }
        history_mode = "response"

    try:
        result = subprocess.run(
            [sys.executable, str(HISTORY_PY), history_mode],
            input=json.dumps(mapped),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log_error("history.py timed out")
        sys.stdout.write("{}")
        return 0
    sys.stdout.write(result.stdout or "{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
