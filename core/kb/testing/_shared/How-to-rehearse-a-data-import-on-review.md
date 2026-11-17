---
id: how-to-rehearse-a-data-import-on-review
when_skills: [plan-data-rehearsal, plan-task-evidence, run-plan, classify-ticket-autonomy]
inputs: [job code path:line, review server export, verdict autonomy.json]
outputs: [plans/<ID>/rehearsal.md, plans/<ID>/rehearsal.json, review-backup/]
stop_if: [job has no export path, operator has not approved, a server write is needed by a worker]
read: section
prose: caveman-lite
---

# Rehearse a data import or sync on review

Use when a task's job writes or deletes shared review data: an Excel product import, a PIM document sync, a bulk update. Verification needs the job to run. Running it unprepared is an irreversible-operation hard stop.

Full text: `~/.agents/skills/plan-data-rehearsal/references/procedure.md`. This How-to holds the shape and the incident lessons.

## Procedure

1. Inventory first, read only. List every entity the job creates, updates, or deletes. Cite the job rule as `path:line`. Read state through admin or content APIs or an existing export.
2. Back up. Export each affected collection to files under the review-backup folder. Record sha256 per file.
3. Pick the input. Sync-delete job (deletes records absent from its input): use a mirror of current state plus one known delta, or redirect scope to isolated data. Never a reduced input.
4. Predict offline. Simulator replays the job rules against the export and writes `created`, `updated`, `deleted`. Hash the simulator and every file it reads.
5. Canary. One record the job changes on every run. Proves the run and the restore.
6. Restore per change. One targeted command per `created`, `updated`, `deleted` kind. Platform snapshot is an extra layer only.
7. Gate. Factory re-runs the simulator right before install and compares expected values. Drift parks the run.
8. List every review write as an operator action with its restore command. Worker makes no server write.
9. Check with `rehearsal.py check`. Operator reads `rehearsal.md`, approves with `agentctl factory resume <ID> --approve-rehearsal`.

## Rules

- Sync-delete example: a one-row sheet passed to an import that deletes every other product. Use the full mirror plus one delta.
- Scope-redirect example: a document sync that deletes unreferenced files in its target folder. Point the job at an isolated folder, not at shared content.
- Canary choice: a field the job always overwrites, such as a run counter in the title. A repeating short schedule blurs it; use one slot.

## Pitfalls

- A service endpoint is never a status probe. A plain GET on a sync or import endpoint started a real sync in one incident. Read state through admin or content reads.
- Cron evidence needs one run. Substitute one near-future slot from an uncommitted build, with a watcher that reverts by a UTC deadline. Name server time in the evidence.
- Snapshot restore is coarse. It reverts unrelated changes made since the snapshot. Keep targeted restores primary.
- Approval binds `rehearsal.json` by hash. Any later edit parks the run as `rehearsal_changed`.
