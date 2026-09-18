---
id: how-to-fetch-jira-issue-via-atlassian-mcp
when_skills: [download-jira-task]
read: section
prose: caveman-lite
---

# How to fetch a Jira issue via Atlassian MCP

## When not to run

If `~/.agents/prds/<ISSUE-KEY>.md` already exists, **do not run this How-to**
(no `getJiraIssue`, no `agentctl jira fetch`) unless the user explicitly asked
to refresh. Pipeline skills (`plan-task-evidence`, `plan-implementation`) read
that file. Worked failure: PROJ-434 evidence planning, 2026-09-15.

## Prefer agentctl (no MCP)

When `~/.agents/.auth/jira-api-token.yaml` exists, do not use MCP:

```bash
agentctl jira fetch <ISSUE-KEY>
```

That call is `getJiraIssue` + attachment bytes + `render_issue.py` in one process. Other MCP equivalents: `agentctl jira capabilities`.

Use the MCP steps below only when the token file is missing or `agentctl jira` returns an auth/permission error you cannot fix in REST.

## Prerequisites

- Prefer `user-atlassian-rovo-preview` for `download-jira-task` (needs `attachment` bytes next). `plugin-atlassian-atlassian` is metadata-only for attachments.
- Always discover tool schemas (`GetDynamicTools`) before `CallDynamicTool`.
- Jira base: `https://example.atlassian.net`

## Resolve cloudId

1. Try `cloudId: "example.atlassian.net"` first on `getJiraIssue`.
2. If that fails, call `getAccessibleAtlassianResources` and use the returned `id` for the client site.
3. Authenticate only when the namespace reports `needsAuth` or a call returns an auth error (`mcp_auth`).

## Fetch issue + comments

Prefer a single `getJiraIssue` call with markdown bodies. On rovo-preview also pass `fieldsByKeys: true` when `fields` uses keys such as `attachment`.

```text
CallDynamicTool
  namespace: user-atlassian-rovo-preview
  toolName: getJiraIssue
  arguments:
    cloudId: "example.atlassian.net"
    issueIdOrKey: "<ISSUE-KEY>"
    fieldsByKeys: true
    responseContentFormat: "markdown"
    fields:
      - summary
      - description
      - status
      - issuetype
      - priority
      - assignee
      - reporter
      - created
      - updated
      - project
      - comment
      - attachment
```

Older docs may show `plugin-atlassian-atlassian` / `CallMcpTool` / `server:` — same fields via the current dynamic MCP surface. Compact rovo-preview views omit `attachment` unless it is in `fields`. `download-jira-task` must pass this `fields` list and must **not** pass `view: compact`. `responseFields` is allowed only if attachment metadata still returns.

## Field extraction

| Field | Source |
|-------|--------|
| Title | `fields.summary` |
| Description | `fields.description` (markdown string) |
| Status | `fields.status.name` |
| Type | `fields.issuetype.name` |
| Priority | `fields.priority.name` |
| Project | `fields.project.name` (`fields.project.key`) |
| Reporter | `fields.reporter.displayName` |
| Assignee | `fields.assignee.displayName` (or "Unassigned") |
| Created / Updated | `fields.created`, `fields.updated` |
| Comments | `fields.comment.comments` — array sorted by `created` ascending |
| Attachments | `fields.attachment[]` — numeric `id`, `filename`, `size`, `mimeType` |

Each comment object: `id`, `author.displayName`, `created`, `updated`, `body` (markdown when `responseContentFormat` is `markdown`).

If `fields.comment` is missing, make a second call with `fields: ["comment"]` only and merge.

`download-jira-task` always persists attachment **bytes** after this fetch. Paths and curl: [How-to-download-atlassian-attachments.md](How-to-download-atlassian-attachments.md). Requires `user-atlassian-rovo-preview`. List local paths first with `render_issue.py <payload.json> --list-attachments --json`.

## Errors

| Situation | Action |
|-----------|--------|
| Issue not found | Report key tried; ask user to verify access |
| MCP auth failure | Ask user to authenticate the Atlassian plugin |
| Empty description / no comments | Still usable; callers write empty sections explicitly |
