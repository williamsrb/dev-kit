---
name: propose-harness-changes
description: "Turn an agentctl harness scan signals file into harness change proposals (remove zero-use skills, edit drifting skills, new skills for repeated sequences, MCP catalog edits) under harness/proposals. Writes proposals only; the operator applies them with agentctl harness proposals apply."
metadata:
  recommendedRole: plan
  cliDependencies:
    required: [agentctl, rg]
---

# Propose harness changes

Read the newest scan signals, decide which harness changes the evidence supports, and write them as proposals. You never
change `skills/`, `rules/`, `hooks/` or `mcp/` yourself, and you never apply a proposal. `agentctl harness proposals apply`
does that, one ref at a time, after the operator reviews it.

## Input

- The newest signals file under `harness/signals/`, or the file given with `--signals <path>`. Produce it with `agentctl harness scan`.
- The harness ledgers: `agentctl harness proposals list --state rejected --json` shows what was refused and why. Do not
  propose the same change for the same reason again.
- `rules/` for the rule a drift row names.

## What to propose

- **remove**: a skill with zero use in the window, older than the window, and not referenced by another skill or rule
  (`rg -l "<skill-name>" skills rules hooks` finds the references; any hit means no `remove`).
- **edit**: a skill whose drift or repeated sequence you can fix in its own text. The diff must be a unified diff
  against the current file (`git -C <home> diff` style, `--- a/` and `+++ b/` lines).
- **new**: a skill when a repeated command sequence (`repeated_sequences`, seen in at least five sessions) has no existing
  primitive. Give the full `SKILL.md` as the body, under `skills/<name>/`.
- **edit of `mcp/catalog.json`**: an unused heavy MCP server (disable it in the catalog). The body is a diff of that file.

Do not propose anything the signals do not show. An empty result is a valid result.

## Output

Write to `harness/proposals/YYYY-MM-DD/harness-proposals.md` (today's date). Use the shared proposal format: one
`## <target>` heading per proposal, then `- kind:` (`edit`, `new` or `remove`), `- evidence:` (the signals file section
and row, for example `scan repeated_sequences: "git status ; git diff"`), optional `- keys:` when the row carries a key,
then one fenced body (the full file for `new`, a diff for `edit`, empty for `remove`).

Then run `agentctl harness proposals check harness/proposals/YYYY-MM-DD/harness-proposals.md`. Fix any invalid
proposal and check again. Print the refs (`review:<date>:<n>`) with `agentctl harness proposals list --source review`.

With nothing to propose, say so in one line and write nothing.
