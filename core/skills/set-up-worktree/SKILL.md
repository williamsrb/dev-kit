---
name: set-up-worktree
description: >-
  Create a sibling git worktree at REPO-NAME-multitask/SLUG on branch SLUG,
  based on the current checkout's latest commit. Use when setting up a task
  worktree, adding a task-id branch folder (Jira key or other slug), or preparing multitask isolation.
  | recommendedRole: follow | aliases: setup-worktree, create-worktree, add-worktree.
disable-model-invocation: true
metadata:
  recommendedRole: follow
  aliases: setup-worktree, create-worktree, add-worktree
  cliDependencies:
    required: [python3, git]
    optional: []
---

# Set up worktree

Create one (or more) **attached** git worktrees using the sibling multitask layout.

## Layout

For a repo named `REPO-NAME` (placeholders, not literals):

```text
<parent>/REPO-NAME                    # original clone / primary checkout
<parent>/REPO-NAME-multitask/SLUG     # worktree → branch SLUG
```

`REPO-NAME` and `REPO-NAME-multitask` are siblings under the same parent folder.

Live example:

```text
~/Workspace/Projects/<project>                          # branch PROJ-295
~/Workspace/Projects/<project>-multitask/PROJ-365        # branch PROJ-365
                                                        # base = PROJ-295 @ HEAD
```

## Inputs

| Input | Required | Meaning |
|-------|----------|---------|
| `SLUG` | yes | Branch name **and** worktree folder (Jira key or other slug) |
| Start dir | no | Defaults to cwd; defines which repo + which HEAD is the base |

Base ref = **current branch at latest commit** of the start directory (`HEAD` SHA), unless `--base` is passed.

## Run

From the primary checkout (or any checkout of that repo):

```bash
python3 ~/.agents/skills/set-up-worktree/scripts/set_up_worktree.py <SLUG> [<SLUG>...]
```

Useful flags:

```bash
# Explicit start dir (when cwd is not the repo)
python3 ~/.agents/skills/set-up-worktree/scripts/set_up_worktree.py --start ~/Workspace/Projects/<project> PROJ-365

# Machine-readable summary
python3 ~/.agents/skills/set-up-worktree/scripts/set_up_worktree.py --json PROJ-365
```

## Agent steps

1. Resolve `SLUG` from the user (Jira key or other slug). Ask if missing.
2. Resolve start directory: user-named path, else the active project/repo cwd.
3. Run the script above (one call; multiple slugs allowed).
4. Report: `main_repo`, `multitask_root`, each `path → branch`, and base SHA/ref.
5. Confirm each new worktree is **on branch `SLUG`** (not detached). The script asserts this.

Do **not**:

- `git worktree add --detach`
- Full `cp -a` / clone-per-task
- Put the worktree *inside* `REPO-NAME/`
- Name the multitask folder anything other than `REPO-NAME-multitask`

## Behavior notes

- Creates `REPO-NAME-multitask/` if missing.
- If `…/SLUG` already exists on branch `SLUG`: skip (idempotent).
- If branch `SLUG` already exists: attach a worktree at that path to it.
- If branch is new: `git worktree add -b SLUG <path> <base>`.
- Prefer this skill for single-slug setup. For a batch with an explicit multitask root override, `multitask-same-repo` still has `scripts/add_worktrees.py`.

## Related

- `multitask-same-repo` — parallel tasks on one repo (Phase 0 calls worktree setup)
- Workspace rule: task worktrees must stay attached to the task branch
