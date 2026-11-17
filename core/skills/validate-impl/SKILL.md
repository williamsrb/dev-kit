---
name: validate-impl
description: "Review and fix the current delivery against its PRD and plan (spec alignment, fit, quality, deslop, security). Run before lint-and-draft-*. Not syntax-only."
metadata:
  recommendedRole: impl-review
  reviewOf: run-plan
  aliases: impl-validate, review-task, validate-implementation
  cliDependencies:
    required: [agentctl, git, rg, jq]
    optional: [ollama, ruff, shellcheck, shfmt, markdownlint-cli2, lychee, codespell, ast-grep, gitleaks, osv-scanner, trivy, semgrep]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Start with `agentctl repo detect --cwd <repo> --json` and `agentctl delivery scope --cwd <repo> --json`. `agentctl plan context <TASK-ID>` returns the PRD and plan paths, `agentctl markdown slice` opens single sections, and `agentctl plan progress <TASK-ID> --json` lists the step state. Use local validators first; open only compact failures and the PRD and plan sections needed for judgment. The security pass runs `agentctl security scan` (step 11) — do not hunt for secrets by reading alone.

# Implementation validation

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md`. Allowlist: delivery **diff** + resolved implementation plan (AC / GO / **Constraints** / Non-Goals / Implicit / `tbd.md` decisions / validation companion) when present + the PRD requirement sections, sliced, for spec alignment. Apply `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md` and `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Honor explicit **user/chat exclusions** over conflicting plan ACs. Unticked implicit extras are out of scope. Do **not** read the whole PRD, its full comment thread, or the evidence plan.

## Goal

Validate **and improve** the current solution delivery:

1. Confirm it does what the PRD asks, through the plan: no requirement dropped, narrowed or changed on the way (**spec alignment**).
2. Confirm it fits the plan's acceptance criteria without breaking unrelated features.
3. Check code quality, less-code-is-better, and **AI slop (deslop)** on the delivery diff.
4. Check for performance and security issues introduced by the delivery.
5. **Apply targeted source fixes** in the delivery scope to move closer to QA goals.

QA is not read-only (default mode). After analysis, edit code when a fix is safe, localized, and clearly improves QA metrics.

A PASS is a claim with proof. Every acceptance criterion and PRD statement reported as met cites `ran` (a test or command executed in this run) or `read` (`file:line`). What only a browser, CMS content or an external system can show is reported as `unproven` under Not verified, not as PASS.

This is the `impl-review` role: run it in a fresh session, on a different model than the one that wrote the delivery. When this session also wrote the code, say so in the first line of the report.

## Knowledge base (mandatory)

**Read and apply** these shared quality-gate guidelines before validating:

| Topic | Path |
|-------|------|
| Delivery scope (staged / unstaged / branch diff) | `~/.agents/kb/validation/Quality-gate-delivery-scope.md` |
| Standards (fix policy, fit, spec alignment, exclusions, quality, less-code, AI slop, perf, security, tests, evidence/verdict) | `~/.agents/kb/validation/Quality-gate-delivery-standards.md` |
| Spec alignment (PRD → plan → delivery: requirement list, states, authorized deviations) | `~/.agents/kb/validation/How-to-check-spec-alignment.md` |
| User scope exclusions | `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md` |
| Implicit requirements (tick list vs DO vs slop) | `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md` |
| Chat report template | `~/.agents/kb/validation/Quality-gate-response-template.md` |

Other skills reusing delivery QA should read the same KB files instead of duplicating these rules.

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **qa** (default) | `validate-impl`, `impl-validate`, `delivery-qa`, `qa-check`, `deslop` | Full QA + fix loop (includes mandatory AI slop pass); report in chat |
| **review** | `qa-review`, `review-task`, `implementation-review`, or user asks for a review file | Same checks + write `.tasks/<KEY>-review.md` (or `tasks/`); **less aggressive auto-fix** unless user asked to fix — see [references/review-mode.md](references/review-mode.md) |
| **report** | The caller says "report only" or "edit nothing" (the `release-review` pipeline), or the user asks for findings without fixes | Same checks, **no edits**: skip steps 13 and 14. The diff range, requirement source, and output path and schema the caller names win over `agentctl delivery scope` and `agentctl plan context`. Judge exactly the caller's criterion ids with exactly its state words (`contradicted` is `unmet`), and follow its rules over the How-to's: when it says the plan never lowers the criteria, an authorized deviation does not turn `unmet` into `met`; name the deviation in the evidence text. Do not re-run a suite whose result the context already reports |

