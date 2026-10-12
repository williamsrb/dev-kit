---
name: orchestrate
description: "Cursor only. Split independent workstreams with Task (cursor-grok-4.7-low/medium/high/xhigh — never Claude or GPT slugs). Use on `mult`, this skill name, 2+ independent streams, a blocking long command, or an independent review. Skip sequential or overlapping edits. Jira same-repo: multitask-same-repo. | recommendedRole: task-owner."
metadata:
  recommendedRole: task-owner
  cliDependencies:
    required: []
    optional: []
---
# Orchestrate (Cursor)

## Host gate

If you opened `~/.claude/skills/orchestrate` or any copy that names `claude-opus-5`, you have the wrong file. This file is the Cursor copy.

Allowed Task `model` values only:

- `cursor-grok-4.7-low` — `deterministic` tool runs only
- `cursor-grok-4.7-medium` — `explore`, `follow`
- `cursor-grok-4.7-high` — `plan`, `build`, `impl-review`, `task-owner` (default spawn)
- `cursor-grok-4.7-xhigh` — `plan-review`, `quality-gate`
- `inherit` — only when the parent is already the same allowed slug

Forbidden even when Task lists them: `composer-2.5-fast`, `auto`, `claude-opus-5-thinking-high`, `claude-4.5-haiku-thinking`, any `claude-*`, `gpt-5.6-*`, `gpt-6*`, `gpt-5.3-codex`, `gemini-3.1-pro`, `glm-5.2-high`, `kimi-k3-max`, `cursor-grok-4.6-high`, `cursor-grok-4.5-high`. If Task rejects the chosen Cursor slug, stay single-agent. Do not fall back to Opus or 4.6.

If **spawn_agent** is available (Codex): follow `~/.codex/skills/orchestrate/SKILL.md`. If you are Claude Code with no Task tool: follow `~/.claude/skills/orchestrate/SKILL.md`.

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Defaults are the Cursor column of `~/.agents/skills-vendor/ROLES.md`: operator picks for `follow`, `plan`, `build`, `plan-review` and `impl-review`, the rest scale `agentctl bench place` (2026-10-09) down, Composer + Grok only. Retune with `agentctl bench collect` then `agentctl bench place --markdown`.

Spawn only Cursor-native models listed above.

Grok 4.7 `xhigh` (37.8 Terminal-Bench points) clears the `explore`/`follow` floor but is below the `plan`, `build`, `impl-review`, `plan-review`, `task-owner`, and `quality-gate` floors; it is still the best Cursor-native config. Cursor has one model family, so a reviewer cannot run on a different model than the author: reviews rely on higher effort and a fresh session. `inherit` skills (`handoff`) get no spawn model. `xhigh` is the top default; there is no `max`. Composer 2.5 and Auto are below the `deterministic` floor. For high-consequence `quality-gate` work, prefer the root or the user over a Cursor spawn.

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

The table applies only when the worker runs a skill and you route on `metadata.recommendedRole`.

When freely orchestrating, with no skill role, the default general-purpose model is `cursor-grok-4.7-high`.

| Model | Role | Use when |
|---|---|---|
| `cursor-grok-4.7-low` | `deterministic` | Tool runs whose result is cheap to verify. Provisional (Artificial Analysis only, estimated cost). |
| `cursor-grok-4.7-medium` | `explore`, `follow` | Read-only gather; defined skill procedures. |
| `cursor-grok-4.7-high` | `plan`, `build`, `impl-review`, `task-owner` | Planning, building, delivery review, coordination. Below band from `plan` up. |
| `cursor-grok-4.7-xhigh` | `plan-review`, `quality-gate` | Plan review and high-consequence gates. Measured on Terminal-Bench; below band. |
| `inherit` | any | Parent is already the same allowed slug at the same tier. Do not use to switch tiers; name the slug instead. |

Workers do not spawn further unless the root explicitly assigns coordination of an independently scoped task. Grok 4.7 low never coordinates.

`subagent_type`: `explore` for read-only gather; `shell` for long defined commands; `generalPurpose` for `plan`, `build`, reviews, `task-owner` and `quality-gate`. Do not use Bugbot or security-review types unless the user asked for those skills.

## Disclose Every Spawn

Immediately before every Task call, tell the user:

