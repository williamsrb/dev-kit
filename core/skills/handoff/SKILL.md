---
name: handoff
description: "Compact this conversation into a Context Summary or persist it as a PRD at ~/.agents/prds/<slug>.md. Use when handing off to another agent, saving a local brief, or turning chat into task context for plan/implement/validate. | recommendedRole: inherit | aliases: persist-local-task, persist-prd, context-summary."
argument-hint: "Context Summary or PRD — optional slug or next-session focus"
metadata:
  recommendedRole: inherit
  aliases: persist-local-task, persist-prd, context-summary
---

# Handoff

Two result formats: **Context Summary** (default) and **PRD**. Pick one, write one file, stop.

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md` when a `<TASK-ID>` is needed. Do not invent a Jira key. Redact secrets (API keys, passwords, tokens, personal data).

## Pick the format

| Format | When | Output |
|--------|------|--------|
| **Context Summary** | Continue this chat in a fresh session. Session glue, not a spec. | `/var/tmp` — not the workspace, not `~/.agents/prds/` |
| **PRD** | Persist chat as task context for `plan-implementation` / `run-plan` / `validate-impl`. | `~/.agents/prds/<slug>.md` |

Triggers (any one is enough):

- **Context Summary:** “context summary”, “handoff for next session”, “compact this”, next-session focus with no ask to persist a spec.
- **PRD:** “PRD”, “persist as PRD”, “handoff as PRD”, “save as task”, “use as context for implementation”, or a nested `called_from: plan-implementation` when the PRD is missing.

If the user named a format, use that name verbatim. If both could apply, ask once. If they passed arguments, treat them as the next-session focus (Context Summary) or the slug/title (PRD).

Do not duplicate content already in specs, plans, ADRs, issues, commits, or diffs — reference those paths.

Templates: [references/formats.md](references/formats.md). Load only the chosen format.

## Context Summary

1. Write the Context Summary template from `references/formats.md`.
2. Include **Suggested skills** — names the next agent should invoke.
3. Save under `/var/tmp` (`/var/tmp/handoff-<slug-or-focus>-<YYYYMMDD>.md`), always, never `$TMPDIR` or `/tmp`: those are cleared on reboot. Do not write into the repo or `~/.agents/prds/`.
4. Tell the user the absolute path. Hard-stop. Do not cascade into planning.

## PRD

`<slug>` is the `<TASK-ID>`. Kebab-case. Never a fabricated `PROJ-123`.

1. Resolve the slug: user-supplied kebab → else derive from the title/focus (lowercase, hyphenate, strip junk) → else ask once.
2. If the slug matches `[A-Z][A-Z0-9]+-\d+` (ignore case), **stop**. That path is a Jira PRD (`download-jira-task`). Do not overwrite it from chat.
3. If `~/.agents/prds/<slug>.md` exists and the user did not ask to replace it, update in place only the sections this conversation changed. Do not re-download Jira.
4. Write the PRD template from `references/formats.md`. Required H2s: `## Description`, `## Acceptance Criteria`. Keep `## Comments` even when empty so `agentctl markdown slice` stays compatible with the shared PRD template (Jira exports use the same H2s).
5. Confirm the absolute path. Nested `called_from: plan-implementation`: confirm only — do not prompt to cascade. Standalone: ask whether to continue into `plan-implementation`.
