---
name: validate-plan
description: "Validate and rewrite implementation or evidence plan files on disk. Not delivery QA, not new-spec drafting, not execution. | recommendedRole: implement | aliases: plan-validation, fix-plan."
disable-model-invocation: true
metadata:
  recommendedRole: implement
  aliases: plan-validation, fix-plan
  cliDependencies:
    required: [agentctl, rg]
    optional: [ollama]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Use `agentctl task resolve`, `agentctl plan resolve`, and `agentctl markdown slice` to open only needed headings. Finish each target with `agentctl plan validate <file-or-dir> --json`. Structure JSON is a gate, not the verdict. Kind comes from `plan resolve`, not from the filename.

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
| Syntax + commit message | `lint-and-draft-*` |
| Execute a written plan | `run-plan` |

## Knowledge base (mandatory)

Read before judging. Do not copy these into the plan.

| Topic | Path |
|-------|------|
| User/chat exclusions | `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md` |
| Implicit extras vs TBD vs slop | `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md` |
| Mechanical consistency (counts, paths, AC satisfiability) | `~/.agents/kb/validation/How-to-validate-a-plan-document-for-internal-consistency.md` |
| Skill routing (“validate” vs QA vs lint) | `~/.agents/kb/implementation/How-to-route-cursor-skills.md` (shared; Cursor / Claude / Codex) |
| Realism vs hallucination + KB routing | [references/realism-and-kb.md](references/realism-and-kb.md) |

## Inputs

Resolve targets in this order:

1. Paths the user attached or listed.
2. `<TASK-ID>` (Jira key, Jira URL, or kebab slug) in the message → convention files under `~/.agents/plans`.
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
| implementation | Draft plan + sectioned PRD (`## Description` / AC headings) + chat exclusions. `## Comments` only if the draft cites them or AC/TBD is thin | Evidence plan; delivery diff; sibling PRDs |
| evidence | Evidence plan + the AC source used in the draft (prefer impl-plan AC headings) | Full impl narrative; full PRD; delivery diff |

## Workflow

Copy and tick:

```
- [ ] Resolve targets and kind
- [ ] Read exclusion + consistency How-tos
- [ ] Load one kind reference + realism-and-kb
- [ ] agentctl plan validate (structure gate)
- [ ] Judge (incl. extra validations) + rewrite the plan file
- [ ] Re-run agentctl; re-check exclusions, realism, KB use
- [ ] Report + hard-stop (no code, no evidence execute)
```

1. **Resolve** — list each plan path + kind. Confirm the file exists.
2. **KB** — exclusions + internal consistency (whole files; they are short).
3. **Kind reference** — load **one**:
   - implementation → [references/implementation.md](references/implementation.md)
   - evidence → [references/evidence.md](references/evidence.md)
   Then always load [references/realism-and-kb.md](references/realism-and-kb.md).
