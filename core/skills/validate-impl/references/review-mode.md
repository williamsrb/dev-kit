# QA review mode (artifact)

Use when `validate-impl` runs in **review mode** (`qa-review` / `review-task`, or the user asks for a written review file).

Apply shared delivery standards from `~/.agents/kb/validation/Quality-gate-*.md` and `~/.agents/kb/validation/How-to-check-spec-alignment.md`. Requirement sources are those of the main workflow (plan sections plus the sliced PRD).

## Extra steps (after core QA checks)

1. Use the `<TASK-ID>` resolved in workflow step 2. A legacy `.tasks/<ISSUE-KEY>.md` / `tasks/<ISSUE-KEY>.md` spec is a requirement source only when the user points at it.
2. Carry the spec-alignment rows from workflow step 5 into the artifact. Do not re-read the PRD for it.
3. Prefer **less aggressive auto-fix** unless the user asked to fix — report first, fix Blockers when safe. AI slop (deslop) is Minor/Note unless it has a failure certificate; do not auto-strip it in review mode unless the user asked to fix.
4. Standards extras: when the stack has a practices skill (Enonic React4XP: `apply-react4xp-practices`), read it and note violations in the artifact.
5. Optional Impeccable (design / frontend UI only): when the delivery is clearly UI/design-related, consult the `impeccable` skill and/or `impeccable detect` on changed UI paths; record material findings in the artifact as Notes/Concerns (not a mandatory redesign). Skip for non-UI deliveries.
6. Optional build gates — record failures as Critical in the artifact. Run the project-native type-check, test and build commands named by the plan's Validation section, by `agentctl repo detect`, or by the project's How-to under `~/.agents/kb/implementation/<project>/` (it names that project's tsconfigs and test commands). Build only when the toolchain is available. Never deploy.
7. Write `tasks/<ISSUE-KEY>-review.md` or `.tasks/<ISSUE-KEY>-review.md` from [assets/review-artifact-template.md](../assets/review-artifact-template.md).

## Artifact rules

- **Classes:** Critical = Blocker, Major = Concern, Minor = Note (`Quality-gate-delivery-standards.md` § Findings).
- **Status:** remaining Critical or Major → **CHANGES REQUESTED**; only Minor → **APPROVED WITH OBSERVATIONS**; none → **APPROVED**. Minors/nits never raise the status to CHANGES REQUESTED.
- Critical and Major issues include the one-line evidence certificate (`Premise → Path → Verdict`) plus file:line. Optional `Also applies: path:line`.
- One finding per root cause. Do not re-list linter-owned, formatter-owned, pre-existing untouched, speculative, or generated/vendor items.
- Tick plan ACs (PASS / FAIL / n/a, each PASS with `ran` or `read` proof) in the artifact when `agentctl plan resolve <KEY>` returns a plan.
- An `unmet` or `contradicted` PRD statement is Critical. Say whether it is a plan gap or a delivery gap.
- No praise section. The artifact lists findings and what was verified.
