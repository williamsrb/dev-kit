---
name: orchestrate
description: "Split independent Codex workstreams with spawn_agent (gpt-6-luna, gpt-6.1-sol, gpt-6-astra). Use on `mult`, this skill name, 2+ independent streams, a blocking command, or an independent review. Skip sequential or overlapping edits. Jira same-repo: multitask-same-repo. | recommendedRole: task-owner."
metadata:
  recommendedRole: task-owner
  cliDependencies:
    required: []
    optional: []
---
# Orchestrate (Codex)

## Host gate

If the **Task** tool is available (Cursor): stop. Follow `~/.cursor/skills/orchestrate/SKILL.md`. Do not spawn GPT models from Cursor.

If the **Agent** tool is available and spawn_agent is not (Claude Code): follow `~/.claude/skills/orchestrate/SKILL.md`.

This copy is for Codex (`spawn_agent`) only.

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Defaults are the Codex column of `~/.agents/skills-vendor/ROLES.md`: operator picks for `follow`, `plan`, `build`, `plan-review` and `impl-review`, the rest scale `agentctl bench place` (2026-10-09) down so no default is `max`. Retune with `agentctl bench collect` then `agentctl bench place --markdown`. Do not spawn models outside `gpt-6-luna`, `gpt-6.1-sol`, and `gpt-6-astra`; GPT-5.6 Luna/Terra/Sol are never the cheapest config in any band.

A reviewer (`plan-review`, `impl-review`) runs on a different model than the author: Astra reviews Sol work. `inherit` skills (`handoff`) get no spawn model; they run on the session's model. `max` effort is never a default; use it only when the user asks.

Requires `multi_agent = true` under `[features]` in `~/.codex/config.toml`. If `spawn_agent` is missing, stay single-agent and say so.

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

Choose by ambiguity, coupling, and consequence rather than task size alone. GPT-6 Luna is the Haiku analogue: `deterministic` work only.

| Model | Effort | Role | Use when |
|---|---|---|---|
| `gpt-6-luna` | `medium` | `deterministic` | Tool runs whose result is cheap to verify. |
| `gpt-6.1-sol` | `medium` | `explore` | Read-only gather: docs, CI inspection, logs. |
| `gpt-6.1-sol` | `medium` | `follow` | Defined skill procedures. |
| `gpt-6.1-sol` | `high` | `plan` | Spec or plan of one surface. |
| `gpt-6.1-sol` | `high` | `build` | Execute a plan or bounded coding. Default coding spawn. |
| `gpt-6-astra` | `medium` | `impl-review` | Review a delivery against its plan. |
| `gpt-6-astra` | `high` | `plan-review` | Review and rewrite a plan before work starts. |
| `gpt-6.1-sol` | `xhigh` | `task-owner` | Substantial independent task; coordination when authorized. |
| `gpt-6-astra` | `xhigh` | `quality-gate` | Architecture, security, payment, release-risk. Best Codex config, but below the absolute `quality-gate` floor (58.0 vs 62.1 Terminal-Bench points). |

Sol cells are provisional (Artificial Analysis only, estimated cost, or an operator pick). For extreme-consequence gates, prefer a second opinion from the root or the user over a stronger Codex tier: none exists.

Do not use GPT-6 Luna below `medium`. Luna never coordinates. GPT-6.1 Sol and GPT-6 Astra may coordinate children only when the root explicitly assigns that, the child work is independently scoped, and slots remain.

## Disclose Every Spawn

Immediately before every `spawn_agent` call, send a concise commentary update:

- The agent task name.
- Exact model slug, such as `gpt-6.1-sol`.
- Exact `reasoning_effort`, such as `medium` or `high`.
- Role, and whether the agent is a leaf or an authorized coordinator.

Group simultaneous spawns into one compact update. Describe these as requested configuration, not verified runtime identity. If the runtime reports a different model or effort, disclose the correction.

