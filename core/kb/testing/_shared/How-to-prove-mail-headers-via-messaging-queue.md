---
id: how-to-prove-mail-headers-via-messaging-queue
when_skills: [plan-task-evidence, run-plan]
read: whole
prose: caveman-lite
---

# How to prove mail headers (Reply-To, From) via the messaging-queue admin

For evidence that a header actually reached the wire — `replyTo`, `from`, the resolved body — on
any XP app that sends through `/lib/messaging-queue/mail`. Needs admin auth only, never a mailbox.

## Scope

Verified on acme-group review 2026-09-09 (queue app `com.example.messagingqueueapp` v1.0.1, PROJ-405).
Applies to Kavli/nla/gk and any consumer of the same lib.

## Prerequisites

- Admin session for the host (storage state; see the Playwright tiers How-to)
- Queue admin: `<base>/admin/com.example.messagingqueueapp/messaging-queue?type=mail`

## Procedure

1. **The row list is server-rendered into the page, not fetched.** Read it without driving the UI:
   grep the page HTML for `"messages":[...]` — each row is `{id, title, date, success}` and the
   `title` already shows `(<from> -> <to,to>) <subject>`. That alone identifies the two mails from
   one submit.
2. **The queue table has no Reply-To column** (`replyTo` appears nowhere in
   `messaging-queue-enonic-app` or `-lib`). The header lives in the stored node: `manage/index.js`
   writes the whole `mailBody` as `c.data.body`, and the app's API returns it as `request`.
3. **API URL** (stable shape, no guessing needed):
   `<base>/admin/com.example.messagingqueueapp/messaging-queue/_/com.example.messagingqueueapp:get-message-details?id=<rowId>`
   → `{request: {from, to[], subject, body, contentType, replyTo}}`. This is the machine-readable
   proof; use it before touching the DOM.
4. **For the screenshot** use the row's blue **eye** button → *Message details → `Request:`* modal.
5. **Absence of the key is itself evidence.** A mail sent by an older build has no `replyTo` key at
   all. Rows from before and after a deploy sit in the same table, so the queue doubles as a
   before/after contrast — worth capturing when the change *is* the header.

## Pitfalls

- **The modal does not fold JSON on v1.0.1** — it renders the whole pretty-printed payload as text.
  (An earlier note claimed it renders folded and needed expanding before screenshotting; that was
  wrong for this build. Check the modal text before planning expand clicks.)
- **The modal clips long values horizontally** — its `<pre>` does not wrap, so a `media:attachment`
  download URL is cut off mid-`href` and OCR of the shot proves nothing. Set
  `white-space: pre-wrap; word-break: break-all` on the modal's `pre`/`code` before the screenshot;
  that reveals the stored value instead of hiding it.
- **The queue silently drops rows while the send still succeeds.** Symptom in `server.log`, same
  second as the send: `(/lib/messaging-queue/manage/index.js) Error getting settings:
  java.lang.NullPointerException` and `Error creating log object: …`. The mail goes out; only the
  queue row is lost. **Do not re-POST to make a row appear** — take the payload from a row produced
  by an equivalent submit on the same build and config, and say so in the chat report.
- **The log is authoritative for delivery and recipients**, the queue only for payload. Log Viewer
  search does **not** filter the view — it highlights, and `document.body.innerText` still holds the
  whole file. Locate the matching `.line` children by index and clip to them.
- Eye icon is view. Never click the red (delete) or green (retry) button. Escape closes the modal
  before opening the next row.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| Row id | `6b8fa09d-2c1c-4a0d-b477-e148733d0e46` |
| `from` | `kavli@leanonsystems.com` (site sender) |
| `replyTo` | `williams@example.com` (the address the editor configured) |
| Log line | `INFO com.example.app - (/services/content-download-form/content-download-form.js) Email successfully sent to: …` |
