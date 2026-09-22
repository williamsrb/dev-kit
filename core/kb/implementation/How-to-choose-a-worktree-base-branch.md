---
id: how-to-choose-a-worktree-base-branch
when_skills: [set-up-worktree, multitask-same-repo, plan-implementation, run-plan]
read: section
prose: caveman-lite
---

# How to choose a worktree base branch

## Rule

Task worktrees / feature branches are created from the **primary checkout's current branch tip** (e.g. `PROJ-295`).

**Never** use `review` / `origin/review` as the base. `review` is a testing/deploy line and may contain non-approved merges.

## Procedure

1. On the primary clone: `git branch --show-current` must be the development branch you build from — not `review`, not detached.
2. Create the worktree with `set-up-worktree` (no `--base`), or `add_worktrees.py` without `--base`.
3. Scripts hard-reject `review` / `origin/review` and refuse to run when the start checkout is on `review` or detached.
4. Do not set the new branch's upstream to `origin/review`.

## Pitfall (PROJ-440, 2026-09-21)

A plan session created `PROJ-440` with `--base origin/review` because an old `DECISIONS.md` Batch 10 note said worktrees branched from `origin/review`. That is wrong. Correct base was the primary checkout's branch `PROJ-295`. Fixed in `set-up-worktree` / `add_worktrees.py` + DECISIONS correction.
