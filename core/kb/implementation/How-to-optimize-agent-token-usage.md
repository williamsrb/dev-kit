---
id: how-to-optimize-agent-token-usage
when_skills: []
read: section
prose: caveman-lite
---

# How to optimize agent token usage

## Adopted

| Layer | What | Where |
|-------|------|--------|
| **RTK** | Compact shell tool output (`ls`, `docker ps`, tests, …) | `~/.local/bin/rtk`; Cursor `preToolUse` → `rtk hook cursor`; Claude `PreToolUse` → `~/.local/bin/rtk hook claude`; Codex `PreToolUse` → `hooks/rtk-codex.py`. Native-command wiring (not wrapper scripts) is what `rtk verify` detects |
| **Caveman-lite rule** | Terse chat; normal prose for Jira/evidence/PRs/commits; same lite register on owned KB How-tos | `~/.agents/rules/token-efficiency-chat.mdc`; `kb/_shared/How-to-author-ai-howtos.md` |
| **KB/skill compaction re-runs** | Loaded-path first; do not re-run owned `main()`; never rewrite skill `name` or templates | `kb/_shared/How-to-compact-kb-skills-and-offline-reference.md` |
| **Round-trips / baseline (2026-08-27)** | Field-list Jira fetch; batched attachment curls; PRD `markdown slice`; Claude Workflows off; plugin Atlassian/Slack removed; Playwright login tiers parked; kb-router slash/notification/`MIN_HITS=3`; shell-batch P7; `agentctl plan resolve` + folder plans | skills, `agentctl`, Claude `settings.json`, four MCP files, `kb-router.py`, constitution trio |
| **Parked Slack + graft MCP (2026-09-09)** | Slack user MCP and Slack marketplace plugins on-demand for `generate-worklogs` only. graft MCP parked; CLI + `graft.mdc` stay. | `~/.agents/.auth/mcp-on-demand/`; `mcp/catalog.json` `parked`; `How-to-enable-playwright-mcp.md` |
| **Playwright MCP on-demand (2026-09-17)** | No resident stdio `playwright`. HTTP instances via `mcp/playwright.py`, one process and output-dir per task id. Skill `spawn-playwright-mcp` for reboot/ad-hoc spawn. | `mcp/playwright.py`; `skills/spawn-playwright-mcp`; `How-to-enable-playwright-mcp.md` |
| **agentctl jira (2026-08-28)** | REST API token at `~/.agents/.auth/jira-api-token.yaml`. `jira fetch` is get+attachments+PRD with no MCP round-trips | `~/.agents/bin/agentctl_jira.py`; `download-jira-task` prefers it |
| **Context packages** | Per-skill read allowlists; auto-resolve `<TASK-ID>` | This folder + pipeline skills' Context budget boxes |
| **BASE P1 ladder (2026-09-13)** | Stdlib / native / installed-dep before custom code; caller-grep on bugfix. Not a second constitution | `BASE.md` + `BASE.mdc` + `AGENTS.md` constitution |
| **ponytail-review** | Explicit over-engineering delete-list. Not always-on | `~/.agents/skills/ponytail-review` |

## Skipped (do not install)

| Tool | Why |
|------|-----|
| Headroom full wrap/proxy | Invasive; can drop grep/log lines needed for XP/Jira; revisit only with proven Cursor proxy + CCR retrieve |
| pxpipe general proxy | Vision/gist compression; unsafe for exact IDs/paths |
| pxpipe on PRDs | PRDs are contract docs (comment ids, AC); silent confabulation risk |
| Stock Caveman full/ultra always-on | Would poison Jira/evidence client prose. Same ban on KB How-tos (fragments make stop-conditions ambiguous). |
| Stock ponytail always-on skill or rule | Ladder already in BASE P1. Stock copy challenges ACs/Figma and fights Jest/JUnit. Use `ponytail-review` when named. |
| Per-skill model routing (O8) | Dropped. Switch model by hand for a known-mechanical session. |
| Moving operational `AGENTS.md` sections (O6) | Left resident. A rule that only fires when a skill loads will not fire without the skill. |

## Expected savings

Meaningful on noisy shell/log turns; small on total monthly bill. Largest levers remain: **fresh sessions per phase**, thin multitask `DECISIONS.md`, and **not** re-attaching full PRD/plan stacks every step (see allowlists).

## RTK recovery

If a filter hid a needed field:

```bash
RTK_DISABLED=1 <original-command>
# or, when supported by the filter:
rtk <command> --no-compact
```

`git push` stays denied for raw and `rtk`-prefixed forms (`hooks/git-push-policy.sh`).

## Verify

1. Shell `ls` / `docker ps` rewrites toward `rtk …` (Cursor/Claude hooks).
2. `git push` and `rtk git push` still denied.
3. Pipeline skill with only `<TASK-ID>` (Jira key or kebab slug) resolves `prds/` + `plans/` without asking for full paths.
4. Chat stays terse; Jira evidence comments stay professional prose (`write-analyst-message`).

## Rollback

Pre-images: `~/.cursor/.token-opt-rollback/<timestamp>/` (+ `CHANGELOG.md`).  
Full backups: `~/backup.cursor.zip`, `~/backup.claude.zip`.
