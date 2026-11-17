---
name: harvest-kb
description: "Turn one run's or one chat session's friction digest into KB proposals (kb-proposals.md) and skill lessons (harness-proposals.md) for the operator to review. Headless from the factory (digest.json beside the report path) or in chat (builds the digest itself). Never applies anything."
metadata:
  recommendedRole: follow
  cliDependencies:
    required: [agentctl, rg]
---

# Harvest KB

Read friction signals, decide which ones teach a reusable fact or a skill lesson, and write proposals. The operator
applies them with `agentctl kb proposals apply` (KB) or `agentctl harness proposals apply` (skills, rules, hooks, MCP).
You never write under `kb/`, `skills/`, `rules/`, `hooks/` or `mcp/`, and you never apply a proposal.

## Mode

- **Factory** (`called_from: factory` or `AGENTCTL_FACTORY` set): read `digest.json` in the folder of the report path the prompt names. Write `kb-proposals.md` and `harness-proposals.md` in that same folder.
- **Chat** (anything else): build the digest with `agentctl kb digest --latest --json` (add `--vendor codex` or `--vendor cursor` when running in Codex or Cursor). Its `first_prompt` must match the current session's first request. If it does not, stop and ask the operator for the session id, then run `agentctl kb digest --session <id> --json`. Write into `kb-inbox/<session-id>/` (the path the digest prints, its folder).

## Signals

The digest holds `signals` (each with `id` S1…Sn, `key`, `kind`, `step`, `detail`), `kit_reads`, `step_proposals` (existing
proposal files of the run), `rejections` (the last 20 decided rejections with reasons) and `has_signals`.

Kinds: `retry`, `escalate`, `park`, `gate`, `denial`, `kit_changed`, `finding`, `learning`, `outlier`, and in chat
`error`, `denial`, `correction`, `interrupt`, `validator_report`, `memory`.

1. Group signals by cause (the `key` prefix and the step). A group is one repeated friction.
2. `outlier` alone proposes nothing. Propose only when another signal of the same step shows the cause.
3. Skip one-off facts about this task (ticket ids, a single bad input). Propose only what a later run would reuse.
4. Never repeat a target that a rejection in `rejections` already refused for the same reason.

## Routing

For each group, decide the kind of lesson:

- **Knowledge** (a fact about a repo, tool, platform, command or check): `kb-proposals.md`.
  - Find coverage in the owned buckets (`_shared`, `implementation`, `testing`, `validation`, `worklog`): read the
    bucket's `llm-index.md` rows by topic and keywords, then `rg -l` over the writable buckets.
  - Covered and the How-to was read in this run (`kit_reads` or `kb_reads`): propose an `edit` to that How-to.
  - Covered and not read: report it as a routing gap and name the index row. Do not propose a duplicate.
  - Not covered and reusable: propose a `new` How-to.
  - `agentctl docs search` indexes only platform docs under `kb/offline-reference`. It is never a proposal target.
- **Skill lesson** (how a skill's procedure runs: a step it skips, an order it gets wrong, a check it lacks, a
  validate-impl finding that traces back to a planning step): `harness-proposals.md`. Only an `edit` of an existing
  file under a real `skills/<name>/` directory. Never a new skill, a rule, a hook or the MCP catalog from here.
- `learning` signals are a worker's own account of what cost time. Turn one into a proposal only when it names a
  reusable fact or procedure, and route it by the two rules above.
- `validator_report` (chat only): a validate-plan or validate-impl verdict and the files it changed. Use it as
  evidence for a skill lesson or a KB fact, never as a proposal by itself.
- `memory` (chat): a feedback memory the session wrote. Promote it only when the lesson is reusable, as a KB edit or
  How-to. Cite the memory path in `evidence:`. Never edit or delete the memory file.

## Proposal format

Append to an existing file; never rewrite or renumber it. One `## <target>` heading per proposal, then fields, then one fenced body:

````markdown
## kb/implementation/How-to-x.md
- kind: edit
- evidence: retry run-plan gate_retry 2026-11-06T12:00:00Z; denial Bash(cd …)
- covers: S3, S5
- keys: retry:run-plan:gate_retry, denial:Bash:cd …

```diff
--- a/kb/implementation/How-to-x.md
+++ b/kb/implementation/How-to-x.md
@@ -1,3 +1,4 @@
…
```
````

- `kind: new` takes the full file as the body. `kind: edit` takes a unified diff with `--- a/<target>` and `+++ b/<target>`.
- `evidence:` names the signal ids and the keys, or the memory path. Every proposal needs one.
- `covers:` lists the signal ids, `keys:` copies the `key` of each covered signal.
- The body of `new` is the How-to in the KB's How-to format (`kb/_shared/How-to-*` shape: frontmatter, Scope, Procedure, Pitfalls).

## Steps

1. Read the digest (factory) or build it (chat). Stop with a one-line report when `has_signals` is false.
2. Group the signals. For each group, decide knowledge or skill lesson, and check coverage.
3. Write the proposals into `kb-proposals.md` and `harness-proposals.md` in the folder (only the files you have content for).
4. Run `agentctl kb proposals check <file>` on each file you wrote. It exits 1 on an invalid proposal: fix it and check again.
5. Report: `ok` with one line per signal group (proposed, covered and read, covered and not read, skipped and why). List the files in `artifacts`. Never report `blocked` for an empty result.
6. In chat, also print the refs with `agentctl kb proposals list --source chat` (knowledge) and
   `agentctl harness proposals list --source chat` (skill lessons).

Do not invent facts. Every proposal names what in this run showed the need.
