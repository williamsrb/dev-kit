---
id: how-to-post-jira-evidence-comments
when_skills: [plan-task-evidence, run-plan]
inputs: [stamped evidence PNGs, issue key, analyst mention]
outputs: [one Jira evidence comment whose images resolve]
stop_if: [second same-body comment, reused fileId from a deleted comment, agentctl image stamp --check exit 1, verify-jira-comment-images.py exit 1, white-spoiled overlay posted]
read: whole
prose: caveman-lite
---

# How to post Jira evidence comments

**Scope:** `_shared`  
**Applies to:** any Jira evidence post from `plan-task-evidence` / `run-plan`  
**Related:** [How to check evidence screenshots before Jira](./How-to-check-evidence-screenshots-before-jira.md)

Worked failures (PROJ-427 / PROJ-429, 2026-09-04–05):

1. Overlay shots were 1440×900 white pages. OCR found the tokens. They were posted.
2. PROJ-429 got the same evidence body twice (529380 and 529381, six seconds apart).
3. Replacement comments copied `data-id` from those comments, then deleted them. Jira dropped the attachments. Most boxes went empty. `check-evidence-comment.py` still passed — it only lints markup.

Do not declare the post done until the after-post script exits 0.

## Prerequisites

- Every Jira-bound PNG already passed the local image gate in the related How-to (whitespace + OCR + Read) and `agentctl image stamp --check` (exit 0). A white overlay or unstamped PNG never reaches upload.
- `fileId`s from `uploadCommand` **in this session** only.
- Each `<figure>` is `data-width-type="pixel"`, `data-width` = PNG width from
  `identify` (after stamp), inner media `data-width`/`data-height` = PNG width/height.
  `data-layout="wide"` when width ≥ 1200; `center` for tight clips.
  Not `percentage`, not `data-width="60"`.

## Procedure

1. Write the HTML body to a file. Run
   `python3 ~/.agents/skills/plan-task-evidence/scripts/check-evidence-comment.py <file>`.
   Exit 1 = do not post.
2. List comments on the issue. Note the current evidence comment ids.
3. Post **once** per issue (`addOrEditJiraIssueComment`, no `commentId`), or edit
   today’s comment (`commentId` + backup script first). Do not fire create twice.
4. List comments again. Exactly one new same-body evidence comment. A duplicate is
   trash — delete the extra now.
5. Run
   `python3 ~/.agents/skills/plan-task-evidence/scripts/verify-jira-comment-images.py --issue <KEY> --comment-id <ID>`.
   Exit 1 = the comment is not done. Re-upload the missing PNGs, edit, re-run.
6. Only then report the comment link in chat.

### Replace or delete a trash comment

1. Re-upload **every** PNG used in the replacement body (this session).
2. Post a new comment or edit today’s comment with those new `fileId`s. Do not
   copy `data-id` from the trash comment.
3. `verify-jira-comment-images.py` exit 0.
4. Delete the trash comment(s).
5. Run `verify-jira-comment-images.py` again on the surviving comment. Delete can
   drop attachments that were still shared.

Do not delete first. Do not reuse ids across a delete.

## Pitfalls

- Markup lint ≠ images exist. Empty boxes still have `data-id` in HTML.
- Deleting a comment deletes its attachments. Reused ids become missing images.
- A successful create retried “to be safe” is a duplicate post.
- `data-width="60" data-width-type="percentage"` (or any percentage, with or
  without inner height) letterboxes: Jira reserves a 250×200-aspect box
  (PROJ-435 comment 531480). Use `data-width-type="pixel"`, figure `data-width`
  from `identify`, and inner media `data-width`/`data-height`.
- Pixel `data-width` without inner `data-height` also letterboxes. Both inner
  dims are required.
- Do not paste Jira’s rendered comment HTML (`ak-renderer-wrapper`, media-card
  wrappers). Author one `<figure>` wrapping one media `<div>` with those pixel attrs.
- Editing an ADF comment in place (`agentctl jira comment --comment-id … --content-format adf`):
  `renderedBody` shows images as `<span class="image-wrap"><img>`, which the linter reads as
  "No media figures". Build the lint twin from the new ADF instead: one `<figure data-type="media-single"
  data-width-type="pixel" data-width=…>` with an inner media `<div data-id data-width data-height>` per
  `mediaSingle` (RFD-687 comment 537890, 2026-10-09).
- OCR finding labels does not pass a 1440×900 white overlay — that is the other How-to.
- An empty HubSpot (or other embed) slot is a **concept fail**. Do not post it as
  a pass and do not treat it as “not an overlay fail, therefore fine”. Diagnose
  first: [How to gate evidence on the product concept](./How-to-gate-evidence-on-the-product-concept.md).
