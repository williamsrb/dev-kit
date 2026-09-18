# Collect

## Phase 1 — Collect

0. **Resolve `<TASK-ID>`** via `How-to-resolve-task-context.md` from the user message (Jira key, Jira URL, or kebab slug; a matching branch name is only a hint). Note `mode` (`jira` or `local`). Do not invent a Jira key. Do not ask for full paths when convention files exist.
   **Shipped code = review.** The testing base URL already serves the merged delivery. Do **not** open `<TASK-ID>` implementation branches, multitask worktrees, or local `src/` / Gradle / `package.json` to discover what shipped, pick selectors, or confirm ACs. Resolve the id, then stay in PRD / impl-plan AC / testing KB / offline-reference / the review host.
1. **Acceptance criteria source (prefer plan).** Run `agentctl plan resolve <TASK-ID>` and read AC / requirements from the companions (`requirements.md` / `plan.md`, or the legacy file). Only open `~/.agents/prds/<TASK-ID>.md` via `agentctl markdown slice` for tips, URLs, or comment ids the plan lacks — not a full comments dump “just in case”.
2. **Offline task copy when needed.** If `~/.agents/prds/<TASK-ID>.md` exists, **that file is the task.** Use it. Do **not** hit Jira for this key during planning.
   Forbidden while the PRD exists (unless the user explicitly says refresh / re-download): `download-jira-task`, `agentctl jira fetch`, `getJiraIssue` on `<TASK-ID>`, and any JQL whose only job is to look up `<TASK-ID>`.
   - Missing + `mode` `jira` — nested `download-jira-task` **once** (`called_from: plan-task-evidence`; keeps comment IDs), then stay on the file.
   - Missing + `mode` `local` — do **not** call `download-jira-task`. Prefer impl-plan AC. Nested `handoff` (PRD) only if a PRD is still required. Evidence may proceed from the impl plan alone.
   Worked failure: PROJ-434 evidence planning (2026-09-15) still called Jira after `~/.agents/prds/PROJ-434.md` already existed.
3. **Testing KB scan (mandatory).** Before drafting URLs or flows:
   - Open `~/.agents/kb/testing/llm-index.md` (chooser). If a folder row matches the project (`<project>/`) or topic (`_shared/` for Content Studio, Guillotine, Jira evidence), open that folder’s `llm-index.md`. Then open only matching How-tos.
   - For part evidence, open `<project>/How-to-create-persistent-part-evidence-content-on-review.md`; it names where that project's evidence pages live.
   - Open only files that match this run (booking, CMS edit, Guillotine, payment). Do not load sibling project How-tos or the whole testing tree.
   - **Reuse instrumentation verbatim** — do not rediscover selectors or Content Studio click paths the KB already documents.
   - Note in the evidence plan which KB file(s) were used (or **gaps** for KB write-back during later execution).
4. **Offline reference scan (when relevant).** After the testing KB scan, consult
   `~/.agents/kb/offline-reference` whenever evidence steps will use Enonic CMS UI or
   platform semantics — especially **creating, editing, publishing, or configuring content
   in Content Studio**, page editor / rich text / permissions / layers / issues, XP lib
   behavior, or React4XP edit-mode expectations. Prefer offline docs over live web fetches.
   1. Open `~/.agents/kb/offline-reference/README.md` and pick the **best-fit catalog(s)**
      (see table below).
   2. Read that catalog’s `llm-index.md`. If it is a chooser (rows ending in
      `llm-index.md`), open the matching subtree index. Match topic/keywords to
      the evidence need (e.g. `publish`, `page editor`, `new`, `content form`, `layers`).
   3. Open only the matching page file(s); use them to draft CMS steps, expected UI labels,
      and auth/reachability notes. Cite paths in the plan **Sources** section.
   4. Skip this step only when the evidence plan is clearly unrelated (e.g. pure GitLab
      source screenshot, non-Enonic app login only).

   | Evidence need | Catalog | LLM index |
   |---------------|---------|-----------|
   | Content Studio UI on **XP 8** / CS 6.x | `content-studio-stable/` | `…/content-studio-stable/llm-index.md` |
   | Content Studio UI on **XP 7** / CS 5.x | `content-studio-5.x/` | `…/content-studio-5.x/llm-index.md` |
   | XP **7** APIs / framework (verify server behavior) | `xp7/` | `…/xp7/llm-index.md` |
   | XP **8** platform / CMS / code | `xp8/` | `…/xp8/llm-index.md` |
   | React4XP **5.x** (XP 7, legacy maintenance) | `react4xp-5.x/` | `…/react4xp-5.x/llm-index.md` |
   | React4XP **6.x** (XP 7, new React4XP work) | `react4xp-6.x/` | `…/react4xp-6.x/llm-index.md` |
   | React4XP **stable / 7.x** (XP 8 default) | `react4xp-stable/` | `…/react4xp-stable/llm-index.md` |

   **Version hints:** Infer from the review host’s stack, the testing KB, or the impl plan — not from checking out the task worktree. XP 8 → Content Studio **stable** + React4XP **stable (7.x)** + `xp8`.
   XP 7 new React4XP → Content Studio **5.x** + React4XP **6.x** + `xp7`. XP 7 legacy 5.x
   apps → React4XP **5.x** maintenance only. If unclear and the task only needs Content
   Studio clicks, default to **stable** unless the project is known XP 7.
   When both a testing How-To and an offline page apply, **How-To wins for selectors/URLs**;
   offline docs win for product semantics (what Publish does, when Page editor appears, etc.).
