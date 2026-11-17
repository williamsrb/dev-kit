---
id: how-to-run-the-dark-factory
when_skills: [run-plan, plan-implementation]
inputs: [bin/agentctl_factory.py, config/factory/pipelines]
outputs: [factory run state under factory/TASK-ID]
stop_if: [hooks cannot stay on for headless workers]
read: whole
prose: caveman-lite
---

# Run the dark factory

`agentctl factory` runs the standard task pipelines end to end in fresh headless sessions and stops at `awaiting_human_review`. Guide for the operator and for a later dashboard.

## Headless workers (S1 spike, 2026-10-26)

Measured with `claude -p` in a scratch repo, `claude-haiku-5-5`, cost USD 0.011 for 7 turns.

- Skills resolve headless: the `init` event lists every installed skill (`draft-commit-message`, `run-plan`, `validate-impl`, ...). The user-level `~/.claude` config is loaded without `--bare`.
- Hooks fire headless: `hook_started` / `hook_response` events appear in `stream-json` with `--include-hook-events --verbose`. The response-format Stop hook did not trap the reply; no exemption is needed, so `hooks/response-format-check.py` stays unchanged.
- A tool call that needs approval is denied, not asked: `This command requires approval`, and the `result` event carries `permission_denials[]` (`tool_name`, `tool_input`). A git write that is not allowlisted is therefore denied by the permission layer before any hook decision matters. The engine records `permission_denials` as a hook/permission denial and parks (`needs_human`).
- Working flags: `--session-id <uuid>`, `--model`, `--effort`, `--max-budget-usd`, `--output-format stream-json --verbose`, `--permission-mode acceptEdits`, `--allowedTools ...`. Run with stdin redirected from `/dev/null`.
- Put the prompt right after `-p` (`claude -p "<prompt>" --model …`). `--tools`, `--allowedTools`, `--disallowedTools` and `--add-dir` take several values, so a prompt placed after them is swallowed and the call fails with `Input must be provided either through stdin or as a prompt argument`. Seen in `bin/agentctl_local.py` on 2026-10-31.
- `stream-json` shape: first `system/init` (`session_id`, `model`, `permissionMode`, `skills`, `tools`), then `assistant`/`user` message events, `rate_limit_event`, and a final `result` with `subtype`, `is_error`, `total_cost_usd`, `duration_ms`, `num_turns`, `session_id`, `permission_denials`, `result` (text).
- A per-task Playwright MCP is not visible to a worker unless the worker is given it. A fresh worker saw no `mcp__playwright*` tool and `ToolSearch` found none. Evidence steps pass `--mcp-config` for the task's instance (`agentctl playwright` knows the URL).
- Allowlist set used for build steps: `Read Edit Write Skill` plus read-only `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`. Anything else (including `git add`) is denied.

## Commands

Run from the git repo of the task. The Jira pipeline needs the task branch checked out; the factory never creates or switches branches.

```bash
agentctl factory start FOO-1 --dry-run
```

- `start TASK` picks the pipeline: a task id matching the tracker's `key_regex` means `tracker-standard`, a slug with `prds/<slug>.md` means `brainstorm`. Flags: `--pipeline`, `--context <handoff>`, `--path standard|plan_only|skip_evidence|park` (only the operator can `skip_evidence`), `--dual plan`, `--vendor claude|codex`, `--max-cost-usd`, `--max-hours`, `--foreground` (tests, debugging), `--dry-run` (steps, roles, models and gates; no model call), `--progress`, `--verbose` (see Watching a run).
- `status [TASK] [--json]`: files only, no model or network call. No id lists all runs. Unknown id exits 1.
- `resume TASK | --all`: replays the event log, marks a step left `running` by a dead engine as `interrupted`, restarts it in the recorded repo. Steps already `ok` are not rerun. An interrupted attempt does not use the retry budget. A parked run also resumes (after the human action).
- `stop TASK`: SIGTERM to the engine and worker group, clears a stale lock, run stays resumable.
- `step TASK STEP-ID`: one step through the same engine path (gates, events, limits).
- `watch [TASK] [--progress] [--verbose]`: read-only live view of a run; see Watching a run.

## Watching a run

`watch` tails `events.jsonl` and the running step's `raw.jsonl`. It never talks to the engine, so a run started detached stays observable and Ctrl-C only detaches the viewer: the engine keeps running and the viewer prints `reattach: agentctl factory watch TASK` (exit 130). The two views combine.

