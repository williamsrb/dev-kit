---
name: lint-and-draft-generic-commit-message
description: "Lint and fix a non-Enonic delivery, then draft a commit message. Does not commit. For XP/React4XP use lint-and-draft-enonic-commit-message. | recommendedRole: implement | aliases: generic-staged-validation-commit-message, lint-and-suggest-generic-commit-msg, lint-generic-and-commit-msg-from-diff."
disable-model-invocation: true
metadata:
  recommendedRole: implement
  aliases: generic-staged-validation-commit-message, lint-and-suggest-generic-commit-msg, lint-generic-and-commit-msg-from-diff
  cliDependencies:
    required: [agentctl, git, rg, jq, shellcheck, shfmt, ruff]
    optional: [markdownlint-cli2, lychee, codespell, ast-grep, gitleaks, osv-scanner]
---
## Local deterministic first

Start with `agentctl repo detect --cwd <repo> --json` and `agentctl delivery scope --cwd <repo> --json`. Prefer project-native commands; use global CLIs only when the project has no declared equivalent — `agentctl checks run` (step 7) is the batched runner for the declared linters.

# Generic Staged Validation + Commit Message

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md` when a TASK-ID prefix is needed. Read the delivery **diff only** (plus full file context for files in that diff). Do **not** read `~/.agents/prds/` or `~/.agents/plans/`.

## Goal

Validate **and fix** the current solution delivery for syntax, semantics, and linter errors, then produce a commit message from the final delivery state.

For Enonic XP / React4XP deliveries, prefer `lint-and-draft-enonic-commit-message`.

## Knowledge base (mandatory)

| Topic | Path |
|-------|------|
| Delivery scope | `~/.agents/kb/validation/Quality-gate-delivery-scope.md` |

Do not copy that procedure into this skill.

## Workflow

1. **Identify delivery scope** — per KB; state tier.
2. **Inspect delivery diff** — hunks **and** full file context.
3. **Group files** by kind (source, tests, config, CI, docs) and note stack from repo cues.
4. **Syntax & semantic validation** — checks below per file type.
5. **Apply fixes** — blockers and safe issues (Fix policy).
6. **Re-validate** — until PASS or only unfixable blockers remain.
7. **Linter diagnostics** — run `agentctl checks run --cwd <repo> --scope changed` after fixes, then `ReadLints` on touched sources.
8. **Optional tooling** — `tsc --noEmit`, `node --check`, etc. when quick and available.
9. **Commit message** — from **final** delivery diff; print full suggestion and stop.

Never run `git commit` or merge, and do not ask to commit or merge.

## Syntax & semantic validation (mandatory)

For **every source file** in the delivery, check and **fix**:

| Check | What to do |
|-------|------------|
| **Unclosed brackets** | Balance `{}`, `[]`, `()`; fix mismatches. |
| **Missing semicolons / statement termination** | Fix where required by style or ASI would break. |
| **Parse/syntax errors** | Language-appropriate checks (`node --check`, JSON.parse, YAML load); fix reported errors. |
| **Undefined / missing symbols** | Confirm calls, imports, identifiers resolve; fix typos/missing imports. |
| **Unresolved imports/requires** | Verify paths and exported names. |
| **Dangling references** | After renames/removals, grep leftovers. |
| **Dead or orphaned fragments** | Remove leftover lines from partial refactors. |

Read the **whole file** when the diff touches control flow, functions, or braces.

## Validation by file type

| Area | Guidance |
|------|----------|
| **JS / TS source** | Braces, semicolons, parse check, import/require resolution, undefined calls. |
| **Config / CI (JSON, YAML)** | Valid structure; fix trailing commas, bad indentation, broken keys. |
| **Typed languages** | Run `tsc`/compiler when project has it; fix errors in delivery scope. |
| **All text** | Secrets in diff, wrong paths, obvious dead code in changed hunks. |
| **Docs / markdown** | Broken links in changed sections; no fabricated changelog entries. |

## Fix policy

Apply fixes for syntax/semantic **Blockers**, clear local linter **errors**, and orphaned fragments introduced in the delivery.

Do **not** change behavior beyond the fix, refactor outside the delivery, or expand feature scope. Prefer the **smallest fix**. Re-validate after each pass.

## Linter checks

- `agentctl checks run --cwd <repo> --scope changed` **before** `ReadLints`: it batches ruff, shellcheck, markdownlint-cli2, xmllint, yq, and codespell over the changed files and returns compact pass/fail/skip per check. It does **not** cover `shfmt`, `lychee`, or `ast-grep` — keep those as their own steps. A check reported `unavailable` was **not run**; do not count it as a pass.
- `ReadLints` after fixes; fix clear local **errors**; summarize warnings.

## Commit message generation

Print **### Commit message suggestion**.

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

## Response template

The layout follows `response-formatting.mdc`: print the fence content as is, with no Markdown list syntax, and keep the blank line between items. The commit message block stays a plain indented block because it leaves the chat.

```markdown
**Delivery scope:** staged | unstaged | branch diff vs main/master

### Fixes applied

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; <file>: <what changed and why>, or `None`

### Syntax & semantic validation

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <path or group>: PASS

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <path or group>: FAIL. <issue → remaining after fixes>

### Linter

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <check>: passed

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <check>: <deciding error after fixes>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; <check>: skipped or unavailable (<reason>); unavailable is not a pass

### Commit message suggestion

    [TASK-ID] Title of change
    * Change 1
    * Change 2

```

Omit `[TASK-ID]` in the suggestion when the current branch is not a jira-task-id branch.

Do not ask to commit or merge after the report.
