---
name: spawn-playwright-mcp
description: "Spawn, revive, list, or stop on-demand Playwright MCP HTTP instances. Use after a reboot, when playwright MCP is missing/disconnected, or when you need a browser MCP outside plan-task-evidence. Not the Playwright CLI. | recommendedRole: follow | aliases: playwright-mcp, revive-playwright-mcp, enable-playwright-mcp."
metadata:
  recommendedRole: follow
  aliases: playwright-mcp, revive-playwright-mcp, enable-playwright-mcp
  cliDependencies:
    required: [python3]
    optional: [agentctl, npx]
---

## Local deterministic first

Run `python3 ~/.agents/mcp/playwright.py list` first. Then spawn or revive. Do not invent npx argv; the launcher writes the config.

# Playwright MCP (on-demand HTTP)

Playwright MCP is parked. There is no resident stdio `playwright`. Each instance is an HTTP process with its own `--output-dir`. Evidence plans still spawn from `plan-task-evidence`; use **this** skill for everything else (reboot, ad-hoc capture, a dead `playwright-<id>`).

Details: `~/.agents/kb/implementation/How-to-enable-playwright-mcp.md`.

## When to use

- Playwright MCP tools are missing or in error after a reboot or a crash.
- The operator wants a browser MCP and this is not an evidence-plan session.
- Revive leftover ids (`JOT-101`, `default`, …) whose pid is dead but `instance.json` remains.

## When not to use

- Ordinary non-MCP browser work → `playwright-cli`.
- Writing or executing an evidence plan → `plan-task-evidence` / `run-plan` (they already spawn/stop).
- Vendor-native browsers (`cursor-ide-browser`, `Claude_Browser`, Codex in-app) unless the operator named one.

## Procedure

1. List:

   ```bash
   python3 ~/.agents/mcp/playwright.py list
   # or: agentctl playwright list
   ```

2. Start what is needed (always `--enable` so vendor MCP files get the URL):

   | Situation | Command |
   |-----------|---------|
   | Reboot, registry has dead ids | `python3 ~/.agents/mcp/playwright.py revive` |
   | Reboot, registry empty (or all slots gone) | `python3 ~/.agents/mcp/playwright.py revive --default` (id `default`; ignored when dead ids exist) |
   | Named task / issue | `python3 ~/.agents/mcp/playwright.py spawn <ID> --enable --storage-state ~/.agents/.auth/<env>.json` |
   | Several parallel ids | `python3 ~/.agents/mcp/playwright.py spawn ID1 ID2 --enable` |

3. **Stop this chat.** MCP names attach at session start. A spawn in this transcript does not give this chat tools, even if the namespace appears in error.

4. In the **new** session, use only `playwright-<ID>` (`user-playwright-default` / `mcp__playwright-JOT-101__*`). Absolute screenshot paths under `~/.agents/.playwright-mcp/<ID>/`.

5. When finished:

   ```bash
   python3 ~/.agents/mcp/playwright.py stop <ID>
   python3 ~/.agents/mcp/playwright.py stop --all
   ```

## Pitfalls

- `revive` re-enables vendor URLs because ports usually change after a reboot. It reuses `storage_state` from `instance.json` when that file still exists.
- Spawn registers `http://localhost:<port>/mcp`, not `127.0.0.1`. A numeric-loopback URL 403s (`Needs authentication` in Claude). `spawn`/`revive` recycle any live instance still on `127.0.0.1`.
- `--storage-state` is copied into the instance output dir (mode 600). Prefer that over `browser_set_storage_state` from `~/.agents/.auth/` (allowed-roots).
- Do not fall back to a vendor-native browser if spawn succeeded but this chat cannot see the tools — open a new chat.
- Token cost is ~80 tool names per live instance. Do not revive five ids for a session that needs one.
