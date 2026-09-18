# Draft and evaluate

## Phase 2 — Draft the Evidence Creation Plan

**Mandatory:** write `~/.agents/plans/<TASK-ID>/evidence.md` from [templates.md](../templates.md), including **Execution**. Use **Write** or **StrReplace**. Create the folder with `agentctl plan init --kind evidence --issue <TASK-ID> --output ~/.agents/plans/<TASK-ID>` if missing. Do not keep the plan only in chat.

Copy the Execution block from the template into the plan file (fill `<TASK-ID>` /
paths). Do not omit it. If **Mode** is `local`, omit E2 and Atlassian upload from the
generated Execution (keep E1 capture + E3). If **Auth required** is yes, keep **Execution step 1 — Login**.
If no, delete that login step so capture starts without a login prompt. That section
is how a later `run-plan` (or approved execute) knows what to do; it is not run
during this skill.

State **Browser MCP: `playwright-<TASK-ID>`** in the plan header.

Each evidence step has: goal, URL, auth needed (y/n), timeout, expected result,
screenshot file name.

Every planned screenshot must have a **goal that states what it proves** (requirement / AC).
If a step would only produce an unlabeled image, rewrite or cut it — evidence without meaning
is not evidence. At execute time, Jira-bound shots are consistency-checked (element, zoom,
example page) before upload; storage-only shots need not be.

Every plan must include **Product concept** (template). Infer what a visitor or editor
should see (a form, a player, a widget). Live-step Expected result names that **paint**,
not only a script count or HTTP 200. “Backend only” does not make an empty integration
slot a pass. Execute-time diagnose path:
`~/.agents/kb/testing/_shared/How-to-gate-evidence-on-the-product-concept.md`.

### Deriving test URLs

- **Direct page**: combine the testing base URL with the path from the description/comments.
- **Enonic component usage** (find where a part/layout/page is used): use the Guillotine
  lookup, then build the page URL from the matched content path. Lookup recipes and the URL
  shape are in [reference.md](../reference.md). Example from a real task — open the XP 8
  Guillotine widget:
  ```
  <base>/admin/com.enonic.app.contentstudio/main#/english/widget/guillotine/guillotine
  ```

### Source-code evidence (GitLab)

For user-transparent changes, plan a screenshot of the relevant file/diff in GitLab on the
branch **review deploys** (project default / review branch after merge), e.g.
`https://<git-host>/<group>/<repo>/-/blob/<review-or-default-branch>/...`, where `<git-host>` is `git_host` in `~/.agents/config/client-overlay.json`.
Take the path from the impl plan, PRD, or MR text. Do **not** `Read` / `Grep` a local
`<TASK-ID>` worktree or implementation branch to draft that URL.
Note: **git CLI auth is usually fine** (ssh-agent),
but the **GitLab web UI needs a logged-in browser session** — **Auth required: yes**,
surface GitLab; flag it in the Authentication map (Phase 4).

---

## Phase 3 — Evaluate & adjust the plan

Apply every check, then **rewrite the plan file on disk** (not only in chat). Keep the
**Execution** section intact (update issue-specific paths if needed).

- **Honor testing tips** from description/comments. Some URLs fail on direct access (need a
  referer, a prior navigation, or a session) — a comment often says so. Do not silently ignore it.
- **Product concept is required.** Reject (rewrite) a plan that has no **Product concept**
  block, or whose live/integration Expected result treats an empty embed as a pass
  (“backend only”, “empty dummy is expected”). Live Expected result must name the paint.
  How-to: `~/.agents/kb/testing/_shared/How-to-gate-evidence-on-the-product-concept.md`.
- **Map auth-gated steps** — any path under `/admin`, `/minside`, `/min-side`, `/user`,
  `/profile` (and the data-toolbox) needs authentication → route to Phase 4.
- **Define acceptance criteria** — if the task has none explicit, write concrete pass/fail
  criteria for each evidence step.
- **Define timeouts** — page load, API request, task execution, and remote services each get a
  different budget (see [reference.md](../reference.md)).
- **Cut useless steps** — drop evidence that proves nothing for this change, and drop any
  screenshot that cannot be paired with a clear “what this proves” explanation.
- **Remove impossible steps** — anything that can't run from an agent (e.g. an account the
  agent can't reach). Note them as manual follow-ups. Screenshot upload is attempted during
  plan execution; do not treat it as impossible up front.

> WARNING — emit this when evidence spans more than one scope (e.g. a value set in the
> frontend that must appear in the backend, or a cookie crossing the boundary). State that it
> needs end-to-end verification, not a single-layer check, and name the layers involved.

### Reachability gate (mandatory — do not skip)

Before finalizing the plan file and moving to Phase 4, apply the following gate to
**every core evidence step** (steps that directly prove an acceptance criterion). A step
is **reachable** only when ALL of these are known or obtainable without user input at
execution time:

| Requirement | Examples of what is missing |
|-------------|-----------------------------|
| A concrete URL the agent can navigate to | feature hidden behind a search result, requires a specific record ID, or depends on post-deploy data that doesn't exist yet |
| Any required data to reach that URL | booking ref + last name, content ID, user account, specific CMS record |
| Auth realm is coverable (Execution step 1: find storage state or ask codegen `--save-storage`, then headless capture) | — |

**If any core step fails the gate:**

1. List every blocked step with the exact missing input (e.g. "booking ref + last name for a post-deploy booking with status `New`").
2. Use `AskQuestion` to ask the user for those inputs **before finalizing** the plan file
   or moving to the hard-stop.
3. **Do not** finalize an untestable skeleton as if it were ready to execute. If the user
   supplies the inputs, update the plan file with concrete URLs/data, then continue.
4. If the user cannot supply the missing inputs and the blocked steps cover all acceptance
   criteria, **still write** `~/.agents/plans/<TASK-ID>/evidence.md` (with Execution
   section) documenting the blocker and that execution cannot proceed, then hard-stop with
   that file as the deliverable: _"This task cannot be evidenced without [X]. Plan file records the gap."_

Only treat the plan as execution-ready when every core step has a reachable URL and all
blocking inputs are in hand — and that state is reflected in the plan file.

---
