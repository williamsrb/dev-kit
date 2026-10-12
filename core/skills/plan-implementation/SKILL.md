---
name: plan-implementation
description: "Write or update ~/.agents/plans/<TASK-ID>/ from a PRD (Jira download or local handoff): user stories, requirements, TBDs, technical plan. Legacy ~/.agents/plans/<TASK-ID>.md still resolves. | recommendedRole: plan | aliases: plan-task-spec, plan-spec, task-spec-plan, jira-task-spec."
metadata:
  recommendedRole: plan
  aliases: plan-task-spec, plan-spec, task-spec-plan, jira-task-spec
  cliDependencies:
    required: [agentctl, rg]
    optional: [ollama]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Use `agentctl task resolve`, `agentctl markdown slice`, and `agentctl plan init --kind implementation --output ~/.agents/plans/<TASK-ID>` (folder) for mechanical work. Finish with `agentctl plan validate <dir-or-file> --kind implementation --json`. Resolve later with `agentctl plan resolve <TASK-ID>`.

## Cursor IDE

**Offline task cache:** `~/.agents/prds/<TASK-ID>.md` (Jira: `download-jira-task`. Local: `handoff` PRD format).  
**Plan / spec output:** `<plans-dir>/<TASK-ID>/` (folder; see Plans directory). Legacy `<plans-dir>/<TASK-ID>.md` still resolves.  
**Enonic offline docs (XP7 / XP8 / React4XP v5 / v6 / v7):** see Step 3c — route via `~/.agents/kb/offline-reference/{xp7,xp8,react4xp-5.x,react4xp-6.x,react4xp-stable}/llm-index.md`.

Write the spec with **Write** / **StrReplace**. Use **Shell** for `mkdir -p <plans-dir>` and file checks. Do **not** call SwitchMode / ask to switch to Plan mode.

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md`. Allowlist: sectioned `~/.agents/prds/<TASK-ID>.md` via `agentctl markdown slice` → write `~/.agents/plans/<TASK-ID>/`. Do not read evidence plans or sibling PRDs.

## Auxiliary skills (optional, on demand)

Not required for every run. When a planning step needs a specialized capability you cannot perform with already-installed skills / MCP / normal tools, and a session-only script is not worth it:

1. Prefer an already-installed skill if one covers the need.
2. Otherwise follow the `find-skills` skill as a nested prerequisite (`called_from: plan-implementation`): search, verify quality, install if appropriate, then **read and follow** the new skill for the blocked action.
3. Resume this skill’s workflow after the gap is closed.

Example: the issue references a `.fig` / Figma file and no Figma reader is installed → `find-skills` → install/use a reader → continue the spec.

# Task Spec Generator

Generates (or updates) a structured Markdown folder at `<plans-dir>/<TASK-ID>/` from the offline PRD (legacy single file `<TASK-ID>.md` still resolves).
This file serves as the **canonical input** for `run-plan` (aliases: `run-implementation-plan`, `execute-plan`, …). There is no separate implementer skill — plan, then run the plan.

**TBD is first-class.** Collect unknowns into `## TBD (ask analyst before implement)`. Empty TBD is allowed (`TBD: none`). Decided exclusions belong in Constraints + Non-Goals, not TBD.

- **Both modes: do not ask obvious questions.** When the recommended option passes the high-confidence test (`references/classify-and-scope.md` § 3f: sourced, the alternatives lose on the ticket's own terms, within the Operator Gate, not an owner's call), auto-select it. Record it under **High-confidence decisions** in `tbd.md` and move on without interrupting the session.
- **`mode` is `jira`:** Phrase the remaining TBD with `write-analyst-message`. Do not invent product decisions to fill gaps. A non-empty TBD is a **hard-stop before coding** unless the user explicitly says to implement with the listed assumptions.
- **`mode` is `local`:** There is no analyst. The planner is the product owner and owns the choice. Harvest the same gaps, reason 2–3 options with the recommendation first, then **auto-select the recommended path** when PRD, codebase, sister parts, recorded How-tos, or surrounding style is enough. Encode the choice as AC/FR/Constraint (`_(local PO: …)_`). Record it under **Local PO decisions** in `tbd.md`, then `- TBD: none`. Do not ask. Do not hard-stop. If reasoning is thin, still pick the least-wrong recommended default that unblocks execution. Operator Gate still applies (auth, schema, irreversible writes).

