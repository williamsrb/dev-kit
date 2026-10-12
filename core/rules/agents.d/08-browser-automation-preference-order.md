Playwright is the one browser. Do not call vendor-native browsers (`cursor-ide-browser`, `Claude_Browser`, `claude-in-chrome`, Codex in-app / bundled browser, `browser-control`) unless the operator names one. A built-in with no disable toggle stays listed; still do not start there. User-named tools always win, and this applies to agents, subagents, and multitask briefs.

**Evidence (hard):** for plan-task-evidence and run-plan on an evidence plan, the browser is the **spawned** headless instance for that task id (`mcp__playwright-<TASK-ID>__*` / `user-playwright-<TASK-ID>`), not the CLI order below.

Ordinary work: Playwright CLI (shared `playwright-cli` skill, headless) first; Playwright MCP only when CLI is unavailable or a long-running introspective session fits better. With the CLI, prefer named sessions, snapshot or find before interaction, state-save/state-load for reusable auth, extension attach only when an existing Chrome session is required, and headed mode for human takeover or debugging.

Do not open a vendor browser first when the user says they are already logged in through another named browser surface. Report which browser tool was used and why, including any fallback reason.

### Playwright MCP — parked, one HTTP instance per task

There is no resident `mcp__playwright__*`: parallel jobs on one stdio server collide on the browser and `--output-dir`. Evidence: `plan-task-evidence` spawns `playwright-<TASK-ID>`; `run-plan` in a **fresh** session captures on it and stops it. Reboot, crash, or ad-hoc MCP: skill `spawn-playwright-mcp` (`list` / `revive` / `spawn --enable`; `--headed` / `--extension` are spawn flags). Full procedure: `How-to-enable-playwright-mcp.md`.

```bash
python3 ~/.agents/mcp/playwright.py spawn <TASK-ID> --enable --storage-state <path-from-find-auth-storage>
```

Storage state: pick it with `find-auth-storage.py --host …` (filename is never a lock) and prefer `--storage-state` at spawn. Skip codegen when a host-matched state still authenticates; new logins use `npx playwright codegen --save-storage=…`. A saved state that lands on a login page is failed evidence: redo login. Keep live state files under `~/.agents/.auth` with mode 700. Storage state omits sessionStorage; an app keeping its token there needs init-script seeding or a headed spawn.
