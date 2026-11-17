# Development process — steps for teammates

Open the HTML files in a browser. Use **Present** for a walkthrough. The red/cyan split is the point: most decisions never reach a person.

| Chart | File |
|---|---|
| Decision classifier (the pitch) | [decision-classifier.html](decision-classifier.html) |
| Single-task pipeline | [single-task.html](single-task.html) |
| Multitask same-repo | [multitask.html](multitask.html) |

## What is auto-solved vs what is asked

The agent does not sit on every fork. It classifies each gap, then either applies a stored rule or stops.

### Auto-solved (do not interrupt the developer)

- Explicit acceptance criteria, later comments that clearly win, and user/chat exclusions
- **DO:** register the part/layout/page, processor, i18n, typed props, reuse the prototype/sister pattern, follow a recorded How-to, match surrounding file style
- **DON'T:** invent copy/locale/URL/env/component, drive-by refactors, deslop (narrating comments, speculative try/catch, `any` casts), Figma deltas on an excluded element
- Platform and stack choices from offline docs (`~/.agents/kb/offline-reference/…`), project How-tos (`~/.agents/kb/implementation/`, `testing/`, `validation/`), and harness instructions (`BASE.md`, `AGENTS.md`, skills)
- Mechanical gates: `agentctl plan validate`, image OCR/whitespace/stamp, delivery deslop

### Human-in-the-loop (jira only, plus operator gates)

1. **Analyst TBD** (`mode: jira`) — missing product decision (copy, locale, URL, env, which component, AC conflicts, unmatched Figma). Each item is 2–3 options with the recommendation first. **Coding hard-stop** until the analyst answers or the operator says implement with those assumptions.
2. **Techlead implicit ticks** (`mode: jira`) — engineering extras the ticket did not state (sister-Figma hover, extra CMS field, extra chrome). Posted as Jira checkboxes. **Not a coding hard-stop.** Silence is not approval; unticked stays out of scope.
3. **Operator Gate** — commit, push, amend, force-push, contract/schema/auth changes, high-risk O1 vs O2. Only on an explicit order.
4. **Evidence post** — Jira evidence comment only if every step passed. Failures stay in chat; the agent does not ask to post a partial.

**Local / non-jira:** there is no analyst and no techlead. The planner is the product owner. Auto-select the recommended TBD path and auto-tick implicit extras that belong. Do not ask. Do not block plan execution. Operator Gate and evidence-post rules still apply.

The next ticket asks less because every run writes reusable `How-to-*.md` back into the KB.

---

## Workflow 1 — Single-task

Use this for one Jira key or one local slug.

### Intake

1. Resolve `TASK-ID` from the message, branch, or folder (`jira` or `local` mode).
2. **Jira:** `download-jira-task` writes `~/.agents/prds/<KEY>.md` if missing. **Local:** `handoff` PRD to the same path. Do not re-fetch an existing PRD.

### Plan (auto knowledge in)

1. `plan-implementation` reads the PRD in sections (description + AC; comments only if AC is thin).
2. Load the knowledge pack: offline XP/React4XP docs via `llm-index.md`, matching project How-tos, `BASE.md` / `AGENTS.md` / skills, prototype component if it exists.
3. Classify the task type (new component, existing change, API, perf/security) and draft the plan folder at `~/.agents/plans/<TASK-ID>/`.
4. Harvest **TBD** and **implicit** into first-class sections. Do not encode extras as `_(inferred)_` ACs. **jira:** do not invent product decisions. **local:** auto-select the recommended TBD path and auto-tick implicit extras that belong.

### Classify (the gate)

1. `validate-plan` rewrites the plan on disk. Verdict: GO / GO-WITH-FIXES / NO-GO.
2. **HITL — Analyst (`jira`):** if TBD is not `none`, copy the options to the analyst. Do not start `run-plan` until answered or the operator accepts the listed assumptions. **local:** auto-select; TBD is `none`; plan is execution-ready.
3. **HITL — Techlead (`jira`):** if implicit is not `none` and mode is `jira`, post the checkbox comment. Coding the explicit AC does not wait for ticks. **local:** auto-tick extras that belong; report `[x]`/`[ ]` in chat.

### Build + prove (auto unless gated)

 1. `run-plan` (implementation): follow the plan, scan `~/.agents/kb/implementation`, implement DOs + ticked extras only. Jira mode: branch must equal `TASK-ID`.
 2. `validate-impl`: fit, exclusions, deslop, security. Then `lint-and-draft-commit-message` for syntax + commit message. **HITL — Operator:** no commit/push unless asked.
 3. `plan-task-evidence` writes `evidence.md` and spawns Playwright for that task id. Fresh `run-plan` captures. Local image gates (whitespace, OCR, stamp) are auto. **HITL:** post to Jira only on all-pass; otherwise report in chat.
 4. Write new How-tos back to the KB. That is the learning loop.

Local mode skips Jira download, branch-equals-key, analyst TBD, the implicit Jira comment, and the evidence Jira post. Capture still runs. The planner auto-selects recommended TBD and auto-ticks implicit extras; that does not block `run-plan`.

---

## Workflow 2 — Multitask same-repo

Use this when two or more independent tasks share one git repo (batch / parallel / “implement these together”). Not for a single key.

Context is **not** shared across parent, subagents, and siblings. Share via disk: plans, PRDs, one `DECISIONS.md`.

### Setup + plan

1. `set-up-worktree` (or `add_worktrees.py`): one git worktree + branch per key. No `cp -a` of `node_modules`.
2. Fresh session **per key:** `plan-implementation` from that key’s PRD. Same classifier as single-task (TBD / implicit / DO / DON'T). Stop after the last plan.

### Validate + GO

1. Fresh session: `validate-plan` once per key against one sample worktree + sister patterns.
2. Write `<multitask-root>/DECISIONS.md`: processor shape, lib paths, shared-port plan, cross-key answers.
3. **HITL (`jira`):** analyst TBD (coding stop), techlead ticks (not a coding stop), operator answers in `DECISIONS.md` once, then **GO on a new session**. `/model` is not a phase boundary. **local:** auto-select TBD and auto-tick implicit in each plan; shared cross-key answers still go in `DECISIONS.md`.

### Implement + QA

1. Fresh session if helpers are shared: port once, cherry-pick to each branch. Implementers must not re-port the same tree.
2. Fresh session: thin orchestrator. One implementer per worktree. Brief is paths + `DECISIONS.md`, not pasted PRDs. Assert `git branch --show-current` equals the key.
3. Fresh QA session(s), preferably one branch per session: `validate-impl` / lint. Same Operator Gate and evidence rules as single-task.

---

## Skills in order (cheat sheet)

**Jira single-task:**  
`download-jira-task` → `plan-implementation` → `validate-plan` → `run-plan` → `validate-impl` → `lint-and-draft-commit-message` → `plan-task-evidence` → `validate-plan` (evidence) → `run-plan` (evidence)

**Local single-task:** same, with `handoff` (PRD) instead of `download-jira-task`. Skip analyst TBD and techlead ticks; auto-select instead.

**Multitask:** `multitask-same-repo` owns phase split, worktrees, and fan-out. Do not loop `run-plan` once per key in one session.