5. **Related tasks.** Local first, even when `mode` is `jira`. Grep `~/.agents/plans`,
   `~/.agents/prds`, and the testing KB for the same component/feature. Reuse any
   **component lookup query** found verbatim (see Phase 2).
   - Do **not** default to `searchJiraIssuesUsingJql`. Context budget: siblings are
     out of the evidence-planning allowlist.
   - `mode` `jira` **and** the impl plan/PRD **names** a sibling key **and** that
     sibling has no local PRD **and** a test URL / lookup is still missing: one
     Jira read of **that named key only**. Never `getJiraIssue(<TASK-ID>)` when
     this task’s PRD exists.
   - `mode` `local`: never invent a Jira search.
6. **Identify the change type** — it decides what evidence is needed:
   - **User-visible** (UI, copy, behavior) → app page screenshots.
   - **User-transparent** (removed comments, formatting, changed hard-coded value, refactor)
     → **GitLab source screenshots** are usually required (diff is the evidence).
7. **Optional — Impeccable (design / frontend UI only).** **Skip by default.** Only when the issue is clearly about **design or frontend presentation** (layout, styling, visual QA of a surface, UX polish) — not for backend, API, schema, or non-UI verification. When it applies, plan **review-env** screenshots that prove the visual/a11y AC. Do **not** run `impeccable detect` on local worktree paths. Do not add Impeccable steps for every UI ticket, invent redesign scope, or treat detect findings as required acceptance criteria unless the task already demands them.

---

## First planning step — Auth required?

Do this **before** deriving test URLs or screenshot steps (after Phase 1 sources: PRD, impl plan, comments, testing KB, project docs).

Decide whether the example pages / test URLs need login (CMS admin, preview, SSO, env cookie, Content Studio, `/admin`, GitLab web, `/minside`, etc.).

Record in the plan header:

- **Auth required:** `yes` | `no`
- **Surfaces:** preview, Content Studio, `/admin`, GitLab, app login, … (or `none`)

If unknown: **Auth required: yes** (safer default). Record it as unknown-treated-as-required. Do not guess credentials; ask via the plan (Execution step 1).

If **yes**: during planning, run
`python3 ~/.agents/skills/plan-task-evidence/scripts/find-auth-storage.py --json --host <testing base URL>`
against a cwd that can see auth files (prefer `~/.agents/.auth`). Do not treat that cwd as a source tree to inspect. Locations searched: `~/.agents/.auth/*.json`,
`~/.agents/.playwright-mcp/*.json`, `~/.agents/.playwright-mcp/auth/*.json`,
`./playwright/.auth/*.json`, `./.auth/*.json`, `./*.json` (storage-state shape only).
The script reads every candidate and ranks by cookie domain, then recency — **the filename
is a guess, never a lock**. Record the chosen absolute path in the Authentication map
(`ready`). Only when no candidate carries cookies for the host: status `pending`, and
**ask** the user to run
`npx playwright codegen --save-storage="$HOME/.agents/.auth/<env>.json" "<login-url>"`
(do not invent credentials). Generated Execution **step 1** re-checks that search; if still
missing, stop and ask for the same codegen command before any capture. Every capture step
afterwards runs on spawned `playwright-<TASK-ID>` with `--storage-state` (or `browser_set_storage_state`) from that
file. If **no**: omit that login step and the state file (do not prompt).

---
