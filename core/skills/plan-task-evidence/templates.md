# Templates — Task Evidence Plan

Two templates: the **Evidence Creation Plan** (written by `plan-task-evidence`;
includes an **Execution** section for later runs) and the **Jira evidence comment**
(used when executing a `mode: jira` plan). Fill placeholders in `<...>`; keep section structure.
`<TASK-ID>` is the same value historically written as `<ISSUE-KEY>`.

**Fill by mode** (`How-to-resolve-task-context.md`):

- `jira` — set **Mode:** `jira`, keep the Jira URL, keep E1 upload + E2.
- `local` — set **Mode:** `local`, **Jira:** `n/a`, **Evidence sink:** chat + local folder. Omit E1 Atlassian upload and the entire E2 section from the generated file. Keep E1 capture/flatten/stamp and E3.

---

## Evidence Creation Plan

Save to `~/.agents/plans/<TASK-ID>/evidence.md` (legacy `~/.agents/plans/<TASK-ID>-evidence-plan.md` still resolves).

**Required:** include the **Execution** section below in every generated plan file.
`plan-task-evidence` stops after writing this file; capture / tracker comment / KB steps run
only when someone later follows that Execution section (e.g. `run-plan`).

```markdown
# Evidence Plan — <TASK-ID>: <summary>

**Mode:** jira | local
**Jira:** https://example.atlassian.net/browse/<TASK-ID>  <!-- n/a when Mode is local -->
**Testing base URL:** <base>
**Change type:** <user-visible | user-transparent | mixed>
**Evidence folder:** ~/.agents/prds/<TASK-ID>/evidence
**Browser MCP:** `playwright-<TASK-ID>` — planning session already spawned this HTTP instance; `run-plan` is a fresh chat that captures on it (skill default; do not start with `cursor-ide-browser` or `user-browser-control` unless the user names a different tool)
**Auth required:** <yes | no | yes (unknown — treat as required)> — <surfaces: preview / Content Studio / `/admin` / GitLab / app login / none>
**Evidence sink:** jira-comment (Mode jira) | chat-and-local-folder (Mode local)
**Jira evidence comment:** <!-- Mode jira only --> post a **new** comment unless an evidence comment on this issue was **created today** (then that one may be edited in place). A prior comment id is history, not an edit target, unless the user strictly asks to edit it. <!-- Mode local: omit this line; do not post. -->
**Status:** planned — do not execute until explicitly approved

## Acceptance criteria
1. <concrete pass/fail criterion>
2. <...>

## Scope warning
<Only if evidence crosses frontend↔backend or a boundary. Name the layers and say it needs
end-to-end verification. Otherwise: "Single scope — no cross-scope warning.">

## Product concept
<!-- Required. Override 13. Infer from the ticket, not from “backend only”. -->
- **Concept:** <one sentence a visitor or editor would use — e.g. “a HubSpot form on the page”>
- **Expected paint:** <fields / iframe / player that must be visible — not “heading present”>
- **If missing:** console (CSP) → failed requests → fixture IDs → report to the operator. Do not mark the live step pass. Do not post.

## Testing tips (from description/comments)
- <tip + source comment id, e.g. "URL X fails on direct access; open via Y first — comment 511700">

## Sources
<!-- Testing KB = instrumentation. Offline reference = product/API semantics.
     Review host = shipped code; do not cite local worktree / implementation-branch paths. -->
- **Testing KB:** <`~/.agents/kb/testing/.../How-to-….md` | none — gap for KB write-back on execute>
- **Offline reference:** <e.g. `~/.agents/kb/offline-reference/content-studio-stable/docs/content-studio/stable/actions/new.md` | n/a>

## Authentication map
| Realm | Steps | Mode | Storage state | Status |
|-------|-------|------|---------------|--------|
| <app login / admin / gitlab / external / none> | <step #s> | <user fills: find storage state or codegen → headless capture> | `<absolute path from find-auth-storage, else ~/.agents/.auth/<env>.json>` | <pending/ready> |

## Steps
<!-- Goal = what the screenshot will prove toward a requirement/AC (feeds the Jira comment
     explanation). Never plan a shot that would land in the comment without that prose. -->
| # | Goal (what it proves) | URL | Auth | Timeout | Expected result | Screenshot file |
|---|------|-----|------|---------|-----------------|-----------------|
| 1 | <ties to AC #…; what analyst should see> | <url> | <y/n realm> | <budget> | <expected> | 01-<name>.png |
| 2 | ... | ... | ... | ... | ... | 02-<name>.png |

## Cut / impossible (with reason)
- <step> — <cut: proves nothing | impossible: agent can't reach / can't upload>

## Posting Gate
- **Mode jira:** post the evidence comment **only** when every AC/step passed. Any fail / blocked / inconclusive: do **not** post and do **not** ask to post a partial.
- **Mode local:** do **not** post to a tracker. Chat-report the local evidence folder and the pass/fail list.

---

## Execution (run only after explicit approval)

> **Gate:** Do not start this section until the user explicitly says to execute
> (e.g. "go", "execute", "run the plan"). Planning alone is not approval.
> Prerequisites: ImageMagick (`mogrify`, `identify`), browser MCP. Atlassian MCP for uploads only when **Mode** is `jira`.
> Detail recipes: `~/.agents/skills/plan-task-evidence/reference.md` and
> `~/.agents/skills/plan-task-evidence/templates.md` (Jira comment / HTML media embed — jira mode).
> **Mode local:** after E1 capture/flatten/stamp, skip upload and skip E2. Chat-report the evidence folder and pass/fail list. Continue to E3 when useful.

### E1 — Capture

0. **Assert `playwright-<TASK-ID>` is already up** (planning spawned it). Discover
   `user-playwright-<TASK-ID>` / `mcp__playwright-<TASK-ID>__*`. If those tools are
   missing: `python3 ~/.agents/mcp/playwright.py list`. Process dead → spawn
   `--enable` (and `--storage-state` when auth is yes), then **stop this chat** and
   ask for a new `run-plan` session. Process alive but no tools → this chat started
   before enable; new chat, do not capture here. Do not fall back to a vendor-native
   browser.
1. **Login — Execution step 1 (include only when Auth required is yes; omit entirely when no).**
   Runs **before** any other browser action (navigate-to-example, screenshots, etc.).
   - **Search first:** prefer `~/.agents/.auth` (do not inspect implementation source). Run
     `python3 ~/.agents/skills/plan-task-evidence/scripts/find-auth-storage.py --json --host <testing base URL>`.
   - **Read every candidate's contents. The filename is a guess, never a lock.**
     The script opens each storage state and prints the cookie domains it actually
     carries, ranked: host match first, then most-recently-updated. A state saved as
     `user.json` routinely holds the only session for the environment under test.
     - A candidate whose domains cover the testing base URL host **is** the auth for this
       run (`host-match` in the output). Use it and go straight to headless capture.
     - Several host matches: take the **most recently updated** one - that is what the
       ranking already puts first (`recommended`).
     - No host match: the ranking still lists every state, newest first. Read that list
       before concluding anything.
     **Do not ask the operator for a login until every candidate has been read and none
     covers the host.** Asking for codegen while a matching state sits in `~/.agents/.auth`
     is a process failure, not a blocker. If a matching state exists but no longer
     authenticates, say so with the path and the evidence (the step landed on the login
     page) before asking for anything.
     Locations searched: `~/.agents/.auth/*.json`, `~/.agents/.playwright-mcp/*.json`,
     `~/.agents/.playwright-mcp/auth/*.json`, `./playwright/.auth/*.json`, `./.auth/*.json`,
     `./*.json` (Playwright storage-state shape only: `cookies` + `origins`). Put the chosen
     absolute path in the Authentication map and skip to headless capture.
   - **Only when no candidate covers the host — ask (do not open MCP login yet):** tell the user to create state with:

     ```bash
     npx playwright codegen --save-storage="$HOME/.agents/.auth/<env>.json" "<login-or-app-url>"
     ```

     Wait for confirmation; re-run the finder. Preferred new-file path is
     `~/.agents/.auth/<env>.json` (mode 700 on the directory).
   - **Skip codegen when reusable:** if the mapped storage-state file already exists and
     still authenticates, go straight to headless capture — no window opens.
   - **Expired-state refresh:** ask for codegen again, or re-spawn the instance with
     `--storage-state` after the file is rewritten.
   Do not try to log in silently with stored passwords. Do not use the Cursor IDE
   embedded browser as the login path unless the user overrides.
   Then run **every** remaining evidence step on `playwright-<TASK-ID>`. Prefer the
   storage-state already applied at spawn; otherwise `browser_set_storage_state`
   from that file as the first call. A step landing on the login page means the state
   expired — that is a **failed step**, not evidence; redo search / codegen / re-spawn
   (re-spawn requires a new chat).
2. Re-check docs if CMS/UI semantics stall: matching `offline-reference` pages and
   testing How-Tos under `~/.agents/kb/testing/_shared` and `~/.agents/kb/testing/<project>`.
   Persist new stable site-specific steps in E3 (testing KB only).
3. Browser MCP is **`playwright-<TASK-ID>`** — the HTTP instance planning started.
   See `How-to-enable-playwright-mcp.md`. Do **not** open `cursor-ide-browser` or
   `user-browser-control` first unless the user explicitly names a different tool.
   Record in the chat report: Playwright was used (skill default). After E1–E3 (and
   E2 when `jira`), stop the instance:
   `python3 ~/.agents/mcp/playwright.py stop <TASK-ID>`.
4. For each row in **Steps**:
   1. `browser_navigate` to the URL.
   2. Confirm the session is still authenticated if the row’s Auth is y.
   3. `browser_snapshot` to confirm expected state.
   4. **Product concept (live / integration rows):** restate the plan’s
      **Product concept**. Assert **Expected paint** in the DOM (form fields,
      player, widget). Headings alone are not paint. If paint is missing, collect
      console CSP / refused-script errors and failed requests, diagnose fixture
      IDs, **stop the step as failed**, report to the operator — do not
      screenshot-and-pass. Procedure:
      `~/.agents/kb/testing/_shared/How-to-gate-evidence-on-the-product-concept.md`.
   5. `browser_take_screenshot` with explicit `filename` into
      `~/.agents/prds/<TASK-ID>/evidence` (e.g. `01-<name>.png`).
      If the MCP writes elsewhere, copy into the evidence folder.
      If two shots are stacked into one PNG, mark the merge **in the image**
      (banner, black bar, a short label per part) before stamp — a silent stitch
      looks like empty space (PROJ-435 `08-featured-cards`).
   6. **Jira-bound consistency check (mandatory before upload/post):** Run the
      local gate in
      `~/.agents/kb/testing/_shared/How-to-check-evidence-screenshots-before-jira.md`
      (`agentctl image whitespace` + `agentctl evidence inspect --ocr`), then
      read the PNG. Confirm **correct element**, **correct zoom**, **correct
      example page**, and **expected paint** for live/integration shots. A
      1440×900 white overlay with a few lines of text is a fail even if OCR
      finds the tokens. A heading over an empty HubSpot slot is a concept fail.
      Retake or diagnose — do not flatten/upload a concept fail.
      (Storage-only captures with no immediate Jira post: check optional.)
   7. Record the local path for each validated shot.
5. After all captures (including `before/` / `after/` if used), flatten and stamp
   pixel size. Do **not** run raw `mogrify … *.png` — that skips the resolution tag:
   ```bash
   agentctl image stamp ~/.agents/prds/<TASK-ID>/evidence/*.png
   agentctl image stamp --check ~/.agents/prds/<TASK-ID>/evidence/*.png
   ```
   `--check` exit 1 = do not upload. Pass **file paths** so names that are not
   `NN-*.png` are included. The script flattens alpha, adds the 2px `#dddedd`
   border, then overlays `WIDTH x HEIGHT` (8pt, bottom-left) using the PNG’s
   pixel size after flatten. It is idempotent (skips files that already carry
   the matching stamp). Equivalent:
   `python3 ~/.agents/skills/plan-task-evidence/scripts/annotate-evidence-resolution.py`.
6. **Upload (Mode jira only).** Skip this step when **Mode** is `local` — keep files in the evidence folder; do not call Atlassian tools. When **Mode** is `jira`, upload each flattened PNG via Atlassian MCP preview
   (`user-atlassian-rovo-preview` → `uploadAttachmentToJiraIssue`):
   - `filePath` → run the returned `uploadCommand` → keep `fileId` (`data.id`, a media UUID)
     and `collection` (the tool response's own `collection` field — one value per session,
     reused across every file).
   - **Do not** call the tool again with `fileId` for a file you intend to embed inline in
     the comment (E2) — that second call attaches it as a bare standalone file instead, and
     doing both creates a duplicate attachment. Referencing `fileId`/`collection` in the E2
     HTML body attaches the file automatically.
   - Resolve `cloudId` once. Track `{ basename, fileId, collection }`.
   - On failure after one corrected retry: stop further uploads; use text
     `[Attachment: <basename>]` in E2 **only** for files that did not upload.
   - **Do not reuse `fileId`s** from an older or soon-to-be-deleted comment.
     Replacement comments re-upload every PNG in this session.
7. If a step fails: fresh snapshot; after a few attempts, stop and report the
   blocker — do not loop.

### E2 — Jira evidence comment

**Skip this entire section when Mode is `local`.** Do not call Atlassian tools. Chat-report the local evidence folder and pass/fail list. Continue to E3 when useful.

**Preflight gate (blocking, in this order — no Jira write tool before it):**

1. **Read** `~/.agents/skills/plan-task-evidence/templates.md` § "Jira evidence
   comment" *in this session*. Not from memory, not from the plan's paraphrase.
2. **Tooling:** post via the `atlassian-rovo-preview` MCP
   (`addOrEditJiraIssueComment`) or `addCommentToJiraIssue`. **Never** use the
   Atlas PM-assistant MCP for any Jira write.
3. **Write the whole body to a file first**, then run:
   `python3 ~/.agents/skills/plan-task-evidence/scripts/check-evidence-comment.py <file>`
   Exit 1 = **do not post**; fix and re-run until it exits 0.
   After stamp, `identify` each PNG. Author `data-width-type="pixel"`, figure
   `data-width` = PNG width, inner `data-width`/`data-height` = PNG width/height,
   `data-layout="wide"` when width ≥ 1200 else `center`. Percentage `60` letterboxes
   (override 15; PROJ-435 comment 531480).
4. **One call posts everything.** Embed each image inline in that single body via
   its `fileId`/`collection`. Do **not** attach files as standalone attachments in
   a separate pass and then post a text-only comment — that produces the gallery
   dump this gate exists to stop.
5. **Backup before edit.** If this write uses `commentId`, fetch the current
   comment as HTML and run
   `python3 ~/.agents/skills/plan-task-evidence/scripts/backup-jira-comment.py --issue <KEY> --comment-id <ID> --body-file <html>`
   first. Exit non-zero = **do not edit**. New comments skip this. Chat-report the
   backup path; never put it in the Jira body.
6. **One create per issue.** Do not call `addOrEditJiraIssueComment` twice without
   `commentId` for the same issue in one run (PROJ-429 posted 529380 and 529381).
   After a create, list comments. A second same-body comment is trash — delete it
   before uploading or reporting.
7. **Replace order.** Re-upload every PNG → write/edit with those new `fileId`s →
   `verify-jira-comment-images.py` exit 0 → then delete trash comments → verify
   again. See `~/.agents/kb/testing/_shared/How-to-post-jira-evidence-comments.md`.

**Audience: analyst/reporter only.** No local paths, upload how-tos, or
evidence-machine logistics in the Jira body. The pass/fail matrix is a **local
report artifact, not Jira content** — the analyst gets prose and evidence, not the
run's scorecard.

**Prose:** before drafting the Jira body, **read and follow**
`write-analyst-message` (`~/.agents/skills/write-analyst-message/SKILL.md`),
**Evidence comment shape** (not the TBD-question path).
What-Why-How, product language, key message first. Keep this template’s
sections and HTML/upload rules. Open by name; never thank, praise, or assess the
analyst's work. **Do not ask questions in this comment** — no TBD, no a/b/c
options, no “which would you like”. Limitations are facts the analyst can
see on the review URL. Decisions belong in chat or a separate question comment.

- **Failure gate (mandatory):** If **any** step or acceptance criterion failed,
  is blocked, or is inconclusive — **do not post** the evidence comment.
  **Do not ask** whether to post a partial/fail comment. Report in chat: pass/fail
  list, why, and local artifact paths. Keep local evidence (and any already-uploaded
  media). This **overrides** always-apply `evidence-post-on-failure-ask` (that rule
  asks on failure; this skill does not). All-pass runs may post without asking.
  Local capture, flatten, and attachment upload may still happen; the gate is the
  Jira comment post.
- Every screenshot must sit under an explanation of **what it proves** (AC).
  Never orphan images or dump a gallery at the end.
- Prefer HTML (`contentFormat: "html"`) with a `<figure data-type="media-single">` /
  `<div data-type="media">` node using the upload's `fileId`/`collection` for each successful
  upload. Never `[Attachment: …]` for an uploaded file.
- Placeholder `[Attachment: <basename>]` only when that file failed to upload.
- Build the comment from the **Jira evidence comment** template in
  `~/.agents/skills/plan-task-evidence/templates.md`.
- Post with `addCommentToJiraIssue` / `addOrEditJiraIssueComment`. Mention the
  analyst via `lookupJiraAccountId` when named.
- **Same-day comment only.** List comments before writing. Edit in place (`commentId`)
  **only** when that comment’s **`created`** date is **today**, or the user **strictly
  asked** to edit a named older comment (id or date). Otherwise post a **new** comment.
  A plan line like “edit comment 523467 in place” does not override this. “Post it”
  does not mean edit an older comment. Any allowed edit still requires override 9
  (local HTML backup of the previous body) before the write.
- **Chat report-back (not Jira):** issue link, comment id (or “not posted — failures
  reported in chat”), `verify-jira-comment-images.py` exit 0, comment count (one
  evidence body, not two), upload vs placeholder, local evidence folder, KB files from E3,
  manual follow-ups, Playwright used (skill default), and any failures that blocked
  the Jira comment post.
- **After post (blocking):** run
  `python3 ~/.agents/skills/plan-task-evidence/scripts/verify-jira-comment-images.py --issue <KEY> --comment-id <ID>`
  Every media `data-id` must match an image attachment on the issue. Exit 1 = not
  done — re-upload, edit, re-run. If you then delete an older comment that held
  reused ids, run the script again. `check-evidence-comment.py` does not catch this.

### E3 — Testing-KB write-back (when know-how was gained)

After E1 (and E2 when Mode is `jira`), if this run taught reusable how-to knowledge (and it was not already
fully covered by existing How-Tos):

1. Scope: `_shared` for Enonic/CMS/Guillotine/Data Toolbox; `<project>` for app-specific flows.
2. Create/update the smallest set of `How-to-*.md` under `~/.agents/kb/testing/…`
   (merge when topic fits; split when mixing concerns). Format: `kb-format.md`.
   For part notes: `How-to-capture-<part>-part-evidence.md` next to that project's persistent-content How-to. Never a `disposable-content/` folder.
3. Procedure + stable selectors only — no screenshot dumps or Jira comment text.
4. Optional short **Sample data** (minimum examples). Report files touched in chat.
```

---

## Jira evidence comment

> **Gate:** do not write or post this comment if the **product concept** failed
> (expected paint absent — empty form/player/widget). Diagnose and report in chat.
> Then write the body to a file and run
> `python3 ~/.agents/skills/plan-task-evidence/scripts/check-evidence-comment.py <file>`
> before posting. It fails on gallery dumps, orphaned or thinly-captioned images,
> percentage-sized media figures (PROJ-435 letterbox), figures missing PNG pixel
> width/height, rendered-comment HTML wrappers, leaked local paths,
> evidence-machine logistics, missing sections, analyst questions (a/b/c lists,
> “my recommendation”), and env-root URLs with no page path.

Post with `addCommentToJiraIssue` or preview `addOrEditJiraIssueComment`. Prefer
`contentFormat: "html"` whenever any screenshot uploaded successfully — get the current node
reference once per session via `execute name: "getContentFormatGuide"`,
`inputs: { toolName: "addOrEditJiraIssueComment" }` rather than reconstructing the shapes from
memory. Use real mentions for people (`<span data-type="mention" data-user-id="AAID">`).

**Audience: analyst/reporter.** Write only what helps them validate the change. Do **not**
include local paths, upload/attach how-tos, or any evidence-generation / developer logistics.

**Deployed testing environment** links the **page that was captured**, not the review host
root. Live URL with its path, plus Content Studio edit URL labelled Admin when CS was in
the run. Useless: the environment root, `https://review.<project>.<env-domain>`.
Useful: `https://review.<project>.<env-domain>/test/evidence/featured-cards`
(`Admin` → `…/admin/com.enonic.app.contentstudio/main/english/edit/<content-id>`).

**Prose:** **read and follow** `write-analyst-message` (`~/.agents/skills/write-analyst-message/SKILL.md`)
for the comment body. What-Why-How in product language; Changes summary is the outcome, not a
file/library changelog. Translate implementation jargon. Logistics stay in the chat report.
Open by name. Never thank, praise, or assess the analyst's work ("thanks for reporting",
"good catch", "the right call" are all banned). **Do not ask the analyst anything in this
comment.** Evidence is the wrong moment for TBD: they are here to check the delivery, not
to pick a product option. Do not follow `How-to-write-analyst-questions-with-options.md`
for E2. Known limitations belong as plain facts (what shipped, how to reproduce on the
deployed URL) — never as a/b/c lists, “my recommendation”, or “without an answer we get …”.
Park open decisions in the chat report and, if they still need the analyst, a **separate**
question comment after evidence is posted. Keep backticks out of bold runs; Jira's
markdown-to-ADF conversion closes the bold at the code span.

**Purpose of each evidence unit:** convince the analyst that the solution fulfills the
requirements and meets the acceptance criteria. A screenshot without explanation has **no
meaning** — never post one.

**Attachments (placement rules):**
- **Uploaded (required when E1 upload succeeded):** embed each image with a
  `<figure data-type="media-single">` / `<div data-type="media">` node using the upload's
  `fileId`/`collection`. Place it **immediately under** that step's explanation.
- **Upload failed only:** `[Attachment: <basename>.png]` under the explanation.
- **Do not** use `[Attachment: …]` for a file that uploaded, and do **not** gather screenshots
  in a gallery at the end of the comment.
- Never put local paths or "please attach" instructions in the comment.

### Preferred: HTML body (uploads succeeded)

Author one HTML fragment (no `<html>`/`<body>` wrapper). For each evidence step: a `<p>`
(explanation), then a `<figure data-type="media-single">` whose child `<div data-type="media">`
uses the upload `fileId`/`collection`. Size each figure to the **PNG pixel size**
from `identify` (after stamp): `data-width-type="pixel"`, figure `data-width` =
PNG width, inner media `data-width` / `data-height` = PNG width / height.
`data-layout="wide"` when the PNG is a full desktop capture (width ≥ 1200, typically
stamped 1440); `data-layout="center"` for tight clips. Do **not** use
`data-width-type="percentage"` or `data-width="60"` — Jira then reserves a 250×200-aspect
box and letterboxes a wide shot (PROJ-435 comment 531480, 2026-09-15). Do not copy Jira's
rendered comment HTML (`ak-renderer-wrapper`, media-card wrappers); one `<figure>` wrapping
one media `<div>` with those pixel attrs is the authored node. Jira adds the rest.

```html
<p><span data-type="mention" data-user-id="<accountId>">@Analyst Name</span> — evidence for <ISSUE-KEY>.</p>

<h3>Changes summary</h3>
<p><Product outcome: what the analyst can now see or do, and which requirements that covers. No file/library/CSS detail.></p>

<h3>Deployed testing environment</h3>
<p><a href="https://review.example/test/evidence/featured-cards">https://review.example/test/evidence/featured-cards</a> (<a href="https://review.example/admin/com.enonic.app.contentstudio/main/english/edit/CONTENT_ID">Admin</a>)</p>

<h3>Evidence</h3>

<p>1. <What to look for in the screenshot and which AC it proves — product language.></p>
<figure data-type="media-single" data-layout="wide" data-width="1444" data-width-type="pixel">
  <div data-type="media" data-media-type="file" data-id="<fileId>" data-collection="<collection>" data-alt="01-<name>.png" data-width="1444" data-height="443"></div>
</figure>

<p>2. <Next evidence unit explanation.></p>
<figure data-type="media-single" data-layout="center" data-width="308" data-width-type="pixel">
  <div data-type="media" data-media-type="file" data-id="<fileId>" data-collection="<collection>" data-alt="02-<name>.png" data-width="308" data-height="173"></div>
</figure>

<h3>Acceptance criteria</h3>
<p><met / partially met — map each AC to evidence # above></p>
```

Pass that fragment as `commentBody` with `contentFormat: "html"`. `data-collection` is required
when *authoring* the node; Jira strips `data-collection` and the filename text on save/read —
expected, not data loss, and a body fetched back as HTML can be written straight back as-is.

### Legacy alternative: ADF body

An ADF JSON `doc` with `mediaSingle`/`media` nodes (`attrs.id` = the upload `fileId`,
`attrs.collection` = the upload `collection`) still works via `contentFormat: "adf"`, for a
caller that already has ADF tooling. Do not default to it over the HTML path above, and do not
hand-write the JSON shape from memory — pull the current schema from `getContentFormatGuide`
first. Same sizing as HTML: `mediaSingle.attrs.width` = PNG width, `widthType = "pixel"`,
`layout` = `wide` (≥ 1200px) or `center` (clips). Set `media.attrs.width` / `height` from
`identify` of the flattened PNG. Never `widthType: "percentage"` — that letterboxes
(PROJ-435).

### Fallback only: markdown placeholders (uploads failed)

```markdown
<@Analyst Name> — evidence for <ISSUE-KEY>.

**Changes summary**
<Product outcome: what the analyst can now see or do, and which requirements that covers. No file/library/CSS detail.>

**Deployed testing environment**
<Live page URL that was captured, full path — never the env root. When Content Studio was in the run, add (Admin) pointing at the CS edit URL, e.g. https://review.<project>.<env-domain>/test/evidence/featured-cards ([Admin](https://review.<project>.<env-domain>/admin/com.enonic.app.contentstudio/main/english/edit/e5410d90-c5da-4be5-8f5b-fd27540e10dd))>

**Evidence**

1. <What to look for in the screenshot and which requirement / AC it proves — product language
   (e.g. the heading and three cards on the live page).>
   [Attachment: 01-<name>.png]

2. <Same pattern: explanation that gives the image meaning, then the placeholder under it.>
   [Attachment: 02-<name>.png]

Optional text evidence (e.g. curl output) — same rule: short meaning first, then the block:
$ curl -sS -I <url> → HTTP/2 200, content-type: application/pdf

**Acceptance criteria:** <met / partially met — note any gaps; map each AC to the evidence # above>

**Additional relevant details (optional)**
<Analyst-facing only: known product limitation as a fact, how to reproduce on the deployed URL, fallback UX.
Never: questions, a/b/c option lists, “my recommendation”, local folders, attach instructions, agent/auth setup, KB/plan paths.>
```

### Notes
- **Explanation + image stay together** as one unit. Never orphan a screenshot (no
  description) and never dump all images at the bottom after the prose.
- Each explanation must state **what the image proves** toward requirements / ACs — not just
  a vague step title.
- The media node's inner text (`<div data-type="media">filename.png</div>`) and placeholder
  labels use the **basename** only (`01-foo.png`), never a directory path.
- **Never** post in Jira: `../.....`, `/home/...`, evidence-folder paths, "please attach
  from …", mogrify/upload steps, or other developer/evidence-machine instructions. Put those
  in the chat report-back only.
- Keep media-node basenames identical to the uploaded (or local) filenames.
- If two screenshots are stacked into one PNG, mark the merge **in the image**
  (banner, black bar, a short label per part). Do not rely on the caption alone.
- **Placeholder fallback only:** after the user attaches the missing files (coordinated in
  chat), edit the same comment (`commentId`) **if it was created today** and replace each
  `[Attachment: ...]` with a `<figure data-type="media-single">` node using the new
  upload's `fileId`/`collection` — still keeping each image under its explanation. If
  that comment is from another day, post a new comment unless the user strictly asked
  to edit the old one.
- **Deployed testing environment** is the captured live page (full path) plus Admin
  (CS `…/main/{project}/edit/{contentId}`) when Content Studio was in the run. Never the
  env root (`https://review.example/` with no path).
- If no analyst is named, drop the mention line; otherwise resolve the account with
  `lookupJiraAccountId` so the mention renders as an entity, not plain text.
