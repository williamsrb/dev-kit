---
name: validate-plan
description: "Validate and rewrite implementation or evidence plan files on disk against their PRD (spec coverage, traceability, consistency, realism). Not delivery QA, not new-spec drafting, not execution."
metadata:
  recommendedRole: plan-review
  reviewOf: plan-implementation, plan-task-evidence
  aliases: plan-validation, fix-plan
  cliDependencies:
    required: [agentctl, rg]
    optional: [ollama]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Use `agentctl task resolve`, `agentctl plan resolve`, and `agentctl markdown slice` to open only needed headings. `python3 ~/.agents/skills/write-prd/scripts/requirement_changes.py <prd> --json` tells whether the PRD has unchecked comments. Finish each target with `agentctl plan validate <file-or-dir> --json`. Structure JSON is a gate, not the verdict. Kind comes from `plan resolve`, not from the filename.

# Validate Plan

Validates **and rewrites** plan files. Default is fix-in-place (same as `validate-impl` on a delivery). Chat-only review is not success — the plan file on disk is.

**This skill does not implement code, execute evidence, open a capture browser, or post to a tracker.** Hard-stop after the report. `run-plan` is a later, explicit step.

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md`. Allowlist is kind-specific (table below). Do not read the delivery diff. Do not dump full PRD comments “just in case”.

## Not this skill

| Need | Use |
|------|-----|
| Draft a new impl spec | `plan-implementation` |
| Draft a new evidence plan | `plan-task-evidence` |
| Delivery fit / deslop / security on a diff | `validate-impl` |
| Syntax + commit message | `lint-and-draft-commit-message` |
| Execute a written plan | `run-plan` |

## Knowledge base (mandatory)

Read before judging. Do not copy these into the plan.

| Topic | Path |
|-------|------|
| User/chat exclusions | `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md` |
| Implicit extras vs TBD vs slop | `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md` |
| Spec coverage (PRD → plan: requirement list, states, authorized deviations) | `~/.agents/kb/validation/How-to-check-spec-alignment.md` |
| Mechanical consistency (counts, paths, AC satisfiability) | `~/.agents/kb/validation/How-to-validate-a-plan-document-for-internal-consistency.md` |
| Skill routing (“validate” vs QA vs lint) | `~/.agents/kb/implementation/How-to-route-cursor-skills.md` (shared; Cursor / Claude / Codex) |
| Realism vs hallucination + KB routing | [references/realism-and-kb.md](references/realism-and-kb.md) |

## Inputs

Resolve targets in this order:

1. Paths the user attached or listed.
2. `<TASK-ID>` (Jira key, Jira URL, or kebab slug) in the message → `agentctl plan context <TASK-ID>`, print the resolved paths before work, then the convention files under `~/.agents/plans`.
3. `agentctl task resolve` / branch / worktree folder per `How-to-resolve-task-context.md`.
4. Ask once if still ambiguous.

| Kind | Convention |
|------|------------|
| **implementation** | `agentctl plan resolve <TASK-ID>` → folder `~/.agents/plans/<TASK-ID>/` or legacy `~/.agents/plans/<TASK-ID>.md` |
| **evidence** | `agentctl plan resolve <TASK-ID> --kind evidence` → `evidence.md` in that folder or legacy `~/.agents/plans/<TASK-ID>-evidence-plan.md` |

Kind from `agentctl plan resolve` (`kind` in the JSON). Do **not** infer kind from the filename once resolve returns. Filename `*-evidence-plan.md` is only the unmigrated fallback. User-pointed legacy names (e.g. `DOCUMENTATION_PLAN.md`) are in scope only when named.

Several keys → one pass per file, then a batch summary. If the user attached `<multitask-root>/DECISIONS.md`, read it as shared constraints; do not invent a second decisions file.

Missing convention file → stop for that key; do not draft a new plan here (hand off to `plan-implementation` / `plan-task-evidence`).

## Kind allowlist

| Kind | Must read | Must not read by default |
|------|-----------|--------------------------|
| implementation | Draft plan + sectioned PRD (Description, Requirement Changes, AC, Requirements, Success Criteria, Edge Cases, Non-Goals, Constraints) + chat exclusions. `## Comments` only for a comment the draft or an RC cites by id, or when AC/TBD is thin | Evidence plan; delivery diff; sibling PRDs |
| evidence | Evidence plan + the AC source used in the draft (prefer impl-plan AC headings) | Full impl narrative; full PRD; delivery diff |

## Workflow

Copy and tick:

```text
- [ ] Resolve targets and kind
- [ ] Read exclusion + spec-alignment + consistency How-tos
- [ ] Load one kind reference + realism-and-kb
- [ ] agentctl plan validate (structure gate)
- [ ] impl: PRD staleness check + spec coverage. evidence: AC coverage against its AC source
- [ ] Judge (traceability, AC quality, extra validations) + rewrite the plan file
- [ ] Re-run agentctl; re-check coverage, exclusions, realism, KB use
- [ ] Report + hard-stop (no code, no evidence execute)
```

