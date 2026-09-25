---
name: plan-task-evidence
description: "Write ~/.agents/plans/<TASK-ID>/evidence.md from a PRD or impl plan (Jira key or local slug). Legacy ~/.agents/plans/<TASK-ID>-evidence-plan.md still resolves. Planning only — does not capture or post. Jira comment is an optional sink when mode is jira. | recommendedRole: implement | aliases: task-evidence-plan, evidence-plan, jira-evidence, evidence-creation-plan."
disable-model-invocation: true
metadata:
  recommendedRole: implement
  aliases: task-evidence-plan, evidence-plan, jira-evidence, evidence-creation-plan
  cliDependencies:
    required: [agentctl, rg, identify, mogrify]
    optional: [ollama, tesseract]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Use `agentctl task resolve`, `agentctl markdown slice`, `agentctl plan resolve`, and `agentctl plan init --kind evidence --output ~/.agents/plans/<TASK-ID>` for mechanical work. When replanning a task that was already captured once, run `agentctl plan progress <TASK-ID> --kind evidence` first: it reports which planned shots already exist under `~/.agents/prds/<TASK-ID>/evidence/`, so the plan can carry them forward instead of scheduling a retake of work that is already on disk. Create screenshot sidecars with `agentctl evidence manifest`. Before model inspection (and before any Jira upload when `mode` is `jira`), run local image gates: `agentctl image whitespace` (blank/zoom) and `agentctl evidence inspect --ocr --expected-text …` (labels), then `agentctl image stamp` and `agentctl image stamp --check` (pixel-size overlay). After a Jira post, run `verify-jira-comment-images.py`. OCR, whitespace, and markup lint are not proof the comment is done. A heading in OCR is not proof the **product concept** painted (override 13). See overrides 10–13 and 15, `~/.agents/kb/testing/_shared/How-to-gate-evidence-on-the-product-concept.md`, `~/.agents/kb/testing/_shared/How-to-check-evidence-screenshots-before-jira.md`, and `~/.agents/kb/testing/_shared/How-to-post-jira-evidence-comments.md`. Skip Jira How-tos, upload, and verify scripts when `mode` is `local`.

# Task Evidence Plan

**Ultimate goal:** create (or update) the Evidence Creation Plan at
`~/.agents/plans/<TASK-ID>/evidence.md` (legacy `~/.agents/plans/<TASK-ID>-evidence-plan.md` still resolves). That file is the success criterion
for this skill. Chat summaries are secondary; **never** hard-stop or claim
planning is done without that file on disk.

`<TASK-ID>` is a Jira key **or** a kebab slug (`How-to-resolve-task-context.md`). Note `mode` (`jira` or `local`). Do not invent a Jira key. Jira upload/comment is a **sink**, not a planning requirement.

**This skill plans only.** It collects context, writes/refines the plan file
(including an **Execution** section for later use), maps auth, **spawns**
`playwright-<TASK-ID>` so a later `run-plan` session can connect, then stops.
It does **not** navigate, take screenshots, upload to a tracker, post comments,
or write testing-KB How-Tos. Those steps live **inside the generated plan file**;
run them later via `run-plan` in a **fresh** session by following that file’s Execution section.

Do **not** call SwitchMode or ask to switch to Plan mode. Write the plan file in the current mode, then hard-stop.

## Skill overrides (evidence planning + spawned execution)

These apply to plans this skill writes and to **evidence execution** of those plans (including `run-plan` on an evidence plan). They do not change other work.

**Mode gate.** Overrides 1–12, 15 and 16 (Jira comment, ADF, figure sizing, backup, upload, `verify-jira-comment-images.py`, problem-found comment) apply only when `mode` is `jira`. When `mode` is `local`: capture to `~/.agents/prds/<TASK-ID>/evidence`, run local image gates, apply override 13, report in chat (including the problem-found text of override 16, if any), skip Atlassian tools and E2. Overrides 13–14 always apply.

