---
name: orchestrate
description: "Claude Code only. Split independent workstreams with the Agent tool (claude-opus-5-5, claude-sonnet-5-5, claude-haiku-5-5). Use on `mult`, this skill name, 2+ independent streams, a blocking long command, or an independent review. Skip sequential or overlapping edits. Cursor: ~/.cursor/skills/orchestrate. Jira same-repo: multitask-same-repo. | recommendedRole: task-owner."
metadata:
  recommendedRole: task-owner
  cliDependencies:
    required: []
    optional: []
---
# Orchestrate (Claude)

## Host gate

If the **Task** tool is available (Cursor): stop. Do not spawn `claude-opus-5-thinking-high`, `claude-4.5-haiku-thinking`, or any Claude slug. Read and follow `${HOME}/.cursor/skills/orchestrate/SKILL.md` (same bytes as `~/.agents/skills-vendor/cursor/orchestrate/SKILL.md`). Cursor ladder: `cursor-grok-4.7-low` (`deterministic`), `-medium` (`explore`, `follow`), `-high` (`plan`, `build`, `impl-review`, `task-owner`), `-xhigh` (`plan-review`, `quality-gate`).

If **spawn_agent** is available (Codex): follow `~/.codex/skills/orchestrate/SKILL.md` instead.

This copy is for Claude Code only (Agent tool).

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Defaults are the Claude column of `~/.agents/skills-vendor/ROLES.md`. The `follow`, `plan`, `build`, `plan-review` and `impl-review` cells are operator picks; the rest scale `agentctl bench place` (2026-10-09) down so no default is `max`. Retune with `agentctl bench collect` then `agentctl bench place --markdown`.

Spawn only `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`. Do not spawn `claude-fable-5-1` or `claude-haiku-4-5-20251001` unless the user names them: Fable is never the cheapest config in any band, and Haiku 4.5 is below the `deterministic` floor.

A reviewer (`plan-review`, `impl-review`) runs on a different model than the author: Opus reviews Sonnet work. `inherit` skills (`handoff`) get no spawn model; they run on the session's model. `max` effort is never a default; use it only when the user asks.

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

Route on three models: Haiku 5.5 for light work, Sonnet 5.5 for planning, building and procedures, Opus 5.5 for reviews and judgment. Effort is the dial.

| Model | Effort | Role | Use when |
|---|---|---|---|
| `claude-haiku-5-5` | `low` | `deterministic` | Tool runs whose result is cheap to verify. |
| `claude-haiku-5-5` | `medium` | `explore` | Read-only gather: docs, CI inspection, logs. |
| `claude-sonnet-5-5` | `medium` | `follow` | Defined skill procedures (commit message, worklogs). |
| `claude-sonnet-5-5` | `high` | `plan` | Spec or plan of one surface. |
| `claude-sonnet-5-5` | `high` | `build` | Execute a plan or bounded coding. Default coding spawn. |
| `claude-opus-5-5` | `medium` | `impl-review` | Review a delivery against its plan. |
| `claude-opus-5-5` | `high` | `plan-review` | Review and rewrite a plan before work starts. |
| `claude-opus-5-5` | `high` | `task-owner` | Substantial independent task; coordination when authorized. |
| `claude-opus-5-5` | `xhigh` | `quality-gate` | Architecture, security, payment, or release-risk. |

Haiku `low`/`medium` and Opus `medium`/`high`/`xhigh` are provisional (Artificial Analysis only, estimated cost, or an operator pick); Sonnet cells are operator picks.

If the Agent tool exposes a thinking or effort argument, set it to the effort above. If it does not, name that effort in the assignment and do not invent a slug.

Workers do not spawn further unless the root explicitly assigns coordination of an independently scoped task. Haiku and Sonnet never coordinate.

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
- `impl_auth` — `claude-sonnet-5-5`, effort `high`, general-purpose — build
- `impl_review` — `claude-opus-5-5`, effort `medium`, general-purpose — impl-review
- `quality_gate` — `claude-opus-5-5`, effort `xhigh`, general-purpose — quality-gate
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — Haiku medium, Explore

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Use `subagent_type` Explore (or the read-only equivalent). Not Jira evidence capture.

### `follow` — Sonnet medium, or Haiku low if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Haiku low only when the CLI is the worker and the result is cheap to verify (wait for CI, copy a path, grep).

### `plan` — Sonnet high, general-purpose

Write the spec or plan of one surface from a PRD. Return the plan file path, open decisions and risks.

### `build` — Sonnet high, general-purpose

Own one bounded code surface or execute one plan. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `impl-review` — Opus medium, general-purpose

Review a delivery against its plan on a different model than the author. Report findings by severity with file and line; do not fix unless assigned.

### `plan-review` — Opus high, general-purpose

Review and rewrite a plan before work starts, on a different model than the author. Report gaps in scope, acceptance criteria and risk.

### `task-owner` — Opus high, general-purpose

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result.

### `quality-gate` — Opus xhigh, general-purpose

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user.

## Delegation Patterns

- **Production incident:** Haiku medium (`explore`) for live health/logs; Sonnet high (`build`) for the relevant code path. Root separates cause from mitigation.
- **PR or release:** Haiku medium (`explore`) for exact-head diff/CI; Opus medium (`impl-review`) for substantive review; Opus xhigh (`quality-gate`) for merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate Haiku medium `explore` gathers; Sonnet high to reconcile; Opus xhigh for money-sensitive ambiguity.
- **UI work:** Sonnet high (`build`) for bounded work; Opus high (`task-owner`) for a larger independent task.
- **Plan then build:** Sonnet high (`plan`), Opus high (`plan-review`), Sonnet high (`build`) per worktree, Opus medium (`impl-review`).
- **Long-running procedure:** Sonnet medium (`follow`), or Haiku low when `deterministic`, so the root stays available.
- **Consulting or research:** Haiku medium (`explore`) for sources; Sonnet high to normalize; Opus xhigh or the root for the recommendation.

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

Never send two agents overlapping implementation ownership in the same checkout. Spawn parallel Agent calls in one response when workstreams are independent.

## Coordinate and Integrate

- One precise worker is better than forced fan-out.
- Keep at least one useful path moving locally while agents work, unless the delegated operation is the whole task.
- Treat every result as evidence. Reopen authoritative live surfaces before claiming merged, deployed, fixed, paid, published, or delivered.
- Follow up with an existing agent when the next task depends on its context; spawn a new one when independence is more valuable.
- Stop or redirect when ownership overlaps, assumptions diverge, or a worker expands scope.
- Synthesize disagreements. State which evidence wins and why.
- Preserve user approval for destructive, production, financial, publishing, messaging, merge, and deployment actions.

Return one integrated answer. Do not dump parallel reports on the user.
