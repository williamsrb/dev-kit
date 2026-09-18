---
id: how-to-backfill-claude-jsonl-ai-titles
when_skills: [run-plan]
inputs: [~/.claude/projects/*.jsonl, Claude Desktop local_*.json titles]
outputs: [ai-title records in work Claude JSONL]
stop_if: [asked to disable cursor/importClaudeCodeAgents]
read: whole
prose: caveman-lite
---

# Backfill Claude JSONL ai-title for Cursor import

Cursor’s native importer titles from JSONL `aiTitle`, else the first non-meta user prompt, else `Claude Code session`. It does not read Desktop index `title` or JSONL `custom-title`.

## Procedure

1. Script: `~/.agents/bin/backfill-claude-jsonl-ai-titles.py`. Dry-run with `--dry-run`. Single chat: `--session-id <uuid>`.
2. Write work Claude only (`~/.claude/projects`). Do not write Personal; `sync-claude-desktop-sessions.py` fans out.
3. Title source, first useful wins: existing non-generic `ai-title` (leave it) → `custom-title` → Desktop index `title`. Generic strings (`Claude Code session`, `Untitled session`, `.`) are not useful.
4. Insert or replace the `ai-title` line. Do not inject `_comment`. Do not write `*_prompt.md` / `*_result.md`.
5. Batch order in `~/.agents/cron/sync-claude-desktop-sessions.job` and live crontab (`*/5`): Codex export, Cursor export, this backfill, then desktop sync.
6. Ledger/lock/log: `~/.local/share/claude-jsonl-title-backfill/` (not Codex, Cursor, or Claude `sync.lock`).

## Pitfalls

- Opened Cursor composers keep the snapshotted sidebar name. JSONL backfill fixes unopened listings; it does not rewrite `state.vscdb`.
- Do not toggle `cursor/importClaudeCodeAgents`.
- Skip files with no useful custom-title or index title (`skip-no-title`). Do not invent a title from `<command-message>` prompts.
