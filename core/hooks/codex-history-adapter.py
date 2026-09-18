#!/usr/bin/env python3
"""Adapt native Codex prompt/stop hook payloads to the shared history writer."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HISTORY_PY = Path.home() / '.agents' / 'hooks' / 'history.py'


def run_history(mode: str, payload: dict[str, object]) -> str:
    result = subprocess.run(
        [sys.executable, str(HISTORY_PY), mode],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {}

        session_id = str(payload.get('session_id') or '')
        turn_id = str(payload.get('turn_id') or '')
        event_name = str(payload.get('hook_event_name') or '')

        if mode == 'prompt':
            cwd = str(payload.get('cwd') or '')
            mapped = {
                'prompt': payload.get('prompt') or '',
                'conversation_id': session_id,
                'generation_id': turn_id,
                'hook_event_name': event_name or 'UserPromptSubmit',
                'workspace_roots': [cwd] if cwd else [],
            }
            sys.stdout.write(run_history('prompt', mapped) or '{"continue": true}\n')
        elif mode == 'stop':
            mapped = {
                'text': payload.get('last_assistant_message') or '',
                'conversation_id': session_id,
                'generation_id': turn_id,
                'hook_event_name': event_name or 'Stop',
                'status': 'completed',
            }
            sys.stdout.write(run_history('response', mapped) or '{}\n')
        else:
            sys.stdout.write('{}\n')
        return 0
    except Exception:
        sys.stdout.write('{"continue": true}\n' if mode == 'prompt' else '{}\n')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
