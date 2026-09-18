---
id: how-to-embed-an-existing-jira-attachment-inline
when_skills: [plan-task-evidence, run-plan, write-analyst-message]
inputs: [issue key, image file on disk or already attached]
outputs: [Jira comment with inline media nodes, verified]
stop_if: [ATTACHMENT_VALIDATION_ERROR, unresolved mediaId, agentctl image stamp --check exit 1, verify script exits non-zero]
read: section
prose: caveman-lite
---

# Embed an existing Jira attachment inline in a comment

An ADF media node is keyed by the **media file UUID**, not the numeric attachment id. No
Jira REST field returns that UUID. It is in the `Location` header of the 303 from
`/rest/api/3/attachment/content/{id}`, readable with the ordinary API token in
`~/.agents/.auth/jira-api-token.yaml`. `agentctl jira media-ids` does that read.

The Atlassian Media service (`api.media.atlassian.com`) needs a separate short-lived JWT
and is **not** required here. Reach for it only when uploading a file that is not on the
issue yet.

## Procedure

1. Stamp a screenshot PNG before attach. Skip this only for a non-screenshot file.

```bash
agentctl image stamp <FILE>
agentctl image stamp --check <FILE>
```

`--check` exit 1 = do not attach. Pass the file path.

2. Attach the file, if it is not on the issue already.

```bash
agentctl jira attach <KEY> <FILE>
```

3. Resolve the media UUIDs.

```bash
agentctl jira media-ids <KEY>
```

Check `unresolved` is empty. Each row gives `filename`, `attachmentId`, `mediaId`.

4. Write the body as ADF, one `mediaSingle` per evidence unit, `id` set to that
   `mediaId`. `collection` is an empty string. Put the explanation in the paragraph
   **before** the image.

```json
{"type": "mediaSingle",
 "attrs": {"layout": "wide", "width": 1444, "widthType": "pixel"},
 "content": [{"type": "media",
              "attrs": {"type": "file", "id": "<mediaId>", "alt": "<filename>",
                        "collection": "", "width": 1444, "height": 443}}]}
```

`media.attrs.width` / `height` and `mediaSingle.attrs.width` are the flattened PNG
pixels (`identify`). `widthType` is `"pixel"`. `layout` is `"wide"` when width ≥ 1200
(desktop 1440); `"center"` for tight clips. Never `widthType: "percentage"` — Jira
then letterboxes against a 250×200 default (PROJ-435 comment 531480).

5. Post or edit. Back up first when editing — Jira cannot revert a comment overwrite.

```bash
python3 ~/.agents/skills/plan-task-evidence/scripts/backup-jira-comment.py --issue <KEY> --comment-id <ID> --body-file prev.json
```

```bash
agentctl jira comment <KEY> --comment-id <ID> --content-format adf --body-file body.json
```

6. Verify the nodes resolve. Do not report success without this.

```bash
python3 ~/.agents/skills/plan-task-evidence/scripts/verify-jira-comment-images.py --issue <KEY> --comment-id <ID>
```

## Pitfalls

- **Unstamped screenshot.** Attach after `agentctl image stamp --check` exits 0. Skip the stamp only for a non-screenshot file.
- **Never post media through `--content-format markdown`** or the MCP markdown path.
  Markdown has no node for media, mentions or tables, and the conversion drops them
  silently: images vanish, the mention degrades to plain text, the table flattens to a
  run-on paragraph. The comment publishes looking broken. `--content-format adf` fails
  loudly instead.
- **MCP `uploadAttachmentToJiraIssue` phase 2 plus inline embedding duplicates the
  file.** Inline embedding attaches it on its own. Pick one.
- **Uploading bytes to `api.media.atlassian.com` may be sandbox-blocked** — a `curl`
  carrying a bearer token to an external host. Another reason to prefer attach plus
  `media-ids` over the media API.
- **`agentctl jira request GET /rest/api/3/attachment/content/{id}` does not help.** It
  follows the redirect and returns PNG bytes, then fails serializing them as JSON. The
  UUID is in the header it discarded.
- Verify after every edit. A body that reads correctly in the write response can still
  carry a media node pointing at nothing.
- **Percentage `widthType` letterboxes.** `width: 60, widthType: "percentage"`
  (and pixel `width` with no media `width`/`height`) makes Jira reserve a 250×200
  box. Use `widthType: "pixel"`, `width` = PNG width, `layout` wide ≥ 1200 else
  center, and set media dimensions from `identify` (PROJ-435 comment 531480).
