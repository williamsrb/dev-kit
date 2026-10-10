---
name: orchestrate
description: "Claude Code only. Split independent workstreams with the Agent tool (claude-opus-5-5, claude-haiku-5-5). Use on `mult`, this skill name, 2+ independent streams, a blocking long command, or an independent review. Skip sequential or overlapping edits. Cursor: ~/.cursor/skills/orchestrate. Jira same-repo: multitask-same-repo. | recommendedRole: task-owner."
metadata:
  recommendedRole: task-owner
  cliDependencies:
    required: []
    optional: []
---
# Orchestrate (Claude)

## Host gate

If the **Task** tool is available (Cursor): stop. Do not spawn `claude-opus-5-thinking-high`, `claude-4.5-haiku-thinking`, or any Claude slug. Read and follow `${HOME}/.cursor/skills/orchestrate/SKILL.md` (same bytes as `~/.agents/skills-vendor/cursor/orchestrate/SKILL.md`). Cursor ladder: `cursor-grok-4.7-low` (`deterministic`), `cursor-grok-4.7-xhigh` (every other role).

If **spawn_agent** is available (Codex): follow `~/.codex/skills/orchestrate/SKILL.md` instead.

This copy is for Claude Code only (Agent tool).

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Defaults are the Claude column of `~/.agents/skills-vendor/ROLES.md`, produced by `agentctl bench place` (2026-10-09): all benchmarks in `~/.agents/benchmarks/latest.yaml` on one Terminal-Bench scale, cheapest config at each role's absolute floor. Retune with `agentctl bench collect` then `agentctl bench place --markdown`.

Spawn only `claude-opus-5-5` and `claude-haiku-5-5`. Do not spawn `claude-sonnet-5-5`, `claude-fable-5-1`, or `claude-haiku-4-5-20251001` unless the user names them: Sonnet and Fable are never the cheapest config in any band, and Haiku 4.5 is below the `deterministic` floor.

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

Route on two models: Haiku 5.5 for light work, Opus 5.5 for coding and judgment. Effort is the dial.

| Model | Effort | Use when | Do not use for |
|---|---|---|---|
| `claude-haiku-5-5` | `high` | `deterministic` tool runs whose result is cheap to verify. | `explore`, coding, review, or `quality-gate`. |
| `claude-haiku-5-5` | `max` | `explore` or `follow`: docs, CI inspection, defined skill procedures. | Coding that would cause rework if weak; high-stakes judgment. |
| `claude-opus-5-5` | `medium` | `implement`: bounded coding or review of one owned surface. Default coding spawn. | `deterministic` grep/wait work; the `quality-gate` slot. |
| `claude-opus-5-5` | `xhigh` | `task-owner`: substantial independent task; coordination when authorized. | Routine `implement` work. |
| `claude-opus-5-5` | `max` | `quality-gate`: architecture, security, payment, or release-risk. The measured frontier. | Routine `explore` or ordinary isolated coding. |

Haiku rows and Opus `medium`/`xhigh` are provisional (Artificial Analysis only, estimated cost); Opus `max` is measured on Terminal-Bench.

If the Agent tool exposes a thinking or effort argument, set it to the effort above. If it does not, name that effort in the assignment and do not invent a slug.

Workers do not spawn further unless the root explicitly assigns coordination of an independently scoped task. Haiku never coordinates.

## Disclose Every Spawn

Immediately before every Agent call, tell the user:

- The agent task name.
- Exact model slug, such as `claude-opus-5-5`.
- Exact effort, such as `medium` or `high`.
- Role, leaf vs authorized coordinator, and `subagent_type`.

Group simultaneous spawns into one compact update. Describe these as requested configuration. If the runtime reports a different model, disclose the correction.

```text
Spawning:
- `log_explore` — `claude-haiku-5-5`, effort `max`, Explore — read-only gather
- `impl_auth` — `claude-opus-5-5`, effort `medium`, general-purpose — implement
- `quality_gate` — `claude-opus-5-5`, effort `max`, general-purpose — quality-gate
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — Haiku max, Explore

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Use `subagent_type` Explore (or the read-only equivalent). Not Jira evidence capture.

### `follow` — Haiku max, or Haiku high if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Haiku high only when the CLI is the worker and the result is cheap to verify (wait for CI, copy a path, grep). Otherwise Haiku max.

### `implement` — Opus medium, general-purpose

Own one bounded code surface, spec, or review target. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `task-owner` — Opus xhigh, general-purpose

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result.

### `quality-gate` — Opus max, general-purpose

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user.

## Delegation Patterns

- **Production incident:** Haiku max (`explore`) for live health/logs; Opus medium (`implement`) for the relevant code path. Root separates cause from mitigation.
- **PR or release:** Haiku max (`explore`) for exact-head diff/CI; Opus medium (`implement`) for substantive review; Opus max (`quality-gate`) for merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate Haiku max `explore` gathers; Opus medium to reconcile; Opus max for money-sensitive ambiguity.
- **UI work:** Opus medium (`implement`) for bounded work; Opus xhigh (`task-owner`) for a larger independent task.
- **Long-running procedure:** Haiku max (`follow`), or Haiku high when `deterministic`, so the root stays available.
- **Consulting or research:** Haiku max (`explore`) for sources; Opus medium (`implement`) to normalize; Opus max or the root for the recommendation.

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
