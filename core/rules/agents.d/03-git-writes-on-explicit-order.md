Do not stage, commit, amend, reset, push, or rewrite history unless the user explicitly asked for that write. Completing implementation is not an implicit commit. Local git **read** commands may run without asking.

When the user asked:

- Commit or stage: `git add` / `git restore --staged` for the paths of that request are allowed. Default otherwise: leave agent edits **unstaged**.
- Push / open the PR / publish the branch: remote-write is allowed. Warn before force-push to main/master.
- Reset: run the asked reset. Do not "clean up" a user's commit with reset on your own. Do not approximate an amend with `git reset`.

Vague ship-it language without a named target uses the Operator Gate.

When creating or managing a task worktree, keep it checked out on its task branch. Never create or leave a task worktree in detached `HEAD` state, including via `git worktree add --detach`, unless the user explicitly asks for a detached worktree.