- `--progress` (the default when no flag is given): `[3/7 43%] [####------] run-plan 12m04s/90m $3.41/$40 run 1h12m/6h loop 1`. `3/7` counts `ok` and `skipped` steps against the total fixed at `run_started`, so a route or mode skip makes the count jump and a review-loop reset moves it back (the loop number is shown). Inside a running step it shows elapsed time against the step timeout, never an invented percentage. A `--only-step` or `step` run has total 1.
- `--verbose`: one timestamped line per engine event (gates, retries, escalations, route, park, ...) and, for the running worker, assistant text (`| ...`), tool calls with truncated arguments (`$ Bash ...`), permission denials (`! denied Bash`) and the final worker line. Tool result bodies, prompts, step summaries and hook or thinking events are never printed. Codex streams fall back to the event type plus bounded text. Attaching mid-run replays the engine events and starts the worker log from the current end of `raw.jsonl`.
- Both flags: on a terminal the progress line stays on the last line and the log scrolls above it. Without a terminal one plain line per progress transition is printed, no control characters. Lines are cut to the terminal width (80 when unknown). No colors are used.
- `start`, `resume` and `step` take the same flags: they launch detached as before, then attach. They are refused with `--foreground`, and with `resume --all`. `watch` without an id follows the one live run.
- The viewer exits when the run reaches a terminal state: 0 for `awaiting_human_review`, 1 for `parked`, `stopped`, `failed`, or a run whose engine died (`interrupted`, after a 10 s grace period for the engine to take its lock). A parked or failed run also prints its `human_action`.
- It only reads: engine liveness comes from the pid in `lock` and that process's command line, never from taking the lock.

## State layout

```text
$AGENTS_HOME/factory/TASK-ID/        ($AGENTS_FACTORY_DIR overrides)
  run.json      snapshot derived from events.jsonl, schema_version 1
  events.jsonl  append-only: run_started, step_started, gate, retry, escalate, decision, route, park, resume, kit_changed, ...
  lock          engine pid; flock plus liveness
  steps/<nn>-<id>/  prompt.md raw.jsonl stderr.log report.json [denials.json] [kb-proposals.md]
  findings/     bounded validate-impl findings handed back to run-plan
  variants/     A, B, judge, compare.json (plan-stage dual run)
```

Pipelines are data in `config/factory/pipelines/` (`tracker-standard.json`, `brainstorm.json`, shared `tail.json`; `release-replay.json` and `release-review.json` are started by `agentctl release`, not by `factory start`; see [How-to-run-a-release-integration.md](How-to-run-a-release-integration.md)), `schema_version` 1. Limits, worker tools, git policy and the tracker flavor are in `.agentctl`, not in code or pipelines.

## Related-issue steps

Two steps run the `find-related-issues` skill, so parallel work by other developers is seen before it costs a rework.

- `related-plan` (after `route`, before `plan-implementation`, role `explore`): tracker epic, siblings, links, and the files the PRD names against released history and unreleased branches. Always `ok`; its summary lines reach `plan-implementation`, which turns them into Constraints and TBD or Local PO decisions.
- `related-impl` (after `validate-plan`, before `run-plan`, role `follow`, pre gate `branch_is_task`): rescan with the plan's files and read the other branches' hunks on shared files. An unacknowledged contradiction is a `blocked` report, so the run parks with `blocked` and the contradiction in `park.action`. The plan owner records the decision in the plan (Constraints, Non-Goals or `decisions.md` naming the issue key) and runs `resume`; the rerun marks it acknowledged and passes. Neither step runs on the `plan_only` path past `validate-plan`.
- TODO, not run yet: one real `AGENTS_HOME=${HOME}/.agents agentctl factory step` for `related-impl` on a task with a parallel branch. Confirm the `blocked` park, record a decision in the plan, `resume`, and confirm the acknowledged path passes. Until then both steps are covered only by tests with a fake Jira. Delete this line once it passes.
- Files written: `$AGENTS_HOME/prds/<TASK-ID>.related.json` and `prds/<TASK-ID>/related/<KEY>.md`. The scan never fetches: a stale-refs warning means an unfetched remote branch is invisible.

## `status --json` schema

Summary first: `task_id`, `state` (`running|interrupted|parked|stopped|failed|awaiting_human_review`), `schema_version`, `pipeline`, `mode`, `repo`, `branch`, `current_step`, `progress` (`done`, `total`, `percent`, `current`, `loop`), `cost_usd`, `route` (verdict, path, signals, override, blockers), `park` (`reason`, `action`, `step`), `human_action`, `engine_pid`, `created_at`, `finished_at`, then `steps[]` with `id`, `status`, `skill`, `attempts`, `model`, `session_id`, `cost_usd`, `started_at`, `finished_at`, `reason`. A dashboard reads these files and calls `agentctl factory step` for manual runs; no engine change is needed.

## Park reasons

