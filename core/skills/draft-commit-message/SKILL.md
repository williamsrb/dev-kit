---
name: draft-commit-message
description: "Draft a commit message from the current diff. Use when the user says \"commit\" (or \"commit this\") without asking for lint. No lint; asks before committing. When the request also says lint (\"lint and commit\"), use lint-and-draft-commit-message instead"
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

Produce a commit message from the **current solution delivery**, then offer to commit with it. Do **not** validate, lint, fix code, merge, or push.

For validation + commit message, use `lint-and-draft-commit-message` (python / PHP / Enonic / generic; detects from the delivery).

## Knowledge base (mandatory)

| Topic | Path |
|-------|------|
| Delivery scope | `~/.agents/kb/validation/Quality-gate-delivery-scope.md` |

## Workflow

1. **Identify delivery scope** — per KB; state tier.
2. **Inspect delivery diff** — enough context to name the *why*.
3. **Commit message** — print the full suggestion.
4. **Commit offer** — ask to commit (Commit offer); commit only on a yes.

## Commit message generation

**Jira-task-id branch** (prepend prefix) — current branch matches:

```text
(?i)^[A-Z][A-Z0-9]+-\d+([._/-].+)?$
```

Examples that **do** prepend: `PROJ-123`, `PROJ-456-v2`, `PROJ-413/fix-icons`, `proj-1224`.
Examples that **do not**: `master`, `main`, `review`, `qa`, `staging`, `develop`, `feature/foo` (no issue key).

When the branch is a jira-task-id branch:

```text
[BRANCH] Title of change

- Change 1
- Change 2
```

- `BRANCH` = current git branch name in **uppercase** (e.g. `proj-456-v2` → `[PROJ-456-V2]`).

When the branch is **not** a jira-task-id branch:

```text
Title of change

- Change 1
- Change 2
```

- Do **not** invent a prefix from `master` / `review` / etc.
- Title reflects **why** or **outcome**.
- Bullets summarize meaningful delivery deltas (not every file rename).

## Commit offer

After the suggestion, ask whether to commit with it. Do not run `git commit` in the same turn.

On "COMMIT" (or an equivalent yes such as "commit it"):

1. Staged tier: commit the index as is. Unstaged tier: stage only the delivery files from `agentctl delivery scope`, then commit. Branch-diff tier: nothing to commit; say so.
2. Run `git commit -F <file>` with the suggested message verbatim, or the operator's edited version. No `Co-authored-by:` or tool trailer, no `--no-verify`, no `--amend`.
3. Report the new short SHA and title. Do not push, merge, or open a PR.

On anything else, stop. A hook failure is reported with its deciding error; do not retry with hooks skipped.

## Response template

```markdown
**Delivery scope:** staged | unstaged | branch diff vs main/master

### Commit message suggestion

    [BRANCH] Title of change

    - Change 1
    - Change 2

&nbsp;&nbsp;&nbsp;&nbsp;❓&nbsp;&nbsp;&nbsp; Commit the <staged | unstaged delivery> changes with this message?

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;👉&nbsp;&nbsp;&nbsp; Reply "COMMIT" to commit, or send an edited message.
```

Omit `[BRANCH]` in the suggestion when the current branch is not a jira-task-id branch.
