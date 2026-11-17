---
id: how-to-route-skills
when_skills: []
read: section
prose: caveman-lite
---

# Skill routing cheat-sheet

Shared by Cursor, Claude Code, and Codex. Historical filename `How-to-route-cursor-skills.md` is kept so old citations resolve.

## Which skill for which intent

| Intent | Use | Avoid confusing with |
|--------|-----|----------------------|
| Compact chat for a fresh session | `handoff` → **Context Summary** | PRD persist; planning |
| Persist chat as a local spec | `handoff` → **PRD** | Context Summary; `download-jira-task` |
| Offline Jira dump | `download-jira-task` | live MCP-only fetch; local `handoff` PRD |
| Spec / Plan from a PRD (Jira or local) | `plan-implementation` | download-only; handoff-only |
| Other issues touching the same code (tracker epic/links, unreleased branches, released history), or the status of one related issue | `find-related-issues` (aliases: `related-issues`, `find-related-tasks`, `parallel-work-scan`, `sync-parallel-work`) | `download-jira-task` (this task's own issue); `multitask-same-repo` (our own parallel tasks); `graft` (code callers) |
| Can this ticket go to review with no human? (Autonomous / Human-in-the-loop verdict for the pipeline) | `classify-ticket-autonomy` | `plan-implementation` TBD harvest; `validate-plan` |
| Implicit extras vs TBD vs slop | `How-to-handle-implicit-requirements.md` (after `plan-implementation`) | encoding extras as ACs; mixing into TBD |
| Validate/fix an impl or evidence/test plan | `validate-plan` | `validate-impl` (delivery); `run-plan` (execute) |
| Run an existing plan file | `run-plan` | inventing a plan |
| Implement from `.tasks/<KEY>.md` | `task-implementer` (+ `apply-react4xp-practices`) | ad-hoc coding without spec |
| Delivery QA / “is this good enough?” / review artifact | `validate-impl` (aliases: `impl-validate`, `review-task`, `validate-implementation`) | syntax lint+commit; Bugbot built-ins; `ponytail-review` |
| Over-engineering delete-list (report only) | `ponytail-review` | `validate-impl` (deslop + fix); Bugbot |
| Syntax + commit message (python, PHP, Enonic, or generic) | `lint-and-draft-commit-message` | `validate-impl` |
| Commit message only | `draft-commit-message` | full validation skills |
| Evidence / screenshots / optional tracker comment | `plan-task-evidence` or `run-plan` | unnamed browser loops |
| Validate captured evidence (local folder, and the Jira comment if posted) | `validate-evidence` (aliases: `evidence-validate`, `review-evidence`, `qa-evidence`) | `validate-plan` (plan document); `run-plan` (capture, retake, post) |
| Validate an imagine context lake against its original concept (fix deviations, contradictions, gaps) | `validate-imagine` (aliases: `imagine-validate`, `validate-lake`, `review-lake`) | `validate-plan`; `validate-impl`; `imagine-design` (asset redo) |
| Playwright MCP after reboot / ad-hoc (not an evidence plan) | `spawn-playwright-mcp` | `plan-task-evidence` (plans then spawns); `playwright-cli` (no MCP) |
| Analyst-facing copy (evidence body, TBD questions; Jira/Slack/paste) | `write-analyst-message` | caveman-lite chat; engineer jargon in the analyst body |
| XP server.log / Gradle fail | `debug-xp-app` | `lint-and-draft-commit-message` |
| Sandbox / deploy CLI | `enonic-cli` | raw `enonic` from memory |
| XP7 → XP8 upgrade | `upgrade-xp-app` | minor 7.x bumps |

## Pipeline (manually-invoked happy path)

```text
Jira:  download-jira-task → find-related-issues (plan) → plan-implementation (posts implicit tick list) → validate-plan (impl)
         → find-related-issues (implement) → run-plan (impl) → validate-impl → lint-and-draft-commit-message
         → plan-task-evidence → validate-plan (evidence) → run-plan (evidence) → validate-evidence

Local: handoff (PRD) → find-related-issues (plan) → plan-implementation (auto-select TBD + auto-tick implicit) → validate-plan (impl)
         → find-related-issues (implement) → run-plan (impl) → validate-impl → lint-and-draft-commit-message
         → plan-task-evidence → validate-plan (evidence) → run-plan (evidence) → validate-evidence
```

Not an automation instruction. User may pass **only** `<TASK-ID>` (Jira key or kebab slug). Skills **auto-resolve** `~/.agents/prds/<TASK-ID>.md` and `agentctl plan resolve <TASK-ID>` (folder or legacy `.md` / `-evidence-plan.md`) — do **not** solicit redundant full paths. See `How-to-resolve-task-context.md` and `How-to-optimize-agent-token-usage.md`. Local mode skips Jira download, branch-equals-key, analyst TBD, techlead ticks, and Jira evidence posting (capture + chat report still run). The planner is the product owner: auto-select recommended TBD and auto-tick implicit extras; do not ask; do not hard-stop.

## Validation vs review vs syntax

- **validate-plan** — rewrite the resolved plan folder or legacy file; GO / GO-WITH-FIXES / NO-GO; no code, no evidence execute.
- **validate-impl** (alias `impl-validate`) — requirements, quality, security, less-code, AI slop (deslop); may fix delivery; optional `.tasks/<KEY>-review.md`. Standards: `~/.agents/kb/validation/Quality-gate-*.md`.
- **validate-evidence** — report-only check of captured evidence against the evidence plan and ACs: coverage, per-shot gate, product concept, and (jira, when posted) one comment, images resolve and match local, claims match shots. Its only write is marking failed steps `pending` in `evidence.progress.md`. Run it in a fresh session on a different model than the capture.
- **validate-imagine** — checks an `imagine` lake against the original brief and fixes it in place: PASS / PASS WITH FIXES / FAIL, `validation-log.md` and an undo snapshot in the lake. Never generates assets; redo ids go to `imagine-design`.
- **ponytail-review** — over-engineering delete-list on the delivery diff; report only. Does not replace `validate-impl`.
- **lint-and-draft-commit-message** — parse/syntax/lint + commit message draft, then asks to commit (commits only on a yes). Lazy-loads python / PHP / Enonic / generic from the delivery. Shared How: `Quality-gate-delivery-scope.md`.
- **draft-commit-message** — message draft only (no commit ask).
- **Bugbot / security review** — Cursor built-ins; escalate from QA when needed.

## Other shared How pointers

- Jira offline fetch: `How-to-fetch-jira-issue-via-atlassian-mcp.md` (`download-jira-task`)
- Jira/Confluence attachment bytes: `How-to-download-atlassian-attachments.md` (rovo-preview `executeRead` only)
- Enonic CLI catalogs: `implementation/enonic-cli/`
- XP debug logs: `How-to-debug-xp-server-logs.md`
- XP8 upgrade catalogs: `How-to-run-xp8migrator.md` + `xp7-to-xp8-upgrade/`
- Implicit extras (techlead tick list, not TBD): `How-to-handle-implicit-requirements.md`
- XP testing recipes: `testing/_shared/How-to-test-enonic-xp-apps.md`

## Pitfalls

- Saying “validate” without context can hit `validate-plan` (plan file), `validate-impl` (delivery), or `lint-and-draft-commit-message` — pick from the table. “Validate/fix the plan” is always `validate-plan`.
- `run-plan` executes a plan. Plan-document QA is `validate-plan`.
- `review-task` / review mode is the same `validate-impl` skill (chat report vs optional `.tasks/<KEY>-review.md` artifact). No separate Codex reviewer path.
- `ponytail-review` is a report-only delete-list. It does not fix code and does not replace `validate-impl`.
- Re-attaching full PRD + impl plan + evidence plan on every step wastes tokens — follow per-skill allowlists in `How-to-resolve-task-context.md`.
