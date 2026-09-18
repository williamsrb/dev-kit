# Authentication and companion files

## Phase 4 — Map authentication → wait/ask

For each auth-gated step, list the **realm** (app login, `/admin` / Content Studio, GitLab web,
external system like Tourplan). Mode is **User fills** via Playwright storage state + headless
capture.

### Find an existing storage-state file first

Before asking the user to log in, search for a Playwright storage-state JSON (must have top-level
`cookies` + `origins` arrays) and **read what each one authenticates**. Do not judge a
candidate by its filename, and do not guess a filename for a state you have not seen.

Run from a cwd that can see auth files (prefer searching `~/.agents/.auth` first). This is **not** permission to read implementation source. If cwd is a task worktree, still do not Grep `src/` / Gradle.

```bash
python3 ~/.agents/skills/plan-task-evidence/scripts/find-auth-storage.py --json --host <testing base URL>
```

**Read every candidate's contents. The filename is a guess, never a lock.**
The script opens each storage state and prints the cookie domains it actually carries,
ranked: host match first, then most-recently-updated. A state saved as `user.json`
routinely holds the only session for the environment under test.

- A candidate whose domains cover the testing base URL host **is** the auth for this run
  (`host-match` in the output). Use it and go straight to headless capture.
- Several host matches: take the **most recently updated** one - the ranking already puts
  it first (`recommended`).
- No host match: the ranking still lists every state, newest first. Read that list before
  concluding anything.

**Do not ask the operator for a login until every candidate has been read and none covers
the host.** Asking for codegen while a matching state sits in `~/.agents/.auth` is a
process failure, not a blocker. If a matching state exists but no longer authenticates, say
so with the path and the evidence (the step landed on the login page) before asking.

**Never write a storage-state path that does not exist on disk.** The plan's Authentication
map carries the path the finder returned. `~/.agents/.auth/<env>.json` is a placeholder for
a file the operator is about to create - do not resolve `<env>` yourself and then report the
invented filename as missing auth.

Locations searched (all of them, every run - ranking decides the pick, not search order):

1. `~/.agents/.auth/*.json`
2. `~/.agents/.playwright-mcp/*.json`
3. `~/.agents/.playwright-mcp/auth/*.json`
4. `./playwright/.auth/*.json`
5. `./.auth/*.json`
6. `./*.json` (cwd only; storage-state shape filter — ignores random JSON)

If **found:** put the absolute path in the plan Authentication map and mark status `ready`
(or `pending` if the env match is ambiguous — ask which file). Preferred default path when
creating new state: `~/.agents/.auth/<env>.json`.

If **not found:** do **not** spawn Playwright yet. At the hard stop (and in the plan map
status `pending`), **ask** the user to create state with visual codegen:

```bash
npx playwright codegen --save-storage="$HOME/.agents/.auth/<env>.json" "<login-or-app-url>"
```

Wait until they confirm the file exists (re-run `find-auth-storage.py` to verify). Then
the planning session spawns `playwright-<TASK-ID>` with `--storage-state` from that file
and hard-stops. Capture is `run-plan` in a new chat.

### Capture phase (after a storage-state path is known)

- **Planning:** spawn only. No navigate/screenshot.
- **`run-plan` (fresh session):** capture on `playwright-<TASK-ID>`. Storage-state
  should already be in the instance from spawn.
- Optional refresh if state is expired: ask the user to re-run the codegen command above,
  then re-spawn (that requires another new chat after spawn).

Record the auth map — realm, steps, mode, **storage-state path**, status — **in the plan
file**, then present it as part of the **hard stop** (after the file exists). Do **not**
start logging in or navigating for capture from this skill. Do not guess credentials.

Do not try to log in silently with stored passwords. Do not use the Cursor IDE embedded
browser as the login path unless the user overrides.

Do not try to log in silently with stored passwords. Do not use the Cursor IDE embedded
browser as the login path unless the user overrides.

---

## Companion files (for plan authors and later executors)

| File | Role |
|------|------|
| [templates.md](../templates.md) | Plan body + **Execution** block to inject; Jira evidence comment / ADF shapes (jira mode only) |
| [reference.md](../reference.md) | Data-toolbox lookups, timeouts, browser MCP, upload Phase A/B |
| [kb-format.md](../kb-format.md) | How-To template for testing-KB write-back during execution |

`plan-task-evidence` is the **primary** entry point for **planning** browser/CMS evidence.
The deliverable is `~/.agents/plans/<TASK-ID>/evidence.md` (legacy `*-evidence-plan.md` still resolves). Running that plan’s
Execution section is a separate step (`run-plan` or explicit user approval). Evidence
runs use Playwright (`playwright-<TASK-ID>`). The all-pass Jira post gate applies when `mode` is `jira`; skip it when `mode` is `local`.
