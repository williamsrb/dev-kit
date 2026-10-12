---
name: ponytail-review
description: "Review a delivery diff for over-engineering only: reinvented stdlib, unneeded deps, speculative abstractions, dead flexibility. One line per finding; does not apply fixes. Use when the user says ponytail-review, review for over-engineering, what can we delete, is this over-engineered, or simplify review. Complements validate-impl deslop. | recommendedRole: impl-review | aliases: over-engineering-review, simplify-review."
metadata:
  recommendedRole: impl-review
  reviewOf: run-plan
  aliases: over-engineering-review, simplify-review
---

# Over-engineering review

Report-only. List what to delete on the **delivery diff**. Do not edit files. Correctness, security, and performance are out of scope — route those to `validate-impl`.

## Context budget

Delivery **diff** plus, when present, plan **Constraints** / **Non-Goals**. Honor `How-to-respect-user-scope-exclusions.md`. Do not read the full PRD or evidence plan.

## Format

One line per finding: `L<line>: <tag> <what>. <replacement>.` Multi-file: `<file>:L<line>: ...`.

Tags:

- `delete:` dead code, unused flexibility, speculative feature. Replacement: nothing.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does. Name the feature.
- `yagni:` abstraction with one implementation, config nobody sets, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

End with `net: -<N> lines possible.` If there is nothing to cut: `Nothing to cut.` Stop.

## Do not flag

- Structure required by operator intent, ACs, Figma, or project conventions (React4XP parts/schemas/processors, design-system components). Native `<input type="date">` is not a finding when the spec is a designed picker.
- Tests that match repo convention (Jest/JUnit). A missing required test is not this skill's job.
- Trust-boundary validation, data-loss handling, security, accessibility.

## Examples

- `L12-38: stdlib: 27-line validator class. "@" in email, 1 line; confirmation mail is the real check.`
- `L4: native: moment.js imported for one format call. Intl.DateTimeFormat, 0 deps.`
- `repo.py:L88: yagni: AbstractRepository with one implementation. Inline it until a second one exists.`
- `L52-71: delete: retry wrapper around an idempotent local call. Nothing replaces it.`
- `L30-44: shrink: manual loop builds dict. dict(zip(keys, values)), 1 line.`
