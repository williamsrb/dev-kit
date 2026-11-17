---
id: how-to-run-a-release-integration
when_skills: [run-plan, plan-implementation]
inputs: [bin/agentctl_release_integration.py, config/factory/pipelines/release-replay.json, config/factory/pipelines/release-review.json]
outputs: [prds/releases/SLUG.state.json, prds/releases/SLUG/audit.md, prds/releases/SLUG/audit.json]
stop_if: [the release would be pushed or posted by a release command]
read: whole
keywords: [agentctl, release, open, merge, audit, score, replay, release-bug]
prose: caveman-lite
---

# Run a release integration

## Scope

`agentctl release` makes a release testable as a whole. `graph` and `notify` (phase 1) give the order. The commands below merge the tasks into one integration branch, run the project's tests after each merge, own the failures, and write an audit. No command pushes, posts or writes to the tracker. The audit proves the test environment, not production.

## Prerequisites

- A saved graph: `agentctl release graph --fix-version X` (or `--epic`, `--keys`). For work that did not go through the factory the tickets are usually closed: add `--include-closed`.
- Test commands in `.agentctl`. In the project repo (only `[release]` is read there):

```toml
[[release.tests]]
name = "unit"
kind = "unit"                # unit | integration | e2e | lint | smoke
run = "python3 -m unittest"  # split with shlex, no shell; a pipe needs `bash -c` in the command itself
cwd = "."
paths = ["tests/**"]         # where tests of this kind live (used to close bugs)
timeout_min = 30
env = false                  # true: needs a deployed test environment
[[release.envs]]
name = "review"
base_url = "https://review.example.com"
deploy = ""                  # optional; gets RELEASE_SHA, RELEASE_BRANCH, RELEASE_ENV, RELEASE_BASE_URL
version_url = ""             # optional; body must carry a hex prefix of the integration head
default = true
```

  The profile can carry the same under `[[release.repos."group/repo".tests]]`. Same `name` → the project file wins. `agentctl release tests --list` prints each effective command, its source file and the project id it resolved; a profile key that does not match that id is silently unused. An environment is rejected unless its name or a host label is review, staging, dev, test, qa, sandbox or preview.

## Procedure

1. `agentctl release tests` runs the commands in a checkout (`--kind`, `--name`, `--env`). Logs go to files; only a 40-line failure tail prints. A command over `timeout_min` is killed with its process group (`timeout`).
2. `agentctl release open --release SLUG` creates `release/<version>` in the sibling worktree `<repo>-release/<version>` (your checkout never moves), records `base_sha`, runs every non-`env` command once and stores the failures as the baseline (`pre-existing`, never blocking). `<version>` is the fixVersion name, the epic key, or the slug.
3. `agentctl release merge --release SLUG KEY [--env E]` merges with `--no-ff`. Refused when KEY is not in the earliest wave with unmerged tasks (excluded tasks do not hold a wave open), a high-confidence `hard` dependency is unmerged, KEY is excluded, or KEY has an evidence plan whose progress is not all passed. A task without an evidence plan merges with a recorded warning. A conflict aborts the merge and names the files. Merging an already merged KEY merges its branch again; with no new commits git makes no commit and the checks still run.
4. After each merge every command runs. Evidence of earlier merged tasks that share a graph edge with KEY is replayed when the environment build is confirmed. A failure not in the baseline sets `blocked` and opens bug `<version>-RB<n>` owned by KEY. A failure that fails then passes on its automatic single re-run is `flaky` and opens no bug.
5. `agentctl release status --release SLUG` shows state (`open|blocked|ready|delivered`), waves, open bugs, last result per check and how far the branch is behind the base. `check` re-runs what failed last time; `check --all` runs everything.
6. `agentctl release remove --release SLUG KEY` reverts every merge commit of KEY (`git revert -m 1`, newest first), marks KEY `excluded`, moves its open bugs with it and re-runs the checks. Refused while another merged task has a `hard` edge from KEY. Re-including a reverted task is not supported.
7. `agentctl release audit --release SLUG [--env E] [--deployed SHA] [--review]` runs on `open` or `ready` (refused on `blocked` and `delivered`), runs everything, replays every merged task's evidence once, and writes `prds/releases/SLUG/audit.md` and `audit.json`.

