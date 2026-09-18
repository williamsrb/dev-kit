---
name: run-plan
description: "Execute an existing plan file (implementation, evidence, or validation). For several plans at once, use multitask-same-repo. | recommendedRole: implement | aliases: execute-plan, follow-plan, run-test-plan, run-implementation-plan, run-validation-plan."
disable-model-invocation: true
metadata:
  recommendedRole: implement
  aliases: execute-plan, follow-plan, run-test-plan, run-implementation-plan, run-validation-plan
  cliDependencies:
    required: [agentctl, git, rg]
    optional: [ollama, tesseract, identify]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Validate the plan mechanically with `agentctl plan resolve` then `agentctl plan validate` before execution. For evidence images create a sidecar with `agentctl evidence manifest`, then run `agentctl evidence inspect` before visual inspection.

# Run Plan

Execute a plan file. Treat KB guidelines as **hints** (not a substitute for the plan). After the run, persist what you learned so future runs are faster.

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md`. **Implementation run:** `agentctl plan resolve <TASK-ID>`, then read `entry` (`plan.md`) plus Constraints/Non-Goals/Implicit companions via `agentctl markdown slice`. Do not load `validation.md` unless this run is validation. `DECISIONS.md` / worktree `CLAUDE.md` if present. Do **not** read the full PRD unless the plan defers to a PRD section; do **not** read the evidence plan. **Evidence run:** `agentctl plan resolve <TASK-ID> --kind evidence` and read that entry only. Do **not** read PRD or impl plan unless a step explicitly cites a path.

## Multiple plans → multitask-same-repo

**Before** the single-plan workflow: if the user wants **two or more** plans run in the same request (batch, parallel, multitask, several task ids / plan paths, “run these together”), **stop this skill** and **read and follow** `multitask-same-repo` instead (`called_from: run-plan`).

Triggers (any one is enough):

- Two or more distinct plan paths, or two or more task ids each implying a plan
- Wording like batch / parallel / multitask / “all of these” / “these N plans”
- Same-repo multi-branch / multi-worktree implementation of several plans

Do **not** loop this skill once per plan in one session when the above applies — that reintroduces the fat-context failure mode. Hand off to `multitask-same-repo` for phase split, worktrees, and parallel fan-out; only use this skill for a **single** plan (or for one plan inside a fresh per-branch session that `multitask-same-repo` already scoped).

If it is unclear whether the user means one plan or many, ask once.

## Guideline roots

| Plan kind | Primary guideline folder (must follow / scan) | Typical plan cues |
|-----------|-----------------------------------------------|-------------------|
| **Implementation** | `~/.agents/kb/implementation` | `*.plan.md`, implementation todos, coding/build steps |
| **Testing / evidence** | `~/.agents/kb/testing` | `*evidence*`, test URLs, screenshots, QA evidence steps |
| **Validation / review** | `~/.agents/kb/validation` | validation, review, lint/QA gates, staged-validation |

Subfolders under a root (e.g. `testing/_shared/`, `testing/<project>/`) are part of that root — scan them when relevant.

**Follow primary; write anywhere:** Always **read/follow** the primary root for the plan kind. You **may write** learnings into **any** of the three roots when the knowledge belongs there (e.g. a testing run discovers an implementation tip → write under `implementation/`).

## Inputs

| Input | Required | Notes |
|-------|----------|--------|
| Plan path **or** `<TASK-ID>` | yes (exactly one plan) | Prefer convention paths under `~/.agents/plans`. User may pass only a Jira key, kebab slug, or “run implementation\|evidence for KEY” |
| Multiple plans | — | If two+ plans/keys: do not treat as this skill’s input set — route to `multitask-same-repo` |

### Resolve the single plan file

1. If the user gave an explicit path that exists, use it (legacy names only when explicitly pointed).
2. Else resolve `<TASK-ID>` via `How-to-resolve-task-context.md`, then `agentctl plan resolve <TASK-ID>` (add `--kind evidence` when wording contains `evidence` / `test`). Kind is `payload.kind`, not the filename. Unmigrated `{TASK-ID}.md` / `{TASK-ID}-evidence-plan.md` still resolve.
3. If that file is missing, ask once for the key or path — do **not** solicit PRD path or both plan types “just in case”.

Before code edits: when `mode` is `jira`, assert `git branch --show-current` equals `<TASK-ID>` (or worktree folder matches) or STOP. When `mode` is `local`, do not require the branch name.

## Auxiliary skills (optional, on demand)

Not required for every run. When an execution step needs a specialized capability you cannot perform with already-installed skills / MCP / normal tools, and a session-only script is not worth it:

1. Prefer an already-installed skill if one covers the need (including skills the plan already names).
2. Otherwise follow the `find-skills` skill as a nested prerequisite (`called_from: run-plan`): search, verify quality, install if appropriate, then **read and follow** the new skill for the blocked action.
3. Resume this skill’s workflow (and KB write-back) after the gap is closed.

Example: the plan requires reading a Figma file and no reader is installed → `find-skills` → install/use it → continue the remaining todos.

Multi-plan orchestration is **not** optional auxiliary work — it is the gate at the top of this skill (`multitask-same-repo`).

## Workflow

```
- [ ] 0. Multi-plan gate → else continue
- [ ] 1. Load plan
- [ ] 2. Classify plan kind → primary guideline root
- [ ] 3. Scan primary guidelines (mandatory)
- [ ] 4. Execute plan steps
- [ ] 5. Write-back learnings (mandatory when new know-how was gained)
- [ ] 6. Report
```

### 0. Multi-plan gate

If multiple plans/keys are in scope (see **Multiple plans → multitask-same-repo**): hand off now. Do not load all plans into this session.

### 1. Load plan

Read the **one** allowlisted plan `entry` from `agentctl plan resolve`. For a folder, load `plan.md` (implementation) or `evidence.md` (evidence), plus companions named in `sections` only as needed (`agentctl markdown slice`). Note goals, acceptance criteria, todos/steps, blockers, and any explicit KB references already listed. Do **not** load PRD / the other plan kind / sibling tasks unless the plan body explicitly requires a cited path. Do **not** load `validation.md` during an implementation run.

### 2. Classify plan kind

Pick **one primary** kind from `agentctl plan resolve` (`payload.kind`). Filename is not the source of truth.

1. `kind: evidence` or evidence companions / testing base URL / screenshot steps → **Testing**
2. Body centers on validation/review/lint/QA gate (not full evidence capture) → **Validation**
3. `kind: implementation` or coding todos → **Implementation**

If ambiguous, ask once; default to **Implementation**.

State in the run: `Plan kind: …` and `Primary KB: ~/.agents/kb/<root>`.

### 3. Scan primary guidelines (mandatory)

Before executing:

1. Open `~/.agents/kb/<root>/llm-index.md` (chooser: folder rows + any root How-tos).
2. If a folder/topic row matches the project or topic (for example `<project>/`, `_shared/` for Content Studio), open that folder’s `llm-index.md`. Do not open sibling project indexes.
3. Open only How-tos whose topic/keywords match the plan’s work. Do not list or load the whole tree.
4. **Reuse** stable procedures/selectors/commands from those guides — do not rediscover blindly.
5. Note which files were used and any **gaps** to fill in step 5.

Project slug is usually the Jira project key lowercased (`GK` → `gk`) when a project subfolder exists.

### 4. Execute plan steps

- Follow the plan’s ordered steps/todos. Do not ask to switch modes.
- Honor plan warnings (auth, reachability, cross-scope frontend↔backend).
- Honor `implicit.md` / `## Implicit requirements`: implement ticked items (Jira checkbox or the user said "include X") and DOs from `How-to-handle-implicit-requirements.md`. Unticked extras are out of scope. Do not implement them to "complete" the ticket.
- If a specialized skill already covers a step (e.g. `validate-impl` for delivery QA), **follow that skill** for those steps instead of reinventing them — still apply this skill’s KB scan + write-back around the whole run.
- **Testing / evidence plans:** follow the plan file’s own **Execution** section (E1–E3). Do **not** re-run `plan-task-evidence` for capture — that skill only writes the plan and **spawns** `playwright-<TASK-ID>`. This `run-plan` session must already see `user-playwright-<TASK-ID>` / `mcp__playwright-<TASK-ID>__*`. If those tools are missing: follow `spawn-playwright-mcp` (`python3 ~/.agents/mcp/playwright.py list`). Process dead → spawn `--enable` (or `revive` after a reboot), then **stop and ask for a new chat** (this session cannot attach). Process alive but no tools → this chat started before enable; new chat. Do not fall back to a vendor-native browser. Before any live/integration step is marked pass, apply the **product concept** gate (`How-to-gate-evidence-on-the-product-concept.md` + plan-task-evidence override 13): expected paint must be in the page; if not, diagnose console/CSP/network/fixture IDs, report to the operator, do not post. If the plan’s **Auth required** is yes, Execution step 1 confirms storage state still authenticates (`npx playwright codegen --save-storage=…` only when no host-matched file exists). A step landing on the login page = expired state = **failed step**, not evidence. After the run (pass or fail), `python3 ~/.agents/mcp/playwright.py stop <TASK-ID>`. Screenshots destined for Jira must pass consistency validation (correct element, zoom, example page) before upload — see `plan-task-evidence` reference / always-apply rule `jira-screenshot-consistency`; storage-only shots skip that gate. **Jira comment post:** skip when `mode` is `local`. When `mode` is `jira`, only if every AC/step passed. Any failure / blocked / inconclusive: **do not post** and **do not ask** whether to post a partial/fail comment — report results in chat (pass/fail list, why, local artifact paths). This overrides always-apply `evidence-post-on-failure-ask` for evidence-plan runs. All-pass may post without asking. Local capture, flatten, and attachment upload may still happen.
- **Validation plans**: prefer `validate-impl` for delivery QA/review; use staged-validation skills for syntax+commit gates.
- On blockers: if the blocker is a missing specialized capability, try **Auxiliary skills** (`find-skills`) once before stopping. Otherwise stop, report, do not loop. Capture any partial learnings in step 5 if useful.

