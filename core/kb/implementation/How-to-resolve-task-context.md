---
id: how-to-resolve-task-context
when_skills: [validate-plan, validate-impl, plan-implementation, run-plan, download-jira-task, plan-task-evidence, handoff, multitask-same-repo, lint-and-draft-commit-message, draft-commit-message]
inputs: [user message, git branch, cwd]
outputs: [TASK-ID, mode, allowlist]
stop_if: [jira TASK-ID and branch != TASK-ID before code edits]
read: section
prose: caveman-lite
---

# Resolve task context

`<TASK-ID>` is a Jira key (`PROJ-430`) **or** a kebab slug (`hubspot-form-macro`). `mode` is `jira` or `local`. Never invent a Jira key from a slug.

## Canonical paths

| Artifact | Path |
|----------|------|
| PRD | `~/.agents/prds/<TASK-ID>.md` |
| PRD attachments | `~/.agents/prds/<TASK-ID>/attachments/` |
| Plan (resolved) | `agentctl plan resolve <TASK-ID>` — folder `~/.agents/plans/<TASK-ID>/` first, then legacy `~/.agents/plans/<TASK-ID>.md` |
| Evidence plan | `agentctl plan resolve <TASK-ID> --kind evidence` — `evidence.md` in that folder, then legacy `~/.agents/plans/<TASK-ID>-evidence-plan.md` |
| Git branch | Jira mode: exactly `<TASK-ID>`. Local mode: current branch is enough |
| Multitask worktree | `<multitask-root>/<TASK-ID>/` (folder name = `<TASK-ID>`) |
| Shared decisions | `<multitask-root>/DECISIONS.md` when multitask; folder plans may also have `decisions.md` |

Do not invent alternate plan names (for example `*.plan.md`) for new work. Open a legacy filename only when the user points at it. New plans are folders created by `agentctl plan init --output ~/.agents/plans/<TASK-ID>`.

Local PRDs come from `handoff` (PRD format). Jira PRDs come from `download-jira-task`. Same path contract.

## Procedure

1. If the user supplies an implementation-plan path, use that plan as task context; `<TASK-ID>` is optional.
2. Else resolve `<TASK-ID>` with `agentctl task resolve --cwd <repo> --text <request> --json` (or the same order by hand): Jira key or Jira URL in the message → kebab slug in the message → `git branch --show-current` if it is a key or slug → CWD / workspace folder name if it is a key or slug → ask once. `payload.mode` is `jira` or `local`. Text beats branch, cwd, and filename scans.
3. Never ask for full paths to PRD / impl plan / evidence plan when the convention files exist.
4. Before code edits (implement / QA / lint): when `mode` is `jira`, assert `git branch --show-current` equals `<TASK-ID>` or STOP. When `mode` is `local`, or the user supplied an implementation-plan path and no `<TASK-ID>` resolved, do **not** require the branch name.
5. Multitask: code lives under `<root>/<TASK-ID>/`. Harness markdown stays under `~/.agents/prds` and `~/.agents/plans`.

## Context budget

Pipeline skills follow this list. Do not copy it into SKILL.md. Keep only the skill-specific allowlist line there.

1. Resolve `<TASK-ID>` with this How-to, or use the implementation-plan path supplied by the user.
2. Open only the allowlisted paths for the active skill (table below).
3. Prefer Grep / section reads over whole-file reads.
4. Ignore extra @-attached harness markdown outside the allowlist unless the user explicitly overrides.
5. Never ask the user to paste paths to PRD / impl plan / evidence plan when the convention files exist.
6. Never paste full markdown bodies into the user-visible prompt. Read or Grep the files.

## Per-step read allowlist

