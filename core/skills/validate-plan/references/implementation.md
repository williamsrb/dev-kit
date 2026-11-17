# Implementation plan checks

Load only for `--kind implementation` targets (`agentctl plan resolve <TASK-ID>` → folder `plan.md` / companions, or a user-named spec).

Canonical template: `../../plan-implementation/references/write-and-validate.md`. Do not re-draft a missing plan here.

## Must-have headings

Keep skill wording (do not strip parentheticals to please agentctl):

- `## Overview`
- `## User Stories` with numbered AC checkboxes
- `## Functional Requirements` (`FR-n`)
- `## Non-Goals` (at least one bullet)
- `## Constraints (user exclusions)` — required when the user excluded anything; keep the heading even if `- none`
- `## TBD (ask analyst before implement)` — **jira:** checklist **or** `- TBD: none`. **local:** `- TBD: none` plus **Local PO decisions** after auto-select. Never omit.
- `## Implicit requirements (techlead tick)` — checkboxes **or** `- Implicit: none`. Never omit. Classify with `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Not TBD. Not ACs.
- `## Already delivered (do not re-do)` — the one-line first-increment note, or ticked ids each with its SHA plus **Open in this increment**. Required by `agentctl plan validate`; add with `agentctl plan migrate <plan> --kind implementation --apply` when it is the only missing section
- `## Implementation Plan` (problem, approach, steps with `S<n>` ids, Definition of Done)
- `## Validation` — **add if missing**: build gates, manual render/test matrix, what evidence/posting is **not** this plan

English only in the plan file.

## Exclusion gate

Apply `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md`.

1. Collect chat/user exclusions in this conversation + plan Constraints / Non-Goals. Chat wins.
2. **NO-GO** (or **GO-WITH-FIXES** that *narrows*) if any AC/FR requires a change to excluded element E beyond allowed delta C — including inherited parent flex/grid alignment.
3. When fixing: add/update Constraints; mirror Non-Goals; strip or rewrite ACs that demanded forbidden position/styling/markup. Mark `_(user said)_` vs `_(inferred from Figma)_`.
4. Decided exclusions stay in Constraints / Non-Goals — **not** TBD.

## Spec coverage (PRD → plan)

Apply `~/.agents/kb/validation/How-to-check-spec-alignment.md`. The plan-side rules:

1. PRD stale (`stale: true` **and** a `checked_through` id: comments arrived after the marker): the plan may encode superseded requirements. Blocker, verdict **NO-GO**; name the unchecked comment ids and the refresh command. Still fix what does not depend on those comments. Do not apply the comments. A legacy PRD (`checked_through: null`) is not stale: judge against the Description plus the comments the plan cites, and say so in the report.
2. Forward: every PRD statement maps to a plan AC, FR, Constraint or Non-Goal, or an authorized deviation covers it. Match by meaning; PRD `FR-001` and plan `FR-1` are separate namespaces.
3. An explicit statement the plan dropped, narrowed or changed with no authorized deviation is a defect. Fix it: add or correct the AC/FR, marked with its PRD source (`_(PRD: RC2)_`, `_(PRD: Description)_`). Cite it on the existing step that already delivers it. Add a step only when the change is evident from files the plan already names; it takes the next free `S<n>`. A statement that needs new technical design is **NO-GO**: hand to `plan-implementation`. Do not invent steps.
4. `Requirement Changes` win: an AC that still encodes text an `RC<n>` superseded is a defect. Rewrite it and cite the RC.
5. Reverse: every plan AC and FR traces to a PRD statement or carries a source mark (`_(from comments)_`, `_(user said)_`, `_(local PO: …)_`, `_(high confidence: …)_`). An unsourced one is an invented requirement: move it to TBD (**jira**), record it as a Local PO decision (**local**), move it to Implicit when it is an engineering extra, or delete it.
6. A plan Non-Goal that contradicts an explicit PRD statement, or a plan AC, FR or step that does what a PRD Non-Goal or Constraint forbids, is `contradicted` unless an operator order, an RC or an analyst answer covers it. A Local PO, High-confidence or Technical decision alone does not: planner decisions fill gaps, they do not override the PRD. **jira:** TBD. **local:** follow the PRD, or report the conflict as a blocker for the operator.
7. A ticked implicit extra must not contradict a Non-Goal or Constraint of the plan or the PRD. Untick it, or report the conflict.

## AC quality

Each AC must be something `validate-impl` and the evidence plan can pass or fail.

- Observable result: Given/When/Then or a measurable check. "Works correctly", "fast", "user-friendly" with no number or visible outcome is a defect.
- One behaviour per AC. Split a bundled AC; keep the PRD wording in each part.
- States behaviour, not implementation ("the list shows at most 6 items", not "add a `limit` param").
- Checkable on review or local (Environment gate).
- Fix wording only from the PRD's own values. A missing value is TBD (**jira**) or a Local PO decision (**local**), never a guessed number.

## Traceability (AC → step → validation)

