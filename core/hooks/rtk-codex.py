#!/usr/bin/env python3
"""Adapt Codex PreToolUse JSON to RTK's Claude-compatible hook adapter."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RTK = Path.home() / '.local' / 'bin' / 'rtk'


def main() -> int:
    raw = sys.stdin.buffer.read()
    result = subprocess.run(
        [str(RTK), 'hook', 'claude'],
        input=raw,
        capture_output=True,
        check=False,
    )
    if result.stderr:
        sys.stderr.buffer.write(result.stderr)

    output = result.stdout.decode('utf-8', errors='replace').strip()
    if not output:
        return 0

    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return 0

    hook_output = payload.get('hookSpecificOutput')
    if isinstance(hook_output, dict) and 'updatedInput' in hook_output:
        hook_output.setdefault('hookEventName', 'PreToolUse')
        hook_output.setdefault('permissionDecision', 'allow')
        payload['hookSpecificOutput'] = hook_output

    sys.stdout.write(json.dumps(payload, separators=(',', ':')) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