`human_in_the_loop`, `route_park`, `tbd_open`, `wrong_branch`, `blocked_by_dependency`, `contradiction`, `foreign_check_touched`, `no_auth_state`, `evidence_failed`, `git_baseline_violation`, `needs_human` (permission or hook denial, no blind retry), `blocked`, `retries_exhausted`, `review_loop_exhausted`, `reviewer_model_collision`, `dual_unavailable`, `supervisor_park`, `cap_cost`, `cap_time`, `adapter_missing`, `deterministic_step_failed`, `never_stage`, `no_commit_message`, `commit_message_trailer`, `commit_failed`, `fetch_failed`, `no_base_branch`, `merge_failed`, `merge_conflict`, `fast_forward_detected`, `protected_branch`, `push_rejected`, `push_unverified`, `review_merge_conflict`, `review_merge_failed`, `review_deploy_failed`, `review_deploy_timeout`.

After the graph, `agentctl release open|merge|check|status|remove|audit|bugs` merges the tasks into `release/<version>` in its own worktree, runs the project's tests and audits the result: [How-to-run-a-release-integration.md](How-to-run-a-release-integration.md).

### Release order parks

Built by `agentctl release graph` (saved under `prds/releases/`); the `release_order` pre-gate on `run-plan` reads the latest graph that lists the task and never starts the other task.

- `blocked_by_dependency`: a high-confidence `hard` dependency has no commit carrying its exact key on the first existing `[git] base_branches` ref, even after one `git fetch origin` (the park text says when the fetch failed). Land the dependency, then `agentctl factory resume TASK`. A dependency on the base but not in the branch only warns; integrate pulls it in.
- `contradiction`: a high-confidence contradiction edge involves the task. Both quoted sides are in the park text. Record the decision in the plan or the tracker, regenerate the graph, then resume.
- `foreign_check_touched`: the work edits, deletes or renames a test or evidence file whose latest base commit carries another task's key (post-gate on `run-plan`, no retry), or `integrate` hit a merge conflict in such a file (the merge is aborted). Restore the file, or agree the change with the owning task, then resume.

## Rules the engine enforces

- Git: the engine owns the writes. `commit` stages everything (refusing `[git.factory] never_stage` matches) and commits with the drafted message; `integrate` fetches, merges the base into the task branch with `--no-ff` (a worker resolves conflicts, the engine adds and commits; unresolved conflicts abort the merge and park), and verifies the tip is a merge commit; Every commit the engine makes (the work commit and the merge commit) ends with a blank line and `[git.factory] signature` (`Automated by: agentctl factory`); `sign_message()` in `agentctl_factory.py` does it, idempotently, and is the function any future review-request step must use for the description. `push` pushes the task branch (no force, never a `[git] protected_branches` entry) and verifies `origin/<branch>` equals HEAD. Fast-forward is never used and never allowed. Workers cannot write git unless `[git.factory] worker_git_writes = true`; even then `--ff*` and force stay denied.
- `commit` is off when `[git.factory] commit = false`; `integrate` and `push` are off when `push = false` or there is no `origin`. The HEAD and index baseline is checked after every worker step and re-recorded after each git step.
- The only tracker write is the evidence comment, posted by `post-evidence` (the only step given `[tracker.<kind>] post_tools`) after `validate-evidence` passed. Any failed evidence step parks with `evidence_failed` and no post.
- Reviewer model differs from the author recorded in state; a collision switches vendor if an adapter exists, else parks.
- The supervisor can only move toward more caution; invalid or timed-out output is `park`.
- The engine runs `agentctl playwright stop TASK` on every terminal state once an evidence step started.

## `.agentctl`

One TOML file at the harness root (`$AGENTCTL_CONFIG`, then `$AGENTS_HOME/.agentctl`, then `~/.agents/.agentctl`) holds every agentctl default: `[tracker]` (kind, default `jira`) and `[tracker.<kind>]` (key regex, download skill, post tools, write guard); `[git]` and `[git.factory]` (base branches, protected branches, commit, push, force_push, never_stage); `[factory]` with limits, worker tools, vendor, pipelines; `[hooks]`. Reader: `bin/agentctl_config.py` (stdlib, no defaults: a missing file stops the factory and makes the safety hooks fail closed). When the file is absent, `python3 bin/agentctl_defaults.py` writes it (target `$AGENTS_HOME/.agentctl`, else `~/.agents/.agentctl`, or `--path`); its first line says the values come from that script, it never overwrites an existing file without `--force`, and `--print` shows the defaults. The script holds the only copy of the defaults text, and a test keeps the shipped `.agentctl` identical to it. The values a run uses are copied into `run_started`, so editing the file never changes a run in flight.

