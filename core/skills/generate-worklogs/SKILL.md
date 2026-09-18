---
name: generate-worklogs
description: "Build copy-paste Jira/Tempo worklogs for a date from Cursor, git, Slack, and Jira evidence. | recommendedRole: follow | aliases: worklogs-for-today, daily-worklogs, jira-worklogs, tempo-worklogs."
disable-model-invocation: true
metadata:
  recommendedRole: follow
  aliases: worklogs-for-today, daily-worklogs, jira-worklogs, tempo-worklogs
  cliDependencies:
    required: [agentctl, python3, git]
    optional: [ollama, jq]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Run `agentctl worklog collect --date YYYY-MM-DD --json` first. Read the cached collector artifact only for unresolved evidence; use Ollama only for bounded, non-authoritative clustering.

# Generate worklogs

This skill defines **what** a complete worklog result must contain. The current
operational **how** lives in `~/.agents/kb/worklog`.

## Before every run

1. Read `~/.agents/kb/worklog/README.md` (sequence, paths, status, learning).
2. Open `~/.agents/kb/worklog/slack.md` when collecting Slack; open `~/.agents/kb/worklog/jira.md` when collecting or posting Jira worklogs. Do not load both "just in case". Slack MCP is parked: enable it first (`How-to-enable-playwright-mcp.md` Slack section), then park it after the run.
3. If the KB conflicts with this skill, this skill wins for output, attribution, safety, and business rules. The KB wins for current tool usage.

Do not copy volatile MCP schemas or procedural walkthroughs back into this skill.

## Goal

Produce one manager-friendly worklog per Jira issue worked on during the target
day. Correlate all available evidence, avoid duplicate logging, distinguish
confirmed work from weak signals, and make every collection gap visible.

Default target date is today in UTC-3. The user may provide a date and total
hours. If hours are omitted, ask or infer a clearly labeled suggestion.

## Required evidence coverage

Collect, when available:

- Cursor prompts and outcomes
- commits and uncommitted project activity
- Slack activity from every discovered Slack workspace
- Jira worklogs and other issue activity
- offline task details from `agentctl markdown slice ~/.agents/prds/<ISSUE-KEY>.md --sections description,comments --json` (do not `Read` the whole PRD)

Every Slack MCP connection represents a separate workspace. A run is incomplete
if a discovered workspace is neither searched nor explicitly reported as failed.

Collection failures must not stop other collectors. Report each failure by source
and state what succeeded.

## Attribution rules

Build `issue key → evidence` using strongest signals first:

1. explicit key in branch or commit
2. explicit key in a prompt, result, Slack message, or Jira URL
3. the user's Jira comment or same-day worklog
4. substantive issue-specific Slack discussion
5. a status transition made by the user
6. assignment plus matching project evidence

Assignment or transition alone is not enough to claim implementation work.
Merge duplicate evidence into one narrative per issue. Never invent work.

Classify unmatched work as follows:

- Agent/Cursor/Claude harness work—skills, rules, agents, commands, hooks, MCPs,
  CLIs, plugins, run post-mortems, and routing—always maps to `LEARN-63`.
- Other study work maps to the best matching `LEARN` issue.
- Internal product/tooling work maps to the best matching `INT` issue.
- Non-technical meetings, planning, or admin default to `INFRA-2`.
- Technical operations, CI, infrastructure, or deployment default to `INFRA-22`.

Mark low-confidence fallback mappings for confirmation.

## Time rules

- Use UTC-3 for all target-day boundaries.
- Subtract time already logged for that date before drafting new entries.
- If requested hours are fully logged, draft nothing unless replacement was asked.
- Split remaining time proportionally to evidence strength.
- Round every draft to a multiple of 15 minutes. 15m is the floor: never
  draft a shorter entry, and merge or drop a stream that cannot justify it.
- Express durations in Jira's form (`15m`, `45m`, `1h 30m`), not decimals.
- When a per-issue split cannot fit the requested total at 15m granularity,
  say so and propose either a larger total or fewer blocks. Do not silently
  inflate the total to satisfy the floor.
- New draft time must equal requested time minus already-logged time.
- When hours were inferred, label both total and split as suggested.

## Worklog writing rules

Use one block per issue. Write outcomes in past tense. Prefer manager-readable
results over low-level implementation detail. Include merge, deployment, review,
or validation only when evidence confirms it happened that day.

```text
ISSUE-KEY | Issue summary | TIME
* Outcome 1
* Outcome 2

Jira: https://example.atlassian.net/browse/ISSUE-KEY
```

## Required response

Always return all sections in this order:

1. **Already logged (Jira)** — issue, duration, comment snippet, and worklog ID
   when available; otherwise state that none were found.
2. **Summary** — issue, draft time, already logged time, confidence, and offline
   task availability.
3. **Evidence by work stream** — evidence grouped by issue or unmatched bucket,
   with each source and Slack workspace identified.
4. **Worklog blocks** — one copy-paste-ready block per issue still needing time.
5. **Warnings** — failures, skipped workspaces, duplicate risk, weak mappings,
   unmatched activity, missing/stale offline tasks, and partial pagination.
6. **Evidence appendix** — counts and success/failure status for every collector,
   including per-workspace Slack counts.

Do not silently omit empty sections.

## Posting

Do not post or update Jira worklogs unless the user explicitly asks.

When posting, preserve the target calendar day in UTC-3. Use the posting method
and timestamp rules from the KB, then verify each written entry resolves to the
target date. Correct any entry that lands on another date.

## Post-run learning loop

After every run, compare observed tool behavior with the KB.

Update `~/.agents/kb/worklog` in the same run when there is **verified, durable
operational learning**, including:

- a new or removed Jira/Slack MCP capability
- changed tool names, parameters, response fields, pagination, or auth behavior
- a newly direct way to retrieve existing worklogs
- a proven collector workaround or obsolete workaround
- a stable source path or query behavior change

Requirements for automatic KB updates:

1. Verify the behavior from a live tool schema or successful/failed call.
2. Update the current procedure; do not merely append a contradictory note.
3. Add a dated entry to the KB changelog with evidence and the replaced behavior.
4. Keep historical facts concise and mark superseded methods as such.
5. Never promote a one-off timeout, permission failure, or guess into guidance.
6. Never change the business/output rules in this skill automatically.
7. Mention the KB update in the response warnings or evidence appendix.

If a discovery would change attribution, time allocation, posting safety, or the
required report, propose a skill change to the user instead of self-modifying it.