- Every AC and FR is delivered by at least one `S<n>` step, and proved by at least one Validation line or Definition of Done item. An AC with no step is a plan that cannot ship it.
- Every step serves an AC, an FR, a **DO**, or a ticked implicit extra. An orphan step is scope creep: delete it, or move the extra to Implicit.
- Definition of Done covers the ACs and the ticked implicit extras, and nothing unticked.
- Each Validation line is a command with its expected result, or a concrete observable check. "Verify it works" is not a line. It runs locally or on review, and it does not hand the proof to the evidence plan.
- `### Technical decisions` (`tbd.md`): every step that hits the Operator Gate (auth or permissions, persisted schema or migration, public contract, irreversible data write, new dependency or cost) has a decision line with `Gate: yes`. Missing: record the line only when the plan already states the choice and its source; otherwise report it as a blocker. Either way surface it for the operator to confirm. It is not an analyst TBD.
- A step that writes or deletes shared review data (import, sync) needs a rehearsal before it runs. Name it in the report's Follow-up so `plan-data-rehearsal` runs before `run-plan`. It is not a blocker and not a verdict input: the factory drafts the rehearsal after this step. Do not draft it here.

## Environment gate (review, never production)

Apply `../../plan-implementation/SKILL.md` § Environment boundary. Any AC, FR, step, Validation line, Definition of Done item or TBD that depends on production is a defect. Fix it in place:

- Restate an AC phrased on a production URL as the same behaviour on the review scenario, and move the production wording to Non-Goals. Do not annotate it "confirmed by the analyst/editors on production".
- Delete production TBD (who publishes or verifies there) and list it as a Non-Goal.
- Bugs: the steps must run Scenario (reuse on review, else create) → Reproduce → Fix → Test after fix on the same scenario. Add missing phases, keeping existing S-ids.
- Delete review-wide republishing or data clean-up that stands in for production.

## TBD harvest

- Fold Questions / Open issues into TBD.
- Add gaps that would force a product guess (copy, locale, URL, env, which component, ownership, Figma node).
- **Both modes, first:** apply the high-confidence test (`../../plan-implementation/references/classify-and-scope.md` § 3f). An open TBD whose recommendation passes it is not a question. Move it to **High-confidence decisions** in `tbd.md`, encode it `_(high confidence: <source>)_`, and do not ask it in the report or the session. A recorded High-confidence decision that fails a test goes back to TBD.
- **jira:** do **not** invent answers. Do **not** promote the remaining TBD into ACs/FRs. Phrase leftover TBD with `write-analyst-message` (decision + Blocks + 2–3 options, recommendation first). Non-empty TBD → hard-stop before coding; not a plan NO-GO by itself.
- **local:** auto-select the recommended path when reasoning is enough (PRD, codebase, sister, How-to, surrounding style). Encode as AC/FR/Constraint (`_(local PO: …)_`). Record under **Local PO decisions**. Then `- TBD: none`. Do not ask. Do not hard-stop. If reasoning is thin, pick the least-wrong recommended default that unblocks execution. Do not use `write-analyst-message`. See `~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md` only for the option-shape while reasoning.

## Implicit harvest

- Fold inferred extras out of ACs/FRs into the tick list. Classify with `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`.
- Add gaps that would be silent engineering extras (Figma sibling states, extra CMS fields, sister-part optionals). Do **not** put product gaps here — those stay TBD.
- DOs (stack wiring, recorded How-tos) stay in Implementation Steps, not on the tick list.
- Phrase leftover items as one-line checkboxes. Empty list: `- Implicit: none`.
- **jira:** Implicit is not a coding hard-stop. This skill does not post the techlead comment. Nested `plan-implementation` posts after the rewrite; standalone validate reports the list in chat.
- **local:** auto-tick `[x]` extras that belong; leave `[ ]` for follow-up. Report in chat. Do not post. Do not wait.

## Consistency

Apply `~/.agents/kb/validation/How-to-validate-a-plan-document-for-internal-consistency.md`:

- Re-derive stated counts from source (registration site, not README).
- Enumerated lists match the count that introduces them.
- File trees match phase totals; no task in two phases.
- Status header matches open items below it.
- Every AC is satisfiable (an “close every register item” AC conflicts with out-of-scope items).
- Grep for paths outside the deliverable boundary; for `not yet` / `does not exist` claims, check current source.

Do not fix a stale number by inference. Measure.

## Technical sanity (cheap)

Against the workspace (or one sample worktree in multitask). Details and PASS/FAIL: [realism-and-kb.md](realism-and-kb.md).

- Cited files/dirs exist or are clearly “to be created”.
- Prototype path / props contract, if claimed, is real (`ls` the prototype file; do not take the plan’s word).
- Sister-pattern references are not a different app’s paths copied blindly.
- Shared helpers named as already present are present, or TBD/shared-port is explicit.
- Enonic/React4XP/CMS approach cites offline-reference pages reached via `llm-index.md`.

Do not implement the missing helper here. Record it.

## Fix policy

- Rewrite the plan file; do not leave the verdict only in chat.
- Prefer deleting a wrong AC over adding speculative implementation steps.
- Idempotent: do not duplicate sections or erase a user’s manual Implementation Plan edits unless they contradict exclusions or facts.
- Ids are permanent: `S<n>`, `US-<n>`, `FR-<n>` and AC positions that `Already delivered`, `validation.md`, `progress.md` or the evidence plan cite. Never renumber or reuse one; a new or split item takes the next free number, wherever it sits. Renumbering moves recorded progress and citations onto a different item.
- Change a step's text only for a real defect: any edit flags recorded progress `stale`.
- Never edit `progress.md`. Never tick or untick an `## Already delivered` item; a tick without a cited SHA is a finding to report, not to repair by guessing.
- Do not add Co-authored / AI trailers or execute `run-plan`.