4. **Structure gate** — `agentctl plan validate <file-or-dir> --kind <kind> --json` (omit `--kind` to use resolve inference). `valid: false` is a real plan defect: fix the file. See [Structure gate semantics](#structure-gate-semantics) for what the validator does and does not flag.
5. **Judge** — apply the kind reference + consistency How-to against the draft and (for impl) the sectioned PRD. Collect chat exclusions; they beat Figma/PRD/inferred ACs. Run both extra validations: **Is realistic or hallucination?** and **Is using the KB properly?**
6. **Fix** — rewrite the plan **on disk** (Write / StrReplace). Narrow toward exclusions; never widen toward a broader Figma reading. Fold open questions into TBD (impl, **jira**) or resolve them as local PO (impl, **local**: auto-select the recommended path, encode as AC/FR/Constraint, `- TBD: none`) or reachability blockers (evidence). Fold inferred extras into Implicit requirements (impl). **jira:** do not invent product decisions. **local:** auto-select is required, not invented-then-hidden — record **Local PO decisions**. Replace hallucinated *technical* claims with measured source, TBD (jira) / local PO default (local), or delete. Add missing KB citations (offline-reference / testing How-to paths).
7. **Re-validate** — agentctl again; re-check exclusions, consistency, realism, and KB use on the edited sections only.
8. **Report** — template below. Surface leftover TBD / implicit / reachability gaps. **Stop.** Non-empty TBD is not a plan **NO-GO**. **jira:** it **is** a hard-stop before coding. **local:** leftover gaps must be auto-selected before this skill finishes; do not hard-stop. Non-empty implicit is not a coding hard-stop. An untestable evidence plan can still be **GO-WITH-FIXES** if the file records the blocker; it is **not** execution-ready.

Nested callers (`called_from: plan-implementation` / `plan-task-evidence` / `multitask-same-repo`) skip any cascade back into those skills.

## Verdicts

| Verdict | Meaning |
|---------|---------|
| **GO** | Plan is internally consistent, exclusions recorded, ACs do not violate them, core steps reachable (evidence), **Is realistic or hallucination?** PASS, **Is using the KB properly?** PASS or n/a. **jira:** ready for a later `run-plan` once TBD is empty or the user accepts assumptions. **local:** execution-ready after auto-select (`TBD: none` + Local PO decisions). |
| **GO-WITH-FIXES** | Defects were (or should be) fixed by **narrowing** the plan (including stripping hallucinations and adding KB citations). File on disk is the contract. |
| **NO-GO** | Unfixable without a product decision the user/analyst has not given; ACs still demand a forbidden delta on an excluded element; or leftover invented facts / unsourced platform behavior after the rewrite attempt. |

Do not start `run-plan` from a **NO-GO**. **jira:** do not treat silence as acceptance of TBD. **local:** auto-selected Local PO decisions **are** acceptance.

## Structure gate semantics

The two long-standing validator mismatches are fixed in `agentctl` (2026-08-19), so treat `valid: false` as a plan defect and fix the file:

1. **`missing_sections`** — matching strips a trailing heading qualifier, so `## Constraints (user exclusions)` satisfies `constraints`, `## TBD (ask analyst before implement)` satisfies `tbd`, and `## Implicit requirements (techlead tick)` satisfies `implicit-requirements`. Keep the skill wording. `## Validation` is a real required section; add it if missing (build/manual/evidence gates). Add Implicit if missing (`- Implicit: none` when there is nothing to tick).
2. **`unresolved_placeholders`** — only template tokens flag: `TODO` plus `<ISSUE-KEY>`, `<TASK-ID>`, `<TASK-KEY>`, `<JIRA-KEY>`, `<ENV>`, `<DATE>`, `<FIXME>`, and siblings (see `PLACEHOLDER_TOKENS` in `~/.agents/bin/agentctl`). Ordinary angle brackets — `Promise<void>`, `<ComponentPrototype>`, `/<[^>]*>/g`, `services/<name>/<name>.ts`, `part.<part>.<field>` — no longer flag. Every remaining hit is real: resolve it or delete the line.

Evidence kind requires H2 slugs `auth-required`, `acceptance-criteria`, `evidence-steps`, `artifacts`, `posting-gate`. If the draft uses `## Steps` instead of `## Evidence Steps`, rename (or add the required H2s) so both the skill template contract and the validator hold. Keep **Execution**.

## Auxiliary skills

Only for a real capability gap (e.g. Figma reader). Follow `find-skills` with `called_from: validate-plan`, then resume. Do not install tooling to avoid reading the plan.

## Report template

```markdown
## Plan validation

**Kind:** implementation | evidence
**Plan:** <absolute path>
**PRD / AC source:** <path or n/a>
**Verdict:** GO | GO-WITH-FIXES | NO-GO

### Fixes applied
- <section>: <what changed and why> — or "None"

### Structure (agentctl)
- valid: true | false — <missing sections / placeholders, and what was fixed>

### Exclusions
- PASS | FAIL | n/a — <element: allowed delta vs plan ACs>

### TBD / blockers
- TBD: none | <checklist> (impl) — **jira:** coding hard-stop if non-empty. **local:** must be `none` plus Local PO decisions.
- Implicit: none | <checkbox list> (impl) — not a coding hard-stop; **local:** `[x]` auto-selected in scope
- Reachability: all core steps reachable | <missing inputs> (evidence)

### Consistency
- <counts / paths / AC satisfiability / phase overlap> — or "None"

### Is realistic or hallucination?
- PASS | FAIL — <sourced claims vs leftovers moved to TBD / deleted>

### Is using the KB properly?
- PASS | FAIL | n/a — <catalog + cited paths, or why n/a>

### Follow-up
- Do not implement or execute from this skill.
- **jira:** non-empty TBD → analyst (or explicit implement-with-assumptions) before `run-plan`.
- **local:** auto-select leftover TBD; plan is execution-ready. Do not ask an analyst.
- Evidence not execution-ready → keep the plan file; do not run Execution.
```

Several files: one block per plan, then a one-line batch verdict.