- The agent task name.
- Exact model slug, such as `cursor-grok-4.7-high`.
- Role, leaf vs authorized coordinator, and `subagent_type`.

Group simultaneous spawns into one compact update. Describe these as requested configuration. If the runtime reports a different model, disclose the correction. Spawn independent Tasks in one message so they run in parallel.

```text
Spawning:
- `log_explore` — `cursor-grok-4.7-medium`, explore — read-only gather
- `impl_auth` — `cursor-grok-4.7-high`, generalPurpose — build
- `impl_review` — `cursor-grok-4.7-high`, generalPurpose — impl-review
- `quality_gate` — `cursor-grok-4.7-xhigh`, generalPurpose — quality-gate
- `ci_watch` — `cursor-grok-4.7-low`, shell — deterministic
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — cursor-grok-4.7-medium, explore

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Not Jira evidence capture. Do not use Grok 4.7 low.

### `follow` — cursor-grok-4.7-medium, or cursor-grok-4.7-low if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Grok 4.7 low only when the CLI is the worker and the result is cheap to verify (wait for CI, copy a path, grep).

### `plan` — cursor-grok-4.7-high, generalPurpose

Write the spec or plan of one surface from a PRD. Return the plan file path, open decisions and risks.

### `build` — cursor-grok-4.7-high, generalPurpose

Own one bounded code surface or execute one plan. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `impl-review` — cursor-grok-4.7-high, generalPurpose

Review a delivery against its plan in a fresh session. Same model family as the author, so lean on the checklist. Report findings by severity with file and line; do not fix unless assigned.

### `plan-review` — cursor-grok-4.7-xhigh, generalPurpose

Review and rewrite a plan before work starts, in a fresh session. Report gaps in scope, acceptance criteria and risk.

### `task-owner` — cursor-grok-4.7-high, generalPurpose

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result.

### `quality-gate` — cursor-grok-4.7-xhigh, generalPurpose

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user. Below the absolute floor: treat the result as one input, not the gate.

## Delegation Patterns

- **Production incident:** Grok 4.7 medium (`explore`) for live health/logs; Grok 4.7 high (`build`) for the relevant code path. Root separates cause from mitigation.
- **PR or release:** Grok 4.7 medium (`explore`) for exact-head diff/CI; Grok 4.7 high (`impl-review`) for substantive review; Grok 4.7 xhigh (`quality-gate`) for merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate Grok 4.7 medium `explore` gathers; Grok 4.7 high to reconcile; the root decides money-sensitive ambiguity.
- **UI work:** Grok 4.7 high (`build`) for bounded or larger independent implementation.
- **Plan then build:** high (`plan`), xhigh (`plan-review`), high (`build`) per worktree, high (`impl-review`).
- **Long-running procedure:** Grok 4.7 medium (`follow`), or Grok 4.7 low when `deterministic`, so the root stays available.
- **Consulting or research:** Grok 4.7 medium (`explore`) for sources and high to normalize; the root for the recommendation.

## Assignment Contract

Pass only the context required to succeed:

1. One concrete objective and why it matters.
2. Exact scope: repository, paths, systems, date range, or source set.
3. Ownership boundary, including files the worker may change.
4. Constraints from the user, repository, and applicable skills.
5. Required validation and the expected return format.
6. Read-only or authorized to mutate.
7. Leaf, or an explicitly authorized coordinator.
8. The exact model slug and `subagent_type` disclosed to the user.
9. Do not delegate further unless the root authorized coordination.

Never send two agents overlapping implementation ownership in the same checkout. Each Task brief must be self-contained; subagents do not share this conversation.

## Coordinate and Integrate

- One precise worker is better than forced fan-out.
- Keep at least one useful path moving locally while agents work, unless the delegated operation is the whole task.
- Treat every result as evidence. Reopen authoritative live surfaces before claiming merged, deployed, fixed, paid, published, or delivered.
- Follow up with an existing agent (`resume`) when the next task depends on its context; spawn a new one when independence is more valuable.
- Stop or redirect when ownership overlaps, assumptions diverge, or a worker expands scope.
- Synthesize disagreements. State which evidence wins and why.
- Preserve user approval for destructive, production, financial, publishing, messaging, merge, and deployment actions.

Return one integrated answer. Do not dump parallel reports on the user.