**Implicit requirements are first-class and not TBD.** Harvest extras the ticket did not state. Classify with `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Implicit is not a coding hard-stop.

- **`mode` is `jira`:** After the plan is written, post a techlead checkbox comment when the list is non-empty. Unticked extras stay out of scope.
- **`mode` is `local`:** There is no techlead. The planner is the techlead. Reason which extras belong in this delivery. Auto-tick (`[x]`) those; leave `[ ]` for follow-up. Do not paste a waiting tick list. Do not block execution.

---

## Environment boundary: review, never production (hard rule)

Developer work ends on review (or local XP). It ends long before production. No plan depends on production.

- **No production evidence.** No step reads, checks, captures, writes or publishes on production. A production URL, screenshot or report in the PRD is the reporter's symptom, not evidence. The plan proves the behaviour on review.
- **Production ACs are restated or dropped.** Restate a ticket AC phrased on a production URL (e.g. `https://example.com/...`) as the same behaviour on the review scenario, and move the production wording to Non-Goals. Never write "confirmed by the analyst/editors on production". Never let an AC, step, Validation line or Definition of Done item wait on production.
- **No production TBD.** Who publishes, republishes or verifies on production is not an analyst question for this plan. It is a Non-Goal (editor / release work).
- **Bugs: scenario, reproduce, fix, test after the fix, all on review.** Reuse the review scenario if it exists. Otherwise create it (duplicate or recreate the example content on review). If the only example exists on production, the plan's one production-related action is asking the analyst to copy it into review. Test after the fix re-runs the **same** scenario.
- **No stand-ins.** Do not add review-wide republishing or data clean-up as a proxy for fixing production content.

---

## Plans directory

`<plans-dir>` is `~/.agents/plans`. Do not write to both agent homes. Do not use workspace `.tasks/` for new specs unless the user points at an existing file there.

---

## Step 1 — Extract the work id

Resolve `<TASK-ID>` per `~/.agents/kb/implementation/How-to-resolve-task-context.md` (Jira key/URL or kebab slug → branch → worktree folder → ask once). Note `mode` (`jira` or `local`). Do not ask for full paths to PRD or plans when convention files exist. Do not invent a Jira key.

### Worktree (when the user asks to create one)

Follow `../set-up-worktree/SKILL.md`. Run it from the **primary** checkout on the development branch tip (e.g. `PROJ-295`). **Never** pass `--base origin/review` or start while that checkout is on `review`. Do not set the new branch's upstream to `origin/review`.

---

## Step 2 — Offline copy (required before planning)

**Source of truth for this skill** is the PRD at:

```text
~/.agents/prds/<TASK-ID>.md
```

1. Check whether that file exists (e.g. `ls ~/.agents/prds/<TASK-ID>.md`).
2. **If it exists** — use it. Do **not** re-download or re-handoff unless the user explicitly asks for a newer version.
3. **If it is missing and `mode` is `jira`** — run the `download-jira-task` skill **as a nested prerequisite**:
   - Read and follow `../download-jira-task/SKILL.md` for this issue key.
   - State clearly: `called_from: plan-implementation` (so `download-jira-task` **skips** its cascade prompt into this skill).
   - Wait until `~/.agents/prds/<TASK-ID>.md` exists, then continue.
4. **If it is missing and `mode` is `local`** — run `handoff` in **PRD** format as a nested prerequisite (`called_from: plan-implementation`). Do **not** call `download-jira-task`. Wait until the PRD exists, then continue.
5. **Read the offline file in sections** (token budget). Call `agentctl markdown slice ~/.agents/prds/<TASK-ID>.md --sections … --json`. Do **not** `Read` the whole PRD.
   - Always: title/summary metadata, `## Description`, and any acceptance-criteria headings (`--sections description` plus `acceptance-criteria` when that H2 exists)
   - Read `## Comments` **only if** AC is missing/thin, TBD gaps remain, or nested `validate-plan` needs comments the draft cites (`--sections comments`)
   - Prefer Grep for criteria keywords, conflicts, missing URLs/locales/envs, and Figma/node mentions over dumping the whole comments thread
   - When comments are read: keep comment **ids**; ignore bot/CI noise (see 3a). Harvest conflicts into TBD (see 3f; **local:** auto-select after harvest)

Do **not** call Atlassian MCP for issue/comment fetch in this skill when the offline file is available (or was just created by a nested download). Live Jira fetch belongs in `download-jira-task` only. Do **not** read `*-evidence-plan.md` or sibling-task PRDs while drafting.

---

## Phase router

Load only the phase being executed:

1. Read [classify-and-scope.md](references/classify-and-scope.md) after the PRD exists. It covers comment filtering, task classification, docs/prototype checks, TBD harvesting, implicit-requirement harvesting, and existing-plan handling.
2. Read [write-and-validate.md](references/write-and-validate.md) only when generating or revising the plan. It contains the complete template, quality gates, handoff rules, the techlead implicit-requirements post (`jira`), and local PO auto-select.
3. **Validate/fix an existing plan** — follow `../validate-plan/SKILL.md` (`called_from: plan-implementation`). Do not duplicate that workflow here.

Do not load both write references in advance. Use the local commands above for issue resolution, section selection, plan scaffolding, and final structure validation.
