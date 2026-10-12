---
name: download-jira-task
description: "Download a Jira issue (description + comments + attachments) to ~/.agents/prds/<KEY>.md via agentctl jira fetch (API token) or Atlassian MCP fallback. Use to fetch, export, or save a Jira task by key or URL. | recommendedRole: deterministic | aliases: fetch-jira-task, export-jira-task, save-jira-task, jira-task-offline."
metadata:
  recommendedRole: deterministic
  aliases: fetch-jira-task, export-jira-task, save-jira-task, jira-task-offline
  cliDependencies:
    required: [agentctl, python3]
    optional: [curl]
---
## Local deterministic first

Resolve the key with `agentctl task resolve --cwd <repo> --text <request> --json`. If `~/.agents/.auth/jira-api-token.yaml` exists, fetch with one CLI call and stop:

```bash
agentctl jira fetch <KEY>
```

That writes `~/.agents/prds/<KEY>.md` and attachment bytes. Do not call Atlassian MCP. After the PRD exists, later skills read it with `agentctl markdown slice`, not whole-file `Read`.

MCP remains the fallback when the token file is missing. Then: save connector JSON, `scripts/render_issue.py --list-attachments --json`, mint `downloadJiraIssueAttachment` URLs, `scripts/run_download_commands.py`, then `scripts/render_issue.py --output ~/.agents/prds/<KEY>.md --json`.

# Download Jira Task

This skill is the **Jira source adapter**. Local/kebab-slug tasks use `handoff` (PRD). Pipeline skills must **not** call this when `mode` is `local`.

Fetch a Jira issue's **description**, **comments**, and **attachments** from client Jira. Write markdown to the task cache and save attachment bytes beside it.

**Jira base URL:** `https://example.atlassian.net`  
**Output directory:** `~/.agents/prds/`  
**Output filename:** `<ISSUE-KEY>.md` (e.g. `AS-1171.md`)  
**Attachments:** `~/.agents/prds/<ISSUE-KEY>/attachments/<id>-<filename>`

Always download `fields.attachment` when this skill runs a live fetch. Do not skip bytes because they are images, PDFs, or large. Empty `fields.attachment` is success (`## Attachments (0)`). Prefer `agentctl jira fetch` (REST). Do not use `image-to-disk`. MCP fallback still runs the minted `downloadCommand` (`curl --output`).

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md`. Write/read this task's PRD only. Do **not** read other tasks' PRDs, impl plans, or evidence plans. Do not open attachment binaries unless the user asked to inspect one.

## Knowledge base (mandatory How)

Preferred fetch (API token, no MCP):

`~/.agents/kb/implementation/How-to-fetch-jira-issue-via-atlassian-mcp.md` (agentctl path at the top)

MCP fallback (cloudId, `getJiraIssue` fields including `attachment`, extraction, auth errors): same How-to, MCP section.

Attachment bytes via REST are part of `agentctl jira fetch`. MCP mint+curl: `How-to-download-atlassian-attachments.md`.

This skill owns the offline file contract, template, cascade rules, and the requirement to always persist attachments. The KB owns live tool usage.

### Nested vs standalone

| Mode | How to detect | After save |
|------|---------------|------------|
| **Nested** (prerequisite) | Caller stated `called_from: plan-implementation` or `called_from: plan-task-evidence`, or the active skill flow is ensuring an offline copy exists | Confirm path only — **do not** prompt to cascade into `plan-implementation`. If `~/.agents/prds/<KEY>.md` already exists and the user did not ask to refresh, **skip the fetch** (no MCP, no `agentctl jira fetch`) |
| **Standalone** | User invoked this skill directly | After confirm, **ask** whether to continue into `plan-implementation` (Step 5) |

If an offline file already exists and the user did **not** ask for a newer version, prefer using it (or skip re-download) — still apply Step 5 cascade rules for standalone runs when the file is ready. Skipping a refresh also skips re-fetching attachments.

## Step 1 — Resolve the issue key

Resolve `<TASK-ID>` per `How-to-resolve-task-context.md` (message key/URL → branch → worktree folder → ask once). Do not ask for full PRD/plan paths.

## Step 2 — Fetch from Jira

**Prefer REST.** If `~/.agents/.auth/jira-api-token.yaml` exists:

```bash
agentctl jira fetch <ISSUE-KEY>
```

Confirm `status` is `ok` or `partial`, then go to Step 4. Do not also call MCP.

**MCP fallback** when the token file is missing: follow the fetch How-to on **`user-atlassian-rovo-preview`**. Keep comment `id`s for every comment you write. Omit automated Git integration comments per formatting rules below.

MCP fallback fields and mint steps:

```text
fields: [summary, description, status, issuetype, priority, assignee, reporter,
         created, updated, project, comment, attachment]