## Deployed build

Replay and `env` commands run only on a confirmed build, in this order: the environment's `deploy` command (run with the `RELEASE_*` variables); else `version_url` whose body holds a hex token of 7+ characters that prefixes the integration head; else `--deployed SHA` matching the head. Otherwise they are `not_run` with the reason. A release command never pushes the integration branch: the deploy is the project's or yours. `[review_env]` and `await-review` are unrelated (they merge task heads into the shared review branch).

## Replay

`release-replay` is a factory pipeline with one step `run-evidence`. For each task `agentctl release` copies only `plans/<KEY>/evidence.md` to `plans/<version>-replay-<KEY>/evidence.md`, rewrites the testing base URL and old origin, the evidence folder, `Mode: local` and `Jira: n/a`, spawns `playwright-<copy-id>` (the factory never spawns), runs the pipeline in the integration worktree, and stops the instance. The task's own plan, progress and captures are never written. No saved auth state for the host → `not_run` naming it, before any spawn.

## Bugs and the verdict

- Owner after a merge: the merged task (`assigned`). A non-`env` failure found later is walked merge by merge in a probe worktree on `release-probe/<version>`; the first failing merge's task owns it. An `env` failure gets `proposed` candidates, newest first, preferring a task whose files match the command's `paths`; `agentctl release bugs --release SLUG --confirm BUG --owner KEY` settles it.
- A bug closes only when `git grep -w -F <bug id>` on the head finds it in a file under a non-`e2e` kind's `paths` and in a file under an `e2e` kind's `paths`, and every check passes including all `e2e`. No `e2e` command configured keeps it open (`no end-to-end command configured`).
- `bugs --draft BUG` writes a tracker draft and prints the `agentctl jira create` command; nothing is created.
- Verdict: `verified` only when every `e2e` command ran on the integration commit and passed (an `e2e` with `env = false` runs on the worktree head; with `env = true` only on the confirmed build), no other check has a new failure and no bug is open. Any new failure or open bug is `blocked`. No `e2e` command, one that did not run, or a `flaky` one is `not verified`. Only `verified` sets `ready`.

## Review and score (`audit --review`)

For work that did not come through the factory. Opt-in: without `--review` no session starts and no score is placed. Each merged task is reviewed report-only against its PRD (`agentctl plan context KEY`, else `agentctl jira fetch KEY --no-attachments`; a delivered plan is context only) through the `release-review` pipeline and a context file naming every path and the exact `git diff <merge>^1 <merge>` range. Criteria are counted once into `prds/releases/SLUG/criteria.json` (PRD path and sha256; edit it to change them).

Score parts: criteria met 50 (proved by running 1, by reading 0.5, unmet or unproven 0), impact on other features and security 20, tests for the criteria 10, evidence quality 10, quality / less code / deslop / performance 10. A Blocker zeroes its part and caps the task and release at 50; a Concern takes a quarter of its part; a Note a twentieth, at most a quarter per part. A part that cannot be assessed is `n/a`: `score = round(100 × earned / assessed)`; the report shows `assessed` and the points proved by running. A deterministic cross-check demotes a `ran` claim whose cited test is missing at head or whose command failed in this audit, and a `read` claim whose file:line is missing. The release score is the mean weighted by criterion count; the report leads with the lowest task. A would-be `not verified` with no Blocker and every task reviewed is `reviewed` (state stays `open`); the report says no end-to-end test proved it and marks model-judged lines. Findings open no release bug. `audit.json` holds every verdict and finding; the score recomputes from it alone.

## Pitfalls

- Settings are read from the release's `repo` (your checkout), never from the integration worktree: a merged task cannot change which commands run.
- Run `agentctl release status` before a re-open: `open` refuses an existing branch or state.
- Replay needs a saved auth state for the environment host (`find-auth-storage.py`); an expired one lands on the login page and fails the step.
- The baseline holds non-`env` commands only. An `e2e` command already failing on the base blocks the release until fixed.
- A fake factory runner cannot prove the replay and review paths. Run each once for real before trusting them.
