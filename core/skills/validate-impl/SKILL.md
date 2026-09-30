---
name: validate-impl
description: "Review and fix the current delivery against requirements (fit, quality, deslop, security). Run before lint-and-draft-*. Not syntax-only. | recommendedRole: implement | aliases: impl-validate, review-task, validate-implementation."
metadata:
  recommendedRole: implement
  aliases: impl-validate, review-task, validate-implementation
  cliDependencies:
    required: [agentctl, git, rg, jq]
    optional: [ollama, ruff, shellcheck, shfmt, markdownlint-cli2, lychee, codespell, ast-grep, gitleaks, osv-scanner, trivy, semgrep]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---
## Local deterministic first

Start with `agentctl repo detect --cwd <repo> --json` and `agentctl delivery scope --cwd <repo> --json`. Use local validators first; open only compact failures and the plan sections needed for judgment. The security pass runs `agentctl security scan` (step 9) — do not hunt for secrets by reading alone.

# Implementation validation

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md`. Allowlist: delivery **diff** + resolved implementation plan (AC / GO / **Constraints** / Non-Goals / Implicit / validation companion) when present. Apply `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md` and `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Honor explicit **user/chat exclusions** over conflicting plan ACs. Unticked implicit extras are out of scope. Do **not** read full PRD comments or the evidence plan by default.

## Goal

Validate **and improve** the current solution delivery:

1. Confirm it fits requirements without breaking unrelated features.
2. Check code quality, less-code-is-better, and **AI slop (deslop)** on the delivery diff.
3. Check for performance and security issues introduced by the delivery.
4. **Apply targeted source fixes** in the delivery scope to move closer to QA goals.

QA is not read-only (default mode). After analysis, edit code when a fix is safe, localized, and clearly improves QA metrics.

## Knowledge base (mandatory)

**Read and apply** these shared quality-gate guidelines before validating:

| Topic | Path |
|-------|------|
| Delivery scope (staged / unstaged / branch diff) | `~/.agents/kb/validation/Quality-gate-delivery-scope.md` |
| Standards (fix policy, fit, exclusions, quality, less-code, AI slop, perf, security, tests, evidence/verdict) | `~/.agents/kb/validation/Quality-gate-delivery-standards.md` |
| User scope exclusions | `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md` |
| Implicit requirements (tick list vs DO vs slop) | `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md` |
| Chat report template | `~/.agents/kb/validation/Quality-gate-response-template.md` |

Other skills reusing delivery QA should read the same KB files instead of duplicating these rules.

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **qa** (default) | `validate-impl`, `impl-validate`, `delivery-qa`, `qa-check`, `deslop` | Full QA + fix loop (includes mandatory AI slop pass); report in chat |
| **review** | `qa-review`, `review-task`, `implementation-review`, or user asks for a review file | Same checks + write `.tasks/<KEY>-review.md` (or `tasks/`); **less aggressive auto-fix** unless user asked to fix — see [references/review-mode.md](references/review-mode.md) |

If unclear, default to **qa**. Optional escalation: Bugbot / Security Review built-in skills (not this skill).

This skill runs entirely in the current agent session — no external Codex/CLI reviewer wrappers.

## Scope boundary

Do **not** validate or rewrite plan documents (`agentctl plan resolve` targets) — that is `validate-plan`.

Do **not** duplicate work covered by follow-up skill `lint-and-draft-commit-message`:

- No commit message generation
- No full syntax/semantic pass (semicolons, brace balance, parse checks, unresolved imports) — that skill validates **and fixes** those issues
- No Enonic XP CommonJS/ES5.1 rule pass, no Python ruff/`py_compile` pass, and no PHP `php -l` pass — that skill lazy-loads those stacks

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

1. **Read KB (section)** — `Quality-gate-delivery-scope.md`, needed headings in `Quality-gate-delivery-standards.md`, `How-to-respect-user-scope-exclusions.md`, `Quality-gate-response-template.md`.
2. **Resolve task context** — per `How-to-resolve-task-context.md`; a user-supplied implementation-plan path is sufficient when no `<TASK-ID>` resolves. Assert the branch only when `mode` is `jira`.
3. **Identify delivery scope** — per KB; state which tier (staged / unstaged / branch diff) is active.
4. **Restate the requirement** in one sentence — prefer the user-supplied implementation plan, otherwise `agentctl plan resolve <TASK-ID>`, for AC / validation. Do not require the user to @-attach the PRD. Tick each plan AC PASS / FAIL / n/a (do not open the PRD or evidence plan for this).
5. **Collect scope exclusions** — from plan **Constraints** / **Non-Goals**, plus any explicit user/chat exclusions in this conversation. Chat wins over plan ACs on conflict.
6. **Inspect the delivery diff** — read changed files and surrounding context as needed. Use surrounding file style as the deslop baseline (comment density, error handling, nesting).
7. **Validate exclusions (Blocker gate)** — for each excluded element E with allowed delta C only: any other property change on E (alignment, typography, markup, inherited parent flex/grid alignment) is a **Blocker**; fix by restoring pre-change placement/styles on E. Do not expand scope to match a wrong plan AC.
8. **Validate** — requirement fit (per-AC), impact, code quality, less-code, **AI slop (deslop)**, performance, security, tests-if-present (per KB standards: evidence bar, do-not-report, one root cause). Deslop is mandatory on every run — delivery hunks only, not a whole-tree sweep.
9. **Security scan (deterministic)** — run `agentctl security scan --cwd <repo> --check secrets,deps --fail-on HIGH` and read the bounded JSON; raw reports stay in `.security-local/`. Attribute a finding as a **Blocker** only when its `location` file is inside the delivery scope — a hard-coded secret in the delivery always is, per KB standards. Findings outside the delivery are pre-existing repo debt: a Note at most, never a delivery verdict. Add `,sast` when the delivery touches input handling, template rendering, deserialization, or shell/SQL/NoQL construction. A check reported `unavailable` was **not run** — name the missing tool instead of reporting a clean security pass.
10. **Optional — Impeccable (design / frontend UI only)** — **skip by default.** Only when the delivery clearly changes **design or frontend UI** (React/TSX views, CSS/styling, layout, visual components, UX copy on a surface). Skip for backend-only, API-only, schema-only, or non-UI diffs. When it applies: read the `impeccable` skill; optionally run `impeccable detect` on delivery UI paths (or `/impeccable audit|critique|polish` guidance). Treat findings as **Notes/Concerns** unless they clearly block the stated UI requirement; do not expand into a redesign the task did not ask for. Never use Impeccable to justify changing an excluded element. UI polish is Impeccable; code slop is deslop — do not mix them.
11. **Apply fixes** — per KB fix policy, including behavior-preserving deslop (comments, defensive noise, type-escape hatches, avoidable nesting). In **review** mode, prefer reporting first; fix only clear Blockers unless the user asked to fix.
12. **Re-validate** — quick pass on the updated delivery diff (re-check exclusions and remaining slop).
13. **Output the QA report** — per KB response template (include **User scope exclusions:** PASS/FAIL). Verdict is post-fix: **FAIL** only if a Blocker remains.
14. **Review mode only** — follow [references/review-mode.md](references/review-mode.md) and write the review artifact when a `<TASK-ID>` is known (Jira key or kebab slug).
