---
id: quality-gate-delivery-scope
when_skills: [validate-impl, lint-and-draft-enonic-commit-message, lint-and-draft-generic-commit-message, draft-commit-message]
inputs: [git status, staged/unstaged/branch diffs]
outputs: [active delivery tier]
stop_if: [empty delivery]
read: whole
prose: caveman-lite
---

# Delivery scope

All validation, fixes, and commit-message drafting apply only to the current solution delivery. Resolve it in this order:

| Priority | Source | Git command |
|----------|--------|-------------|
| 1 | **Staged code** | `git diff --cached --name-only` and `git diff --cached` |
| 2 | **Unstaged changes** (when the index is empty) | `git diff --name-only` and `git diff` |
| 3 | **Branch diff vs base** (when the working tree is clean) | `git diff main...HEAD` or `git diff master...HEAD` (use whichever exists) |

Also run `git status --short` every time to confirm which case applies.

## Procedure

1. Prefer the highest-priority source that has content.
2. When fixing, edit only files in that delivery scope unless a one-line import/caller fix is required to keep the delivery correct.
3. AI slop (deslop) uses this same scope — delivery hunks only. Never a whole-tree sweep and never "always vs main."
4. After fixes, re-diff the delivery. Re-validate until clean or remaining issues are reported as blockers.
5. Draft commit messages from only files in that delivery scope (after fixes, when the skill also validates).
6. If the delivery is empty, say so and skip validate/draft. Tell the user which files to stage if work exists unstaged.
7. Do not stage fixes after editing. Use `git diff` (unstaged) to verify.
8. Never run `git add` or `git restore --staged`. Leave all agent edits unstaged. The user stages manually.

## Pitfalls

- Do not mix staged and unstaged as one delivery when the index has content. Staged wins.
- Do not `git add` to "include" QA fixes.
