#!/usr/bin/env python3
"""Session-end hook: write the chat digest of the session that just ended (factory-kb-harvest RC4, FR-22).

Usage: kb-digest-session-end.py [claude|codex|cursor]  (default claude; the hook JSON arrives on stdin).
Claude and Cursor call it at session end. Codex has no session-end event, so its `Stop` hook calls it after each
turn and the digest is rewritten.

Deterministic only: no model call, no network. Code comes from the bin/ next to this hook; data (kb-inbox,
history) goes to $AGENTS_HOME. Writes $AGENTS_HOME/kb-inbox/<session>/digest.json when the digest has signals.
Factory worker sessions and AGENTCTL_FACTORY runs write nothing. Any error goes to
$AGENTS_HOME/history/.state/hook-errors.log, and the hook always exits 0 so it never blocks the session.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import traceback
from pathlib import Path


def agents_home() -> Path:
    raw = os.environ.get("AGENTS_HOME")
    return Path(raw).expanduser() if raw else Path.home() / ".agents"


def log_error(home: Path, text: str) -> None:
    try:
        log = home / "history" / ".state" / "hook-errors.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} kb-digest-session-end: {text}\n")
    except OSError:
        pass


def main() -> int:
    if os.environ.get("AGENTCTL_FACTORY"):
        return 0
    home = agents_home()
    vendor = sys.argv[1] if len(sys.argv) > 1 else "claude"
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))  # the code ships with this hook
        from agentctl_kb import KbError
        from agentctl_kb_digest import write_digest
        from agentctl_kb_digest_vendors import digest_for, resolve_for

        transcript = payload.get("transcript_path")
        if transcript:
            path = Path(transcript).expanduser()
        else:  # Cursor can send a null transcript_path; its session id still names the file
            session = payload.get("conversation_id") or payload.get("session_id")
            path = resolve_for(vendor, str(session), False) if session else None
        if path is None or not path.is_file():
            return 0
        try:
            digest = digest_for(vendor, path, home)
        except KbError:
            return 0  # a factory worker session: its run already has a digest
        if digest["has_signals"]:
            write_digest(home, path, digest)
    except Exception:  # noqa: BLE001 - the hook must never block the session end
        log_error(home, traceback.format_exc(limit=3).strip().replace("\n", " | "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
