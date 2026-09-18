---
name: orchestrate
description: "Split independent Codex workstreams with spawn_agent (gpt-5.6-luna, terra, sol). Use on `mult`, this skill name, 2+ independent streams, a blocking command, or an independent review. Skip sequential or overlapping edits. Jira same-repo: multitask-same-repo. | recommendedRole: task-owner."
metadata:
  recommendedRole: task-owner
  cliDependencies:
    required: []
    optional: []
---
# Orchestrate (Codex)

## Host gate

If the **Task** tool is available (Cursor): stop. Follow `~/.cursor/skills/orchestrate/SKILL.md`. Do not spawn Luna/Terra/Sol from Cursor.

If the **Agent** tool is available and spawn_agent is not (Claude Code): follow `~/.claude/skills/orchestrate/SKILL.md`.

This copy is for Codex (`spawn_agent`) only.

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Defaults follow `~/.agents/benchmarks/2026-08-deepswe.yaml`. Retune when that file is replaced. Do not spawn models outside `gpt-5.6-luna`, `gpt-5.6-terra`, and `gpt-5.6-sol`.

Requires `multi_agent = true` under `[features]` in `~/.codex/config.toml`. If `spawn_agent` is missing, stay single-agent and say so.

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

Choose by ambiguity, coupling, and consequence rather than task size alone. Luna high is the Haiku analogue: `deterministic` work only.

| Model | Effort | Use when | Do not use for |
|---|---|---|---|
| `gpt-5.6-luna` | `high` | `deterministic` tool runs whose result is cheap to verify. | `explore`, coding, review, or `quality-gate`. |
| `gpt-5.6-luna` | `xhigh` | `explore` or `follow`: docs, CI inspection, defined skill procedures. | Implementation that would cause rework if weak; final high-stakes judgment. |
| `gpt-5.6-luna` | `max` | `implement`: bounded coding or review of one owned surface. Default coding spawn. | Coordinating other agents. |
| `gpt-5.6-terra` | `xhigh` | `task-owner`: substantial independent task; delegated coordination when the root authorizes it. | Routine Luna-max `implement` work. |
| `gpt-5.6-sol` | `medium` | `quality-gate` under ambiguity. Default critic. | Routine `explore` or ordinary isolated coding. |
| `gpt-5.6-sol` | `xhigh` | `quality-gate` when consequence is extreme (architecture, security, payment, release-risk). | Anything Sol medium can finish. |

Do not use Luna `medium` or `low` for SWE. Luna does not delegate. Luna high never coordinates. Terra and Sol may coordinate children only when the root explicitly assigns that, the child work is independently scoped, and slots remain.

## Disclose Every Spawn

Immediately before every `spawn_agent` call, send a concise commentary update:

- The agent task name.
- Exact model slug, such as `gpt-5.6-luna`.
- Exact `reasoning_effort`, such as `xhigh` or `max`.
- Role, and whether the agent is a leaf or an authorized coordinator.

Group simultaneous spawns into one compact update. Describe these as requested configuration, not verified runtime identity. If the runtime reports a different model or effort, disclose the correction.

Prefer `fork_turns: "none"` with explicit `model` and `reasoning_effort`. When a history fork is required, say the values are inherited and name the parent's model and effort when known; never guess.

```text
Spawning:
- `log_explore` — `gpt-5.6-luna`, reasoning `xhigh` — read-only gather
- `impl_auth` — `gpt-5.6-luna`, reasoning `max` — implement
- `ci_watch` — `gpt-5.6-luna`, reasoning `high` — deterministic
- `quality_gate` — `gpt-5.6-sol`, reasoning `medium` — quality-gate
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — Luna xhigh

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Do not use Luna high. Not Jira evidence capture.

### `follow` — Luna xhigh, or Luna high if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Luna high only when the CLI is the worker and the result is cheap to verify (wait for CI, copy a path, grep). Otherwise Luna xhigh.

### `implement` — Luna max

Own one bounded code surface, spec, or review target. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `task-owner` — Terra xhigh

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result.

### `quality-gate` — Sol medium, or Sol xhigh when consequence is extreme

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user.

## Delegation Patterns

- **Production incident:** Luna xhigh (`explore`) for live health/logs; Luna max (`implement`) for the relevant code path; Terra xhigh (`task-owner`) only if it becomes a coordinated task. Root separates cause from mitigation.
- **PR or release:** Luna xhigh (`explore`) for exact-head diff/CI; Luna max (`implement`) for substantive review; Sol medium (`quality-gate`) for merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate Luna xhigh `explore` gathers; Luna max to reconcile; Sol medium or xhigh for money-sensitive ambiguity.
- **UI work:** Luna max (`implement`) for bounded implementation; Terra xhigh (`task-owner`) for a larger independent task.
- **Long-running procedure:** Luna xhigh (`follow`), or Luna high when `deterministic`, so the root stays available.
- **Consulting or research:** Luna xhigh (`explore`) for sources; Luna max (`implement`) to normalize; Sol or the root for the recommendation.

## Assignment Contract

Default to `fork_turns: "none"`. Pass only the context required to succeed:

1. One concrete objective and why it matters.
2. Exact scope: repository, paths, systems, date range, or source set.
3. Ownership boundary, including files the worker may change.
4. Constraints from the user, repository, and applicable skills.
5. Required validation and the expected return format.
6. Read-only or authorized to mutate.
7. Leaf, or an explicitly authorized Terra/Sol coordinator. Luna is always a leaf.
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
