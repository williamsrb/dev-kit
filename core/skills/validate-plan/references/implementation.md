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
- `## Implementation Plan` (problem, approach, steps, Definition of Done)
- `## Validation` — **add if missing**: build gates, manual render/test matrix, what evidence/posting is **not** this plan

English only in the plan file.

## Exclusion gate

Apply `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md`.

1. Collect chat/user exclusions in this conversation + plan Constraints / Non-Goals. Chat wins.
2. **NO-GO** (or **GO-WITH-FIXES** that *narrows*) if any AC/FR requires a change to excluded element E beyond allowed delta C — including inherited parent flex/grid alignment.
3. When fixing: add/update Constraints; mirror Non-Goals; strip or rewrite ACs that demanded forbidden position/styling/markup. Mark `_(user said)_` vs `_(inferred from Figma)_`.
4. Decided exclusions stay in Constraints / Non-Goals — **not** TBD.

## TBD harvest

- Fold Questions / Open issues into TBD.
- Add gaps that would force a product guess (copy, locale, URL, env, which component, ownership, Figma node).
- **jira:** do **not** invent answers. Do **not** promote TBD into ACs/FRs. Phrase leftover TBD with `write-analyst-message` (decision + Blocks + 2–3 options, recommendation first). Non-empty TBD → hard-stop before coding; not a plan NO-GO by itself.
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
- Do not add Co-authored / AI trailers or execute `run-plan`.
