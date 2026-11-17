Playwright is the one browser. Do not call vendor-native browsers (`cursor-ide-browser`, `Claude_Browser`, `claude-in-chrome`, Codex in-app / bundled browser, `browser-control`) unless the operator names one. A built-in with no disable toggle stays listed; still do not start there. User-named tools always win, and this applies to agents, subagents, and multitask briefs.

**Evidence (hard):** for plan-task-evidence and run-plan on an evidence plan, the browser is the **spawned** headless instance for that task id (`mcp__playwright-<TASK-ID>__*` / `user-playwright-<TASK-ID>`), not the CLI order below.

Ordinary work: Playwright CLI (shared `playwright-cli` skill, headless) first; Playwright MCP only when CLI is unavailable or a long-running introspective session fits better. The `playwright-cli` skill lists the CLI practices (named sessions, snapshot before interaction, state-save/state-load, headed mode for takeover).

Do not open a vendor browser first when the user says they are already logged in through another named browser surface. Report which browser tool was used and why, including any fallback reason.

There is no resident `mcp__playwright__*` (parallel jobs on one server collide). One HTTP instance per task: `plan-task-evidence` spawns it, `run-plan` in a **fresh** session captures and stops it; after a reboot, crash, or for ad-hoc use, follow `spawn-playwright-mcp`. Procedure: `~/.agents/kb/implementation/How-to-enable-playwright-mcp.md`. Auth storage state: pick by host with `~/.agents/skills/plan-task-evidence/scripts/find-auth-storage.py`, keep it under `~/.agents/.auth`; a saved state that lands on a login page is failed evidence (details in the How-to).
