---
id: how-to-read-claude-transcripts-for-usage-counts
when_skills: [run-plan, plan-implementation, validate-impl]
inputs: [~/.claude/projects, ~/.agents-profiles/*/claude/projects, ~/.cursor/projects, ~/.codex/sessions, ~/.agents/factory/*/events.jsonl]
outputs: [usage counts that match a hand count, dedupe by uuid, vendor attribution]
stop_if: [a count that disagrees with a hand count over the same window]
read: whole
prose: caveman-lite
topic: read-claude-transcripts
keywords: [read-claude, claude-transcripts, transcripts-usage, usage-counts, transcript, counting, skill, mcp, hook, dedupe, uuid, cursor, codex, native]
---

# Read Claude transcripts for usage counts

Counting skill, MCP, tool or hook use from session transcripts is easy to get wrong. Each rule below was measured on the live stores (2026-11-06). Implementation: `bin/agentctl_harness.py` (`agentctl harness scan`).

## Scope

Record shapes and counting rules for the Claude JSONL stores, plus the Cursor and Codex native stores. Not the signals file layout; that lives in the harness plan.

## Record shapes (Claude)

- One JSON object per line. Every usage record has `type`, `uuid`, `timestamp` (fixed-width `YYYY-MM-DDTHH:MM:SS.mmmZ`, so string comparison orders correctly), `sessionId`, `entrypoint`.
- `assistant` records: `message.content` is a list. A tool call is a block with `type` `tool_use`, `name`, `input`, `id`. One record can hold several tool calls.
- `user` records: `message.content` is a string (a typed prompt or a slash command) or a list. Only `text` blocks count. `tool_result` blocks hold tool output and must not be read for commands.
- `attachment` records: hook events. Hook name is `attachment.hookName` (for example `PreToolUse:Bash`).
- Other types (`api-request-blob`, `api-request-shape`, `ai-title`) carry no usage. Ignore them silently. They are not skips.

## Counting rules

- Skill use: a `Skill` tool call (`input.skill`) plus a slash command. The slash command is `<command-name>/name</command-name>` in a `user` string or `text` block. Strip the leading `/`.
- A `<command-name>` inside a `tool_result` is file or command output that merely contains the tag. Do not count it. Measured: 15 of 1,466 user records.
- MCP: the tool name `mcp__<server>__<tool>`. Split with `name.split("__", 2)`. A per-task server such as `playwright-PROJ-1` is a different server from `playwright`.
- Hook use: `attachment.hookName`. Per-script counts are not in the transcript.

## Dedupe and window

- The same session sits in several stores (`~/.claude`, each profile). Dedupe by record `uuid`. Tool calls also dedupe by `tool_use.id`. Measured: 60% of pre-filtered records were duplicates, so dedupe is required.
- Window is a half-open string comparison: `since <= timestamp < until`. Pin `until` to a UTC day start so reruns match.
- Pre-filter lines by substring (`"tool_use"`, `<command-name>`, `"hookName"`) before `json.loads`. Do not pre-filter on `"entrypoint"`: every record has it.
- Skip mtime-old files before reading (mtime before `since` cannot hold a record in the window). Include subagent files: they live under the session folder and the recursive glob reaches them.

## Vendor attribution

- `entrypoint` `cursor-export` or `codex-export` marks a session copied from another product by `bin/export-*-sessions-to-claude.py`. Attribute those records to `cursor` or `codex`, not `claude`.
- When the native store is read in the same run, drop the export copies from the Claude stores so the same work does not count twice.

## Native Cursor and Codex stores

- Cursor (`~/.cursor/projects/*/agent-transcripts/**/*.jsonl`): records are `{"role": ..., "message": {"content": [...]}}`. No `timestamp`, no `uuid`, no `type`. Tool calls are `tool_use` blocks, for example `Shell`, `Read` (input key `path`). Date each record with the file mtime and key it by `cursor:<session>:<line>`. Mark the source `best_effort`.
- Codex (`~/.codex/sessions/**/*.jsonl`): records `{"timestamp", "ordinal", "type", "payload"}`. Tool calls are `response_item` payloads of type `function_call` (`name`, JSON `arguments`) or `custom_tool_call` (`name`, `input`). Key by `codex:<session>:<ordinal>`. Mark `best_effort`.

## Pitfalls

- A `"message":"tool_use blob"` line does not match the quoted prefilter token `"tool_use"`. Match the exact JSON form when writing fixtures.
- A truncated last line has no trailing newline. Count it as `incomplete last line`, not `malformed json`.
- Cursor `Read` puts the path under `path`; Claude uses `file_path`. Accept both or bloat read-tracking misses Cursor reads.
- `grep` over the stores counts system prompts and rule text that name tool names. Count from parsed records only.
- The window for a Cursor file is its mtime, so a long-running session reads as recent. Say so in the report.

## Verify

Hand count three skills and two servers with the recipe in the harness plan's `validation.md` over the same window. Equal = pass. The scan's raw per-name counts (before alias resolution) are what compare with a hand count.
