---
id: how-to-check-spec-alignment
when_skills: [validate-impl, validate-plan]
inputs: [sliced PRD sections, plan AC / FR / Constraints / Non-Goals / tbd, delivery diff (validate-impl only)]
outputs: [requirement list, state per requirement, plan gaps, delivery gaps]
stop_if: [applying unchecked PRD comments, re-fetching the issue, editing the plan from validate-impl]
read: whole
prose: caveman-lite
---

# Check spec alignment (PRD → plan → delivery)

The plan is derived from the PRD and the delivery from the plan. Each hop can drop, narrow or change a requirement. A delivery that satisfies a drifted plan is still wrong. `validate-plan` checks the first hop. `validate-impl` checks both.

## Requirement source

Authority order. A higher row overrides a lower one.

| # | Source | Notes |
|---|--------|-------|
| 1 | Operator instruction or exclusion in this conversation | `How-to-respect-user-scope-exclusions.md` |
| 2 | Requirement source the caller names (context file, attached spec path) | Wins over `agentctl plan context` |
| 3 | PRD `## Requirement Changes` (`RC<n>`) | Overrides Description and Acceptance Criteria. A later RC on the same point replaces the earlier one |
| 4 | PRD requirement sections | Local PRD: `## Description`, `## Acceptance Criteria`, `## Requirements`, `## Success Criteria`, `## Edge Cases`, `## Non-Goals`, `## Constraints`. Jira PRD: `## Description` only |
| 5 | Planner decisions in `tbd.md` (Local PO, High-confidence, Technical) | Fill a gap or pick between readings. Never override rows 1 to 4 |

No PRD on disk (run started from a plan path only): alignment is `n/a` and the plan is the only contract. Report that under Not verified. Do not fetch the issue.

## Procedure

1. Paths: `agentctl plan context <TASK-ID>` (PRD, plan, mode).
2. Staleness: `python3 ~/.agents/skills/write-prd/scripts/requirement_changes.py <prd> --json`. Read `stale` together with `checked_through`:
   - `stale: true` with a `checked_through` id: comments arrived after the marker. **Stale.** Name the unchecked comment ids and the refresh command (`write-prd` "refresh `<slug>`" for local, a new `download-jira-task` run for jira). Judge against the PRD as checked. Do not apply the comments.
   - `stale: true` with `checked_through: null`: a **legacy PRD** written before Requirement Changes existed (most older Jira exports). Not a stop. Judge against the Description plus the comments the plan cites (`_(from comments)_`, by comment id), and report "comments not extracted" under Not verified.
   - `stale: false`: go on.
3. Slice, never read the whole file: `agentctl markdown slice <prd> --sections description,requirement-changes,acceptance-criteria,requirements,success-criteria,edge-cases,non-goals,constraints --json`. Missing sections are normal: a Jira PRD holds Description, Requirement Changes, Comments and Attachments only. The command exits 2 when any requested section is missing; read `found` and `missing` in the JSON, not the exit code. Open `## Comments` only for a comment that an RC or the plan cites by id.
4. Build the requirement list, one row per statement a tester could pass or fail.
   - Counts: an acceptance checkbox, an `FR`, an `SC`, an `RC`, a Description sentence that states required behaviour, a value, a field list or a prohibition, a PRD Non-Goal or Constraint (as a prohibition).
   - Does not count: background, the reporter's symptom, a production URL (the scenario is restated on review), narrative marked `_(inferred)_`, an Open Question with no answer, examples.
   - Row id: the PRD's own code (`RC2`, `FR-003`, `SC-001`, `US1 #2`). Uncoded statements get report-local labels in document order: `AC1…` (acceptance), `D1…` (Description), `EC1…` (edge case), `C1…` (Constraint), `NG1…` (Non-Goal). Keep a quote of at most 15 words.
   - One row per requirement, not per sentence: a Description sentence that an AC or FR restates merges into that row. A bundled statement stays one row unless its parts end in different states; then split it (`AC7a`, `AC7b`).
