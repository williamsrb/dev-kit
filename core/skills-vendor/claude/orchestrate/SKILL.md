---
name: orchestrate
description: "Claude Code only. Split independent workstreams with the Agent tool (claude-haiku-5-5, claude-opus-5-5). Use on `mult`, this skill name, 2+ independent streams, a blocking long command, or an independent review. Skip sequential or overlapping edits. Cursor: ~/.cursor/skills/orchestrate. Jira same-repo: multitask-same-repo."
metadata:
  recommendedRole: task-owner
  cliDependencies:
    required: []
    optional: []
---
# Orchestrate (Claude)

## Host gate

If the **Task** tool is available (Cursor): stop. Do not spawn `claude-opus-5-thinking-high`, `claude-4.5-haiku-thinking`, or any Claude slug. Read and follow `${HOME}/.cursor/skills/orchestrate/SKILL.md` (same bytes as `~/.agents/skills-vendor/cursor/orchestrate/SKILL.md`). Cursor ladder: `cursor-grok-4.7-low` (`deterministic`, `explore`, `follow`, `plan`, `build`), `-high` (`impl-review`, `task-owner`), `-xhigh` (`plan-review`, `quality-gate`).

If **spawn_agent** is available (Codex): follow `~/.codex/skills/orchestrate/SKILL.md` instead.

This copy is for Claude Code only (Agent tool).

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Defaults are the Claude column of `~/.agents/skills-vendor/ROLES.md`, the output of `agentctl bench place` (2026-11-10) against absolute role floors in `benchmarks/bands.yaml`. No default is `max`. Retune with `agentctl bench collect` then `agentctl bench place --markdown` (`agentctl bench rank --markdown` shows cost against quality; `max` is ignored).

Spawn only `claude-haiku-5-5` and `claude-opus-5-5`. Do not spawn `claude-sonnet-5-5`, `claude-fable-5-1` or `claude-haiku-4-5-20251001` unless the user names them: Sonnet 5.5 is never the cheapest config (Haiku `high` matches its `medium` for a twentieth of the list price, and Opus `medium` is cheaper per task), Fable is never the cheapest config in any band, and Haiku 4.5 is below the `deterministic` floor.

A reviewer (`plan-review`, `impl-review`) runs on a different model than the author: Opus reviews Haiku work. `inherit` skills (`handoff`) get no spawn model; they run on the session's model. `max` effort is never a default; use it only when the user asks.

Jira-oriented PRD work on several keys of the same repo is `multitask-same-repo` (worktrees, fresh sessions). Stop here and follow that skill instead.

## Benchmark freshness

Before the first spawn of a session, run `~/.agents/bin/agentctl bench status`. It always exits 0 and prints JSON.

- `stale: false`: say nothing.
- `stale: true`: show its `warning` to the user once, as a ⚠️ line, then continue orchestrating with the current table. Do not wait for a reply and do not run `agentctl bench collect` unless the user asks.
- Command missing or unreadable output: say once that benchmark freshness could not be checked, then continue.

Stale means `benchmarks/latest.yaml` is more than one calendar month old. This check never blocks a spawn.

## Decide Whether to Delegate

Delegate only when at least one condition holds:

- Two or more workstreams can proceed independently.
- A slow command, transfer, test suite, monitor, or data pull would otherwise make the root unavailable.
- A bounded investigation can gather evidence while the root handles the main path.
- An independent review would materially reduce implementation, production, security, payment, or release risk.
- The user started with `mult` or named this skill. That is permission to split; still skip spawn when the work is sequential or would overlap files.

Stay single-agent when the task is small, the next step depends on the immediately previous result, multiple agents would touch the same mutable files, or delegation overhead is comparable to doing the work directly.

## Select the Model

Route on two models: Haiku 5.5 for everything up to planning and building, Opus 5.5 for reviews, coordination and gates. Small models now do the work that needed a top model a generation ago, so start at the cell and escalate only on evidence. Effort is the dial.

| Model | Effort | Role | Use when |
|---|---|---|---|
| `claude-haiku-5-5` | `low` | `deterministic` | Tool runs whose result is cheap to verify. |
| `claude-haiku-5-5` | `medium` | `explore` | Read-only gather: docs, CI inspection, logs. |
| `claude-haiku-5-5` | `medium` | `follow` | Defined skill procedures (commit message, worklogs). |
| `claude-haiku-5-5` | `high` | `plan` | Spec or plan of one surface. |
| `claude-haiku-5-5` | `high` | `build` | Execute a plan or bounded coding. Default coding spawn. |
| `claude-opus-5-5` | `medium` | `impl-review` | Review a delivery against its plan. |
| `claude-opus-5-5` | `medium` | `plan-review` | Review and rewrite a plan before work starts. |
| `claude-opus-5-5` | `medium` | `task-owner` | Substantial independent task; coordination when authorized. |
| `claude-opus-5-5` | `high` | `quality-gate` | Architecture, security, payment, or release-risk. |

Every Claude cell is provisional (Artificial Analysis only or an estimated cost) except where ROLES.md says otherwise.

Escalation: when a review or the checks reject a worker's output, respawn once one effort up on the same model (the factory does the same) and say so in the disclosure. If that fails too, move a Haiku role to Opus `medium`; a reviewer or coordinator stays on Opus. Do not start a role above its cell "to be safe".

If the Agent tool exposes a thinking or effort argument, set it to the effort above. If it does not, name that effort in the assignment and do not invent a slug.