Prefer `fork_turns: "none"` with explicit `model` and `reasoning_effort`. When a history fork is required, say the values are inherited and name the parent's model and effort when known; never guess.

```text
Spawning:
- `log_explore` — `gpt-6.1-sol`, reasoning `medium` — read-only gather
- `impl_auth` — `gpt-6.1-sol`, reasoning `high` — build
- `impl_review` — `gpt-6-astra`, reasoning `medium` — impl-review
- `ci_watch` — `gpt-6-luna`, reasoning `medium` — deterministic
- `quality_gate` — `gpt-6-astra`, reasoning `xhigh` — quality-gate
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — 6.1 Sol medium

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Do not use Luna. Not Jira evidence capture.

### `follow` — 6.1 Sol medium, or Luna medium if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Luna only when the CLI is the worker and the result is cheap to verify (wait for CI, copy a path, grep).

### `plan` — 6.1 Sol high

Write the spec or plan of one surface from a PRD. Return the plan file path, open decisions and risks.

### `build` — 6.1 Sol high

Own one bounded code surface or execute one plan. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `impl-review` — Astra medium

Review a delivery against its plan on a different model than the author. Report findings by severity with file and line; do not fix unless assigned.

### `plan-review` — Astra high

Review and rewrite a plan before work starts, on a different model than the author. Report gaps in scope, acceptance criteria and risk.

### `task-owner` — 6.1 Sol xhigh

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result.

### `quality-gate` — Astra xhigh

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user.

## Delegation Patterns

- **Production incident:** 6.1 Sol medium (`explore`) for live health/logs; 6.1 Sol high (`build`) for the relevant code path; 6.1 Sol xhigh (`task-owner`) only if it becomes a coordinated task. Root separates cause from mitigation.
- **PR or release:** 6.1 Sol medium (`explore`) for exact-head diff/CI; Astra medium (`impl-review`) for substantive review; Astra xhigh (`quality-gate`) for merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate 6.1 Sol medium `explore` gathers; 6.1 Sol high to reconcile; Astra xhigh for money-sensitive ambiguity.
- **UI work:** 6.1 Sol high (`build`) for bounded implementation; 6.1 Sol xhigh (`task-owner`) for a larger independent task.
- **Plan then build:** Sol high (`plan`), Astra high (`plan-review`), Sol high (`build`) per worktree, Astra medium (`impl-review`).
- **Long-running procedure:** 6.1 Sol medium (`follow`), or Luna medium when `deterministic`, so the root stays available.
- **Consulting or research:** 6.1 Sol medium (`explore`) for sources; 6.1 Sol high to normalize; Astra or the root for the recommendation.

## Assignment Contract

Default to `fork_turns: "none"`. Pass only the context required to succeed:

1. One concrete objective and why it matters.
2. Exact scope: repository, paths, systems, date range, or source set.
3. Ownership boundary, including files the worker may change.
4. Constraints from the user, repository, and applicable skills.
5. Required validation and the expected return format.
6. Read-only or authorized to mutate.
7. Leaf, or an explicitly authorized 6.1 Sol / Astra coordinator. Luna is always a leaf.
8. The exact model and reasoning effort disclosed to the user.

Use a history fork only when the subtask depends on conversation context too dense or fragile to restate. Never send two agents overlapping implementation ownership in the same checkout.

## Coordinate and Integrate

- Respect the slot limit. One precise worker is better than forced fan-out.
- Keep at least one useful path moving locally while agents work, unless the delegated operation is the whole task.
- Treat every result as evidence. Reopen authoritative live surfaces before claiming merged, deployed, fixed, paid, published, or delivered.
- Follow up with an existing agent when the next task depends on its context; spawn a new one when independence is more valuable.
- Stop or redirect when ownership overlaps, assumptions diverge, or a worker expands scope.
- Synthesize disagreements. State which evidence wins and why.
- Preserve user approval for destructive, production, financial, publishing, messaging, merge, and deployment actions.

Return one integrated answer. Do not dump parallel reports on the user.