1. **Jira comment post — all-pass only.** Post the Jira evidence comment **only** when every acceptance criterion / evidence step **passed**. If **any** step failed, is blocked, or is inconclusive: **do not post**. **Do not ask** whether to post a partial/fail comment. Report results in chat (pass/fail list, why, local artifact paths). All-pass may still post without asking. Local capture, flatten, and attachment upload may still happen; the gate is the Jira comment post. This is **stricter** than always-apply `evidence-post-on-failure-ask` (that rule asks on failure). **Do not follow the ask-on-failure rule** during evidence posting for this skill.
2. **Jira comment format — hard gate.** Before any Jira write tool runs, read
   [templates.md](templates.md) § "Jira evidence comment" **in that session**, write the
   body to a file, and run
   `python3 scripts/check-evidence-comment.py <file>` (path relative to this skill dir).
   Exit 1 means do not post. One call posts the comment with every image embedded
   inline under its own explanation — never a standalone-attachment pass followed by a
   text-only comment, and never a pass/fail matrix in place of analyst prose. Post via
   `atlassian-rovo-preview` (`addOrEditJiraIssueComment`) or `addCommentToJiraIssue`;
   **never** the Atlas PM-assistant MCP.
3. **Browser MCP = Playwright.** Planning **spawns** `playwright-<TASK-ID>` (`python3 ~/.agents/mcp/playwright.py spawn <TASK-ID> --enable [--storage-state <path>]`) after the auth map is ready (or Auth required is no). That process stays up. Capture is a **fresh** `run-plan` session that uses `playwright-<TASK-ID>` / `user-playwright-<TASK-ID>` / `mcp__playwright-<TASK-ID>__*`. Do **not** capture in the planning chat. Do **not** open `cursor-ide-browser` or `user-browser-control` first unless the user names a different tool. Generated plans must state the browser MCP is `playwright-<TASK-ID>`. Spawn-only after a reboot or outside this skill: `spawn-playwright-mcp`. See `How-to-enable-playwright-mcp.md`.
4. **Evidence CMS content is persistent.** Display name is the component title. Copy and images come from the prototype. No ticket key in names. Reuse the existing page. Do **not** create throwaway evidence pages (`DELETE-ME`, `delete-me-*`, ticket-keyed paths) and do **not** write KB files under a `disposable-content/` folder. Jira comments follow override 8 — persistent pages are not permission to overwrite an old evidence comment. The evidence path and the site it lives on are project-bound: take them from that project's `~/.agents/kb/testing/<project>/How-to-create-persistent-part-evidence-content-on-review.md`, never from another project's. This repo's `AGENTS.md` § "Creating Jira evidence — persistent content, not disposable pages".
5. **Evidence comments do not ask questions.** The E2 Jira body is verification only: what shipped, where to look, which ACs it meets. Do **not** put TBD, a/b/c option lists, “my recommendation”, or “without an answer we get …” in that comment, in the evidence plan’s “carry into the Jira comment” section, or in Additional details. Known limitations may be stated as facts (what the page does, how to reproduce on the review URL). Open decisions go to chat or a **separate** TBD/question comment — never piggybacked on the evidence post. `check-evidence-comment.py` fails the body if it looks like a question. This **overrides** always-apply “every question carries 2-3 options” for evidence posts: that rule applies when the comment’s purpose *is* a question, not when the purpose is evidence.
6. **Stamp PNG pixel size before upload.** This is the always-apply Jira screenshot rule (`jira-screenshot-consistency.mdc`), not evidence-only. After capture and the local image gate, run `agentctl image stamp <png> […]` then `agentctl image stamp --check <png> […]`. Exit 1 = do not upload. Pass **file paths** (a directory only auto-stamps `NN-*.png`). Do **not** run raw `mogrify … *.png`. Equivalent: `python3 ~/.agents/skills/plan-task-evidence/scripts/annotate-evidence-resolution.py`. Do not mention the stamp in the Jira comment.
7. **Evidence links are the pages under test, not the env root.** **Deployed testing environment** names the live URL that was captured (full path) and, when Content Studio was in the run, the CS edit URL labelled Admin. Never the testing base URL with no path. Shape: `<base>/test/evidence/featured-cards ([Admin](<base>/admin/com.enonic.app.contentstudio/main/english/edit/<content-id>))`. CS-only evidence may omit live; live-only may omit Admin. `check-evidence-comment.py` fails a host-only environment URL, using the host patterns in `~/.agents/config/client-overlay.json`.
8. **Never edit a Jira comment from another day unless the user strictly asked to.** Compare the comment’s **`created`** calendar date (not `updated`) to **today**. If they differ, do **not** pass `commentId` — post a **new** comment. Same-day re-runs may edit today’s evidence comment in place. A plan, KB How-to, or prior run that records an old comment id is **not** permission. “Post it” / “post the evidence” is **not** an order to edit an older comment. Strict ask means the user named that comment (id, or its date) and said to edit it. This **overrides** “edit the existing Jira comment in place” in always-apply rules, KB How-tos, and generated plans.
9. **Backup before every Jira comment edit.** Jira cannot revert a comment overwrite. Before any `addOrEditJiraIssueComment` (or equivalent) **with** `commentId`: fetch that comment as HTML, write it with `python3 ~/.agents/skills/plan-task-evidence/scripts/backup-jira-comment.py --issue <KEY> --comment-id <ID> --body-file <html>`, and **do not edit** unless the script exits 0. New comments (no `commentId`) skip this. Report the backup path in chat only — never in the Jira body.
10. **Local image gate before flatten/upload/post.** OCR of a few labels is not enough. For every Jira-bound PNG, in this session, run local tools and **read the image** (preview if the long edge is over 1280). Fail and retake — do not flatten, upload, or post — on any of:
    - **Whitespace / zoom:** `agentctl image whitespace <png> --background auto --grid 3`. A full-viewport overlay (text in one corner, rest white) fails: `blank_percent` ≥ 85 **and** the longest edge ≥ 1200 **and** `border_blank_percent` is low only because a 1px rule or stamp exists, **or** the 3×3 grid has ≥ 6 cells at blank ≥ 0.95. Clip overlays to the overlay element; never screenshot a 1440×900 white page with a few lines of text.
    - **Expected text:** `agentctl evidence inspect <png> --ocr --expected-text '<token from the step>'` (or `tesseract-cli` `ocr.py`). Missing planned labels / URL slug / field names → retake.
    - **Element + example page:** the Read of the PNG must show the step’s target and the planned URL/content. Wrong panel, sibling, or env is a fail.
    Common errors and the exact commands: `~/.agents/kb/testing/_shared/How-to-check-evidence-screenshots-before-jira.md`. Do not send the image to a vendor vision model for OCR or for this gate.