Workers do not spawn further unless the root explicitly assigns coordination of an independently scoped task. Haiku never coordinates; only an Opus `task-owner` does.

## Disclose Every Spawn

Immediately before every Agent call, tell the user:

- The agent task name.
- Exact model slug, such as `claude-opus-5-5`.
- Exact effort, such as `medium` or `high`.
- Role, leaf vs authorized coordinator, and `subagent_type`.

Group simultaneous spawns into one compact update. Describe these as requested configuration. If the runtime reports a different model, disclose the correction.

```text
Spawning:
- `log_explore` — `claude-haiku-5-5`, effort `medium`, Explore — read-only gather
- `impl_auth` — `claude-haiku-5-5`, effort `high`, general-purpose — build
- `impl_review` — `claude-opus-5-5`, effort `medium`, general-purpose — impl-review
- `quality_gate` — `claude-opus-5-5`, effort `high`, general-purpose — quality-gate
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — Haiku medium, Explore

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Use `subagent_type` Explore (or the read-only equivalent). Not Jira evidence capture.

### `follow` — Haiku medium, or Haiku low if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Haiku low only when the CLI is the worker and the result is cheap to verify (wait for CI, copy a path, grep).

### `plan` — Haiku high, general-purpose

Write the spec or plan of one surface from a PRD. Return the plan file path, open decisions and risks.

### `build` — Haiku high, general-purpose

Own one bounded code surface or execute one plan. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `impl-review` — Opus medium, general-purpose

Review a delivery against its plan on a different model than the author. Report findings by severity with file and line; do not fix unless assigned.

### `plan-review` — Opus medium, general-purpose

Review and rewrite a plan before work starts, on a different model than the author. Report gaps in scope, acceptance criteria and risk.

### `task-owner` — Opus medium, general-purpose

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result.

### `quality-gate` — Opus high, general-purpose

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user.

## Delegation Patterns

- **Production incident:** Haiku medium (`explore`) for live health/logs; Haiku high (`build`) for the relevant code path. Root separates cause from mitigation.
- **PR or release:** Haiku medium (`explore`) for exact-head diff/CI; Opus medium (`impl-review`) for substantive review; Opus high (`quality-gate`) for merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate Haiku medium `explore` gathers; Haiku high to reconcile; Opus high for money-sensitive ambiguity.
- **UI work:** Haiku high (`build`) for bounded work; Opus medium (`task-owner`) for a larger independent task.
- **Plan then build:** Haiku high (`plan`), Opus medium (`plan-review`), Haiku high (`build`) per worktree, Opus medium (`impl-review`).
- **Long-running procedure:** Haiku medium (`follow`), or Haiku low when `deterministic`, so the root stays available.
- **Consulting or research:** Haiku medium (`explore`) for sources; Haiku high to normalize; Opus high or the root for the recommendation.

## Assignment Contract

Pass only the context required to succeed:

1. One concrete objective and why it matters.
2. Exact scope: repository, paths, systems, date range, or source set.
3. Ownership boundary, including files the worker may change.
4. Constraints from the user, repository, and applicable skills.
5. Required validation and the expected return format.
6. Read-only or authorized to mutate.
7. Leaf, or an explicitly authorized coordinator.
8. The exact model, effort, and `subagent_type` disclosed to the user.
9. Do not delegate further unless the root authorized coordination.
10. The checkpoint file path, for a worker that mutates files or runs long (see Checkpoints and Resume).

Never send two agents overlapping implementation ownership in the same checkout. Spawn parallel Agent calls in one response when workstreams are independent.

## Checkpoints and Resume

A usage limit, crash or stop ends a worker mid-task, and its final report never arrives. The checkpoint file is what survives.

Every assignment that mutates files or will run more than about ten tool calls names a checkpoint file: `~/.agents/runs/<run-id>/<agent-name>.md`, where `<run-id>` is `<YYYY-MM-DD>-<task key or slug>`. The root creates the directory before spawning. The brief tells the worker to:

- Write the checkpoint before its first change, then rewrite it after each completed step (a step, not a tool call).
- Keep it under 40 lines with these sections: `Objective`, `Done` (step, files, evidence), `Findings`, `Next` (the exact next step), `Open questions`.
- Record findings there as they appear, not only in the final report.

After a limit or crash, resume with the least loss first:

1. Session still open (or reopened with `claude --resume`): SendMessage the stopped agent by its ID. It keeps its full context.
2. Otherwise run `~/.agents/bin/agentctl subagents list` (status `rate_limit`, `interrupted`, `stopped_by_user`), then `~/.agents/bin/agentctl subagents brief <agent-id>`. The brief holds the assignment, the checkpoint, files changed, the last steps with results and the worker's last notes. Spawn a fresh worker with that brief on the same model and effort, and the same checkpoint path.

Never respawn the original assignment from scratch while a checkpoint or transcript exists.

## Coordinate and Integrate

- One precise worker is better than forced fan-out.
- Keep at least one useful path moving locally while agents work, unless the delegated operation is the whole task.
- Treat every result as evidence. Reopen authoritative live surfaces before claiming merged, deployed, fixed, paid, published, or delivered.
- Follow up with an existing agent when the next task depends on its context; spawn a new one when independence is more valuable.
- Stop or redirect when ownership overlaps, assumptions diverge, or a worker expands scope.
- Synthesize disagreements. State which evidence wins and why.
- Preserve user approval for destructive, production, financial, publishing, messaging, merge, and deployment actions.

Return one integrated answer. Do not dump parallel reports on the user.
