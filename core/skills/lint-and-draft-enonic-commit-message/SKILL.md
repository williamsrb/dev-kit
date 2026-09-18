---
name: lint-and-draft-enonic-commit-message
description: "Lint and fix Enonic XP / React4XP delivery (backend JS and TS/TSX), then draft a commit message. Does not commit. | recommendedRole: implement | aliases: enonic-staged-validation-commit-message, lint-and-suggest-enonic-commit-msg, lint-enonic-and-commit-msg-from-diff."
disable-model-invocation: true
metadata:
  recommendedRole: implement
  aliases: enonic-staged-validation-commit-message, lint-and-suggest-enonic-commit-msg, lint-enonic-and-commit-msg-from-diff
  cliDependencies:
    required: [agentctl, git, rg, jq, xmllint, xmlstarlet, yq, shellcheck, shfmt]
    optional: [ruff, ast-grep, gitleaks, osv-scanner]
---
## Local deterministic first

Start with `agentctl repo detect --cwd <repo> --json` and `agentctl delivery scope --cwd <repo> --json`. Run only applicable local checks and return compact failures with file/line pointers — `agentctl checks run` (step 8) is the batched runner for the declared linters.

# Enonic Staged Validation + Commit Message

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md` when a TASK-ID prefix is needed. Read the delivery **diff only** (plus full file context for files in that diff). Do **not** read `~/.agents/prds/` or `~/.agents/plans/`.

## Goal

Validate **and fix** the current solution delivery for Enonic XP apps (backend JS and React4XP/CMS TypeScript), then produce a commit message from the final delivery state.

This skill is not read-only. Find syntax/semantic issues **and apply fixes** before reporting.

## Knowledge base (mandatory)

Read before resolving scope:

| Topic | Path |
|-------|------|
| Delivery scope (staged / unstaged / branch) | `~/.agents/kb/validation/Quality-gate-delivery-scope.md` |

Do not copy that procedure back into this skill. This skill wins for Enonic/React4XP rule sets, fix policy, and report sections below.

## Scope

Default validation path for **Enonic XP** and **React4XP** deliveries. Classify each delivery file:

| Class | Typical paths / extensions | Rules |
|-------|----------------------------|--------|
| **Backend Enonic JS** | Controllers, services, libs under `xp/` as `*.js` (not React4XP entries/assets) | Enonic CommonJS + ES5.1 (+ allowed extras) |
| **XP / CMS TypeScript** | `*.ts` under `xp/src/main/resources/` (processors, libs, types) — not React view `.tsx` | Generic TS syntax/semantic + `tsconfig.xp.nashorn.json` |
| **React4XP views** | `*.tsx`, React4XP components/entries/utils | Generic TS/TSX syntax/semantic + `tsconfig.react4xp.json` |
| **Other frontend JS** | Browser bundles, `assets/js/`, client utilities | Generic JS checks only (no Enonic ES5.1) |
| **Skip** | Generated/bundled assets, `node_modules`, build output | Do not validate/fix |

**Never** apply Enonic backend CommonJS/ES5.1 rules to TypeScript (`*.ts` / `*.tsx`), React4XP view code, Next.js, or browser bundles.

## Workflow

1. **Identify delivery scope** — per KB; state tier.
2. **Inspect delivery diff** — changed hunks **and** full file context around edits.
3. **Classify files** — apply the matching rule set per file.
4. **Syntax & semantic validation** — checks below; record every issue.
5. **Apply fixes** — blockers and safe issues in delivery scope (Fix policy).
6. **Re-validate** — until PASS or only unfixable blockers remain.
7. **Typecheck** — when delivery includes `.ts` / `.tsx` (React4XP / TypeScript section).
8. **Linter + optional tooling** — run `agentctl checks run --cwd <repo> --scope changed` first, then `ReadLints` on touched sources; optionally `node --check` on backend `.js`.
9. **Commit message** — from **final** delivery diff; print full suggestion and stop.

Do **not** commit, push, merge, create PRs, or ask whether to commit/merge.

## Syntax & semantic validation (mandatory)

For **every source file** in the delivery, check and **fix**:

| Check | What to do |
|-------|------------|
| **Unclosed brackets** | Balance `{}`, `[]`, `()`; fix mismatched or dangling braces from bad merges/edits. |
| **Missing semicolons / statement termination** | Fix where required by project style or where omission breaks ASI. |
| **Parse/syntax errors** | Backend `.js`: `node --check` when Node is available. TS/TSX: `tsc` + IDE diagnostics. |
| **Undefined / missing functions** | Confirm symbols resolve; fix wrong names or missing imports/requires. |
| **Unresolved requires / imports** | Confirm paths and exported names exist. |
| **Dangling references** | After renames/removals, grep leftover symbol/route/config references. |
| **Dead or orphaned fragments** | Remove leftover lines from partial refactors. |

Read the **whole file** when the diff touches control flow, functions, or braces.

## Backend JS validation rules (Enonic XP 7.16)

For each **backend Enonic JS** file only:

- CommonJS only (`require`, `exports`, `module.exports`); no ESM `import`/`export`.
- Syntax: ES5.1 + allowed extras: arrow functions; template strings (not containing regex patterns); `let`/`const`; default parameters; computed property names; object shorthand.
- Flag and **fix** unsupported modern syntax when a safe ES5.1-compatible rewrite exists within the delivery.

If no backend JS files are in the delivery, state that and skip Enonic-specific rules.

## React4XP / TypeScript validation

When the delivery includes `*.ts` or `*.tsx` in an Enonic/React4XP tree:

1. Apply the mandatory syntax/semantic checks (imports allowed; modern TS/JS is fine).
2. Prefer a root **Makefile** typecheck target if one exists; otherwise from the XP app dir:
   - XP/CMS `.ts` → `npx tsc --noEmit -p tsconfig.xp.nashorn.json` (or `npm run check:types:xp`).
   - React4XP `.tsx` → `npx tsc --noEmit -p tsconfig.react4xp.json` (or `npm run check:types:react4xp`).
   - Both → run both (or aggregating `npm run check:types`).
3. Fix **errors that originate in delivery-scope files** only.
4. Treat delivery-scoped `tsc` errors as blockers.
5. Skip typecheck only when no `.ts`/`.tsx` are in the delivery — say so in the report.

## Fix policy

Apply fixes when they fix syntax/semantic **Blockers**, linter **errors** in delivery files, or Enonic CommonJS/ES5.1 violations with a minimal local rewrite (**backend JS only**).

Do **not** change behavior beyond the fix, refactor outside the delivery, expand feature scope, or rewrite TS/TSX to ES5.1 CommonJS style.

Prefer the **smallest fix**. After each pass, re-read and re-validate.

## Linter checks

- `agentctl checks run --cwd <repo> --scope changed` **before** `ReadLints`: it batches ruff, shellcheck, markdownlint-cli2, xmllint, yq, and codespell over the changed files and returns compact pass/fail/skip per check. It does **not** cover `shfmt`, `xmlstarlet`, `ast-grep`, or the TypeScript typecheck — keep those as their own steps. A check reported `unavailable` was **not run**; do not count it as a pass.
- `ReadLints` on all touched source files **after** fixes (include `.ts` / `.tsx`).
- Fix linter **errors** when clear and local; report warnings; fix warnings only when trivial and in changed code.

## Commit message generation

Use **final delivery diff** (after fixes). Print **### Commit message suggestion** (title + bullets). Do not ask to commit.

**Jira-task-id branch** (prepend prefix) — current branch matches:

```text
(?i)^[A-Z][A-Z0-9]+-\d+([._/-].+)?$
```

Examples that **do** prepend: `RFD-123`, `AS-456-v2`, `PROJ-413/fix-icons`, `ntf-1224`.
Examples that **do not**: `master`, `main`, `review`, `qa`, `staging`, `develop`, `feature/foo` (no issue key).

When the branch is a jira-task-id branch:

```text
[TASK-ID] Title of change
* Change 1
* Change 2
```

- `TASK-ID` = current git branch name in **uppercase** (e.g. `as-456-v2` → `[AS-456-V2]`). Prefer the Jira key from the branch over inventing one.

When the branch is **not** a jira-task-id branch:

```text
Title of change
* Change 1
* Change 2
```

- Do **not** invent a prefix from `master` / `review` / etc.
- Title reflects **why** or **outcome**.
- Bullets summarize meaningful deltas (include validation fixes if part of this delivery).

## Response template

```markdown
**Delivery scope:** staged | unstaged | branch diff vs main/master

### Fixes applied
- <file>: <what changed and why> — or "None"

### Syntax & semantic validation
- <file>: PASS | FAIL (<issue → fixed | remaining>)

### Enonic backend JS (XP 7.16)
- <file>: PASS | FAIL | SKIPPED (<reason>)

### React4XP / TypeScript
- <file or tsc project>: PASS | FAIL | SKIPPED (<reason>)
- tsc: <command(s) run or skipped> — PASS | FAIL (<summary>)

### Linter
- <status summary after fixes>

### Commit message suggestion

    [TASK-ID] Title of change
    * Change 1
    * Change 2

```

Omit `[TASK-ID]` in the suggestion when the current branch is not a jira-task-id branch.

Do not ask to commit or merge after the report.