11. **Media must resolve on the issue before you claim the post is done.** `check-evidence-comment.py` only lints markup. HTML `data-id` nodes can sit in a comment with empty boxes.
    - Every `fileId` in the body must come from `uploadCommand` **in this session**. Do not copy `data-id` from an older comment, a deleted comment, or a previous run.
    - Replacing a comment, or deleting one that held the media: re-upload **every** PNG. Deleting a comment drops its attachments; reused ids become missing images.
    - After post, and again after any delete of a related comment, run
      `python3 ~/.agents/skills/plan-task-evidence/scripts/verify-jira-comment-images.py --issue <KEY> --comment-id <ID>`
      Exit 1 = the comment is not done. Re-upload the missing files, edit the same-day comment, re-run until 0. Do not report success while this fails.
12. **One evidence comment per issue per run.** A retried create posts the same body twice, and a replacement that reuses `fileId`s from a deleted comment loses its images; `check-evidence-comment.py` passes both.
    - Call `addOrEditJiraIssueComment` **once** per issue unless you pass `commentId` (same-day edit). Do not retry a successful create.
    - Immediately after a create, list comments. Two same-body evidence comments → delete the extra before anything else.
    - Replace trash comments in this order only: re-upload **every** PNG this session → post or edit with those new ids → `verify-jira-comment-images.py` exit 0 → delete the trash comments → run the verify script again. Do not delete first. Do not copy `data-id` from the trash comment.
    Full order and commands: `~/.agents/kb/testing/_shared/How-to-post-jira-evidence-comments.md`.
