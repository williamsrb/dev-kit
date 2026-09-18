---
name: orchestrate
description: "Cursor only. Split independent workstreams with Task (cursor-grok-4.6-high, composer-2.5-fast only — never Claude or GPT slugs). Use on `mult`, this skill name, 2+ independent streams, a blocking long command, or an independent review. Skip sequential or overlapping edits. Jira same-repo: multitask-same-repo. | recommendedRole: task-owner."
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

- `cursor-grok-4.6-high` — all quality work (explore, implement, review, quality-gate)
- `composer-2.5-fast` — deterministic tool runs only
- `inherit` — only when the parent is already grok-4.6 or composer

Forbidden even when Task lists them: `claude-opus-5-thinking-high`, `claude-4.5-haiku-thinking`, any `claude-*`, `gpt-5.6-*`, `gpt-5.3-codex`, `gemini-3.1-pro`, `glm-5.2-high`, `kimi-k3-max`, `cursor-grok-4.5-high`. If Task rejects grok, stay single-agent. Do not fall back to Opus.

If **spawn_agent** is available (Codex): follow `~/.codex/skills/orchestrate/SKILL.md`. If you are Claude Code with no Task tool: follow `~/.claude/skills/orchestrate/SKILL.md`.

Keep the root responsible for decomposition, user communication, approvals, synthesis, and the final claim. Delegate outcomes, not vague help.

Defaults follow `~/.agents/benchmarks/2026-08-deepswe.yaml`. Retune when that file is replaced.

Spawn only Cursor-native models listed above.

Cursor has no Luna/Terra/Sol ladder. Grok 4.6 medium is the DeepSWE winner among grok efforts (67.48) and dominates grok high/xhigh. Task currently exposes `cursor-grok-4.6-high`; use that slug for all quality work and disclose it. There is no Cursor-native row near Sol max (~73); grok is the `quality-gate` too. `composer-2.5` is a guessed cheap clone (~28); `deterministic` only.

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

| Model | Use when | Do not use for |
|---|---|---|
| `cursor-grok-4.6-high` | `explore`, `follow`, `implement`, `task-owner`, `quality-gate`. Default quality spawn. | Completely deterministic wait/grep/copy work. |
| `composer-2.5-fast` | `deterministic` tool runs whose result is cheap to verify. | `explore`, coding, review, or `quality-gate`. |
| `inherit` | Parent is already grok-4.6 (or composer for a `deterministic` child). | Switching quality tiers; name the slug instead. |

Workers do not spawn further unless the root explicitly assigns coordination of an independently scoped task. Composer never coordinates.

`subagent_type`: `explore` for read-only gather; `shell` for long defined commands; `generalPurpose` for `implement`, review, and `quality-gate`. Do not use Bugbot or security-review types unless the user asked for those skills.

## Disclose Every Spawn

Immediately before every Task call, tell the user:

- The agent task name.
- Exact model slug, such as `cursor-grok-4.6-high`.
- Role, leaf vs authorized coordinator, and `subagent_type`.

Group simultaneous spawns into one compact update. Describe these as requested configuration. If the runtime reports a different model, disclose the correction. Spawn independent Tasks in one message so they run in parallel.

```text
Spawning:
- `log_explore` — `cursor-grok-4.6-high`, explore — read-only gather
- `impl_auth` — `cursor-grok-4.6-high`, generalPurpose — implement
- `ci_watch` — `composer-2.5-fast`, shell — deterministic
```

## Personas

Assignment shapes, not permanent project agents. Role slugs match `~/.agents/skills-vendor/ROLES.md`.

### `explore` — grok, explore

Read-only gather: logs, diffs, docs, health. Return paths, commands, timestamps, exact failures, and confidence. Not Jira evidence capture.

### `follow` — grok shell, or composer if `deterministic`

Run an already-written skill or procedure with explicit inputs and completion checks. Composer only when the CLI is the worker and the result is cheap to verify.

### `implement` — grok, generalPurpose

Own one bounded code surface, spec, or review target. Run targeted checks. Report changed files, checks, and residual risk. Distinct file ownership.

### `task-owner` — grok, generalPurpose

Own a substantial independent task (worktree / key). Coordinate children only when explicitly authorized. Return one integrated result.

### `quality-gate` — grok, generalPurpose

Challenge architecture, diagnosis, security, financial correctness, or release readiness. Ask for the strongest competing explanation. Return a recommendation; keep the final decision with the root and user. Disclose that Cursor has no Sol-max equivalent.

## Delegation Patterns

- **Production incident:** grok `explore` for live health/logs; grok `implement` for the relevant code path. Root separates cause from mitigation.
- **PR or release:** grok `explore` for exact-head diff/CI; grok `implement` for substantive review and merge-risk. Approval, merge, deploy stay with the root unless the user delegates those actions.
- **Analytics or payments:** separate grok `explore` gathers, then grok to reconcile. Root keeps money-sensitive final judgment.
- **UI work:** grok `implement` for bounded or larger independent implementation.
- **Long-running procedure:** grok shell, or composer when `deterministic`, so the root stays available.
- **Consulting or research:** grok `explore` for sources; grok `implement` to normalize; root for the recommendation.

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