If unclear, default to **qa**. Optional escalation: Bugbot / Security Review built-in skills (not this skill).

This skill runs entirely in the current agent session — no external Codex/CLI reviewer wrappers.

## Scope boundary

Do **not** validate or rewrite plan documents (`agentctl plan resolve` targets) — that is `validate-plan`. Do **not** edit the plan, the PRD, or `progress.md`, even when spec alignment finds the plan wrong: report the plan gap.

Do **not** duplicate work covered by follow-up skill `lint-and-draft-commit-message`:

- No commit message generation
- No full syntax/semantic pass (semicolons, brace balance, parse checks, unresolved imports) — that skill validates **and fixes** those issues
- No Enonic XP CommonJS/ES5.1 rule pass, no Python ruff/`py_compile` pass, and no PHP `php -l` pass — that skill lazy-loads those stacks
- No `agentctl checks run` (lint and spelling)

You **may** fix obvious delivery bugs found during QA (undefined variables, broken braces, wrong format strings) when they block requirement fit or code quality.

Do **not** commit, push, or create PRs unless the user asks.

## Auxiliary skills (optional, on demand)

Not required for every run. When a QA/review step needs a specialized capability you cannot perform with already-installed skills / MCP / normal tools, and a session-only script is not worth it:

1. Prefer an already-installed skill if one covers the need (including Bugbot / Security Review when those are the right escalation).
2. Otherwise follow the `find-skills` skill as a nested prerequisite (`called_from: validate-impl`): search, verify quality, install if appropriate, then **read and follow** the new skill for the blocked action.
3. Resume this skill’s workflow after the gap is closed.

Example: validating against a design source requires a Figma reader that is not installed → `find-skills` → install/use it → continue QA.

## Workflow

Follow this sequence every time:

