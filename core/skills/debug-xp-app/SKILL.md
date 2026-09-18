---
name: debug-xp-app
description: "Debug Enonic XP build (Gradle, TypeScript) and runtime (server.log Nashorn/JS) errors. Use when troubleshooting an XP app or pasting ERROR/WARN log output. | recommendedRole: explore | aliases: xp-app-debugger, xp-debugger, enonic-debugger, server-log-debug."
license: MIT
metadata:
  recommendedRole: explore
  aliases: xp-app-debugger, xp-debugger, enonic-debugger, server-log-debug
  author: enonic
  source: enonic/ai-enonic-marketplace@v0.3.1
  xp-version: ">=7.0"
  cliDependencies:
    required: [agentctl, rg]
    optional: [ollama, enonic, npm]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Run `agentctl logs extract <server.log> --json` before reading raw logs. Open only reported event blocks. For non-critical grouping or summarization, use `agentctl local run`; verify its result against the extracted blocks.

## Cursor IDE

| Claude Code | Cursor |
|-------------|--------|
| Bash | Shell |
| Read / Grep / Glob | Read / Grep / Glob |
| Edit | StrReplace / Write |
| Task (haiku subagent) | Task (`subagent_type`: `shell` or `explore`) |

## Knowledge base (mandatory How)

Log paths, source↔compiled mapping, large-log extraction, deploy-while-debugging, sibling repos:

`~/.agents/kb/implementation/How-to-debug-xp-server-logs.md`

This skill owns Critical Rules and the gated workflow below.

## Critical Rules

1. **Never skip analysis** — complete Phase 2 before fixing.
2. **Compiled JS is runtime truth** — check `build/resources/main/` for Nashorn errors, then map to source.
3. **Server-side logging** — global `log` object only (no `console.log` on server).
4. **Large logs get a subagent** — never read a full `server.log` in the main context (see KB).
5. **Don't deploy unless asked.**
6. **Check sibling repos** — `ls ..` (see KB).
7. **Read logs directly** — never trust user paraphrases of log output.

## Workflow

### Phase 1: Gather

- Pasted logs → parse; classify build vs runtime.
- "Check the logs" → read `$XP_HOME/logs/server.log` via KB large-log recipe when needed.
- "App doesn't load" / empty logs → grep app name; zero matches ⇒ deploy path mismatch (KB).
- "Debug my app" → ask whether to deploy first (CLI preferred per KB).
- Locate source under `src/main/resources/` and compiled under `build/resources/main/`.

**Gate:** Present findings — error type, location, files. Ask before analysis.

### Phase 2: Analyze

- Trace to exact source (file, line).
- Map Nashorn compiled paths back to TS/JS source.
- Check [references/known-patterns.md](references/known-patterns.md).
- Cross-reference `develop-xp7-backend` / React4XP develop skills; XP internals via `gh` if needed.
- Check sibling repos.

**Gate:** Present root cause, evidence, reasoning. Ask before fix.

### Phase 3: Fix

- Propose specific fix with before/after; get approval; apply.

**Gate:** Ask whether to redeploy and verify.

### Phase 4: Verify

- Redeploy only with approval; tail logs; if unresolved return to Phase 2.
- On success, suggest adding a reusable entry to `references/known-patterns.md` (max ~5 lines; prune at ~30).
