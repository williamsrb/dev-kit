Playwright is the one browser. Do not call vendor-native browsers (`cursor-ide-browser`, `Claude_Browser`, `claude-in-chrome`, Codex in-app / bundled browser, `browser-control`) unless the operator names one. If a built-in has no disable toggle, leave it listed and still do not start there.

**Evidence exception (hard):** For plan-task-evidence and run-plan on an evidence plan, the browser MCP is the **spawned** headless Playwright instance for that task id (`mcp__playwright-<TASK-ID>__*` / `user-playwright-<TASK-ID>`). Do not start with a vendor-native browser MCP unless the user names a different tool for that run. Do not follow the ordinary CLI preference below for evidence work.

When automating a browser for ordinary implementation, validation, or other non-evidence work, use this order unless the user names a different tool:

1. Playwright CLI with the shared playwright-cli skill, headless by default.
2. Playwright MCP when CLI is unavailable or when a long-running, richly introspective MCP session is the better fit.

User-named tools always win.

Playwright CLI is the normal path for navigation, interaction, snapshots, assertions, and screenshots. Prefer named sessions, snapshot or find before interaction, state-save/state-load for reusable authentication, and extension attach only when an existing Chrome session is required. Use headed/show mode for human takeover or debugging.

### Playwright MCP — parked, one HTTP instance per task

There is no resident `mcp__playwright__*`. Parallel jobs sharing one stdio server collide on the browser and on `--output-dir`. Evidence: `plan-task-evidence` spawns `playwright-<TASK-ID>`, then `run-plan` in a **fresh** session captures on it and stops the instance. Reboot, crash, or ad-hoc MCP (not an evidence plan): skill `spawn-playwright-mcp` (`list` / `revive` / `spawn --enable`). Full procedure: `How-to-enable-playwright-mcp.md`.

```bash
python3 ~/.agents/mcp/playwright.py spawn <TASK-ID> --enable --storage-state <path-from-find-auth-storage>
```

`--headed` / `--extension` are spawn flags, not catalog servers. Pick `<path-from-find-auth-storage>` with `find-auth-storage.py --host …` (filename is never a lock). New logins: `npx playwright codegen --save-storage=…`. `browser-control` remains parked.

Skip codegen when a host-matched state exists and still authenticates. Prefer `--storage-state` at spawn. If a saved state lands on a login page, treat capture as failed evidence and redo login. Keep live state files under ~/.agents/.auth with mode 700. Storage state does not include sessionStorage; an app that stores its token there needs init-script seeding or a headed spawn.

- Prefer the highest-ranked usable tool (evidence: spawned Playwright MCP for that task id; ordinary work: Playwright CLI).
- Do not open a vendor browser first when the user says they are already logged in through another named browser surface.
- Report which browser tool was used and why, including any fallback reason.
- This preference applies to agents, subagents, and multitask briefs.
