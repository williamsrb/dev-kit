# QA review mode (artifact)

Use when `validate-impl` runs in **review mode** (`qa-review` / `review-task`, or the user asks for a written review file).

Apply shared delivery standards from `~/.agents/kb/validation/Quality-gate-*.md`.

## Extra steps (after core QA checks)

1. Resolve issue key from user or nearest `.tasks/<ISSUE-KEY>.md` / `tasks/<ISSUE-KEY>.md`.
2. Read the task spec fully when present.
3. Prefer **less aggressive auto-fix** unless the user asked to fix — report first, fix Blockers when safe. AI slop (deslop) is Minor/Note unless it has a failure certificate; do not auto-strip it in review mode unless the user asked to fix.
4. Standards extras (Enonic React4XP): when relevant, read `apply-react4xp-practices` and note violations in the artifact.
5. Optional Impeccable (design / frontend UI only): when the delivery is clearly UI/design-related, consult the `impeccable` skill and/or `impeccable detect` on changed UI paths; record material findings in the artifact as Notes/Concerns (not a mandatory redesign). Skip for non-UI deliveries.
6. Optional build gates (React4XP projects) — record failures as CRITICAL in the artifact:
   - `npx tsc --noEmit -p xp/tsconfig.xp.nashorn.json`
   - `npx tsc --noEmit -p xp/tsconfig.react4xp.json`
   - `cd xp && npx jest --no-coverage`
   - `make build` only if Docker/available; do not `make deploy`
7. Write `tasks/<ISSUE-KEY>-review.md` or `.tasks/<ISSUE-KEY>-review.md` from [assets/review-artifact-template.md](../assets/review-artifact-template.md).

## Artifact rules

- **Status:** remaining Critical or Major → **CHANGES REQUESTED**; only Minor → **APPROVED WITH OBSERVATIONS**; none → **APPROVED**. Minors/nits never raise the status to CHANGES REQUESTED.
- Critical and Major issues include the one-line evidence certificate (`Premise → Path → Verdict`) plus file:line. Optional `Also applies: path:line`.
- One finding per root cause. Do not re-list linter-owned, formatter-owned, pre-existing untouched, speculative, or generated/vendor items.
- Tick plan ACs (PASS / FAIL / n/a) in the artifact when `agentctl plan resolve <KEY>` returns a plan.
