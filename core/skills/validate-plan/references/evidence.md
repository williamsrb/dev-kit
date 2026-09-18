# Evidence / test plan checks

Load only for `--kind evidence` targets (`agentctl plan resolve <TASK-ID> --kind evidence` → folder `evidence.md` or legacy `~/.agents/plans/<TASK-ID>-evidence-plan.md`).

Canonical template: `../../plan-task-evidence/templates.md`. Detail recipes live in that skill’s `reference.md` / `references/draft-and-evaluate.md`. Do not execute **Execution**. Do not open a capture browser or post to Jira.

## Must-have contract

Keep **Execution** intact (update issue-specific paths only).

Header fields: **Mode** (`jira` | `local`), TASK-ID, Jira URL when `jira` else `n/a`, testing base URL, change type, evidence folder, **Browser MCP: `playwright-<TASK-ID>`**, **Auth required** (yes/no/unknown→yes + surfaces), evidence sink, status `planned`.

Required H2 slugs for `agentctl plan validate --kind evidence` (add/rename; do not delete Execution):

| Slug | Typical heading |
|------|-----------------|
| `auth-required` | `## Auth Required?` |
| `acceptance-criteria` | `## Acceptance Criteria` |
| `evidence-steps` | `## Evidence Steps` (rename `## Steps` if that is the only steps table) |
| `artifacts` | `## Artifacts` (folder + screenshot names) |
| `posting-gate` | `## Posting Gate` — all-pass tracker comment when `jira`; skip post when `local` |

Also expect: authentication map, testing tips, sources, cut/impossible, scope warning.

## Evaluate (then rewrite the file)

From `plan-task-evidence` Phase 3:

- Honor testing tips from description/comments (referer, prior navigation, session). Cite comment ids when present.
- Auth-gated paths (`/admin`, `/minside`, `/min-side`, `/user`, `/profile`, data-toolbox, GitLab web UI) → Auth required yes + map row.
- Each evidence step: goal (what it **proves** toward an AC), URL, auth y/n, timeout, expected result, screenshot filename. Cut unlabeled shots.
- Timeouts: page / API / task / remote each get a budget (`plan-task-evidence/reference.md`).
- Drop steps that prove nothing for this change. Impossible agent steps → Cut / impossible + manual follow-up. Screenshot upload is not “impossible” up front.
- **WARNING** when evidence spans frontend↔backend (or another boundary). Name the layers. Otherwise: “Single scope — no cross-scope warning.”
- Browser MCP remains `playwright-<TASK-ID>`. Do not rewrite toward `cursor-ide-browser` / `user-browser-control` unless the user named that tool.
- Posting gate text: when `mode` is `jira`, post the Jira evidence comment **only** when every AC/step passed; on any fail/block/inconclusive do **not** post and do **not** ask to post a partial. When `mode` is `local`, skip the tracker comment; chat-report the local evidence folder. Local capture/flatten may still be in Execution.

## Reachability gate

Every **core** step (directly proves an AC) needs all of:

- A concrete URL the agent can navigate without a new product decision
- Any data to reach that URL (booking ref, content id, CMS record, …)
- Auth realm coverable (Execution login tier if Auth required, then headless from `~/.agents/.auth/<env>.json`)

If a core step fails:

1. List the exact missing input.
2. Ask the user for it **before** calling the plan execution-ready.
3. Still write the gap into the plan file. If the user cannot supply it and blocked steps cover all ACs: file is the deliverable — “cannot be evidenced without [X]”. Verdict **GO-WITH-FIXES** (documented blocker) or **NO-GO** if the file still pretends it is runnable.

Do not finalize an untestable skeleton as ready. Do not probe live URLs just to “see”; this skill is document QA.

## AC source

Prefer AC headings from `agentctl plan resolve <TASK-ID>` (implementation companions). Use sectioned PRD only when the impl plan lacks the criterion the evidence step claims to prove. Tick: every impl AC has a proving step, or is explicitly cut with reason.

## Realism and KB

Apply [realism-and-kb.md](realism-and-kb.md) **except** workspace / worktree `ls`/`rg`. For evidence, the shipped tree is the **review host** (user-given testing base), not an implementation branch or worktree. Back claims with: impl-plan/PRD AC, a testing How-to, an offline-reference page, or that review URL. Do not open `<TASK-ID>` worktrees to verify selectors or file paths.

- URLs stay on the user-given testing base host; example paths exist in the PRD/impl plan or a testing How-to.
- **Sources** cites `~/.agents/kb/testing/.../How-to-….md` and/or `~/.agents/kb/offline-reference/...` — or an explicit gap. Empty Sources plus invented click paths is **FAIL** on both extra validations.
- Guillotine / Data Toolbox / Content Studio steps must match a How-to or an offline-reference page, not folklore.

## Fix policy

- Rewrite the evidence plan on disk.
- Do not start Execution, login tiers, or tracker writes.
- Do not invent example page URLs on a different host than the user-given testing base.
- Do not store full screenshot sets or Jira comment prose in `kb/testing` from this skill.