13. **Product concept before pass.** Name what a visitor or editor should see or do (the
    integration, not the AC number). Live/integration steps must show that **paint**
    (form fields, player, widget — not a heading over an empty slot). If paint is
    missing: read console (CSP / refused scripts), failed requests, and fixture IDs;
    propose the smallest fix; **report to the operator**; do **not** mark the step
    pass and do **not** post. “Backend only” / “empty dummy is expected” in a plan or
    How-to does **not** waive this unless the operator excluded paint **in this
    session**. Full procedure:
    `~/.agents/kb/testing/_shared/How-to-gate-evidence-on-the-product-concept.md`.
14. **Existing PRD is the task copy (planning).** If `~/.agents/prds/<TASK-ID>.md`
    exists, do **not** fetch that issue from Jira during planning. No
    `download-jira-task`, no `agentctl jira fetch`, no `getJiraIssue(<TASK-ID>)`,
    no JQL whose only job is this key. Related-task Jira search is **not** a
    default — local PRDs / plans / testing KB first. Refresh the PRD only when
    the user explicitly asks. This override applies in both `jira` and `local`
    mode.
15. **Figure sizing matches the Jira editor (PROJ-435).** Evidence screenshots use PNG pixel size, not 60% of the comment column. After stamp, `identify` the flattened PNG. Author `data-width-type="pixel"`, figure `data-width` = PNG width, inner media `data-width`/`data-height` = PNG width/height. `data-layout="wide"` when width ≥ 1200 (desktop 1440 captures); `center` for tight clips. `data-width="60"` `data-width-type="percentage"` with no inner height letterboxes a wide shot (empty band around a small image). `check-evidence-comment.py` fails that pattern. Ground truth: PROJ-435 comment 531480 after the 2026-09-15 UI save. If two screenshots are stacked into one PNG, mark the merge in the image (banner, black bar, a short label per part).
16. **Problem-found comment after the evidence post (E2b).** When the run hit a problem the analyst would otherwise never see, post a short **second** comment after the evidence comment. Examples: a blocker that had to be cleared, a root cause different from the planned one, an environment or content-publishing gap, or fixtures rebuilt because the plan's approach was impossible. The evidence body says what shipped. This comment says what was wrong and what that means for the analyst. Shape: [templates.md](templates.md) § "Problem-found comment". It has three bold-labelled parts (**What we found**, **What we did** or **What we will fix**, **What this means for you**), in product language, a few short paragraphs, no screenshots, no local paths, no questions, no praise. Draft with `write-analyst-message`. Post it only after the evidence comment is posted and `verify-jira-comment-images.py` exits 0, and post it once. When nothing unexpected happened, skip it; do not invent a problem to fill the slot. When the evidence post is blocked by override 1, do not post this either: put the draft in the chat report so the operator can decide. An open decision is still a separate TBD comment with options, not part of this one. Reference: PROJ-440 comment 533195, PROJ-443 comment 533625.

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md`. Prefer AC from `agentctl plan resolve <TASK-ID>` (implementation companions); use `agentctl markdown slice` on the PRD only for tips/URLs/comment ids when the impl plan lacks them. Do **not** re-read full impl narrative or full PRD comments “just in case”. Do **not** inspect implementation worktrees, `<TASK-ID>` branches, or local source trees — the testing base URL already serves the merged review delivery. Existing `~/.agents/prds/<TASK-ID>.md`: do **not** call `download-jira-task`, `agentctl jira fetch`, or `getJiraIssue` for that key (override 14). Validate-evidence mode: `agentctl plan resolve <TASK-ID> --kind evidence` + the AC source used in the draft — not the full impl plan / full PRD / worktree source. Missing PRD + `mode` local: continue from the impl plan; do not call `download-jira-task`.

### Cursor IDE

**Always** persist the plan with **Write** / **StrReplace** to
`~/.agents/plans/<TASK-ID>/evidence.md` (create the folder with `agentctl plan init --kind evidence --issue <TASK-ID> --output ~/.agents/plans/<TASK-ID>` if needed). Planning must not open browsers or post to a tracker. Legacy `*-evidence-plan.md` may be updated in place when that is the resolved entry.

## Two doc sources (do not mix roles)

| Source | Path | Role | Write back? |
|--------|------|------|-------------|
| **Testing KB** | `~/.agents/kb/testing` | Project/site **instrumentation** — click paths, selectors, auth tips, Guillotine/Data Toolbox queries | **Yes** (during plan *execution*, not this skill) |
| **Offline reference** | `~/.agents/kb/offline-reference` | Official **LLM-dense** product/API docs (Content Studio, XP, React4XP, …) | **No** — refresh via sync scripts only |

Prefer testing How-Tos for *how we automate this site*. Prefer offline-reference when the
flow depends on *how Content Studio / XP / React4XP actually works* (create content, publish
wizard, layers, page editor, rich text, permissions, lib APIs) and the How-To is missing or
thin. Catalog index: `~/.agents/kb/offline-reference/README.md`.

## Knowledge base — purpose and self-feed loop

The KB at `~/.agents/kb/testing` is **not** an evidence dump. It stores **how to perform
tasks** (instrumentation): UI steps, selectors, CMS navigation, auth realms, URL
patterns, and Guillotine/Data Toolbox queries — so agents can run tests **by themselves** on
the next issue.

| Store in KB | Do **not** store in KB |
|-------------|------------------------|
| Repeatable procedure (ordered steps) | Full screenshot sets, Jira comment text |
| Stable selectors, field names, save/publish sequence | Large booking dumps, email bodies, audit tables |
| Minimal **sample data** (one example email, one tour slug, one date) | Every test run's IDs unless they illustrate a reusable pattern |
| Auth tips, blockers, "needs referer" notes | Task-specific acceptance-criteria prose |

**Folder layout:**

| Path | Content |
|------|---------|
| `~/.agents/kb/testing/_shared` | Cross-project instrumentation (e.g. Enonic Content Studio, Guillotine, Data Toolbox) |
| `~/.agents/kb/testing/<project>` | Project-specific flows (`as` for Authentic Scandinavia) |

**File naming:** `How-to-<verb>-<object>.md` (e.g. `How-to-search-components-via-guillotine.md`,
`How-to-start-booking-from-tour.md`). Link related guides; split when a file grows
past one concern.

**Sample data rule:** one short **Sample data** section at the end — only values
needed to execute the procedure (e.g. review base URL, one bookable tour slug, one
test email). Never the focus of the document.

See [kb-format.md](kb-format.md) for the How-To template. KB write-back instructions
belong in the plan file’s **Execution** section (filled from [templates.md](templates.md)).

## Auxiliary skills (optional, on demand)

Not required for every run. When planning needs a specialized capability you cannot perform
with already-installed skills / MCP / normal tools, and a session-only script is not worth it:

1. Prefer an already-installed skill if one covers the need.
2. Otherwise follow the `find-skills` skill as a nested prerequisite (`called_from: plan-task-evidence`): search, verify quality, install if appropriate, then **read and follow** the new skill for the blocked action.
3. Resume this skill’s planning workflow after the gap is closed.

Example: the issue references a `.fig` / Figma file and no Figma reader is installed →
`find-skills` → install/use a reader → continue drafting the plan.

## Inputs

| Input | Required | Example |
|-------|----------|---------|
| `<TASK-ID>` | yes | Jira key `AS-1171` or kebab slug `hubspot-form-macro` |
| Testing base URL | yes | the review or staging root the user gave, e.g. `https://review.<project>.<env-domain>/` |

