When the user **explicitly orders** an amend (date-only rewrite, message fix, or including hook-touched files), run `git commit --amend` as asked — even if `HEAD` was not created by the agent in this conversation. This overrides the default "HEAD must be agent-created in this chat" gate.

Still required:

- Prefer `--no-edit` for date-only amends.
- Do **not** amend a commit already on the remote unless the user explicitly accepts a history rewrite (and any needed force-push); warn if it is pushed.
- Never approximate an amend with `git reset`.
- Never skip hooks unless the user explicitly requests it.
- Never add `Co-authored-by` / AI trailers.

Date-only amend:

```bash
GIT_COMMITTER_DATE="<datetime>" git commit --amend --no-edit --date "<datetime>"
```
