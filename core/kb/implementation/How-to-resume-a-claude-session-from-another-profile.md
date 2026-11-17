---
id: how-to-resume-a-claude-session-from-another-profile
when_skills: [resume-session, run-plan]
inputs: [devkit profile session-find, devkit profile session-pull, Claude Code transcripts, Claude Desktop local_*.json]
outputs: [one Claude session copied into the current profile or stock]
stop_if: [asked to touch Cursor or Codex stores, asked to delete the source session]
read: section
prose: caveman-lite
---

# Resume a Claude session from another profile

A session is `<config dir>/projects/<cwd slug>/<id>.jsonl`, an optional sidecar folder `<cwd slug>/<id>/`, and for Desktop an index file `<user data dir>/claude-code-sessions/<account>/<org>/local_*.json` whose `cliSessionId` is the id. Each Desktop fork runs with its profile's `CLAUDE_CONFIG_DIR`, so a Desktop session is a Code session plus one index file.

## Procedure

1. Find: `devkit profile session-find --title "<text>" [--since YYYY-MM-DD] [--profile NAME] --json`. Titles: Desktop `title`, else the last `custom-title`, else the last `ai-title` record in the transcript. Transcripts are scanned from `--since`, default 30 days.
2. Copy: `devkit profile session-pull --session <id> --source <name>`, review, then `--apply`. Target is `--target`, else `DEVKIT_PROFILE`, else `stock`.
3. Open in Claude Code: `cd <cwd> && claude-<profile> --resume <id>` (`claude` for stock).
4. Open in Claude Desktop: restart the target Desktop, then open it from the sidebar.

## Pitfalls

- Live Desktop pickup without a restart was not verified (plan step S1 needs a person watching the sidebar). Until it is, tell the operator to restart.
- The commands run from the kit checkout until a kit release is cut and `devkit profile sync` runs: `python3 ~/Workspace/Projects/devkit/devkit.py`.
- Stock transcripts are rewritten by the 5-minute cron that exports Codex and Cursor sessions and backfills titles ([How-to-backfill-claude-jsonl-ai-titles](How-to-backfill-claude-jsonl-ai-titles.md)); a stock source can warn "changed in the last 60 seconds" without a new turn.
- While the target app runs, only files the target lacks are added; replacing one is refused. A newer target copy is always kept.
- The Desktop index goes to the target's org folder with the most sessions. Override with `--org DIR`.
- Never write the source, never delete, never touch Cursor or Codex stores.