Resolve `<TASK-ID>` and `mode` per `How-to-resolve-task-context.md`. Do not ask for a Jira key when the slug is local. If either required input is missing, ask for it before continuing. Derive any other URL from the base URL — never hardcode a different host than the one the user gave.

## Workflow

```
- [ ] Phase 1: Collect (use existing PRD if present — **do not Jira-fetch that key**; **testing KB scan**, **offline-reference when needed**, local related-task grep, lookups). Shipped code = review host, not a worktree.
- [ ] First planning step: **Auth required?** (yes/no + surfaces; unknown → yes). Before URL derivation / screenshot steps.
- [ ] Phase 2: **Write** `~/.agents/plans/<TASK-ID>/evidence.md` from [templates.md](templates.md) — includes **Product concept**, Steps, **and** Execution (E2 only when `mode` is `jira`)
- [ ] Phase 3: Evaluate & **rewrite the plan file** on disk
- [ ] Phase 4: Map authentication — run `scripts/find-auth-storage.py --host <testing base URL>`; it reads every candidate's cookie domains and ranks host match first, then newest. Filename is a guess, not a lock. Ask for `npx playwright codegen --save-storage=…` **only** when no candidate covers the host; write the chosen absolute path into the plan file
- [ ] Spawn `playwright-<TASK-ID>` (`python3 ~/.agents/mcp/playwright.py spawn <TASK-ID> --enable` plus `--storage-state <path>` when Auth required is yes and the file exists). Do not spawn while auth is still `pending`. Do not navigate. Leave the process running for `run-plan`.
- [ ] STOP: confirm plan file exists; present path + auth map + spawn url; ask whether to execute later in a **new** session. Do not run the Execution section.
```

