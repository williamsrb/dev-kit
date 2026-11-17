---
name: handoff
description: "Compact this conversation into a Context Summary or persist it as a PRD at ~/.agents/prds/<slug>.md. Use when handing off to another agent, saving a local brief, or turning chat into task context for plan/implement/validate."
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

Context Summary template: [references/formats.md](references/formats.md). The PRD format is written by `write-prd`.

## Context Summary

1. Write the Context Summary template from `references/formats.md`.
2. Include **Suggested skills** — names the next agent should invoke.
3. Save under `/var/tmp` (`/var/tmp/handoff-<slug-or-focus>-<YYYYMMDD>.md`), always, never `$TMPDIR` or `/tmp`: those are cleared on reboot. Do not write into the repo or `~/.agents/prds/`.
4. Tell the user the absolute path. Hard-stop. Do not cascade into planning.

## PRD

Follow `../write-prd/SKILL.md` with **this conversation** as the source (`called_from: handoff`). It owns the slug rules, the Feature/Bug/Report templates, and validation. Pass along any slug or title from the arguments.

Then apply this skill's cascade: nested `called_from: plan-implementation` → confirm the path only. Standalone → ask whether to continue into `plan-implementation`. On no, end the reply with `/plan-implementation <slug>` in a `text` block, right after the 👉 line, for a fresh session.
