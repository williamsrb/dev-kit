---
id: how-to-choose-validation-skills
when_skills: [validate-plan, validate-impl, lint-and-draft-commit-message, draft-commit-message]
inputs: [user intent]
outputs: [skill name]
stop_if: []
read: whole
prose: caveman-lite
---

# Choose validation vs QA vs commit-message skills

## Procedure

1. Implementation spec or evidence/test plan document (`Validate/fix the plan`) → `validate-plan`. Not delivery code.
2. Requirements / quality / security / less-code / AI slop (deslop) on a **delivery diff** → `validate-impl` (alias `impl-validate`; review artifact: `qa-review` / `review-task`). Standards live under `~/.agents/kb/validation/Quality-gate-*.md`.
3. Syntax + lint + commit message → `lint-and-draft-commit-message`. It detects python / PHP / Enonic / generic from delivery files and lazy-loads only matching stack rules.
4. Commit message only (no validate) → `staged-commit-message`.

## Shared quality-gate KB

| File | Purpose |
|------|---------|
| `Quality-gate-delivery-scope.md` | Staged → unstaged → branch diff |
| `Quality-gate-delivery-standards.md` | Fix policy, fit, exclusions, quality, less-code, AI slop, perf, security, tests, verdict |
| `How-to-respect-user-scope-exclusions.md` | User/chat exclusions > Figma |
| `../implementation/How-to-handle-implicit-requirements.md` | Tick list vs DO vs slop; not TBD |
| `Quality-gate-response-template.md` | Chat QA report structure |

Reuse these from any skill that validates or drafts a delivery commit message. Do not copy the rules inline.

## Pitfalls

- Do not run `validate-impl` on a plan Markdown file. That is `validate-plan`.
- Do not run `lint-and-draft-commit-message` expecting requirement-fit review. That is `validate-impl`.
- Do not skip `validate-impl` before `lint-and-draft-commit-message` when the user asked for both quality and commit.
- Do not install a separate deslop skill for delivery cleanup. AI slop is a mandatory `validate-impl` check on the delivery diff.