### 5. Write-back learnings

Run after execution (or after a useful partial run) whenever you gained reusable **how-to** knowledge.

**Store**

| Store in KB | Do **not** store |
|-------------|------------------|
| Repeatable procedure / checklist | Full screenshot sets, raw Jira comment dumps |
| Stable selectors, paths, commands, queries | Large datasets / every run’s IDs |
| Minimal sample data (one example) | Task-only prose already in the plan |
| Pitfalls, auth tips, “needs referer” notes | Secrets / credentials |

**Where to write**

- Prefer the **primary** root for learnings about that plan kind.
- Also write to **other** roots when the learning clearly belongs there (implementation tip found during testing → `implementation/`; validation check found during implement → `validation/`).
- Use `_shared/` for cross-project Enonic/CMS patterns; `<project>/` for app-specific flows when that layout exists. If the root is flat/empty, write `How-to-*.md` at the root or create `_shared/` / `<project>/` as needed.

**File rules**

- Name: `How-to-<verb>-<object>.md`
- Merge into an existing guide when the topic fits; split when mixing unrelated concerns.
- Format: same How-To shape as testing KB (title, Scope, Prerequisites, Procedure, Pitfalls, optional Sample data). For testing-shaped content, you may mirror [plan-task-evidence kb-format](../plan-task-evidence/kb-format.md).