1. **Read KB (section)** — `Quality-gate-delivery-scope.md`, needed headings in `Quality-gate-delivery-standards.md`, `How-to-check-spec-alignment.md`, `How-to-respect-user-scope-exclusions.md`, `Quality-gate-response-template.md`.
2. **Resolve task context** — per `How-to-resolve-task-context.md`; given only a key or slug, run `agentctl plan context <TASK-ID>` and print its paths (PRD, plan, mode) before work; a user-supplied implementation-plan path is sufficient when no `<TASK-ID>` resolves. A requirement source or diff range the caller names wins. Assert the branch only when `mode` is `jira`.
3. **Identify delivery scope** — per KB; state which tier (staged / unstaged / branch diff) is active.
4. **Restate the requirement** in one sentence — prefer the user-supplied implementation plan, otherwise `agentctl plan resolve <TASK-ID>`, for AC / validation. Do not require the user to @-attach the PRD. Tick each plan AC PASS / FAIL / n/a, each PASS with its proof (`ran` or `read`). Read `agentctl plan progress <TASK-ID> --json`: a `pending` or `blocked` step points at unfinished work, but the AC verdict decides, not the tick. `stale: true` only says the step text changed after progress was recorded; it is not a finding.
5. **Spec alignment** — per `How-to-check-spec-alignment.md`: run the staleness check, slice the PRD, build the requirement list, and map each row PRD → plan. The delivery half (plan → `file:line`) and each row's final state are settled in step 9, once the diff is read. An explicit statement that is `unmet` or `contradicted` is a Blocker, tagged **plan gap** or **delivery gap**. Delivery gaps are fixed in step 13. A plan gap is reported, never fixed here: do not edit the plan and do not code past it. No PRD on disk: `n/a`, the plan is the only contract.
6. **Collect scope exclusions** — from plan **Constraints** / **Non-Goals**, plus any explicit user/chat exclusions in this conversation. Chat wins over plan ACs on conflict.
7. **Inspect the delivery diff** — read changed files and surrounding context as needed. Use surrounding file style as the deslop baseline (comment density, error handling, nesting).
8. **Validate exclusions (Blocker gate)** — for each excluded element E with allowed delta C only: any other property change on E (alignment, typography, markup, inherited parent flex/grid alignment) is a **Blocker**; fix by restoring pre-change placement/styles on E. Do not expand scope to match a wrong plan AC.
9. **Validate** — spec alignment (delivery half of step 5), requirement fit (per-AC), impact (users of every changed export, route, config key, schema and i18n key), code quality, less-code, **AI slop (deslop)**, performance, security, tests-if-present (per KB standards: evidence bar, do-not-report, one root cause). Deslop is mandatory on every run — delivery hunks only, not a whole-tree sweep.
10. **Run the plan's checks** — run the lines of the plan's Validation section (`validation.md`) that are local and read-only: existing tests and the greps or commands it names, plus the existing suite of a touched layer (KB § Tests). Report each command with its result. A line that needs a browser, a deploy, a server write or credentials goes under **Not verified** with the reason; that is the evidence plan's job. Lint, type-check and syntax lines stay with `lint-and-draft-commit-message`. A command likely to run past two minutes runs in the background.
11. **Security scan (deterministic)** — run `agentctl security scan --cwd <repo> --check secrets,deps --fail-on HIGH` and read the bounded JSON; raw reports stay in `.security-local/`. Attribute a finding as a **Blocker** only when its `location` file is inside the delivery scope — a hard-coded secret in the delivery always is, per KB standards. Findings outside the delivery are pre-existing repo debt: a Note at most, never a delivery verdict. Add `,sast` when the delivery touches input handling, template rendering, deserialization, or shell/SQL/NoQL construction. A check reported `unavailable` was **not run** — name the missing tool instead of reporting a clean security pass.
12. **Optional — Impeccable (design / frontend UI only)** — **skip by default.** Only when the delivery clearly changes **design or frontend UI** (React/TSX views, CSS/styling, layout, visual components, UX copy on a surface). Skip for backend-only, API-only, schema-only, or non-UI diffs. When it applies: read the `impeccable` skill; optionally run `impeccable detect` on delivery UI paths (or `/impeccable audit|critique|polish` guidance). Treat findings as **Notes/Concerns** unless they clearly block the stated UI requirement; do not expand into a redesign the task did not ask for. Never use Impeccable to justify changing an excluded element. UI polish is Impeccable; code slop is deslop — do not mix them.
13. **Apply fixes** — per KB fix policy, including delivery gaps from step 5 when the change is local, and behavior-preserving deslop (comments, defensive noise, type-escape hatches, avoidable nesting). In **review** mode, prefer reporting first; fix only clear Blockers unless the user asked to fix. In **report** mode, skip.
14. **Re-validate** — quick pass on the updated delivery diff (re-check exclusions, remaining slop, and the rows and step-10 checks a fix touched).
15. **Output the QA report** — per KB response template (include **Spec alignment** and **User scope exclusions:** PASS/FAIL). Verdict is post-fix: **FAIL** only if a Blocker remains. A plan gap is a remaining Blocker; its 👉 line names `validate-plan` (or `plan-implementation` when the plan needs new steps), then `run-plan`.
16. **Review mode only** — follow [references/review-mode.md](references/review-mode.md) and write the review artifact when a `<TASK-ID>` is known (Jira key or kebab slug).

## Headless and nested callers

When `AGENTCTL_FACTORY` is set, the step prompt names the report file and its keys. The factory sends `report.blockers` to `run-plan` as its only findings, so:

- `report.blockers` holds one self-contained line per remaining Blocker that `run-plan` can fix: `<file:line>: "<requirement quote>" (<PRD or plan id>): <what is missing>`. A line that needs this session to make sense is useless there.
- A **plan gap** is not fixable by `run-plan`. Report status `blocked`, with the statement, its PRD source, and the plan item that should carry it, so the run parks for the operator.
- Notes and unfixed Concerns go in `summary`, never in `blockers`: each blocker costs a `run-plan` loop.
- A stale PRD goes in `summary` and `next_hint` with the unchecked comment ids.
- A command the worker is denied, or one likely to run past two minutes, is listed under Not verified in `summary`. Do not retry it, rephrase it, or start it in the background.

A caller that supplies a context file (the `release-review` pipeline) defines the range, the requirements and the output schema. Follow it in **report** mode.

## Final reply: next step (always last)

When the verdict is PASS or PASS WITH NOTES, put this block right after the 👉 line, as the last thing in the reply, with `<TASK-ID>` expanded (Jira key or slug). The operator pastes it into a fresh session. Skip it when `called_from` is set or `AGENTCTL_FACTORY` is set. FAIL: no block.

```text
/lint-and-draft-commit-message <TASK-ID>
```
