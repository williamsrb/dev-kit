---
name: set-up-worktree
description: >-
  Create a sibling git worktree at REPO-NAME-multitask/SLUG on branch SLUG,
  based on the start checkout's current branch tip. Use when setting up a task
  worktree, adding a task-id branch folder (Jira key or other slug), or preparing multitask isolation.
  Use only when the operator or an orchestrator names this skill. | recommendedRole: follow | aliases: setup-worktree, create-worktree, add-worktree.
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
~/Workspace/Projects/<project>-multitask/PROJ-440        # branch PROJ-440
                                                        # base = PROJ-295 tip (never review)
```

## Inputs

| Input | Required | Meaning |
|-------|----------|---------|
| `SLUG` | yes | Branch name **and** worktree folder (Jira key or other slug) |
| Start dir | no | Defaults to cwd; defines which repo + which **current branch** is the base |

**Base = tip of the start checkout's current branch** (`git branch --show-current` → that ref's latest commit), unless `--base` is passed.

### Forbidden base: `review`

`review` / `origin/review` is a **testing/deploy** line. It may contain non-approved merges. It must **never** be the source of a task worktree or feature branch — not as default, not via `--base`, not by starting the script while the checkout is on `review`.

If the start checkout is detached or on `review`, the script exits non-zero. Check out the development branch you actually build from (e.g. `PROJ-295`), then retry.

Do **not** invent `--base origin/review` because CI deploys from `review`, or because an old DECISIONS note said so.

## Run

From the primary checkout (or any checkout of that repo **on the intended base branch**):

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
2. Resolve start directory: user-named path, else the **primary** project checkout (not an existing multitask worktree unless intentional).
3. Confirm start is on the intended development branch (`git -C <start> branch --show-current`) — not `review`, not detached.
4. Run the script above (one call; multiple slugs allowed). **Do not pass `--base origin/review`.**
5. Report: `main_repo`, `multitask_root`, each `path → branch`, and base branch name + SHA.
6. Confirm each new worktree is **on branch `SLUG`** (not detached). The script asserts this.
7. Do **not** set the new branch's upstream to `origin/review`. Leave upstream unset until the branch is pushed as `origin/<SLUG>`.

Do **not**:

- `git worktree add --detach`
- Full `cp -a` / clone-per-task
- Put the worktree *inside* `REPO-NAME/`
- Name the multitask folder anything other than `REPO-NAME-multitask`
- Use `review` / `origin/review` as `--base` or as the start checkout's current branch

## Behavior notes

- Creates `REPO-NAME-multitask/` if missing.
- If `…/SLUG` already exists on branch `SLUG`: skip (idempotent).
- If branch `SLUG` already exists: attach a worktree at that path to it.
- If branch is new: `git worktree add -b SLUG <path> <base>` where `<base>` is the start branch name (tip).
- Prefer this skill for single-slug setup. For a batch with an explicit multitask root override, `multitask-same-repo` still has `scripts/add_worktrees.py` (same forbidden-base rules).

## Related

- `multitask-same-repo` — parallel tasks on one repo (Phase 0 calls worktree setup)
- Workspace rule: task worktrees must stay attached to the task branch
- KB: `~/.agents/kb/implementation/How-to-choose-a-worktree-base-branch.md`