Skip write-back only when every step was already fully covered by existing guides with no corrections.

### 6. Report

Return:

- Plan path + plan kind + primary KB root
- Outcome per major step (done / blocked / skipped)
- KB files **read**
- KB files **created/updated** (path + one-line why), including cross-root writes
- Manual follow-ups

## Examples

**Implementation plan:** user says `run PROJ-341` or `run hubspot-form-macro` or path `~/.agents/plans/<TASK-ID>.md` / folder `~/.agents/plans/<TASK-ID>/`  
→ `agentctl plan resolve <TASK-ID>`; read `entry` only; scan `~/.agents/kb/implementation`; execute coding todos. Local slugs skip the branch-equals-key assert.

**Evidence plan:** user says `run evidence PROJ-341` or `run evidence hubspot-form-macro` or a path that `plan resolve --kind evidence` returns  
→ read evidence plan only; scan `~/.agents/kb/testing`; follow **Execution** (capture / Jira comment when `mode` is `jira` / chat report when `local` / KB write-back).

**Validation-oriented plan:** steps that are review/lint/gate focused  
→ scan `~/.agents/kb/validation`; record reusable checklists there.

**Multiple plans at once:** “run PROJ-339, PROJ-341, and PROJ-343” or two+ plan paths  
→ do **not** execute here; read and follow `multitask-same-repo`.
