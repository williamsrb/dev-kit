---
name: plan-data-rehearsal
description: "Draft a reversible rehearsal for a task whose job writes or deletes shared review data (an import or a sync). Writes plans/<ID>/rehearsal.md and rehearsal.json: inventory, backups, offline prediction, canary, restore, gate, and the operator's server writes. Plans only. Makes no server write and calls no endpoint that starts a task. Use from the factory's plan-rehearsal step, or when a plan needs a safe path for an irreversible-operation or existing-data hard stop."
metadata:
  recommendedRole: plan
  aliases: plan-rehearsal, data-rehearsal, rehearse-data-import
  cliDependencies:
    required: [agentctl, python3]
---

## Local deterministic first

Scaffold and check with the script, path relative to this skill dir. Do not hand-write the JSON shape.

```bash
python3 scripts/rehearsal.py init <TASK-ID>
python3 scripts/rehearsal.py check <TASK-ID>
```

`init` writes the skeleton (no overwrite) and creates `<agents home>/prds/<TASK-ID>/review-backup/`. `check` validates both files and exits 1 on any error. Procedure, prediction rules and the JSON schema: [references/procedure.md](references/procedure.md).

# Plan data rehearsal

A task that imports or syncs data into a shared review server cannot be verified without letting the job write. This skill does not make that write safe by trust. It records a reversible rehearsal the operator can read and approve: what the job can touch, what is backed up, what the job is predicted to do, how the prediction is re-checked right before the install, and how each change is undone.

## Hard rules

- **No server write.** The worker reads nothing from the review server to change it, and writes nothing to it. No tool is added to the worker allowlist for this step. Read-only inventory goes through admin or content APIs or existing exports, never a service endpoint that starts a task. A plain GET to a sync or import endpoint is a write; do not use one as a status probe.
- **Every server write is an operator action.** Each one goes under `Server writes (operator)` with its exact command and its restore command. The factory never runs them.
- **Do not reduce the input of a job that deletes.** A job that deletes target records absent from its input (sync-delete) forbids a reduced or fabricated input. Use a mirror of the current state plus one known delta, or redirect the job's scope to isolated data.
- **Snapshot is an extra layer.** A platform snapshot never replaces the targeted restore commands.
- **Cron evidence needs one run.** A scheduled job is rehearsed with a single near-future slot from an uncommitted build, with a watcher that reverts by a deadline. A repeating short schedule blurs the canary.
- **Name server time** in the wording wherever a time appears.
- **Approval is not yours.** Write the rehearsal and stop. The operator approves with `agentctl factory resume <TASK-ID> --approve-rehearsal` after reading `rehearsal.md`. The approval binds the sha256 of `rehearsal.json`, so any later edit blocks the install.

## Inputs

- `<TASK-ID>`, the plan at `<agents home>/plans/<TASK-ID>/`, and the verdict at `<agents home>/prds/<TASK-ID>.autonomy.json` (its `rehearsal` object names `sync_delete` and `isolation`).
- Read the repo's own job code only as far as the inventory needs (path:line for each rule the job applies).

## Workflow

1. `init`, then fill `rehearsal.md` section by section following [references/procedure.md](references/procedure.md).
2. Put the backups under `review-backup/` and record each with its sha256 in `rehearsal.json`.
3. Write the offline simulator as a script inside `review-backup/`. It replays the job's own rules against the export and writes `gate.output`. Record it in `gate.source_hashes`.
4. Run `check` until it passes. A section that does not apply is `n/a — <reason>`, never blank.
5. Report: status `ok`, `rehearsal.md` and `rehearsal.json` in artifacts, and the list of server writes the operator must run.

## Pitfalls

- A simulator that reads the live server is a read the factory cannot bound. Use exports only.
- `gate.argv[0]` must appear in `source_hashes`, or the gate cannot prove what it runs.
- A prediction with deletions and no `restore` entry covering `deleted` fails `check`.
- Do not add `allowed_tools_extra` to any step spec: the rule is this skill's text, not a sandbox.