```

Save the raw payload JSON, then:

```bash
python3 scripts/render_issue.py <payload.json> --list-attachments --json
```

`--list-attachments --json` is inventory only (`id`, `outputPath`, `dir`). It is not a download URL source. `mkdir -p` the listed `dir`.

**Bulk (two or more attachments):** mint every URL first. For each listed `id`, `executeRead` `downloadJiraIssueAttachment` with that numeric `attachmentId` and absolute `outputPath`. Collect the returned `downloadCommand`s. Do **not** run curl between mints. Write one JSON file of `{id, outputPath, downloadCommand}` objects, then run it once:

```bash
python3 scripts/run_download_commands.py <commands.json>
```

Check the script exit code. Do not invent curl flags. Do not pass media UUIDs from HTML/ADF.

**Single attachment:** the same MCP mint, then run that one `downloadCommand` (or the same script with a one-element list). Keep this path for "fetch me this one file".

Zero attachments: skip MCP download calls; still write `## Attachments (0)`.

If `user-atlassian-rovo-preview` is missing: still write the PRD from whatever `getJiraIssue` you have; list attachments in markdown; report download as **failed** in Step 4. Do not silently omit them.

## Step 3 — Write the markdown file

1. Ensure `~/.agents/prds/` exists; write `~/.agents/prds/<ISSUE-KEY>.md`.
2. Tell the user the absolute path and the attachments directory.

### Markdown template

```markdown
# <ISSUE-KEY> — <summary>

**Jira:** https://example.atlassian.net/browse/<ISSUE-KEY>
**Project:** <project name> (<project key>)
**Type:** <issuetype>
**Status:** <status>
**Priority:** <priority>
**Reporter:** <reporter>
**Assignee:** <assignee>
**Created:** <created>
**Updated:** <updated>

---

## Description

<fields.description — preserve markdown as-is>

---

## Comments (<count>)

<For each kept comment, in chronological order:>

### Comment <id> — <author.displayName> — <created ISO date>

<body — preserve markdown as-is>

---

## Attachments (<count>)

Directory: `~/.agents/prds/<ISSUE-KEY>/attachments`

- `<id>-<filename>` — <filename> (<mimeType>, <size> bytes); id `<id>`

---

*Exported from Jira on <today's date>*
```

**Formatting rules:**

- Preserve description and comment bodies verbatim.
- **Omit Git automated Jira comments:** skip any comment whose `author.displayName` is `Solutions Jira x GitLab` (GitLab commit/MR mention spam). Do not write them to the PRD. `<count>` is the number of **kept** comments only.
- Strip Jira-only blob image URLs (`blob:https://media.staging.atl-paas.net/...`) — note `(image attachment — see ## Attachments)`.
- Convert `<custom data-type="smartlink" ...>` wrappers to plain URLs when visible.
- Do not invent acceptance criteria or implementation plans.
- Attachment stored names come from `render_issue.py` (`<id>-<basename>`). Do not rename after download.

## Step 4 — Confirm

Reply with issue key + Jira link, saved PRD path, attachments directory, kept comment count, and attachment download counts (ok / failed / none).

## Step 5 — Cascade into `plan-implementation` (standalone only)

**Skip** when nested (`called_from: plan-implementation`).

When standalone and the file is ready, ask (prefer `AskQuestion`):

> Offline copy saved. Continue into **plan-implementation** to draft the implementation spec under the agent plans dir (`~/.agents/plans/<ISSUE-KEY>/`)?

- **Yes** — follow `plan-implementation` next (must **not** re-download).
- **No** — stop.

Do **not** auto-start `plan-implementation` without approval.

## Examples

**Input:** `https://example.atlassian.net/browse/AS-1171` → `~/.agents/prds/AS-1171.md` + `~/.agents/prds/AS-1171/attachments/`  
**Input:** `download NTF-1209` → `~/.agents/prds/NTF-1209.md` + attachments dir

## Errors

| Situation | Action |
|-----------|--------|
| Issue not found / MCP auth | Per fetch How-to |
| Empty description | Write file; note "No description" |
| No comments | Write `## Comments (0)` with a short note |
| No attachments | Write `## Attachments (0)`; still success |
| Rovo preview missing / downloadCommand fails | Write PRD; keep ## Attachments metadata; report failed ids in Step 4 |
