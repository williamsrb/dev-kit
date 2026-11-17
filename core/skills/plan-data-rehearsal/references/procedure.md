# Data rehearsal procedure

Authoritative text for `plan-data-rehearsal`. Shipped with the skill, so every profile receives it. Scope: a job that writes or deletes shared review data. Output: `plans/<ID>/rehearsal.md` and `plans/<ID>/rehearsal.json`, checked by `scripts/rehearsal.py check`.

## Steps

1. **Inventory (read only).** List everything the job can touch: the target entity types, the fields it sets, and every record it may update or delete. Cite the job's rules as `path:line`. Read state through admin or content APIs, or an existing export. Never call an endpoint that starts a task to read state.
2. **Backups.** Export each affected collection to `review-backup/` as files. Record `{path, sha256}` for each in `backups`. Paths are relative to the backup folder. Backups are files, not a database dump the job reads back.
3. **Sync-delete rule.** If the job deletes target records absent from its input, the input for the rehearsal must be either:
   - a mirror of the current state plus one known delta (for example, one new product row), or
   - a scope redirect: point the job at isolated data (for example, a duplicate folder), as the document-sync case did with an unreferenced-files folder.
   A one-row sheet is not a mirror: it would delete every other record. A fabricated or reduced input is refused by routing (`isolation: reduced-input` is not a valid value).
4. **Offline prediction.** Write a simulator script in `review-backup/` that replays the job's own rules against the exported input and writes a JSON result (`gate.output`). It reports the counts `created`, `updated`, `deleted`, plus the keys in `gate.keys`. Record its sha256 and every other file it reads in `gate.source_hashes`. Put the expected values inline in `gate.expected`, so the approved hash of `rehearsal.json` covers them.
   If no simulator is possible, set `gate.argv` to `null` and state the reason in `gate.reason_if_null`. The factory then skips the gate and says why.
5. **Canary.** Choose one record the job is guaranteed to change on each run (for example, a title with a run counter). The canary proves the job ran and proves the restore. Record it in `canary`. If none is possible, `n/a — <reason>`.
6. **Restore.** For each kind of change in the prediction, one targeted restore command, `covers` set to `created`, `updated` or `deleted`. Deletions need a `deleted` entry: `check` fails otherwise. A platform snapshot may be listed as an extra layer, never as the only restore.
7. **Gate.** Describe the re-check the factory runs right before the install: `gate.argv` (script path relative to `review-backup/`, then arguments), `gate.output`, `gate.keys`, `gate.expected`, `gate.source_hashes`, `gate.timeout_s`. The factory runs `python3 -I` on it, compares the keys, and recomputes the hashes.
8. **Server writes (operator).** For every write to the review server (install, config edit, schedule build, data import, restore), list the exact command and its restore command under `Server writes (operator)` and in `server_writes`. The factory never runs these. It parks with them.
9. **Check.** Run `python3 scripts/rehearsal.py check <ID>` until it reports `ok`.

## Scheduled jobs

- A job on a cron schedule is rehearsed with one slot: a single run near the present, from an uncommitted build, installed and reverted by the operator. A watcher reverts the build at the stated deadline (UTC).
- The evidence plan records this in its `**Scheduled run:**` line (see `plan-task-evidence`).
- Name the server time zone in the wording. A repeating short schedule blurs the canary: one run only.

## Pitfalls

- **A service endpoint is never a status probe.** A GET on a sync or import endpoint started a real sync once. Use admin or content reads.
- **Worker tools cannot be narrowed per step.** The no-server-write rule is this procedure's text plus the operator's read of `rehearsal.md` before approval. It is not a sandbox.
- **A stale export is not a backup of the current state.** Re-export right before the rehearsal, and record the export time.
- **Approval binds the file.** Edit `rehearsal.json` before approval only. A change after approval parks the run as `rehearsal_changed`.
