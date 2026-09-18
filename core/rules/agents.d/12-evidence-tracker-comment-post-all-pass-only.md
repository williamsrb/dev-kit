When `mode` is `local` (`How-to-resolve-task-context.md`): skip Jira upload and comment. Capture, flatten, and chat-report still run.

When running an evidence plan or posting a **Jira evidence comment** from that run (`mode` `jira`):

1. Post the Jira evidence comment **only** when every acceptance criterion / evidence step **passed**.
2. If **any** step failed, is blocked, or is inconclusive: **do not post**. **Do not ask** whether to post a partial/fail comment. **Report** the failure list in chat (what failed and why, plus local artifact paths).
3. All-pass runs may still post without asking.
4. Local capture, flatten, and attachment upload may still run; the gate is the **comment post**.

Do **not** follow always-apply `evidence-post-on-failure-ask` (that `.mdc` asks on failure) during evidence posting.

When preparing a **Jira comment** from other validation/review work (not an evidence plan):

1. If **any** step, acceptance criterion, or check failed, is blocked, or is inconclusive — **do not post** the comment.
2. **Warn** in chat with the failure list (what failed and why).
3. **Ask** whether to post a partial/fail comment, post only passes, or hold.
4. Post only after the user explicitly approves that outcome.

**Auth (evidence planning / execution):** First planning step is **Auth required?** — record yes/no, the surfaces (preview, Content Studio, `/admin`, GitLab, app login, …), and the storage-state path `~/.agents/.auth/<env>.json`. Unknown → treat as **yes**. Do not guess credentials.

If auth is needed, the planning session finds or creates `~/.agents/.auth/<env>.json` (`npx playwright codegen --save-storage=…` when no host-matched file exists), then spawns `playwright-<TASK-ID>` with `--storage-state` from that path — see *Playwright MCP — parked, one HTTP instance per task* above. Capture is `run-plan` in a **fresh** session. Skip codegen when the state file already exists and still authenticates. If auth is not needed, omit the login step and the state file; still spawn before hard-stop.