1. **Resolve** — list each plan path + kind. Confirm the file exists.
2. **KB** — exclusions + spec alignment + internal consistency (whole files; they are short).
3. **Kind reference** — load **one**:
   - implementation → [references/implementation.md](references/implementation.md)
   - evidence → [references/evidence.md](references/evidence.md)
   Then always load [references/realism-and-kb.md](references/realism-and-kb.md).
4. **Structure gate** — `agentctl plan validate <file-or-dir> --kind <kind> --json` (omit `--kind` to use resolve inference). `valid: false` is a real plan defect: fix the file. See [Structure gate semantics](#structure-gate-semantics) for what the validator does and does not flag.
5. **Judge** — apply the kind reference + consistency How-to against the draft and (for impl) the sectioned PRD. **Implementation kind only**, start with the PRD: run the staleness check, then **spec coverage** per `How-to-check-spec-alignment.md` (every PRD statement is carried by the plan or covered by an authorized deviation; every plan AC/FR has a source), then traceability and AC quality. The evidence kind runs no staleness or spec-coverage pass: its coverage check is every AC of its AC source (the implementation plan first, per the evidence reference § AC source) against a proving step. Then the kind reference's gates. Collect chat exclusions; they beat Figma/PRD/inferred ACs. Run both extra validations: **Is realistic or hallucination?** and **Is using the KB properly?**
6. **Fix** — rewrite the plan **on disk** (Write / StrReplace). Narrow toward exclusions; never widen toward a broader Figma reading. Restoring an explicit PRD statement the plan dropped or changed is not widening: add or correct the AC/FR with its PRD source. Keep step ids stable and leave `progress.md` alone (kind reference § Fix policy). Fold open questions into TBD (impl, **jira**) or resolve them as local PO (impl, **local**: auto-select the recommended path, encode as AC/FR/Constraint, `- TBD: none`) or reachability blockers (evidence). Fold inferred extras into Implicit requirements (impl). **jira:** do not invent product decisions. **local:** auto-select is required, not invented-then-hidden — record **Local PO decisions**. Replace hallucinated *technical* claims with measured source, TBD (jira) / local PO default (local), or delete. Add missing KB citations (offline-reference / testing How-to paths).
7. **Re-validate** — agentctl again; re-check spec coverage, exclusions, consistency, realism, and KB use on the edited sections only.
8. **Report** — template below. Surface leftover TBD / implicit / reachability gaps. **Stop.** Non-empty TBD is not a plan **NO-GO**. **jira:** it **is** a hard-stop before coding. **local:** leftover gaps must be auto-selected before this skill finishes; do not hard-stop. Non-empty implicit is not a coding hard-stop. An untestable evidence plan can still be **GO-WITH-FIXES** if the file records the blocker; it is **not** execution-ready.

Nested callers (`called_from: plan-implementation` / `plan-task-evidence` / `multitask-same-repo`) skip any cascade back into those skills.

## Verdicts

| Verdict | Meaning |
|---------|---------|
| **GO** | Plan is internally consistent, carries every PRD statement or records the deviation that covers it (impl), every AC has a step and a validation line (impl), exclusions recorded, ACs do not violate them, core steps reachable (evidence), **Is realistic or hallucination?** PASS, **Is using the KB properly?** PASS or n/a. **jira:** ready for a later `run-plan` once TBD is empty or the user accepts assumptions. **local:** execution-ready after auto-select (`TBD: none` + Local PO decisions). |
| **GO-WITH-FIXES** | Defects were (or should be) fixed in the file: by **narrowing** the plan (including stripping hallucinations and adding KB citations), or by restoring an explicit PRD statement the plan had dropped or changed. File on disk is the contract. |
| **NO-GO** | Unfixable without a product decision the user/analyst has not given; ACs still demand a forbidden delta on an excluded element; leftover invented facts / unsourced platform behavior after the rewrite attempt; a PRD statement the plan cannot carry without new technical design (hand to `plan-implementation`); or a stale PRD (comments after the `Checked through:` marker may supersede what the plan encodes; a legacy PRD with no marker is not stale). |

Do not start `run-plan` from a **NO-GO**. **jira:** do not treat silence as acceptance of TBD. **local:** auto-selected Local PO decisions **are** acceptance.

## Structure gate semantics

Treat `valid: false` as a plan defect and fix the file:

1. **`missing_sections`** — matching strips a trailing heading qualifier, so `## Constraints (user exclusions)` satisfies `constraints`, `## TBD (ask analyst before implement)` satisfies `tbd`, and `## Implicit requirements (techlead tick)` satisfies `implicit-requirements`. Keep the skill wording. `## Validation` is a real required section; add it if missing (build/manual/evidence gates). Add Implicit if missing (`- Implicit: none` when there is nothing to tick).
2. **`unresolved_placeholders`** — only template tokens flag: `TODO` plus `<ISSUE-KEY>`, `<TASK-ID>`, `<TASK-KEY>`, `<JIRA-KEY>`, `<ENV>`, `<DATE>`, `<FIXME>`, and siblings (see `PLACEHOLDER_TOKENS` in `~/.agents/bin/agentctl`). Ordinary angle brackets — `Promise<void>`, `<ComponentPrototype>`, `/<[^>]*>/g`, `services/<name>/<name>.ts`, `part.<part>.<field>` — do not flag. Every remaining hit is real: resolve it or delete the line.

Evidence kind requires H2 slugs `auth-required`, `acceptance-criteria`, `evidence-steps`, `artifacts`, `posting-gate`. If the draft uses `## Steps` instead of `## Evidence Steps`, rename (or add the required H2s) so both the skill template contract and the validator hold. Keep **Execution**.

## Auxiliary skills

Only for a real capability gap (e.g. Figma reader). Follow `find-skills` with `called_from: validate-plan`, then resume. Do not install tooling to avoid reading the plan.

## Report template

```markdown
**Verdict:** GO | GO-WITH-FIXES | NO-GO. <kind> plan `<absolute path>`, AC source `<path>` or n/a

## Blockers

&nbsp;&nbsp;&nbsp;&nbsp;🚫&nbsp;&nbsp;&nbsp; TBD: <item> (impl, **jira**): coding hard-stop until the analyst answers or the operator says "IMPLEMENT WITH THESE ASSUMPTIONS"

&nbsp;&nbsp;&nbsp;&nbsp;🚫&nbsp;&nbsp;&nbsp; Reachability: <missing input> (evidence)

## Fixes applied

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; <section>: <what changed and why>

## Structure (agentctl)

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; valid: true. <what was fixed>

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; valid: false. <missing sections / placeholders>

## Spec coverage

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; PRD `<path>`: <n> statements. <n> met, <n> waived, <n> open (impl)

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; `<id>` "<short quote>": unmet | contradicted. <restored as AC/FR … | needs `plan-implementation`>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; `<id>` "<short quote>": waived (<authorized deviation>)

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; Plan AC/FR with no source: <item> (moved to TBD | Implicit | deleted)

&nbsp;&nbsp;&nbsp;&nbsp;🚫&nbsp;&nbsp;&nbsp; PRD stale: comments <ids> arrived after the marker. Refresh: <command>

&nbsp;&nbsp;&nbsp;&nbsp;🔸&nbsp;&nbsp;&nbsp; Legacy PRD (no marker): comments not extracted; judged against Description + cited comments

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; Every AC has a proving step, or a recorded cut (evidence)

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; n/a: no PRD on disk, the plan is the only contract (impl)

## Exclusions

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; PASS: <element: allowed delta vs plan ACs>

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; FAIL: <element: plan AC delta beyond the allowed one>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; n/a

## TBD / implicit

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; TBD: none (impl). **local:** plus Local PO decisions: <list>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; Implicit: none | <checkbox list> (impl). Not a coding hard-stop; **local:** `[x]` auto-selected in scope

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; Reachability: all core steps reachable (evidence)

## Consistency

&nbsp;&nbsp;&nbsp;&nbsp;🔹&nbsp;&nbsp;&nbsp; <counts / paths / AC satisfiability / phase overlap>

&nbsp;&nbsp;&nbsp;&nbsp;🔹&nbsp;&nbsp;&nbsp; <traceability: AC with no step or validation line / step with no AC, FR or DO / untestable AC wording> (impl)

## Is realistic or hallucination?

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; PASS: <sourced claims vs leftovers moved to TBD / deleted>

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; FAIL: <unsourced claim still in the plan>

## Is using the KB properly?

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; PASS: <catalog + cited paths>

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; FAIL: <missing or wrong KB citation>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; n/a: <why>

## Follow-up

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; Do not implement or execute from this skill.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; **local:** leftover TBD auto-selected; the plan is execution-ready. Do not ask an analyst.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; Evidence not execution-ready: keep the plan file; do not run Execution.

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;👉&nbsp;&nbsp;&nbsp; <next step: `run-plan`, or the analyst for non-empty **jira** TBD>
```

Layout per Response formatting (`response-formatting.mdc`): no Markdown list syntax, a blank line between items. Markers: ✅ PASS or clean, ⛔ FAIL, 🚫 hard-stop, 🔹 finding, plain `•` for neutral items. Omit **Blockers** when there is no hard-stop; a section with nothing to report holds the plain line `None`. Several files: one block per plan under a `## <plan path>` heading, then a one-line batch verdict.

## Final reply: next step (always last)

When the verdict is GO or GO-WITH-FIXES and the plan is execution-ready (**jira** impl: TBD empty), put this block right after the 👉 line, as the last thing in the reply, with `<TASK-ID>` expanded (Jira key or slug). The operator pastes it into a fresh session. Skip it when `called_from` is set or `AGENTCTL_FACTORY` is set. Evidence kind: `/run-plan ~/.agents/plans/<TASK-ID>/evidence.md` instead. NO-GO or an open **jira** TBD: no block; the 👉 line names the blocker.

```text
/run-plan <TASK-ID>
```