### Hard stop (mandatory)

**Precondition:** resolved evidence entry (`evidence.md` or legacy `*-evidence-plan.md`) **must already exist**
(written in Phase 2, updated through Phase 3/4). If it does not, go back and write
it — do not hard-stop with only a chat outline.

After Phase 3/4:

1. If Auth required is no, or the storage-state path exists on disk: spawn
   `playwright-<TASK-ID>` (`python3 ~/.agents/mcp/playwright.py spawn <TASK-ID> --enable`
   and `--storage-state <path>` when auth is yes). Record `url` / `output_dir` from the
   JSON in the plan. If spawn fails, say so and do not claim the MCP is ready.
   If auth is still `pending` (waiting on codegen), skip spawn and hard-stop for the file.
2. Confirm the plan file is on disk; present its path, **Auth required**, Browser MCP
   (`playwright-<TASK-ID>`), spawn url, the step list, auth map, and any scope warnings.
3. **Ask** whether the user wants to execute later via `run-plan` in a **fresh** session.
   Do **not** start the plan’s Execution section from this skill. This chat cannot see
   the new MCP tools.
4. Staying in the current mode is **not** permission to execute. Silence or
   answering only planning questions is **not** a go-ahead.
5. If the user only wanted the plan, end here — success is the written plan file plus
   a running instance (stop it with `python3 ~/.agents/mcp/playwright.py stop <TASK-ID>`
   if they will not execute).
6. If the user explicitly approves execution **in this same transcript**, stop and tell
   them to open a new chat for `run-plan`. Do not capture here.

---

## Phase router

Load one reference at a time:

1. Read [collect.md](references/collect.md) for source/KB collection (Jira only when `mode` is `jira`) and the mandatory auth decision.
2. Read [draft-and-evaluate.md](references/draft-and-evaluate.md) only while writing and checking evidence steps, URLs, GitLab evidence, and reachability.
3. Read [auth-and-companions.md](references/auth-and-companions.md) only for the auth wait/ask mapping and companion-file contracts.

Do not preload later phases. Finish by running `agentctl plan validate <file> --kind evidence --json`, then hard-stop for approval as required above.

## Validate-evidence mode

Trigger: user asks to **validate/fix** an evidence or test plan (`agentctl plan resolve <TASK-ID> --kind evidence`).

Read and follow `../validate-plan/SKILL.md` (`called_from: plan-task-evidence`). Do **not** execute Execution, open a capture browser, or post to a tracker from this skill.