`[tracker.jira]` also carries the constants the Jira code used to hardcode: `site`, `token_file` (relative to the harness root), `browse_path`, `key_regex` (anchored, tells a tracker id from a local slug), `key_pattern` (finds keys in text, group 1), `issue_fields` and `skip_comment_authors`. Consumers: `agentctl_jira.py` (`default_site`, `default_token_path`, `issue_fields`, `render_script`), `agentctl.py` (`issue_re`), `agentctl_plan.py` (`task_mode`, which prints the tracker kind, `jira` by default, or `local`), `find-related-issues/scripts/related.py` and `download-jira-task/scripts/render_issue.py`. `[git] base_branches` is read by `related.py` and the factory. Not migrated: the Jira REST implementation itself (`CAPABILITIES`, field handling), skill prose, the evidence comment lint rules (they describe Jira's comment format), and the `generate-worklogs` Slack query.

`[git_host]` is the same idea for the git server: `kind = "gitlab"` by default, a `[git_host.github]` table ships ready, and `review_request_terms` makes MR, PR, merge request and pull request one concept (see `How-to-switch-the-git-host-flavor.md`).

A new tracker flavor is a `[tracker.<kind>]` table with the same keys plus `kind = "<kind>"`; pipelines reference it as `@tracker.<key>`. `kind = "none"` leaves local pipelines only.

## Pitfalls

- Source lives in `$HOME/.agents`; in the personal profile `$AGENTS_HOME/bin` and `config` link into the installed devkit release, so edit the source checkout and run the live gate with `AGENTS_HOME` unset.
- `--bare` would skip hooks; workers never use it.
- Codex reports no cost: it is recorded as unknown and bounded by wall-clock and attempts.
- `devkit_cli/export.py` has no root-level section, so `.agentctl` at the harness root is not exported yet; ship it with a `root` section in the allowlist when devkit profiles need it. Allowlist directory entries (`factory/pipelines`) work; globs (`*.json`) match nothing.
- `bin/agentctl.py` imports `agentctl_disk`, `agentctl_git`, `agentctl_tools`, `agentctl_disk_collectors`, `agentctl_disk_scan`, none in `bin.core` of `export-allowlist.json`; an exported agentctl cannot import. Reported to the operator, not changed.

## Pipeline steps (25 tracker, 24 brainstorm)

Counts from `config/factory/pipelines/tracker-standard.json` (25 steps) and `brainstorm.json` (24 steps) after factory-kb-harvest added `kb-harvest` as the last tail step (`skipped` with `no harvest signals` when the run has none). `sync-inbox`, `sync-outbox` and `sync-notice` run only when `[sync] enabled`; `download-issue` and `post-evidence` run in tracker mode only.

Tracker order: `download-issue`, `route`, `related-plan`, `plan-implementation`, `validate-plan`, `plan-rehearsal`, `sync-inbox`, `related-impl`, `run-plan`, `validate-impl`, `lint-commit`, `commit`, `integrate`, `sync-outbox`, `sync-notice`, `push`, `rehearsal-gate`, `deploy-review`, `plan-evidence`, `validate-plan-evidence`, `await-review`, `run-evidence`, `validate-evidence`, `post-evidence`. Brainstorm (`brainstorm.json`) has no `download-issue` step; otherwise its order matches the tracker list. The review environment deploys from an integration branch (`review` in client repos), not from the task branch, so evidence waits for `deploy-review` and `await-review`.

- `deploy-review` (builtin): when origin's project has a `[review_env."group/repo"]` table and `[git.factory] deploy_review = true`, merges the task branch into its `branch` with `--no-ff` in a temporary worktree (signed message `Merge branch 'TASK' into review`), pushes it, and verifies `origin/<branch>` is that merge commit. The task checkout is never touched. A branch that already contains the task head is left alone. A push rejected because the shared branch moved is retried from a fresh fetch, three times in all. A conflict parks with `review_merge_conflict` and the exact commands; nothing is pushed and no worker resolves it, since the other side is someone else's unreleased work.
- `plan-rehearsal` (model step, after `validate-plan`, skill `plan-data-rehearsal`): runs only when routing gave a rehearsal-able hard stop (`irreversible-operation` or `existing-data` with `rehearsal.required`). It writes `plans/<ID>/rehearsal.md` and `rehearsal.json` and adds no worker tool. The run then parks `rehearsal_ready`. Read `rehearsal.md`, then `agentctl factory resume <ID> --approve-rehearsal`. A plain `resume` is refused. Approval binds the sha256 of `rehearsal.json`. On route path `plan_only` the run finishes `awaiting_human_review` after `plan-rehearsal` instead.
- `rehearsal-gate` (builtin, before `deploy-review`): skipped with `no rehearsal required`, or with `gate.argv is null: <reason>`. Otherwise it fails closed without an approval (`rehearsal_ready`), parks `rehearsal_changed` when `rehearsal.json` differs from the approved hash, and parks `rehearsal_drift` when a source hash or an expected value differs. It runs only the approved `gate.argv` with `python3 -I`, in the backup folder `prds/<ID>/review-backup/`, never an install.
- Install-kind `[review_env."group/repo"]` (`kind = "install"`, with `artifact`, `backup`, `install`, `restore`, `verify`): `deploy-review` verifies the built artifact's sha256 through `verify` and otherwise parks `operator_install` with the install and restore commands. The factory never installs. Park reasons `backup_missing`, `artifact_missing`, `artifact_ambiguous` and `install_unverified` name the fix. Branch kind is unchanged.
- `[factory.repo_tools."group/repo"] allowed_tools`: adds worker tool patterns for that repo's origin project only (for example `Bash(npx eslint:*)`).
- `run-evidence` parks `browser_instance_mismatch` before the worker starts when the task's `instance.json` names another id or name, a dead pid, or a port that does not answer. Revive with `python3 ~/.agents/mcp/playwright.py revive <ID>`.
- `await-review` (builtin, before `run-evidence`): polls the git host's deployments of `environment` every `poll_s` until the newest successful one contains the task head (`git merge-base --is-ancestor`). The newest deployment that contains the head failing or being canceled parks with `review_deploy_failed`; no such deployment within `timeout_min` parks with `review_deploy_timeout`. It also runs with `deploy_review = false`, so a human merge passes it.
- Both are skipped for a repo without a `[review_env]` table, and `--path skip_evidence` skips `await-review`.

- `related-plan` and `related-impl` run `find-related-issues` (read only). `related-impl` reports `blocked` for an unacknowledged contradiction, which parks the run; record the decision in the plan and `resume`.
- `run-evidence` captures only and never posts. `validate-evidence` reviews it on another model; failed shots come back as blockers and loop to `run-evidence` (limit `review_loops`, same as `validate-impl` to `run-plan`). `post-evidence` runs only after validation.
- `kb-harvest` (model step, role `follow`, skill `harvest-kb`, last in the tail): runs when the digest has signals, reads `digest.json` in its step folder, and writes proposals only. Pipelines are read from `$AGENTS_HOME/config/factory/pipelines`, so an agents home whose copy predates this step will not run it.
- Unverified live: the split post, and `integrate`/`push` against a real remote. A conflict resolution is not re-validated; the push goes to review where a human reads it.

Pitfalls (factory-kb-harvest, 2026-11-06):

- The workspace-write sandbox allows `/tmp` by default. A probe that expects a write to fail must place its target outside `/tmp` and outside the sandbox's working directory, for example under `$HOME`.
- `AGENTS_HOME` selects the data and the pipelines (`config/factory/pipelines`, `factory/`, `kb-inbox/`, `harness/`), while the code runs from `~/.agents/bin`. A profile home that is a devkit copy lacks new pipeline steps, KB inbox and harness state (`harness/checks.json`) until the copy is refreshed. The weekly timer failed for exactly that reason before it was bound to the harness home.
- Run `AGENTS_HOME=<home> agentctl harness schedule install` with the home that holds `harness/checks.json`.

## Hooks

Workers carry the env var named by `.agentctl [factory] env` (`AGENTCTL_FACTORY`). Hooks read their policy from `.agentctl` through `bin/agentctl_config.py`:

- `hooks/response-format-check.py` skips factory workers (`[hooks] response_format_skip_factory`): formatting is for the operator's chat.
- `hooks/claude-git-guard.py` for factory workers follows `[git.factory]`: commit and push are allowed when the file says so, never a fast-forward, a force push or a push of a `[git] protected_branches` entry; commit or push is denied when switched off; every other `ask` (reset, rebase, clean) becomes `deny`. Operator sessions keep the old policy (push denied, commit asks).
- `hooks/jira-write-guard.py` (tracker-agnostic despite the name) denies the MCP tools in `[tracker.<kind>] write_tools` and prints `write_guard_hint`.
- A missing or unreadable `.agentctl` makes the git guard deny commit and push for workers and the write guard block. The installed profile hooks link into the devkit release, so these edits apply after the hooks are redeployed.

## Live rehearsals (S29, 2026-10-27)

Both ran with `AGENTS_HOME` unset, real `claude` workers, `--path skip_evidence`. Costs are from the Claude `result` events; `commit`, `integrate` and `push` are engine steps and cost nothing.

Offline: throwaway repo with a bare remote whose `main` moved, brainstorm pipeline, engine and worker killed during `plan-implementation` then `resume`. Total USD 2.68 (plus 0.54 spent in the interrupted attempt), 327 s after the resume. Result: only the interrupted step reran, a work commit signed `Automated by: agentctl factory`, a `--no-ff` merge commit `Merge origin/main into fac-live-2` (also signed), `origin/fac-live-2` equal to HEAD, `awaiting_human_review`.

| Step | Model | USD | Seconds |
|---|---|---|---|
| route | opus-5-5 | 0.52 | 43 |
| related-plan | haiku-5-5 | 0.02 | 39 |
| plan-implementation | sonnet-5-5 | 0.38 | 57 |
| validate-plan | opus-5-5 | 0.65 | 52 |
| related-impl | sonnet-5-5 | 0.19 | 21 |
| run-plan | sonnet-5-5 | 0.30 | 41 |
| validate-impl | opus-5-5 | 0.44 | 36 |
| lint-commit | sonnet-5-5 | 0.19 | 30 |

Tracker run: `INFRA-141` from its worktree (`devkit-multitask/INFRA-141`, cut from `origin/master`), tracker pipeline. Total USD 5.33 (3.20 until a park, 2.13 after the fix and `resume`), about 2060 s wall clock including the park. Result: signed commit `[INFRA-141] Report every behind file in export --check, grouped by section` (5 files, 214 insertions), `master` had not moved so `integrate` found the branch up to date, `origin/INFRA-141` equal to HEAD, `master` untouched, no tracker write.

| Step | Model | USD | Seconds |
|---|---|---|---|
| download-issue | sonnet-5-5 | 0.22 | 37 |
| route | opus-5-5 | 0.53 | 55 |
| related-plan | haiku-5-5 | 0.02 | 42 |
| plan-implementation | sonnet-5-5 | 0.70 | 184 |
| validate-plan | opus-5-5 | 1.48 | 208 |
| related-impl | sonnet-5-5 | 0.54 (2 attempts) | 61 |
| run-plan | sonnet-5-5 | 0.92 | 849 |
| validate-impl | opus-5-5 | 0.70 | 519 |
| lint-commit | sonnet-5-5 | 0.24 | 46 |

Findings: the first tracker run parked at `related-impl` because `git merge-base` matched the forbidden `git merge` pattern (`\b` after `merge`); fixed with a whitespace lookahead and a test. A worker command using `$(...)` is denied by the permission layer and only noted (`denials_noted`). Limits are still uncalibrated: the whole tracker run used about USD 5 of the USD 40 cap. Not covered live: the evidence steps and a base that moved on the tracker run (covered offline).

## Redeploy (S30, 2026-10-27)

Two dev-kit repos exist. `~/Workspace/Personal/dev-kit` is the scrubbed public export (its `core/` is not installable into the personal profile: `devkit update apply` refuses it as a foreign lineage). The installed kit comes from `~/Workspace/Projects/devkit` (branch `with-extractkit`). Redeploy from there:

1. In that repo: allowlist entries for `agentctl_config.py`, `agentctl_defaults.py`, `agentctl_factory.py`, `config.core: factory/pipelines`, a `root` section with `.agentctl`; `devkit_cli/export.py` reads the `root` section; `devkit_cli/profiles.py` links `.agentctl` and `skills-vendor/ROLES.md` (the factory and `agentctl bench` read `$AGENTS_HOME/skills-vendor/ROLES.md`). A new rule in `~/.agents/rules` must be classified in the allowlist or the installed rules generator fails (it was `unattended-mode-no-gated-commands.mdc`).
2. `./devkit export --apply` (gitleaks gate), `./devkit docs generate`, `python3 -m unittest tests.test_devkit`.
3. `./devkit update apply --from ~/Workspace/Projects/devkit --profile personal` (dry run), then `--apply`. Only the personal profiles move; kaio-squad stays on its release.
4. Check: the profile has `.agentctl` and `skills-vendor/ROLES.md` links, `agentctl factory start FOO-1 --dry-run` resolves 17 steps with `AGENTS_HOME` set.

Changes in the devkit working tree are uncommitted. The same root-section edits were also made in `~/Workspace/Personal/dev-kit` (uncommitted).

## Parallel-issue sync steps (factory-sync, 2026-10-27)

Tracker pipeline only (`modes: ["tracker"]`; brainstorm records them as skipped), and skipped when `[sync] enabled = false` or the repo has no `origin`. Order: `sync-inbox` before `related-impl`; `sync-outbox` and `sync-notice` after `integrate`, before `push`. Read `How-to-sync-parallel-issues-through-review-requests.md` for the design.

- `sync-inbox` lists review requests that target this branch or whose marker names this issue (`agentctl sync scan` does the same read-only). An open factory proposal parks the run with `sync_blocked`; merging or closing it is the acknowledgement. A host or token failure parks with `host_unavailable`, never "no related work".
- `sync-outbox` takes the relation classes from the `KEY (class)` lines of the `related-plan` and `related-impl` summaries and applies the ladder: a proposal (temporary worktree of the related branch, a `build` worker limited to the files in the marker, diff-scope check, signed commit, proposal branch pushed, labelled signed request with the marker), an append to the open request for the pair, or nothing. A contradiction parks with `proposal_contradiction` unless the plan names the issue key. The task checkout (branch, HEAD, index) is verified unchanged; the worktree and the local proposal branch are removed in a `finally`.
- `sync-notice` posts one restricted tracker comment (Jira: `--visibility` from `[tracker.jira] restricted_comment_visibility`) on a related issue that has no branch, after checking the group exists, skipping a comment that already carries the notice marker, and reading the comment back; a read-back without the group parks with `restricted_comment_unavailable` and names the comment id. This is the second permitted tracker write, made by the engine; workers still have none.
- Released or discarded issues are never considered: `agentctl sync scan` skips a related candidate, and `agentctl release graph` leaves out a member, whose status category is `done` or whose status name is in `[tracker.jira] closed_statuses` (default Closed, In Production, Released, Discarded, Backlog; case-insensitive). The release graph names the skipped keys in a warning; `agentctl release graph --include-closed` keeps them. `agentctl factory start` refuses a tracker task in such a status (an unreadable tracker does not block it).
- A proposal pair whose earlier factory request was closed without a merge is never reopened or repeated automatically: the outbox action is `confirm` and the run parks with `proposal_needs_confirmation`. Add the line `confirm-proposal: KEY` to `plans/TASK/sync-confirmed.md` and resume to allow one.
- New park reasons: `sync_blocked`, `proposal_needs_confirmation`, `host_unavailable`, `proposal_contradiction`, `restricted_comment_unavailable`. `agentctl factory status` shows `sync` (last scan) and `sync_writes`; `agentctl sync status TASK` lists the `sync_*` events from files.
- The `sync` pipeline (`related-impl`, `sync-inbox`, `sync-outbox`, `sync-notice`) re-runs the scan on a finished task: move the task's old run directory aside first, the state directory holds one run per task id.

### Real GitLab and Jira run (factory-sync S11, 2026-10-27)

Repo `williams/devkit`, branches `INFRA-141` (pushed earlier) and `INFRA-142`, token `factory_token`.

- No-branch case: the `sync` pipeline on `INFRA-141` while `INFRA-142` had no branch. `related-impl` (sonnet) classed `INFRA-142` as `dependency` and `INFRA-90` as `context`; `sync-notice` posted comment `541113` on `INFRA-142` with visibility `group:leanon`, read back OK. Cost USD 0.23, 66 s. First try parked: `agentctl jira comment` refuses a second comment on an issue the same day (the S1 test comment); the notice now passes `--allow-second`, its own marker lookup being the duplicate guard.
- Proposal case: the full tracker pipeline on `INFRA-142` (USD 5.91, about 25 min over two runs). `run-plan` first reported blocked, because `INFRA-141` was not in its base (a hard dependency cannot be implemented before the other branch lands); I merged `origin/INFRA-141` into the branch with `--no-ff` by hand, re-recorded the git baseline with a `baseline_updated` event, and resumed. `sync-outbox` then opened request `!2` from `proposal/INFRA-142-into-INFRA-141` into `INFRA-141`: label `factory-proposal`, marker block that parses back (class `dependency`, three files), signature as the last line after a blank line. The task checkout stayed clean, the temporary worktree and local proposal branch were gone. `!2` was closed and its remote branch deleted afterwards; `!1` (S1 test) is closed too. The `INFRA-141` and `INFRA-142` branches are left in place for the operator to merge or delete.
- Findings: a dependency needs the other branch merged first, which the factory does not do (it merges only the base); the first-unique-commit tie-break counts commits merged in from the other branch, so after such a merge both branches share the oldest commit and the issue key decides.

## Harvest: proposals from friction (factory-kb-harvest)

The engine builds a bounded digest of a run's friction and a `kb-harvest` step (role `follow`, skill `harvest-kb`) turns
it into proposals. Nothing applies itself: the operator reviews each proposal and applies or rejects it.

**State layout** (per run folder `factory/<TASK>/`):

- `digest.json` in `steps/<nn>-kb-harvest/`: the digest the harvest reads. Signals `S1…Sn` with a stable `key`
  (`retry:<step>:<class>`, `park:<reason>`, `gate:<step>:<gate>`, `denial:<tool>:<input head>`, `kit_changed:<step>`,
  `learning:<step>`, `outlier:<step>`, `finding:<step>`). Keys are what `agentctl harness measure` counts.
- `steps/<nn>-<id>/kb-proposals.md`: knowledge proposals (shared format: `## <target>`, `- kind:`, `- evidence:`,
  optional `- covers:` and `- keys:`, one fenced body).
- `steps/<nn>-<id>/harness-proposals.md`: skill lessons (see below).
- `kb-decisions.jsonl` and `harness-decisions.jsonl`: append-only decision logs. A decision counts only while the
  proposal at its ref still has the same `sha`, so a rewritten proposal is pending again.

**The `kb-harvest` step**: the last step of the tail pipeline (after `post-evidence`), no post gate, no modes. It is
skipped with `no harvest signals` when the digest has nothing. Learnings come from the report's optional `learnings` key
(at most 3 strings of 300 characters) for model steps outside `deterministic` and `explore`.

**Review** (`<ref>` is `<TASK>:<step-id>:<n>` for factory, `<session-id>:chat:<n>` for chat, `review:<date>:<n>` for
harness review):

```bash
agentctl kb proposals list --task <TASK>
agentctl kb proposals show <ref>
agentctl kb proposals check <file>        # exits 1 when any proposal is invalid
agentctl kb proposals apply <ref>         # unstaged; re-validates; refreshes the bucket index
agentctl kb proposals reject <ref> --reason "<why>"
```

Invalid proposals (missing evidence, a target outside the owned buckets, a stale diff, `calibration/` or
`offline-reference/`) are listed as `invalid` and cannot apply. They never fail or retry the step that wrote them.

**Status**: `agentctl factory status <TASK>` prints `kb proposals pending`, `kb proposals invalid`, `harness proposals`,
`kit writes by workers` (attributed) and `kit changed outside attribution` (git saw a kit change no worker call
claimed; visibility only, nothing is reverted or parked).

**Kit deny**: every Claude worker gets `Edit(//<home>/<folder>/**)` deny rules for `skills/`, `kb/` and `rules/` (Edit
covers Write and NotebookEdit). A Bash write is not blocked; it shows up as `kit changed`.

**Harness-repo refusal**: the factory refuses start, resume and step on a harness repo (the agents home inside the
repo, or the repo or one direct child holding both `kb/` and `skills/`). This is structural, so a devkit export matches
too. Reason: a worker on the kit would change the harness it runs on. `resume --all` skips such a run and prints why.

**Automatic harvest**: when a run parks (not on `cap_cost` or `cap_time`, the operator's spend limits) and has signals,
the engine runs `kb-harvest` once. The run keeps its state and the tail harvest stays pending. A harvest error becomes an
`auto_harvest_failed` event and never masks the park.

**Codex workers**: the sandbox writable roots are the repo, the run folder, `plans/<TASK>`, `prds` and
`[factory.worker] codex_writable_extra`. The kit is not listed. Probe (2026-11-06, codex-cli 0.166.0, no model call):
`codex sandbox -c 'sandbox_mode="workspace-write"' -c 'sandbox_workspace_write.writable_roots=["DIR"]' -- touch DIR/ok`
succeeds (DIR is a scratch folder), and a write under another folder fails with `Read-only file system`. The `-c` array replaces the
config's array rather than merging into it, which is why the list is complete on its own.

**Harness proposals**: skills, rules, hooks and the MCP catalog change only through `agentctl harness proposals`.
`harvest-kb` writes skill lessons to `harness-proposals.md` as an `edit` of an existing skill file only. `harness
proposals apply` writes unstaged, refuses while a factory run is `running`, and reports the checks for the touched folder
(`agentctl skills audit` for `skills/`, `generate-agents-md.py --check` for `rules/`, a JSON parse for
`mcp/catalog.json`). It never reverts a failed check.

**Chat harvest**: a `SessionEnd` hook (`hooks/kb-digest-session-end.py`) writes the chat digest to
`kb-inbox/<session>/digest.json` when it has signals. It makes no model call and never blocks the session end. Errors go to
`history/.state/hook-errors.log`. The same hook serves Codex (`Stop` event, rewritten after each turn, no session-end event
exists) and Cursor (`sessionEnd`) with a vendor argument (`kb-digest-session-end.py codex|cursor`); those digests carry a
`vendor` field. Codex yields `error`, `denial` and `correction` signals, Cursor only `correction` (its transcript has no
tool results). `agentctl kb digest --vendor codex|cursor` builds one by hand. Batch harvest: `agentctl kb harvest --pending [--limit 5] [--dry-run]`, oldest first,
one `harvest-kb` run per folder (role `follow`). Retention: `agentctl kb inbox prune --older-than 30d`. Memory candidates:
`agentctl kb digest --memories`. Chat sessions can also run `/harvest-kb` in the session, which follows the skill's
"In chat" section.

**Weekly timer**: `agentctl harness schedule install|status|remove` writes a systemd user timer (`OnCalendar=Mon 07:00`,
`Persistent=true`) that runs `agentctl harness weekly`: scan (60 days), measure, inbox prune. No model call. Install with
the agents home you want it to read: `AGENTS_HOME=<home> agentctl harness schedule install`.

See also the harness review loop in `How-to-run-the-harness-review-loop.md`.
