# Reference — Task Evidence Plan

Recipes for URL derivation, authentication realms, timeouts, and the browser MCP. Read only the heading you need.

---

## Enonic Guillotine component lookups

The Content Studio Guillotine widget is the preferred way to find **where a
component is used**, so you can build a real page URL to screenshot.

**Tool URLs** (need `/admin` auth):

```
# XP 8:
<base>/admin/com.enonic.app.contentstudio/main#/english/widget/guillotine/guillotine
# XP 7:
<base>/admin/tool/com.enonic.app.contentstudio/main#/en/widget/guillotine/guillotine
```

Use the widget's schema/query controls to search the relevant `part`, `layout`,
or `page` component collection by descriptor. Keep the descriptor exact, then
inspect the returned content paths and verify the branch/publish state before
building a public page URL.

For raw node, property, permission, or Data Toolbox service operations, use the
shared `~/.agents/kb/testing/_shared/How-to-search-via-datatoolbox.md`.

### From a match to a page URL

A result gives the content `_path`. Build the live URL:

- Site page: `<base>/<site-path-without-/content-root>` — confirm the exact prefix on the env
  (often the path after `/<site-name>`), then verify by navigating.
- Content Studio edit view: use the version-specific Content Studio route in the
  shared testing KB, then open the matching project/branch and content ID.

When unsure about the public route, open the content in Content Studio and use its **Preview** to
get the canonical URL.

---

## Authentication realms

| Realm | Triggers | Default mode | Notes |
|-------|----------|--------------|-------|
| App login | `/minside`, `/min-side`, `/user`, `/profile`, "My Page" | User fills (find storage / codegen → headless capture) | Often SSO/social login |
| XP admin / Content Studio | `/admin`, Content Studio, Guillotine, or Data Toolbox | User fills (find storage / codegen → headless capture) | Admin session reused across tools |
| GitLab web | self-hosted GitLab (`git_host` in `client-overlay.json`) screenshots | User fills (find storage / codegen → headless capture) | git CLI uses ssh-agent; **web UI still needs login** |
| External system | Tourplan, Ticketco, etc. | User fills (find storage / codegen → headless capture) | May be unreachable from the agent → mark impossible |

**Modes** (see plan **Authentication map** / skill Phase 4):
- *User fills* — find or create a Playwright storage-state JSON, spawn `playwright-<TASK-ID>` with `--storage-state`, then run every capture step on that instance. Full procedure: *Login when auth is required* below.
- Do not try to log in silently with stored passwords. Do not use the Cursor IDE embedded browser as the login path unless the user overrides.

If **Auth required** is yes, this login prompt is **Execution step 1** — before any navigate/screenshot. If auth is not needed, omit that step.

Always prefer *User fills* for sensitive realms. During plan **Execution**, **wait** until
the realm is ready before capturing — do not screenshot a login wall as "evidence".

---

## Timeouts (budgets)

Pick per operation; don't reuse one global value.

| Operation | Budget | Poll/verify |
|-----------|--------|-------------|
| Page load (local/review) | 10–15 s | `browser_snapshot` for the target element |
| Page load (cold/remote env) | 30 s | retry once before failing |
| API request (`curl`) | 10 s | check status + body shape |
| Remote/3rd-party service | 30–60 s | longer; flag flakiness |
| Task/job execution (XP task, build) | 60–300 s | poll status, don't block blindly |
| Auth wait (user logs in) | until ready | ask, then re-check session |

Prefer short polling loops (snapshot / `browser_evaluate`) over a single long sleep.

---

## Browser MCP (evidence default: Playwright)

This skill **names Playwright** (`playwright-<TASK-ID>`) as the browser MCP for evidence
planning and for evidence execution spawned from this skill (including `run-plan` on
an evidence plan). That **overrides** the ordinary Playwright CLI preference for
this flow only.

- Use the spawned `playwright-<TASK-ID>` instance for all navigation and capture. Do **not** open
  `cursor-ide-browser` or `user-browser-control` first unless the user explicitly names a
  different tool for that run.
- Generated evidence plans must state **Browser MCP: `playwright-<TASK-ID>`**.
  **Planning** runs `python3 ~/.agents/mcp/playwright.py spawn <TASK-ID> --enable`
  (`--storage-state <path>` when auth is yes) after the auth map is ready, then
  hard-stops. **`run-plan` is a fresh session** and captures on that instance.
  After the run, `python3 ~/.agents/mcp/playwright.py stop <TASK-ID>`.
  See `How-to-enable-playwright-mcp.md`.
- Report in the local/chat report that Playwright was used and why: skill default.

### Login when auth is required (Execution step 1)

Handoff through disk: each instance is `--isolated`, so capture needs a
storage-state file on disk first. Prefer `--storage-state` at spawn.

