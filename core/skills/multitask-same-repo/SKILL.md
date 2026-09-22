---
name: multitask-same-repo
description: "Run multiple tasks on one git repo in parallel: worktrees, phase-split sessions, one implementer per branch. Jira keys or local slugs. | recommendedRole: task-owner."
disable-model-invocation: true
metadata:
  recommendedRole: task-owner
  cliDependencies:
    required: [python3, git]
    optional: []
---
# Multitask same-repo

Context is **not** shared across parent ↔ subagents ↔ siblings. Parallelism multiplies cost unless you share via **disk artifacts** and **session splits**.

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md` per key (worktree/branch name = key). Orchestrator holds a **key table** + `DECISIONS.md` path — **not** pasted PRD/plan bodies. Each agent reads **only** its allowlisted files.

## When this applies

- Two or more independent tasks on **one** repo (e.g. PROJ-339 / 341 / 343, or several kebab slugs)
- User says multitask, batch, parallel worktrees/branches, or “implement these together”
- Same PRD→plan→impl pipeline repeated per key (Jira download or local handoff)

If only one task: stop; use normal single-task skills.

## Phase map (mandatory)

Roles are the `orchestrate` role slugs (`~/.agents/skills-vendor/ROLES.md`). Resolve each to a model/effort for the harness you are in; do not name vendor models here.

| Phase | Session | Role (default) | Does | Exit artifact | Stop? |
|-------|---------|----------------|------|---------------|-------|
| 0 Setup | Shell / short agent | `deterministic` | `git worktree add` per key | Worktree dirs + branches | Yes if user only asked setup |
| 0b Plan | **Fresh, one per key** | `quality-gate` | `plan-implementation` per key from its PRD; skip keys that already have a plan | Impl plan under `~/.agents/plans/<KEY>/` | **Yes** |
| 1 Validate | **Fresh A** | `quality-gate` | Fix plans vs one sample worktree + sister refs | Corrected plans + `DECISIONS.md` | **Yes — new chat for next phase** |
| 2 Shared port | **Fresh B** (skip if none) | `implement` | Helpers / path rules **once** | One commit SHA (or identical unstaged patch) cherry-picked to each branch | **Yes** |
| 3 Implement | **Fresh C** + parallel agents | `task-owner` orchestrator, `implement` per worktree | Thin orchestrator; one agent per worktree | Unstaged diffs per branch | **Yes** |
| 4 QA / lint | **Fresh D1…Dn** | `implement`, `quality-gate` when release risk is material | One session per branch preferred | Fixes + notes | — |

Never chain 0b→1, 1→3, or 3→4 in the same transcript. Never use `/model` as a phase boundary.

## Phase 0 — worktrees

Preferred layout (siblings under the same parent folder):

```text
<parent>/REPO-NAME
<parent>/REPO-NAME-multitask/<TASK-KEY>   # branch <TASK-KEY>
```

From the **parent** repo (the real clone), **on the development branch you build from** (e.g. `PROJ-295` — never `review`), use `set-up-worktree` so the sibling `REPO-NAME-multitask/` root is derived automatically:

```bash
python3 ~/.agents/skills/set-up-worktree/scripts/set_up_worktree.py <KEY> [<KEY>...]
```

Base = tip of that checkout's **current branch**. Do **not** pass `--base origin/review`. `review` is a testing/deploy line and is hard-rejected by the scripts.

Or, with an explicit multitask root: `python3 ./scripts/add_worktrees.py --repo <parent> --root <multitask-root> <KEY> [<KEY>...]` (same default / same `review` ban).

Rules:

- Prefer worktrees over `cp -a` / full clones (especially anything with `node_modules`)
- Do not copy build caches into each tree; use project Makefile/Docker as usual
- Each worktree checks out a branch named like the task id (Jira key or slug; never `--detach`)
- Parent repo stays the object store; worktrees share `.git`

## Phase 0b — plan (fresh session per key)

Phase 1 validates plans, so it cannot start before they exist. Check first:

```bash
ls -d ~/.agents/plans/<KEY>
```

For every key **without** a plan, follow `../plan-implementation/SKILL.md` (`called_from: multitask-same-repo`) in a **fresh session per key**. Plan authoring pulls the PRD plus repo research; keeping it in the validate transcript defeats the phase split.

- PRDs come from `download-jira-task` when `mode` is `jira`, or from `handoff` / an existing `~/.agents/prds/<KEY>.md` when `mode` is `local`. Do **not** re-download an existing PRD. Do **not** call `download-jira-task` for a local slug.
- A scope limit the user stated (backend-only, frontend-only, one surface) belongs **in the plan**, not only in the Phase 3 spawn brief.
- One key per session: do not author two plans in one transcript.
- **Stop** after the last plan is written.

Keys that already have a plan skip straight to Phase 1.

## Phase 1 — validate (`quality-gate`, fresh session)

Prerequisite: every key has a plan (Phase 0b).

Follow `../validate-plan/SKILL.md` (`called_from: multitask-same-repo`) once per key. Shared `DECISIONS.md` is extra context, not a substitute for per-plan files.

1. Keys only: `agentctl plan resolve <KEY>` and `~/.agents/prds/<KEY>.md` per conventions (do not re-fetch PRDs unless asked; do not paste file bodies into chat)
2. Sectioned PRD reads when needed; plans are the primary contract
3. Verify claims against **one** sample worktree + sister repo patterns (not every worktree in one dump)
4. Write corrections into each plan via `validate-plan` (validation block at top)
5. Write **one** shared decisions file, e.g. `<multitask-root>/DECISIONS.md` or `~/.agents/plans/<KEY>/decisions.md`, containing:
   - Cross-cutting conventions (processor shape, registration style, lib paths)
   - Sister-pattern paths / short excerpts worth reusing
   - Shared-port plan (what to copy once, where it lands)
   - Open questions resolved with the user
6. **Stop and wait** for GO on a **new** session

## Phase 2 — shared port (`implement`, fresh session)

If helpers or path rules are shared:

1. Apply once on one branch (or a short-lived base branch)
2. Cherry-pick / replay onto each task branch
3. Document the SHA (or file list) in `DECISIONS.md`
4. **Stop**

Do **not** tell implementer subagents to “port the same tree identically into each worktree.”

## Phase 3 — implement (`task-owner` orchestrator, fresh session)

Orchestrator prompt should list only: multitask root, table of key → worktree → branch (paths implied by convention), and `DECISIONS.md` path. **No** pasted PRD/plan bodies or validation research dumps.

For each task, spawn **one** `implement` subagent with a **thin** brief:

- Work **only** under that worktree path (`<root>/<KEY>/`)
- `git branch --show-current` must equal `<KEY>` or STOP
- Read: `agentctl plan resolve <KEY>` (validation companion wins over body), `DECISIONS.md`, worktree `CLAUDE.md` if present; PRD **AC sections only** if the plan defers to PRD
- **Do not** re-read sister processors already summarized in `DECISIONS.md`
- **Do not** re-port shared helpers
- **Do not** touch other worktrees
- Backend/frontend scope as the user stated; leave changes **unstaged** (honor user git rules)
- Browser automation (if any): user-named tool wins; otherwise use Playwright CLI for ordinary headless work. Evidence plans use Playwright MCP; use vendor-native browser MCPs for an explicitly requested existing tab/session or when CLI attachment cannot satisfy the task.

Spawn with whatever parallel-subagent primitive the harness exposes, one per worktree, and disclose model/effort per `orchestrate`. Same brief rules everywhere.

When agents return: short per-task summary only. Do not dump full subagent transcripts into follow-up work — open **fresh** sessions for fixes if context is already large.

## Phase 4 — QA / lint

New session(s). Prefer **one branch per session**. Auto-resolve that key with `agentctl plan resolve <KEY>` + worktree; do **not** attach every sibling PRD. Use existing `validate-impl` / lint skills as appropriate.

## Spawn brief template

```text
You implement ONE task in isolation.
Worktree: <abs-path>   Branch must be: <KEY>
Assert: git -C <abs-path> branch --show-current
Resolve paths via How-to-resolve-task-context.md
Read in order: agentctl plan resolve <KEY> (validation companion overrides body), DECISIONS.md, <worktree>/CLAUDE.md; PRD AC only if plan defers
Forbidden: other worktrees; re-porting shared helpers; re-deriving conventions already in DECISIONS.md; reading sibling PRDs/plans; git add/commit/push unless user asks
Scope: <backend-only | …>
Leave edits unstaged. Return: files touched + how to verify.
```

## Disk layout (recommended)

```text
<parent>/REPO-NAME/                     # real clone
<parent>/REPO-NAME-multitask/
  DECISIONS.md                          # shared, phase 1–2
  <KEY>/                                # git worktree → branch <KEY>
```

PRDs/plans stay under `~/.agents/prds` and `~/.agents/plans` (Claude plans dir may symlink — do not duplicate content).

## Failure modes to refuse

| Ask / instinct | Do instead |
|----------------|------------|
| Full copy per task including `.git` + `node_modules` | `git worktree add` / `set-up-worktree` |
| Continue validate chat with “GO implement” | New session; link plans + DECISIONS |
| Three agents each port `lib/modules` | Phase 2 once, then implement |
| QA inside the implement orchestrator after Agents finish | Fresh per-branch sessions |

## Scripts

- `../set-up-worktree` — sibling `REPO-NAME-multitask/<SLUG>` from the start checkout's current branch tip (never `review`)
- [scripts/add_worktrees.py](scripts/add_worktrees.py) — batch with explicit `--repo` / `--root`
