---
id: how-to-validate-a-plan-document-for-internal-consistency
when_skills: [validate-plan, plan-implementation]
inputs: [plan file, source tree]
outputs: [arithmetic / AC / phase consistency findings]
stop_if: []
read: whole
prose: caveman-lite
---

# Validate a plan document for internal consistency

A plan that has been revised several times fails in derived values that stopped tracking their sources. Check the arithmetic before the argument. Only mechanically checkable claims (counts, paths, file lists, states, flags) are in scope here. Rationale is not.

## Procedure

1. Re-derive every stated number from its own source. Do not trust a figure because an earlier revision states it.
2. Check derived numbers against their own operands (`X of Y`, `Y − X missing`, `so N remain`). When a revision changes `Y`, the downstream sentence is usually left alone.
3. Check enumerated lists against the count that introduces them.
4. Check any file tree against the phase counts that total it.
5. Check every acceptance criterion is satisfiable. An AC that requires closing every register item conflicts with any item marked out of scope.
6. Check the same task is not assigned to two phases.
7. Check the status header against the open items below it.
8. Grep for references to files outside the deliverable boundary.

Folder plans (`~/.agents/plans/<TASK-ID>/`): run `agentctl plan validate <dir>` so required headings are checked across companion files. `agentctl plan resolve` is the path contract.

## Deriving counts without trusting a README

Read the registration site, not the summary:

| Claim | Derive from |
|---|---|
| CLI command count | decorator/registration table in source, not the README table |
| HTTP route count | router registration calls, per file, then reconcile against the by-prefix split the plan uses |
| Module count | `ls` of the package source dir |
| Documented-vs-real | grep the doc for its own entry markers, then diff against the derived list |

Where a crude grep and the plan disagree by one or two, the counting method differs. Say so rather than declaring the plan wrong. Fix the method once and use its output everywhere.

## Pitfalls

- A false negative is worse than an omission. Grep plans and docs for `not yet`, `no ... yet`, `lands in`, `reserved for`, `does not exist` and verify each against current source.
- A document asserting it is generated tells readers it cannot drift. Confirm a generator actually emits that artifact.
- State a number only where it changes a decision, and date it.
- Do not fix a stale number by inference. Measure the thing being described.
- Counting rows with `grep -c` over a whole file catches identical rows in other sections. Scope to the section first.

## Sample data

```bash
awk '/^### 3.1/,/^### 3.2/' PLAN.md | grep -c '| \*\*Accurate\*\*'
```
