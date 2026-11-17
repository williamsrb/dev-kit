---
id: how-to-run-the-harness-review-loop
when_skills: [propose-harness-changes, harvest-kb]
inputs: [harness scan signals file, factory and chat harvest proposals]
outputs: [applied harness changes (unstaged), measurements]
stop_if: [a factory run is running, a check reports failure after apply]
read: whole
prose: caveman-lite
---

# Run the harness review loop

Skills, rules, hooks and the MCP catalog change only through `agentctl harness`. This loop turns evidence into
reviewed changes and checks whether the applied ones helped.

## Procedure

1. Scan: `agentctl harness scan --since 60d`. The signals file has `usage`, `drift`, `bloat`, `kb_reads`,
   `proposals` and `repeated_sequences` (Bash 3-grams in at least 5 sessions).
2. Propose: run `/propose-harness-changes` (role `plan`). It writes
   `harness/proposals/YYYY-MM-DD/harness-proposals.md` and checks it with `agentctl harness proposals check`. With nothing
   to propose it writes nothing.
3. Review: `agentctl harness proposals list --source review` and `show <ref>`. Also list the lessons from harvests:
   `agentctl harness proposals list --source factory` and `--source chat`.
4. Apply one at a time: `agentctl harness proposals apply <ref>`. Apply refuses while a factory run is `running`. It
   writes unstaged and prints the checks for the touched folder. A failed check is reported; apply never reverts. Fix
   the file in a new change, not by undoing the apply.
5. Measure: `agentctl harness measure --window 30d`. A proposal under 7 days old is `too recent`; one without
   `keys:` is `not measurable`. Results go to `harness/signals/<date>_measure.json`.

## Pitfalls

- A `remove` of a file that git does not track is refused. Remove tracked files only.
- `skills-vendor/` and symlinked skill folders are never writable through a proposal.
- A rejected proposal stays in its ledger with its reason; `propose-harness-changes` reads that ledger so it does not
  propose the same change again.
- The weekly timer runs scan, measure and inbox prune only. Nothing it does applies a proposal.
