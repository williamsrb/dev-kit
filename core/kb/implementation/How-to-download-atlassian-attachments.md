---
id: how-to-download-atlassian-attachments
when_skills: [download-jira-task]
inputs: [Jira issue key or Confluence content/attachment id]
outputs: [local file via returned downloadCommand]
stop_if: [only plugin-atlassian-atlassian is available]
read: section
prose: caveman-lite
---

# Download Atlassian attachments

Prefer `agentctl jira fetch <KEY>` when `~/.agents/.auth/jira-api-token.yaml` exists. That path uses Jira REST `GET /rest/api/3/attachment/content/{id}` and does not mint MCP `downloadCommand`s.

MCP fallback below is only for when the API token file is missing.

Only `user-atlassian-rovo-preview` (Atlassian Rovo MCP Preview, `https://mcp.atlassian.com/v1/mcp/preview`) can fetch bytes via MCP. Catalog: https://developer.atlassian.com/cloud/rovo-mcp/preview/tools/

`plugin-atlassian-atlassian` is the GA remote MCP. It has no download operation.

Download/upload are **discovery operations**, not primary tools. They do not appear in `tools/list`. Find with `discover`, then `executeRead` / `executeWrite`. Do not call `downloadJiraIssueAttachment` as a top-level MCP tool name.

The MCP never writes the file. `executeRead` returns a short-lived URL plus `downloadCommand`. Run that command in the shell. Bytes do not pass through the LLM — not as base64, not as a file blob. Do not paste `downloadUrl` / `downloadCommand` into PRDs or KB — the URL carries a JWT.

`cloudId` is a top-level `executeRead` argument (sibling of `name` / `inputs`), never inside `inputs`. Site UUID or `example.atlassian.net`.

## Procedure — Jira

1. `getJiraIssue` with `fields: ["attachment"]`. On rovo-preview also pass `fieldsByKeys: true`. Compact view omits the field. Each item: numeric `id`, `filename`, `size`, `mimeType`.

### Bulk inventory

For many issues, use `executeRead` `searchJiraIssuesUsingJql` once to retrieve only attachment metadata. `responseFields` keeps the response compact:

```text
CallDynamicTool
  namespace: user-atlassian-rovo-preview
  toolName: executeRead
  arguments:
    cloudId: "<cloudId or example.atlassian.net>"
    name: "searchJiraIssuesUsingJql"
    inputs:
      jql: "<JQL selecting the target issues>"
      fields: ["attachment"]
      maxResults: 100
    view: "full"
    responseFields:
      - "issues.key"
      - "issues.fields.attachment.id"
      - "issues.fields.attachment.filename"
      - "issues.fields.attachment.size"
      - "issues.fields.attachment.mimeType"
      - "isLast"
```

This batches the inventory only. Call `downloadJiraIssueAttachment` once per numeric attachment id to obtain each short-lived `downloadCommand`; the MCP does not offer a batch byte-download operation. Do not run each `downloadCommand` as its own model round-trip. Collect the minted commands, then run them in one process (`download-jira-task/scripts/run_download_commands.py`). A single-attachment fetch may still mint and curl immediately.

2. If the operation name is uncertain, `discover` query `download Jira attachment`. Confirmed name: `downloadJiraIssueAttachment` (`executeRead`).
3. `executeRead`:

```text
CallDynamicTool
  namespace: user-atlassian-rovo-preview
  toolName: executeRead
  arguments:
    cloudId: "<cloudId or example.atlassian.net>"
    name: "downloadJiraIssueAttachment"
    inputs:
      attachmentId: "<numeric id from fields.attachment[].id>"
      outputPath: "./<filename>"   # optional; relative; used only to build downloadCommand
```

4. Run the returned `downloadCommand` from the working directory so a relative `outputPath` lands there. Do not invent curl flags. For one file, run it as soon as it is minted. For many files, mint every URL first, write the commands to JSON, and run `scripts/run_download_commands.py` once. `--list-attachments --json` has no URL; it cannot drive curl by itself.

`download-jira-task` always does this for every `fields.attachment` entry. Use the absolute `outputPath` from `render_issue.py --list-attachments` (`~/.agents/prds/<KEY>/attachments/<id>-<filename>`). `mkdir -p` that directory first. Do not use `image-to-disk`.

`attachmentId` is the numeric Jira attachment id. It is not a filename, not the media UUID in description/comment HTML (`data-id` / `data-media-id`), and not the UUID in `api.media.atlassian.com/file/<uuid>/binary`.

Observed response keys: `attachmentId`, `downloadUrl`, `outputPath`, `downloadCommand`, `instructions`. URL host is `api.media.atlassian.com`. Token lifetime is about 10 minutes.

## Procedure — Confluence

1. `executeRead` `name: "listConfluenceAttachments"` with `inputs.contentId` (page/blog numeric id). Or `getConfluenceAttachment` when the attachment id is already known. Id is digits, or `att` plus up to 19 digits.
2. `executeRead` `name: "downloadConfluenceAttachment"` with `inputs.attachmentId`. Optional `outputPath`, `version` (omit for latest).
3. Run the returned curl/`downloadCommand` immediately.

## Plugin MCP (`plugin-atlassian-atlassian`)

No download tool. `getJiraIssue` `fields: ["attachment"]` returns metadata only. `searchConfluenceUsingCql` can find attachment pages (`type = attachment`) but not bytes. `createConfluenceFooterComment.attachmentId` includes an existing attachment on a comment. `fetch` accepts issue/page ARIs only.

## Pitfalls

- Re-call `executeRead` if the command fails with 401/403/404; do not reuse a stale URL.
- `download-jira-task` always downloads `fields.attachment` into `~/.agents/prds/<KEY>/attachments/`. Blob image URLs in description/comments still strip to `(image attachment — see ## Attachments)`.
- Upload is a different pair (`executeWrite`): `uploadAttachmentToJiraIssue`, `createConfluenceAttachment`. Do not use those to fetch.
- Ignore stale aliases from GitHub comments / LLM writeups: `downloadAttachment`, `getAttachments`, `getAttachment`, `createAttachment`, `getConfluencePageAttachments`. Current names are the `*JiraIssueAttachment` / `*ConfluenceAttachment` ops above. There is no Jira `getAttachments`; list via `getJiraIssue` `fields: ["attachment"]`.
- `JRACLOUD-97830` is an unresolved gap ticket (ACLI/MCP cannot download). Do not treat it as proof the feature exists. Preview ops above are the actual path.
- Discover catalog is session-filtered (OAuth scopes, toolsets, product access). Empty discover is a scope miss, not proof the op was removed.
- Attachment/whiteboard bytes leave `mcp.atlassian.com`. If the **agent sandbox** is on, allow `api.media.atlassian.com` and `*.frontend.public.atl-paas.net` ([preview network allowlist](https://developer.atlassian.com/cloud/rovo-mcp/preview/index/)). Observed Jira download host is the first. Claude Code: `sandbox.network.allowedDomains` in `~/.claude/settings.json` (only if `sandbox.enabled` is true). Cursor CLI: `sandbox.networkAllowlist` in `~/.cursor/cli-config.json` (only if `sandbox.mode` is `enabled`). Codex already has `[sandbox_workspace_write] network_access = true` — no domain list. Do not add these to `webFetchDomainAllowlist`; the path is local `curl`, not WebFetch.
