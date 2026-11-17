# Tracker checks (Jira)

Load only when `mode` is `jira`. Jira is the only supported tracker. Everything here is read-only: `agentctl jira get|request GET|attach --download|myself|capabilities`. Never call `agentctl jira comment|edit|attach <file>|transition|link|create`, never use the Atlassian MCP, never delete.

Token and site: `agentctl jira capabilities`. Missing, expired or unreachable: record `Tracker: unverified (<why>)`, run the local half, verdict INCOMPLETE at best.

## T0. Find the evidence comment

```bash
agentctl jira request GET '/rest/api/3/issue/<KEY>/comment?orderBy=created&maxResults=100&expand=renderedBody'
```

An evidence comment holds media nodes, or the template sections (`Changes summary`, `Deployed testing environment`, `Evidence`, `Acceptance criteria`). A user-given comment id wins. Also read the local `jira-comment-draft.md` in the evidence folder when it exists.

- No evidence comment: `Tracker: not posted`. Judge the draft (T4, T6) and answer **post-ready** or **blocked**. Blocked is any local FAIL or INCOMPLETE: override 1 forbids posting a partial.
- One comment: `Tracker: posted (comment <id>, created <date>)`. Continue.
- A comment whose `created` is earlier than the newest evidence file's mtime is stale: the shots changed after the post. Finding.

## T1. One comment per run

Two evidence comments with the same body or the same images within minutes are a duplicate post (PROJ-429). Report both ids as trash. Do not delete them: deletion drops attachments the survivor may share, and the safe order is in `How-to-post-jira-evidence-comments.md`.

## T2. Images resolve

```bash
python3 ~/.agents/skills/plan-task-evidence/scripts/verify-jira-comment-images.py --issue <KEY> --comment-id <ID>
```

Exit 1 = FAIL. Empty boxes still carry `data-id` in the HTML, so markup lint is no substitute.

## T3. Posted images are the validated images

Upload is byte-for-byte, so hashes must match. For each media node, resolve its attachment (`/rest/api/3/issue/<KEY>?fields=attachment`), download with `agentctl jira attach --download <attachment-id> --output <scratch dir>`, then compare `sha256sum` and `identify` size with the local stamped file of the same name.

- Mismatch: the posted image is not the one this skill validated. FAIL.
- Media count differs from the number of shots the comment explains: finding.
- Attachments on the issue that no comment references, from this run: ⚠️, not a fail (bare attachments are a known side effect of a second upload phase).

## T4. Body rules

Lint the local draft, or the posted `renderedBody` text:

```bash
python3 ~/.agents/skills/plan-task-evidence/scripts/check-evidence-comment.py <body.html> [--format markdown]
```

On a posted ADF comment, `renderedBody` shows images as `<span class="image-wrap">`, so the linter reports "No media figures". Ignore that one result and check sizing directly in the ADF `mediaSingle` nodes: `widthType` `pixel`, `width` equal to the PNG width, `layout` `wide` when width ≥ 1200 else `center`, and inner `media` `width` and `height` both set to the PNG size. Percentage widths letterbox (override 15).

Any other violation is a finding: local paths, evidence-machine logistics (agentctl, playwright, folder names), questions or TBD options, thanks or praise aimed at the analyst, env-root links with no page path, a pass/fail matrix in place of prose.

## T5. Posted over a failure

Compare the comment with `evidence.progress.md` and the local result. A comment posted while any step was `failed`, `blocked`, `pending` or inconclusive breaks override 1. Report it as a Blocker with the comment id. Do not delete or edit it; that needs the operator's explicit order, a backup (`backup-jira-comment.py`) and the same-day rule.

## T6. Claims match shots

For every sentence that asserts an outcome, find the shot that shows it or a stated check that backs it (a log line, a pipeline result, a diff reference). Mark:

- claim with no shot and no stated check: FAIL;
- shot that contradicts the claim: FAIL;
- AC the comment says is met but the plan cut or the run never captured: FAIL;
- AC stated as not covered, with the reason: fine.

Each image sits under its own explanation (what to look at, which AC it proves). Opens by mentioning the right person: the analyst, or the reviewer who bounced the ticket when the evidence answers a bounce, in the reviewer's numbering.

## T7. Problem-found comment

If the progress notes or run report show a problem the analyst would not otherwise see (a cleared blocker, a different root cause, rebuilt fixtures) and no second comment with **What we found / What we did / What this means for you** exists, note it as ⚠️. Skip when nothing unexpected happened. Do not invent a problem.

## T8. Edit history

`updated` on a different calendar day than `created` means an older evidence comment was edited. Override 8 forbids that without a strict order naming the comment. Report as ⚠️ with both dates.
