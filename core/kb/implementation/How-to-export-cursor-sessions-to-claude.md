---
id: how-to-export-cursor-sessions-to-claude
when_skills: [run-plan]
inputs: [~/.cursor/projects/*/agent-transcripts, composerHeaders table]
outputs: [Claude JSONL + Desktop index, cron chain]
stop_if: [destination entrypoint is not cursor-export]
read: whole
prose: caveman-lite
---

# Export Cursor sessions to Claude

One-way native parent chats → work Claude. Personal is a fan-out of `sync-claude-desktop-sessions.py`, not a second writer.

TBD defaults (operator silence, 2026-08-25): parent JSONL only; full corpus (no `--since`); skip when dest SHA diverged (`claude-diverged`).

## Procedure

1. Script: `~/.agents/bin/export-cursor-sessions-to-claude.py`. Dry-run with `--dry-run`. Single chat: `--composer-id <uuid>`. Force one associated/handoff chat: `--force --composer-id <uuid>` (`--force` alone exits).
2. Inputs: `~/.cursor/projects/*/agent-transcripts/<id>/<id>.jsonl`. Skip `subagents/` and `composerHeaders.isSubagent=1`. Drafts (`isDraft=true`) skip when a header exists; most drafts have no parent JSONL.
3. IDs: UUID5 of `cursor:<composerId>` in namespace `https://agents.local/cursor-to-claude`. Title prefix `[cursor] ` once (same as Codex `[codex] `). If the title already starts with `[cursor]`, do not prepend again. `entrypoint=cursor-export`. Do not reuse the raw composer UUID.
4. JSONL `cwd` is the real workspace folder. Dest path uses that slug. Desktop index uses the same `cwd`. Cursor may list the export next to the native composer (Codex echo). Distinct UUID5 + skip-echo keep that from growing.
5. Dest: `~/.claude/projects/<project_slug>/<cli>.jsonl` and `local_<cli>.json` under `pick_org_dir(~/.config/Claude/claude-code-sessions)`. Ledger/lock/log: `~/.local/share/cursor-to-claude-sync/` (`export.lock` is not Codex or Claude `sync.lock`).
6. Batch order in `~/.agents/cron/sync-claude-desktop-sessions.job` and live crontab (`*/5`): Codex export, Cursor export, `backfill-claude-jsonl-ai-titles.py`, then desktop sync.
7. Do not write `~/.agents/history/*_prompt.md` / `*_result.md`. Do not toggle `cursor.sharedSessionFileWatcher.enabled`. Query the `composerHeaders` **table** (`mode=ro`), not ItemTable `composer.composerHeaders`.

## Pitfalls

- Real `cwd` makes Cursor re-list the export as a Claude Code agent. That is the Codex echo: keep it. `skip-echo` is no longer a hard skip for associated composers. Order: already in the export ledger (`entrypoint=cursor-export` or `kind=native`) → keep updating; Cursor title starts with `[cursor]` or `--force --composer-id` and no *other* Claude session has that exact dest title → first force write (overrides `glass.claudeCodeSessionRegistry.v1`); else associated, `[codex]` prefix, or title `Claude Code session` → `skip-echo`.
- `[cursor]` on the Cursor header is an opt-in force, not an echo marker. `[codex]` stays skip-only. Same-name ignores our own UUID5 dest so a lost ledger can re-attach. `--force` does not bypass `claude-diverged` or a non-export dest entrypoint.
- Do not write `[cursor] [cursor]`. `title_from_session` returns the title unchanged when it already starts with `[cursor]`.
- Check `dest_was_edited` **before** the source-SHA ledger skip. Rewrite dest if a prior run still has `/.cursor-export` in JSONL cwd (one-time restore to real cwd).
- Refuse dest whose `entrypoint` is not `cursor-export`.
- Sqlite may be locked while Cursor is open; continue JSONL-only (cwd from `workspace.json` / slug map).
- Do not inject `_comment` into JSON/JSONL.
- First apply is ~318 native chats. Reruns are ledger no-ops until the Cursor JSONL SHA changes.