- An unstamped PNG is not ready to upload. `agentctl image stamp --check` exit 1
  is a stop, including analyst comments that are not evidence-plan runs.
- `agentctl jira comment --content-format html` drops `<figure>`/media nodes: the post
  succeeds as text only and verify reports `has no media nodes` (JOT-266 534132,
  2026-09-24). Post media bodies with `--content-format adf` (`mediaSingle` with
  `layout`, `width`, `widthType: pixel`; inner `media` `type: file`, `id` = mediaId from
  `agentctl jira media-ids`, `collection: ""`, `width`, `height`). Lint the HTML first,
  convert, then post. If a text-only create already landed today, back it up and edit it
  with `--comment-id`; do not create a second one.
  The same HTML conversion also turns the mention into plain `@Name` text, wraps
  `<pre><code>` content in literal backticks, and splits `1.`/`2.` units around a code
  block into separate lists that each restart at 1 (JOT-257 534133). Build the whole
  body in ADF, and use `N. ` paragraph text for evidence units rather than `orderedList`.
- Two screenshots stacked into one PNG without a banner, black bar, and per-part
  labels look like one empty shot. Flag the merge in the image (PROJ-435 `08-featured-cards`).

## Sample data

| Field | Example |
|-------|---------|
| Verify | `python3 ~/.agents/skills/plan-task-evidence/scripts/verify-jira-comment-images.py --issue PROJ-427 --comment-id 529383` |
| Pass | script prints `OK — N/N media nodes resolve` and exit 0 |

## Uploading: run `uploadCommand` verbatim, one Bash call per file

Phase 1 of `uploadAttachmentToJiraIssue` returns a curl carrying a short-lived bearer token. The
auto-mode classifier refuses, as **Credential Materialization**, any attempt to:

- write that token to a file (`cat > tok.txt`),
- inline it in a loop over several files,
- substitute a different `name=` / `--data-binary` path into a command it already returned.

What passes is the returned command **verbatim, character for character, as its own single Bash
call**. So it is one `uploadAttachmentToJiraIssue` call per file followed by one Bash call — N files
means 2N round trips. Budget for it; do not try to batch it.

The response's `collection` is stable across files in a session, but read each phase-1 response's own
`collection` and pair it with that file's `fileId`.

**Do not run phase 2** (calling the tool again with `fileId`) for a file you embed inline. Inline
embedding attaches it automatically; phase 2 adds a duplicate standalone attachment.

Jira normalises the stored body — it strips `data-collection` from media nodes and wraps `<li>`
contents in `<p>`. Both are server-side ADF normalisation, not data loss; `verify-jira-comment-images.py`
still resolves the images. Do not "repair" them.

## Capturing when the task's Playwright MCP is not attachable

A session that starts while `playwright-<TASK-ID>` is dead holds no tools for it, and reviving the
process does **not** attach it to that session. Rather than stopping, drive Playwright directly:

```bash
node --input-type=module -e "import {chromium} from '/path/to/node_modules/playwright/index.mjs'; ..."
```

Resolve the module by absolute path (a script in a scratch dir cannot `import 'playwright'`); an npx
cache copy under `~/.npm/_npx/*/node_modules/playwright` works, and browsers are already in
`~/.cache/ms-playwright`. Feed the review session in with
`context.addCookies()` built from `review-auth <project> --json`.

`waitUntil: 'networkidle'` times out on Jotron pages carrying video or maps (`/maritime`). Use
`domcontentloaded` plus a fixed settle wait instead.

## Lint false positive: the page under test is the site root

`check-evidence-comment.py` flags every bare env-root URL, including when the front page itself
is the page under test (JOT-271, 2026-09-24: JSON-LD on `/`). There is no path to link instead.
Add the Content Studio Admin link for the content the run touched, keep the root link, and post
only with the operator's explicit go-ahead on that one violation. Every other violation still
blocks.

## Bounce addendum: address the reviewer, not the reporter

When the evidence answers a review bounce (a reviewer moved the ticket back with numbered items),
mention the **reviewer who bounced it** and structure the body as a reply to that comment:
one paragraph or evidence unit per item, in the reviewer's own numbering and terms, including
any push-back question they asked (answer it as a fact). The reporter/analyst is not the
audience of that comment. JOT-271 comment 534137 was first posted to the reporter and had to be
edited to answer Kaio's 532868 (2026-09-24). A plan line naming the reporter does not override this.
