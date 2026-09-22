---
name: orchestrate
description: "Cursor only. Split independent workstreams with Task (composer-2.5-fast, cursor-grok-4.7-medium/high, auto — never Claude or GPT slugs). Use on `mult`, this skill name, 2+ independent streams, a blocking long command, or an independent review. Skip sequential or overlapping edits. Jira same-repo: multitask-same-repo. | recommendedRole: task-owner."
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

- `composer-2.5-fast` — `explore` / `follow` (docs, CI, defined procedures)
- `cursor-grok-4.7-medium` — `implement` / `task-owner` (default coding spawn)
- `cursor-grok-4.7-high` — `quality-gate` only
- `auto` — `deterministic` tool runs only
- `inherit` — only when the parent is already the same allowed slug

Forbidden even when Task lists them: `claude-opus-5-thinking-high`, `claude-4.5-haiku-thinking`, any `claude-*`, `gpt-5.6-*`, `gpt-5.3-codex`, `gemini-3.1-pro`, `glm-5.2-high`, `kimi-k3-max`, `cursor-grok-4.6-high`, `cursor-grok-4.5-high`. If Task rejects the chosen Cursor slug, stay single-agent. Do not fall back to Opus or 4.6.

If **spawn_agent** is available (Codex): follow `~/.codex/skills/orchestrate/SKILL.md`. If you are Claude Code with no Task tool: follow `~/.claude/skills/orchestrate/SKILL.md`.

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Composer / Auto cost–score guesses still follow `~/.agents/benchmarks/2026-08-deepswe.yaml`. Grok 4.7 has no DeepSWE rows yet (launched 2026-09-21); this ladder is provisional — retune when a benchmark file includes 4.7.

Spawn only Cursor-native models listed above.

Cursor still has no Luna/Terra/Sol product ladder. Route on four Cursor-native slugs that mirror the Claude effort split: Composer for light gather/follow, Grok 4.7 medium for coding ownership, Grok 4.7 high for the critic slot, Auto for cheap verifiable tool runs.

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

The table applies only when the worker runs a skill and you route on `metadata.recommendedRole`.

When freely orchestrating, with no skill role, the default general-purpose model is `cursor-grok-4.7-medium`.

| Model | Use when | Do not use for |
|---|---|---|
| `composer-2.5-fast` | `explore` or `follow`: docs, CI inspection, defined skill procedures. Closest to Terra medium. | Weak-result coding that would cause rework; high-stakes judgment. |
| `cursor-grok-4.7-medium` | `implement` or `task-owner`. Default coding spawn. Collapses Luna max, Terra max, and Sol high. | `deterministic` grep/wait work; the Sol-max `quality-gate` slot. |
| `cursor-grok-4.7-high` | `quality-gate`: architecture, security, payment, or release-risk. Intended Sol-max slot (no DeepSWE yet). | Routine `explore` or ordinary isolated coding. |
| `auto` | `deterministic` tool runs whose result is cheap to verify. Guessed Luna-medium clone (score 11). | `explore`, coding, review, or `quality-gate`. |
| `inherit` | Parent is already the same allowed slug at the same tier. | Switching quality tiers; name the slug instead. |

Workers do not spawn further unless the root explicitly assigns coordination of an independently scoped task. Auto never coordinates. Composer never coordinates.

`subagent_type`: `explore` for read-only gather; `shell` for long defined commands; `generalPurpose` for `implement`, review, and `quality-gate`. Do not use Bugbot or security-review types unless the user asked for those skills.

## Disclose Every Spawn

Immediately before every Task call, tell the user:

- The agent task name.
- Exact model slug, such as `cursor-grok-4.7-medium`.
- Role, leaf vs authorized coordinator, and `subagent_type`.

Group simultaneous spawns into one compact update. Describe these as requested configuration. If the runtime reports a different model, disclose the correction. Spawn independent Tasks in one message so they run in parallel.

```text
Spawning:
- `log_explore` — `composer-2.5-fast`, explore — read-only gather
- `impl_auth` — `cursor-grok-4.7-medium`, generalPurpose — implement
- `quality_gate` — `cursor-grok-4.7-high`, generalPurpose — quality-gate
- `ci_watch` — `auto`, shell — deterministic
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — composer-2.5-fast, explore

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Not Jira evidence capture. Do not use Auto.

### `follow` — composer-2.5-fast, or auto if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Auto only when the CLI is the worker and the result is cheap to verify (wait for CI, copy a path, grep). Otherwise Composer.

### `implement` — cursor-grok-4.7-medium, generalPurpose

Own one bounded code surface, spec, or review target. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `task-owner` — cursor-grok-4.7-medium, generalPurpose

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result.

### `quality-gate` — cursor-grok-4.7-high, generalPurpose

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user. Do not use medium for this slot.

## Delegation Patterns

- **Production incident:** Composer (`explore`) for live health/logs; Grok 4.7 medium (`implement`) for the relevant code path. Root separates cause from mitigation.
- **PR or release:** Composer (`explore`) for exact-head diff/CI; Grok 4.7 medium (`implement`) for substantive review; Grok 4.7 high (`quality-gate`) for merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate Composer `explore` gathers; Grok 4.7 medium to reconcile; Grok 4.7 high for money-sensitive ambiguity.
- **UI work:** Grok 4.7 medium (`implement`) for bounded or larger independent implementation.
- **Long-running procedure:** Composer (`follow`), or Auto when `deterministic`, so the root stays available.
- **Consulting or research:** Composer (`explore`) for sources; Grok 4.7 medium (`implement`) to normalize; Grok 4.7 high or the root for the recommendation.

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
