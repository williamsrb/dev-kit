---
name: lint-and-draft-commit-message
description: "Lint and fix the current delivery then draft a commit message. Use when the user says \"lint and commit\" (lint plus commit in one request). Asks before committing. Detects python, PHP, Enonic XP/React4XP, or generic stacks from agentctl repo detect plus delivery files and lazy-loads only matching rules. Use for lint, ruff, php -l, python scripts, PHP, XP JS, React4XP, staged validation, or lint-and-draft-*."
metadata:
  recommendedRole: follow
  aliases: lint-and-draft-enonic-commit-message, lint-and-draft-generic-commit-message, enonic-staged-validation-commit-message, generic-staged-validation-commit-message, lint-and-suggest-enonic-commit-msg, lint-and-suggest-generic-commit-msg, lint-enonic-and-commit-msg-from-diff, lint-generic-and-commit-msg-from-diff
  cliDependencies:
    required: [agentctl, git, rg, jq, python3, ruff, shellcheck, shfmt]
    optional: [php, xmllint, xmlstarlet, yq, markdownlint-cli2, lychee, codespell, ast-grep, gitleaks, osv-scanner]
---
## Local deterministic first

Start with `agentctl repo detect --cwd <repo> --json` and `agentctl delivery scope --cwd <repo> --json`. Classify delivery files, then read **only** the matching stack files below. Run only applicable local checks and return compact failures with file/line pointers — `agentctl checks run` (workflow step 8) is the batched runner for the declared linters.

# Lint and draft commit message

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md` when a TASK-ID prefix is needed. Read the delivery **diff only** (plus full file context for files in that diff). Do **not** read `~/.agents/prds/` or `~/.agents/plans/`. Do **not** preload unused stack files.

## Goal

Validate **and fix** the current solution delivery for syntax, semantics, and linter errors, then produce a commit message from the final delivery state.

This skill is not read-only. Find issues **and apply fixes** before reporting.

## Knowledge base (mandatory)

| Topic | Path |
|-------|------|
| Delivery scope (staged / unstaged / branch) | `~/.agents/kb/validation/Quality-gate-delivery-scope.md` |

Do not copy that procedure into this skill.

## Stack router (lazy-load)

Run detect + delivery scope first. Classify **delivery files**, not the whole repo. Load a stack file only when the delivery has matching files. Mixed deliveries load every matching file. Never preload unused stack files.

Repo `stacks` from `agentctl repo detect` are hints for typecheck commands and project-native tools. They do **not** load a stack file when the delivery has no matching files. Enonic apps often nest under `xp/` — classify from delivery paths even when detect missed `xp/src/main/resources/application.xml`.

| Load | When (delivery files) |
|------|------------------------|
| [references/python.md](references/python.md) | any `*.py` |
| [references/php.md](references/php.md) | any `*.php` or `*.phtml` |
| [references/enonic.md](references/enonic.md) | backend Enonic JS, XP/CMS `*.ts` under `xp/` or `src/main/resources/`, React4XP `*.tsx` / entries, or XP descriptors (`*.xml` / `*.yml` under those trees) |
| [references/generic.md](references/generic.md) | remaining source: JS/TS outside Enonic classes, JSON/YAML/CI, shell, markdown, other typed languages |

Skip generated/bundled assets, `node_modules`, `vendor/`, `.venv`, `__pycache__`, and build output in every stack.

## Workflow

1. **Identify delivery scope** — per KB; state tier.
2. **Inspect delivery diff** — changed hunks **and** full file context around edits.
3. **Route** — classify files; read only the matching stack files.
4. **Syntax & semantic validation** — shared checks below, then each loaded stack’s rules.
5. **Apply fixes** — blockers and safe issues in delivery scope (Fix policy).
6. **Re-validate** — until PASS or only unfixable blockers remain.
7. **Stack-specific compilers** — only what the loaded files require (ruff/`py_compile`, `php -l`, `tsc`, `node --check`).
8. **Linter** — `agentctl checks run --cwd <repo> --scope changed`, then `ReadLints` on touched sources. Extra CLIs named in the loaded stack files (`shfmt`, `lychee`, `xmlstarlet`, `ast-grep`, phpcs/phpstan) stay their own steps.
9. **Commit message** — from **final** delivery diff; print full suggestion.
10. **Commit offer** — ask to commit (Commit offer); commit only on a yes.

Do **not** push, merge, or create PRs.

## Syntax & semantic validation (mandatory)

For **every source file** in the delivery, check and **fix**:

| Check | What to do |
|-------|------------|
| **Unclosed brackets** | Balance `{}`, `[]`, `()`; fix mismatched or dangling braces from bad merges/edits. |
| **Missing semicolons / statement termination** | Fix where required by project style or where omission breaks ASI. |
| **Parse/syntax errors** | Language-appropriate checks from the loaded stack file. |
| **Undefined / missing symbols** | Confirm calls, imports, identifiers resolve; fix typos/missing imports. |
| **Unresolved imports/requires** | Verify paths and exported names. |
| **Dangling references** | After renames/removals, grep leftovers. |
| **Dead or orphaned fragments** | Remove leftover lines from partial refactors. |

Read the **whole file** when the diff touches control flow, functions, or braces.

## Fix policy

Apply fixes when they fix syntax/semantic **Blockers**, linter **errors** in delivery files, or stack-rule violations with a minimal local rewrite.

Do **not** change behavior beyond the fix, refactor outside the delivery, or expand feature scope.

Prefer the **smallest fix**. After each pass, re-read and re-validate.

## Linter checks

- `agentctl checks run --cwd <repo> --scope changed` **before** `ReadLints`: it batches ruff, `php -l`, shellcheck, markdownlint-cli2, xmllint, yq, and codespell over the changed files and returns compact pass/fail/skip per check. It does **not** cover `shfmt`, `lychee`, `xmlstarlet`, `ast-grep`, phpcs/phpstan, or TypeScript typecheck — keep those as their own steps when the loaded stack file names them. A check reported `unavailable` was **not run**; do not count it as a pass.
- `ReadLints` on all touched source files **after** fixes.
- Fix linter **errors** when clear and local; report warnings; fix warnings only when trivial and in changed code.

## Commit message generation

Use **final delivery diff** (after fixes). Print **### Commit message suggestion** (title + bullets), then follow Commit offer.

**Jira-task-id branch** (prepend prefix) — current branch matches:

```text
(?i)^[A-Z][A-Z0-9]+-\d+([._/-].+)?$
```

Examples that **do** prepend: `PROJ-123`, `PROJ-456-v2`, `PROJ-413/fix-icons`, `proj-1224`.
Examples that **do not**: `master`, `main`, `review`, `qa`, `staging`, `develop`, `feature/foo` (no issue key).

When the branch is a jira-task-id branch:

```text
[TASK-ID] Title of change