5. Map each row to the plan item that carries it (AC, FR, Constraint, Non-Goal or a `tbd.md` decision). **Match by meaning, never by code.** PRD `FR-001` and plan `FR-1` are separate namespaces, and a Jira PRD has no codes at all. One row may map to several plan items. Folder plan: ACs and FRs are in `requirements.md`, Non-Goals and Constraints in `plan.md`, decisions in `tbd.md`, ticks in `implicit.md`, Already delivered and steps in `implementation.md` (`agentctl plan resolve <TASK-ID>` lists them under `sections`). Slice the companion file, not the folder.
6. `validate-impl` only: map each plan item on to the delivery (`file:line` in the diff, or existing code the diff relies on).
7. Give each row a state (table below) and, when it is not `met` or `waived`, a gap location.
8. Reverse pass: every plan AC and FR traces back to a row or carries a source mark (`_(from comments)_`, `_(user said)_` or another recorded operator order, `_(local PO: …)_`, `_(high confidence: …)_`). A ticked implicit extra is a plan addition too: it must not contradict a PRD or plan Non-Goal or Constraint. An unsourced plan requirement is a realism defect in `validate-plan`. A delivered behaviour no requirement asks for is scope creep in `validate-impl` (`Quality-gate-delivery-standards.md` § Requirement fit).

## Authorized deviations

A difference between PRD and plan, or plan and delivery, is legitimate only when one of these covers it. Cite which one.

- An operator instruction or exclusion in this conversation, or one recorded in the plan (a Constraint marked `_(user said)_`, a decision that cites the operator's order). A recorded order cannot be re-checked here, so list each one in the report for the operator to see.
- An `RC<n>` that overrides the Description or an acceptance criterion.
- A PRD Non-Goal, or a production-phrased criterion restated on the review scenario (`plan-implementation` § Environment boundary).
- An analyst-answered TBD, or an open `jira` TBD the operator accepted with "implement with these assumptions".
- A planner decision in `tbd.md` (**Local PO**, **High-confidence**, **Technical**), only where the PRD is silent or ambiguous. It fills a gap; it never overrides an explicit statement or prohibition. A planner decision that does is `contradicted`, unless it cites one of the items above.
- On a rework plan, an `## Already delivered` `[x]` item with its SHA. It is closed and is not re-proved.
- An unticked implicit extra. It was never a PRD statement, so its absence is not a gap.

Not a deviation: the plan silently drops, narrows or changes an explicit statement; a plan Non-Goal that contradicts the PRD with no recorded decision; "the plan did not mention it".

## States

| State | Meaning |
|-------|---------|
| `met` | `validate-plan`: a plan item carries it; the proof is that item. `validate-impl`: implemented, with proof `ran` (a test or command executed in this run shows it) or `read` (traced at `file:line`) |
| `waived` | An authorized deviation covers it. Cite it |
| `open` | Waits on a TBD that is neither answered nor accepted. Name the TBD |
| `unproven` | `validate-impl` only: the code path exists but only a runtime check can show the behaviour (browser, CMS content, external system). The evidence plan proves it |
| `unmet` | Explicit statement, no coverage, no authorized deviation |
| `contradicted` | The plan or the delivery does the opposite or uses a different value |

No proof, no `met`. In `validate-impl`, a claim without a `file:line` or a run command is `unproven`. In `validate-plan`, a row with no plan item to cite is `unmet`.

Gap location: **plan gap** (the plan lost or changed the statement) or **delivery gap** (the plan carries it, the code does not).

Severity: an explicit statement that is `unmet` or `contradicted` is a Blocker. PRD narrative, an implied "nicer" reading or an inferred extra is a Concern at most; classify it with `../implementation/How-to-handle-implicit-requirements.md` (PROJ-270). Between two classes, choose the lower.

## Pitfalls

- Do not match by code. A plan `FR-3` that reuses the number of PRD `FR-003` may state something else.
- Do not read the whole Comments thread "to be sure". Requirement Changes is the extracted view.
- Do not flag an unticked implicit extra, or a closed Already delivered item, as missing.
- Do not treat a production URL in the PRD as a requirement to verify on production.
- `validate-impl` does not close a plan gap by coding past the plan: the delivery would then disagree with its own plan. Report it; the plan goes back through `validate-plan` or `plan-implementation`.
- A stale PRD is not a failed alignment. It is an alignment judged against a known cut-off; say which comments were not considered.
- Do not treat a legacy PRD (no `Checked through:` marker) as stale. The script flags it `stale: true` because every comment is unchecked; refreshing is the operator's choice, not a gate.