| Step | Skill(s) | Must read | Must not read by default |
|------|----------|-----------|--------------------------|
| Persist local PRD | `handoff` (PRD) | This conversation → write `prds/<TASK-ID>.md` | Other tasks' PRDs/plans |
| Download (jira mode) | `download-jira-task` | Jira MCP / `agentctl jira fetch` → write PRD + `prds/<TASK-ID>/attachments/` | Other tasks' PRDs/plans; attachment binaries unless asked; skip this row when `mode` is `local` |
| Draft impl plan | `plan-implementation` | PRD: `## Description` + AC-bearing sections first; `## Comments` only if AC incomplete; classify extras with `How-to-handle-implicit-requirements.md` | Full comments when Description already has AC; evidence plan; sibling PRDs; whole offline-reference catalogs (use llm-index) |
| Validate/fix plan | `validate-plan` (impl) / `multitask-same-repo` Phase 1 | Draft from `agentctl plan resolve <TASK-ID>` + sectioned PRD + user/chat exclusions; apply `How-to-respect-user-scope-exclusions.md` and `How-to-handle-implicit-requirements.md` | Evidence plan; delivery diff; other keys' full plans |
| Run impl | `run-plan` | Resolve then load `entry` (`plan.md`) plus Constraints/Non-Goals/Implicit companions; `DECISIONS.md` if multitask; worktree `CLAUDE.md` if present. Do not load `validation.md` unless validating | Full PRD unless the plan says see PRD §…; evidence plan; other worktrees |
| QA gate | `validate-impl` | Delivery **diff** + resolved implementation plan (AC / GO / **Constraints** / Non-Goals / Implicit) + chat exclusions; apply `How-to-respect-user-scope-exclusions.md` and `How-to-handle-implicit-requirements.md` | Full PRD comments; evidence plan |
| Lint + commit msg | `lint-and-draft-commit-message` / `draft-commit-message` | Delivery diff only; TASK-ID from branch when Jira | `~/.agents/prds/`; `~/.agents/plans/` |
| Draft evidence plan | `plan-task-evidence` | AC from resolved impl plan first; PRD sectioned only for tips/URLs/comment ids when the plan lacks them | Full impl narrative; full PRD comments; siblings; Jira MCP / `download-jira-task` / `getJiraIssue` for `<TASK-ID>` when the PRD exists; implementation worktrees / `<TASK-ID>` branches / local source trees |
| Validate evidence plan | `validate-plan` (evidence) | `agentctl plan resolve <TASK-ID> --kind evidence` + AC source used in the draft | Full impl plan; full PRD; implementation worktrees / local source |
| Run evidence | `run-plan` / `run-test-plan` | Resolved evidence entry only | PRD; impl plan unless a step cites a path |
| Jira comment | Evidence Execution (E2) | Evidence outcomes + `plan-task-evidence/templates.md` | Re-read PRD/impl plan to summarize the whole task. Skip the whole row when `mode` is `local` (chat-report the evidence folder instead) |

## `run-plan` path resolution

If the user gives only `<TASK-ID>` or "run implementation/evidence":

1. `agentctl plan resolve <TASK-ID>` (add `--kind evidence` when the wording contains `evidence` / `test`).
2. Load the returned `entry`. Kind is `payload.kind`, not the filename.
3. Open companion files from `sections` only as needed (`agentctl markdown slice`). Unmigrated `{TASK-ID}.md` / `{TASK-ID}-evidence-plan.md` still resolve.

Stop asking for an absolute plan path when resolve returns `status: ok`.

## Pitfalls

- Do not invent a Jira key from a kebab slug or a similar folder name. `as-1171` is Jira (`AS-1171`). `hubspot-form-macro` is local.
- Do not attach the full PRD + impl plan + evidence plan on every step.
- Evidence planning/execution: do not Grep a task worktree or implementation branch. The review host is the shipped tree.
- Evidence planning: an existing `prds/<TASK-ID>.md` **is** the task copy. Do not `download-jira-task` / `agentctl jira fetch` / `getJiraIssue` that key “to be sure”, and do not JQL-search siblings by default (siblings are must-not-read). Refresh only when the user asks. Worked failure: PROJ-434, 2026-09-15.
- Local mode: do not call `download-jira-task`. Missing PRD → `handoff` (PRD format) or ask once.
- Jira comment / Tempo / analyst-comment sinks run only when `mode` is `jira`. `plan-implementation` posts the implicit-requirements techlead comment in that mode; TBD is copied for the analyst, not auto-posted. **local:** no analyst and no techlead — auto-select recommended TBD and auto-tick implicit extras; do not ask; do not hard-stop.
- **`agentctl plan resolve <TASK-ID>` resolves against the CWD first, so in the multitask root it returns the *worktree*, not the plan.** From `~/Workspace/Projects/acme-group-multitask` (which holds a `<TASK-ID>/` worktree per ticket) `plan resolve PROJ-345` returned `status: ok` with `entry: <root>/PROJ-345/plan.md` and `sections` listing `AGENTS`/`CLAUDE`/`README` — the repo's own files. `plan.md` did not even exist there. Tell: `sections` names repo files instead of `plan`/`requirements`/`implementation`/`validation`/`evidence`/`tbd`/`implicit`. Re-run resolve from a neutral CWD (`cd ${HOME}`) to get `~/.agents/plans/<TASK-ID>/plan.md`. Confirmed 2026-09-03 on PROJ-345.
- `agentctl plan validate <plans>/<TASK-ID>/plan.md` reports `layout: file` and `missing_sections` for every companion (`functional-requirements`, `implementation-plan`, `tbd`, `implicit-requirements`, `validation`) on a **folder-layout** plan. That is the validator scoping to the one file, not a broken plan — validate the folder root, or read the companions and move on.