1. **Search for storage state.** Prefer `~/.agents/.auth`. Searching auth JSON is not permission to read implementation source:

   ```bash
   python3 ~/.agents/skills/plan-task-evidence/scripts/find-auth-storage.py --json --host <testing base URL>
   ```

   Locations searched: `~/.agents/.auth/*.json`, `~/.agents/.playwright-mcp/*.json`,
   `~/.agents/.playwright-mcp/auth/*.json`, `./playwright/.auth/*.json`, `./.auth/*.json`,
   `./*.json`. Only JSON with Playwright `cookies` +
   `origins` counts. **The script reads every candidate and prints the cookie domains it
   actually carries — the filename is a guess, never a lock** (a state saved as `user.json`
   routinely holds the only session for the environment under test). Take the candidate
   flagged `host-match`; with several, take the most recently updated, which the ranking
   already puts first as `recommended`. Record that absolute path in the Authentication map.

2. **Only when no candidate carries cookies for the host — ask for visual codegen (do not
   invent a session, and do not invent a filename for one that does not exist).** Stop
   capture and ask the user to run (preferred save path `~/.agents/.auth/<env>.json`):

   ```bash
   npx playwright codegen --save-storage="$HOME/.agents/.auth/<env>.json" "<login-or-app-url>"
   ```

   Re-run the finder after they confirm. Do not spawn Playwright until a file exists
   if the step is auth-gated.

3. **Optional refresh (expired state only).** If a file exists but a protected URL still
   lands on login: ask them to re-run the codegen command, then re-spawn the instance
   with `--storage-state` pointing at that file.

4. **Capture.** Spawn `playwright-<TASK-ID>` if it is not up. Prefer `--storage-state` at
   spawn; otherwise `browser_set_storage_state` as the **first** call, then every
   navigate/screenshot step on that instance.

When the state file already exists and still authenticates, skip codegen —
that is the normal case for re-runs and retakes, and it means no window ever opens.

Do not try to log in silently with stored passwords. Do not use the Cursor IDE embedded browser as the login path unless the user
overrides.

**Limits.** Storage state carries cookies + localStorage, **not** sessionStorage — an app
holding its token there comes up logged out headless; fall back to a `--headed` spawn for that
app. Expired state shows up as a step landing on the login page: treat it as a **failed
step**, never as evidence, and redo step 2 or 3. The state files are live session cookies —
keep `~/.agents/.auth` at mode 700.

If auth is not needed, omit the login step and the state file (do not prompt).

## Browser MCP cheatsheet (`playwright-<TASK-ID>`)

| Need | Tool |
|------|------|
| List/inspect tabs | `browser_tabs` (action `list`) |
| Open/navigate | `browser_navigate` |
| Read structure for actions | `browser_snapshot` |
| Capture image | `browser_take_screenshot` (`filename`) |
| Click / type / fill | `browser_click`, `browser_type`, `browser_fill` |
| Dropdowns / keys | `browser_select_option`, `browser_press_key` |
| Evaluate JS | `browser_evaluate` |

After a few failed attempts on a step, stop and report the blocker. If the user named
`cursor-ide-browser` for this run, use that MCP’s lock/unlock rules instead.

### Screenshot storage and Jira upload

Save to `~/.agents/prds/<TASK-ID>/evidence` with ordered, descriptive names
(`01-...png`, `02-...png`). Skip the Jira upload subsection when `mode` is `local`.

### Screenshot consistency (mandatory when posting to Jira)

If screenshots are **meant to post on Jira** (immediate evidence upload/comment), validate
each shot for consistency **before** flatten / upload / comment:

| Check | Pass when |
|-------|-----------|
| Correct **element** | Intended target from the step is what’s shown (not wrong panel/sibling/modal) |
| Correct **zoom** | Scale/crop matches the step — subject readable and dominant as planned |
| Correct **example page** | Env, URL/path, locale, and sample content match the planned example |

**How:** First run the local gate
(`~/.agents/kb/testing/_shared/How-to-check-evidence-screenshots-before-jira.md`):
`agentctl image whitespace` and `agentctl evidence inspect --ocr --expected-text`.
Then read the PNG (preview if the long edge is over 1280) and compare to the
step’s goal / URL / expected result. A full-viewport white overlay with text in
one corner fails zoom even when OCR hits. Retake until all three pass plus the
local numbers. Never upload or embed a failed shot. Do not use vendor vision for OCR.

If screenshots are **just for storage** (not for Jira evidence immediate post), validation
is **not** mandatory.

After all screenshots for an issue are captured (and Jira-bound shots validated), flatten
transparency, add a light gray border, and stamp the PNG’s pixel size at bottom-left
(browser shots often have alpha; the border separates them from Jira’s white page;
the tag is `WIDTH x HEIGHT` at 8pt). This is the always-apply Jira screenshot rule,
not evidence-only:

```bash
agentctl image stamp ~/.agents/prds/<TASK-ID>/evidence/*.png
agentctl image stamp --check ~/.agents/prds/<TASK-ID>/evidence/*.png
```

`--check` exit 1 = do not upload. Pass **file paths** so names that are not
`NN-*.png` are included. Do **not** fall back to a bare `mogrify … *.png` — that
omits the resolution tag. The script is in-place (same basename) and idempotent.
`--no-flatten` stamps already-flattened files. Equivalent:
`python3 ~/.agents/skills/plan-task-evidence/scripts/annotate-evidence-resolution.py`.