* Change 1
* Change 2
```

- `TASK-ID` = current git branch name in **uppercase** (e.g. `proj-456-v2` → `[PROJ-456-V2]`). Prefer the Jira key from the branch over inventing one.

When the branch is **not** a jira-task-id branch:

```text
Title of change

* Change 1
* Change 2
```

- Do **not** invent a prefix from `master` / `review` / etc.
- Title reflects **why** or **outcome**.
- Bullets summarize meaningful deltas (include validation fixes if part of this delivery).

## Commit offer

After the suggestion, ask whether to commit with it. Do not run `git commit` in the same turn.

On "COMMIT" (or an equivalent yes such as "commit it"):

1. Staged tier: commit the index as is. Unstaged tier: stage only the delivery files from `agentctl delivery scope`, then commit. Branch-diff tier: nothing to commit; say so.
2. Run `git commit -F <file>` with the suggested message verbatim, or the operator's edited version. No `Co-authored-by:` or tool trailer, no `--no-verify`, no `--amend`.
3. Report the new short SHA and title. Do not push, merge, or open a PR.

On anything else, stop. A hook failure is reported with its deciding error; do not retry with hooks skipped.

When ⛔ failures remain, add a ⚠️ line before the question naming them; still ask.

## Response template

The layout follows `response-formatting.mdc`: print the fence content as is, with no Markdown list syntax, and keep the blank line between items. The commit message block stays a plain indented block because it leaves the chat.

Print shared sections always. Print a stack section only when that stack file was loaded. Omit `[TASK-ID]` in the suggestion when the current branch is not a jira-task-id branch.

```markdown
**Delivery scope:** staged | unstaged | branch diff vs main/master

**Stacks loaded:** python | php | enonic | generic  (only those actually read)

### Fixes applied

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; <file>: <what changed and why>, or `None`

### Syntax & semantic validation

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <file>: PASS

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <file>: FAIL. <issue → remaining after fixes>

```

Then append each loaded stack’s report section from that file, then:

```markdown
### Linter

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <check>: passed

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <check>: <deciding error after fixes>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; <check>: skipped or unavailable (<reason>); unavailable is not a pass

### Commit message suggestion

    [TASK-ID] Title of change

    * Change 1
    * Change 2

&nbsp;&nbsp;&nbsp;&nbsp;❓&nbsp;&nbsp;&nbsp; Commit the <staged | unstaged delivery> changes with this message?

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;👉&nbsp;&nbsp;&nbsp; Reply "COMMIT" to commit, or send an edited message.
```

## Final reply: next step (always last)

After the commit lands, when the branch names a task, put this block right after the 👉 line, as the last thing in the reply, with `<TASK-ID>` expanded (Jira key or slug). The operator pastes it into a fresh session. Skip it when `called_from` is set or `AGENTCTL_FACTORY` is set.

```text
/plan-task-evidence <TASK-ID>
```
