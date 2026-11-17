---
id: how-to-stop-graft-re-registering-its-mcp-server
when_skills: [graft]
inputs: [graft CLI (@nanonets/graft 0.21.1), ~/graft/.cache/wiring-stamp.json, hooks/graft-guard.py]
outputs: [no graft entry in ~/.mcp.json, ~/.claude.json, ~/.cursor/mcp.json or ~/.codex/config.toml after a graft upgrade]
stop_if: [graft MCP is wanted again]
read: whole
prose: caveman-lite
---

# Stop graft re-registering its MCP server

Graft MCP is removed (`mcp/catalog.json` `skip.graft`). It still came back after graft upgrades. Cause: `graft init` once ran in `$HOME`, so graft treats `~` as a wired repo. On a version change, graft's `session-start` hook (`dist/claude/hooks.js`) or its MCP server boot runs `reconcileWiring` (`dist/upkeep.js`). That replays `runInit` (`dist/claude/init.js`), and the replay writes `~/.mcp.json` and `~/.claude.json` `mcpServers.graft`, plus `~/.cursor/mcp.json` and Codex when the stamp's `mcp`/`global` are on. Through the `~/.claude/helpers`, `~/.claude/skills/graft` and `~/.cursor/rules` symlinks it also rewrites `hooks/graft-*.cjs`, `skills/graft/SKILL.md` and `rules/graft.mdc` in the harness.

The replay fires only when `~/graft/.cache/wiring-stamp.json` names a different version than the installed graft. Deleting the stamp does not help: `~/.claude/helpers/graft-hooks.cjs` and `~/.cursor/rules/graft.mdc` keep `~` looking wired, and a missing stamp replays with every flag on.

## Procedure

1. Keep `hooks/graft-guard.py` registered on `UserPromptSubmit`: `~/.claude/settings.json` (timeout 10) and `~/.codex/hooks.json` (last group, so existing Codex trust hashes keep their index). Codex runs it only after you trust it.
2. Each prompt, the guard pins the home stamp to the installed graft version with `mcp: false` and `global: false`, so an upgrade replays nothing. It also removes `mcpServers.graft` from the JSON configs and restores the graft-rewritten files.
3. Keep `disabledMcpjsonServers: ["graft"]` and `permissions.deny: ["mcp__graft"]` in Claude settings. Claude's replay writes `~/.mcp.json` regardless of the flags; these keys keep it inert until the guard drops it.
4. Verify: `cat ~/graft/.cache/wiring-stamp.json` shows the installed version and `"mcp": false`; `claude mcp get graft` reports no server.

## Pitfalls

- Never run `graft init`. It is the only command that writes MCP or hook wiring, and it starts the replay loop for that directory. `graft build`, `map`, `ask`, `grep` and `upgrade` do not wire.
- Cursor cannot trigger the replay: its hooks use only `cursor-post-tool`, `cursor-mcp` and `cursor-session-end`, and without a graft MCP entry the server never boots.
- An upgrade made outside any session can still replay once at the next `~` session start. With the stamp pinned, that writes only `~/.mcp.json`.
- devkit installs only the graft CLI and wires nothing, so a fresh kit install has no loop. The guard is not exported (`export-allowlist.json` `hooks.excluded`).
- The guard reads the version from `~/.claude/helpers/graft-hooks.cjs`, not `$AGENTS_HOME`: inside a devkit profile `AGENTS_HOME` points at the profile copy.
