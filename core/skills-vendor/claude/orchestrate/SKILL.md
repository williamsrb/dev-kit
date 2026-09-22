---
name: orchestrate
description: "Claude Code only. Split independent workstreams with the Agent tool (claude-opus-5-5, claude-haiku-4-5-20251001). Use on `mult`, this skill name, 2+ independent streams, a blocking long command, or an independent review. Skip sequential or overlapping edits. Cursor: ~/.cursor/skills/orchestrate. Jira same-repo: multitask-same-repo. | recommendedRole: task-owner."
metadata:
  recommendedRole: task-owner
  cliDependencies:
    required: []
    optional: []
---
# Orchestrate (Claude)

## Host gate

If the **Task** tool is available (Cursor): stop. Do not spawn `claude-opus-5-thinking-high`, `claude-4.5-haiku-thinking`, or any Claude slug. Read and follow `${HOME}/.cursor/skills/orchestrate/SKILL.md` (same bytes as `~/.agents/skills-vendor/cursor/orchestrate/SKILL.md`). Cursor ladder: `composer-2.5-fast` (`explore`/`follow`), `cursor-grok-4.7-medium` (`implement`/`task-owner`), `cursor-grok-4.7-high` (`quality-gate`), `auto` (`deterministic`).

If **spawn_agent** is available (Codex): follow `~/.codex/skills/orchestrate/SKILL.md` instead.

This copy is for Claude Code only (Agent tool).

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Defaults follow `~/.agents/benchmarks/2026-08-deepswe.yaml`. Retune when that file is replaced.

Spawn only `claude-opus-5-5` and `claude-haiku-4-5-20251001` (or the installed Haiku 4.5 slug). Do not spawn `claude-sonnet-5` or `claude-fable-5-1` unless the user names them. Sonnet is dominated on DeepSWE (worse and more expensive than Opus Low). Fable matches Terra-range scores at 2–4× the cost.

Jira-oriented PRD work on several keys of the same repo is `multitask-same-repo` (worktrees, fresh sessions). Stop here and follow that skill instead.

## Decide Whether to Delegate

Delegate only when at least one condition holds:

- Two or more workstreams can proceed independently.
- A slow command, transfer, test suite, monitor, or data pull would otherwise make the root unavailable.
- A bounded investigation can gather evidence while the root handles the main path.
- An independent review would materially reduce implementation, production, security, payment, or release risk.
- The user started with `mult` or named this skill. That is permission to split; still skip spawn when the work is sequential or would overlap files.

Stay single-agent when the task is small, the next step depends on the immediately previous result, multiple agents would touch the same mutable files, or delegation overhead is comparable to doing the work directly.

## Select the Model

Claude has no Luna/Terra/Sol family. Route on Opus effort, plus Haiku for `deterministic` work only.

| Model | Effort | Use when | Do not use for |
|---|---|---|---|
| `claude-opus-5-5` | `low` | `explore` or `follow`: docs, CI inspection, defined skill procedures. Closest to Luna xhigh. | Weak-result coding that would cause rework; high-stakes judgment. |
| `claude-opus-5-5` | `medium` | `implement` or `task-owner`. Default coding spawn. Collapses Luna max, Terra max, and Sol high. | `deterministic` grep/wait work; the Sol-max `quality-gate` slot. |
| `claude-opus-5-5` | `high` | `quality-gate`: architecture, security, payment, or release-risk. Closest to Sol max, cheaper on DeepSWE. | Routine `explore` or ordinary isolated coding. |
| `claude-haiku-4-5-20251001` | default | `deterministic` tool runs whose result is cheap to verify. Guessed Luna-medium clone (score 11). | `explore`, coding, review, or `quality-gate`. |

If the Agent tool exposes a thinking or effort argument, set it to the effort above. If it does not, name that effort in the assignment and do not invent a slug. Opus `xhigh` / `max` are optional user-named upgrades, not defaults (High already matches Sol max).

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
- `log_explore` — `claude-opus-5-5`, effort `low`, Explore — read-only gather
- `impl_auth` — `claude-opus-5-5`, effort `medium`, general-purpose — implement
- `quality_gate` — `claude-opus-5-5`, effort `high`, general-purpose — quality-gate
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — Opus low, Explore

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Use `subagent_type` Explore (or the read-only equivalent). Do not use Haiku. Not Jira evidence capture.

### `follow` — Opus low, or Haiku if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Haiku only when the CLI is the worker and the result is cheap to verify (wait for CI, copy a path, grep). Otherwise Opus low.

### `implement` — Opus medium, general-purpose

Own one bounded code surface, spec, or review target. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `task-owner` — Opus medium, general-purpose

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result. There is no cheaper Claude row above Opus medium under the cost cap.

### `quality-gate` — Opus high, general-purpose

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user.

## Delegation Patterns

- **Production incident:** Opus low (`explore`) for live health/logs; Opus medium (`implement`) for the relevant code path. Root separates cause from mitigation.
- **PR or release:** Opus low (`explore`) for exact-head diff/CI; Opus medium (`implement`) for substantive review; Opus high (`quality-gate`) for merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate Opus low `explore` gathers; Opus medium to reconcile; Opus high for money-sensitive ambiguity.
- **UI work:** Opus medium (`implement`) for bounded or larger independent implementation.
- **Long-running procedure:** Opus low (`follow`), or Haiku when `deterministic`, so the root stays available.
- **Consulting or research:** Opus low (`explore`) for sources; Opus medium (`implement`) to normalize; Opus high or the root for the recommendation.

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
