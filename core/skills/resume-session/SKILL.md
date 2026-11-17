---
name: resume-session
description: "Continue one Claude session in the profile you are in now, by title: find it across every devkit profile and stock, copy it here, and give the command to open it. Use when a profile hit its quota and the work must continue elsewhere, or to resume a Claude Code or Claude Desktop session from another profile."
metadata:
  recommendedRole: follow
  aliases: resume, pull-session
  cliDependencies:
    required: [devkit]
---

## Local deterministic first

`devkit` does the finding and the copying. Do not search transcript folders by hand.

# Resume a session from another profile

The running session cannot turn into the earlier one. The earlier session is copied into the side you are in and opened there. The id is kept.

## Procedure

1. Run `devkit profile session-find --title "<title>" [--since YYYY-MM-DD] [--profile NAME] --json`. Transcripts are scanned from `--since`, default the last 30 days; widen it when nothing matches.
2. Read `total` and `sessions`.
   - Zero: say so, suggest another title word or an earlier `--since`. Stop.
   - Several: list profile, title, last activity and working folder. Ask which one. Copy nothing until the operator picks.
   - One: continue.
3. Dry run: `devkit profile session-pull --session <id> --source <profile>`. Show the target, the org folder and the files. Keep the target default (`DEVKIT_PROFILE`, else stock) unless the operator names another.
4. Run it again with `--apply`.
5. Close with the printed `open it:` command for Claude Code. For Claude Desktop: restart the target Desktop, then open the session from its sidebar. Live pickup without a restart is not verified.

## Rules

- The source side is never written and nothing is deleted. A newer file on the target is kept; tell the operator when that happens.
- A warning that the source changed in the last 60 seconds means the copy is a snapshot of a session still in use. Relay it.
- Cursor and Codex stores are out of scope. Do not touch them.
- Use `--org DIR` only when the operator names a Desktop organisation folder.
