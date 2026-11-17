#!/usr/bin/env python3
"""Claude Code PreToolUse hook: deny the issue tracker's MCP comment and attachment writes.

Which tools count is not decided here: .agentctl [tracker.<kind>] write_tools lists the MCP tool names
and write_guard_hint says where those writes go instead (for Jira, `agentctl jira comment|attach`, which
enforces --confirm-issue, the all-steps-done evidence gate, one comment per day and the pre-edit backup).
Matches by tool-name suffix under any server prefix (mcp__<server>__<tool>), and executeWrite calls
whose operation name is one of those tools.

Fails closed: unreadable input or an unreadable .agentctl exits 2, which blocks the call.
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

EXECUTE_NAME = re.compile(r"^mcp__.+__executeWrite$")


def blocked(payload: dict, write_tools: list[str]) -> bool:
    if not write_tools:
        return False
    name = str(payload.get("tool_name") or "")
    if re.match(rf"^mcp__.+__({'|'.join(map(re.escape, write_tools))})$", name):
        return True
    if EXECUTE_NAME.match(name):
        return (payload.get("tool_input") or {}).get("name") in write_tools
    return False


def main() -> int:
    cfg = agentctl_config.load_quiet()
    if cfg is None:
        print("jira-write-guard: cannot read .agentctl; blocking", file=sys.stderr)
        return 2
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise TypeError("payload is not an object")
        tracker = agentctl_config.tracker(cfg) or {}
        deny = blocked(payload, list(tracker.get("write_tools", [])))
    except (ValueError, AttributeError, TypeError, agentctl_config.ConfigError) as exc:
        print(f"jira-write-guard: cannot parse hook input ({exc}); blocking", file=sys.stderr)
        return 2
    if deny:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": tracker.get("write_guard_hint", "Tracker writes go through agentctl."),
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