**Then upload immediately** via Atlassian MCP preview (`user-atlassian-rovo-preview`):

1. Resolve `cloudId` once (`getAccessibleAtlassianResources` or pass the Jira site URL).
2. For each flattened PNG, `execute` with `name: "uploadAttachmentToJiraIssue"`, `inputs: { issueIdOrKey, filePath }`.
   The response's `uploadCommand` is a local `curl` — run it in the shell; its JSON reply's
   `data.id` is the media `fileId`, and the tool response's own `collection` field (a
   per-session value, e.g. `upload-user-collection-<n>`) is the same for every file uploaded
   in that session — capture it once and reuse it.
3. **That's it — do not call `uploadAttachmentToJiraIssue` a second time with `fileId` for a
   file you intend to embed inline.** That second call (Phase 2 / "standalone attachment") is
   an **alternative** to inline embedding, not a prerequisite: referencing the `fileId` in the
   comment body (below) attaches the file automatically. Only run Phase 2 when you genuinely
   want a bare file-list attachment with **no** inline placement.
4. Track `{ basename, fileId, collection }` for every file. On failure: one corrected retry,
   then stop further uploads; use `[Attachment: <basename>]` placeholders in the evidence
   comment **only for files that did not upload**. Report upload success/failure in **chat
   only** (never in the Jira comment body). Do not reuse a `fileId` from an older or
   deleted comment — re-upload every PNG for a replacement comment. After post, run
   `verify-jira-comment-images.py`; markup lint is not enough.

### Evidence comment: inline media embeds (mandatory when upload succeeded)

Do **not** put `[Attachment: filename.png]` in the comment for an uploaded file — that is
plain text and does not show the image. Post with `addOrEditJiraIssueComment`,
`contentFormat: "html"`, and an HTML `commentBody` — call `execute` with
`name: "getContentFormatGuide"`, `inputs: { toolName: "addOrEditJiraIssueComment" }` once per
session for the authoritative reference (it also covers headings, panels, tables, mentions).
Under each step's explanation, place:

```html
<figure data-type="media-single" data-layout="wide" data-width="1444" data-width-type="pixel">
  <div data-type="media" data-media-type="file" data-id="<fileId>" data-collection="<collection>" data-alt="01-example.png" data-width="1444" data-height="443"></div>
</figure>
```

- `data-id` **must** be the upload's `fileId` (media UUID) — not the numeric Jira attachment id.
- `data-collection` is required when **authoring** the node (from the upload step); Jira strips
  `data-collection` and the filename text on save and read-back — that omission on a
  subsequent read is expected, not data loss or a broken embed.
- Size each figure to the **PNG pixel size** from `identify` (after stamp). That is ADF
  `mediaSingle.attrs.widthType = "pixel"`, `width` = PNG width, plus inner
  `media.attrs.width` / `height` from the same identify
  ([mediaSingle](https://developer.atlassian.com/cloud/jira/platform/apis/document/nodes/mediaSingle/)).
  `data-layout="wide"` when width ≥ 1200 (stamped desktop 1440); `center` for tight clips.
  Always set `data-width-type` — a bare `data-width` is treated as pixels but still
  needs the inner height. Do **not** use `data-width-type="percentage"` or
  `data-width="60"` — Jira then reserves a 250×200-aspect box and letterboxes the
  shot (PROJ-435 comment 531480). Do not paste Jira's rendered comment HTML; one
  `<figure>` + one media `<div>` with those pixel attrs is the authored node.
- **This HTML path (single upload call + inline `<figure>`/`<div data-type="media">` markup) is
  the current recommended approach** — simpler than hand-authoring raw ADF JSON, and it does
  not require a separate "attach" call. An ADF JSON `mediaSingle` body via
  `contentFormat: "adf"` still works as an alternative if a caller already has ADF tooling, but
  do not default to it or invent the JSON shape from memory — pull it from
  `getContentFormatGuide` (or Jira API docs) if used.
- **Any failure / blocked / inconclusive AC or step:** do **not** post the Jira
  evidence comment. **Do not ask** whether to post a partial/fail comment. Report
  in chat (pass/fail list, why, local artifact paths). This **overrides**
  `evidence-post-on-failure-ask` for this skill. All-pass may post without asking.
  Local capture, flatten, and attachment upload may still happen.
- Avoid markdown `![…](attachment-url)` and wiki `!file|thumbnail!` for this flow — they often
  become broken external blobs.

Text `[Attachment: <basename>]` is **fallback only** when that file never uploaded. Full HTML
shape (and the legacy ADF alternative) is in [templates.md](templates.md).
---

## curl evidence (non-UI)

For backend-only checks, a request tool is enough and needs no scope warning:

```bash
curl -sS -D - -o /dev/null "<base>/service/<app>/<service>"      # status + headers
curl -sS -I "<base>/path/to/file.pdf"                             # verify content-type
```

Capture the command + output into the plan/comment as text evidence (no screenshot needed).
