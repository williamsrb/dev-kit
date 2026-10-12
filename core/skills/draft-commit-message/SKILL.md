---
name: draft-commit-message
description: "Draft a commit message from the current diff. No lint, no commit. Prefer lint-and-draft-* when validation is also needed | recommendedRole: follow | aliases: staged-commit-message, suggest-commit-message, commit-msg-from-diff."
metadata:
  recommendedRole: follow
  aliases: staged-commit-message, suggest-commit-message, commit-msg-from-diff
  cliDependencies:
    required: [agentctl, git]
    optional: []
---
## Local deterministic first

Run `agentctl delivery scope --cwd <repo> --json` first, then inspect only the reported delivery diff.

# Staged Commit Message

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md` when a TASK-ID prefix is needed. Read the delivery **diff only**. Do **not** read `~/.agents/prds/` or `~/.agents/plans/`.

## Goal

Produce a commit message from the **current solution delivery**. Do **not** validate, lint, fix code, or run git commit/merge.

For validation + commit message, use `lint-and-draft-commit-message` (python / PHP / Enonic / generic; detects from the delivery).

## Knowledge base (mandatory)

| Topic | Path |
|-------|------|
| Delivery scope | `~/.agents/kb/validation/Quality-gate-delivery-scope.md` |

## Workflow

1. **Identify delivery scope** — per KB; state tier.
2. **Inspect delivery diff** — enough context to name the *why*.
3. **Commit message** — print the full suggestion; stop. Do not ask to commit or merge.

## Commit message generation

**Jira-task-id branch** (prepend prefix) — current branch matches:

```text
(?i)^[A-Z][A-Z0-9]+-\d+([._/-].+)?$
```

Examples that **do** prepend: `RFD-123`, `AS-456-v2`, `PROJ-413/fix-icons`, `ntf-1224`.
Examples that **do not**: `master`, `main`, `review`, `qa`, `staging`, `develop`, `feature/foo` (no issue key).

When the branch is a jira-task-id branch:

```text
[BRANCH] Title of change
- Change 1
- Change 2
```

- `BRANCH` = current git branch name in **uppercase** (e.g. `as-456-v2` → `[AS-456-V2]`).

When the branch is **not** a jira-task-id branch:

```text
Title of change
- Change 1
- Change 2
```

- Do **not** invent a prefix from `master` / `review` / etc.
- Title reflects **why** or **outcome**.
- Bullets summarize meaningful delivery deltas (not every file rename).

## Response template

```markdown
**Delivery scope:** staged | unstaged | branch diff vs main/master

### Commit message suggestion

    [BRANCH] Title of change
    - Change 1
    - Change 2
```

Omit `[BRANCH]` in the suggestion when the current branch is not a jira-task-id branch.
