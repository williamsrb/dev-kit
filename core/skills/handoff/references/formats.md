# Handoff formats

Load only the format the skill selected.

## Context Summary

Save under the OS temp dir. Not a PRD. Not a plan.

```markdown
# Handoff — <focus>

**Format:** Context Summary
**Date:** <YYYY-MM-DD>

## Goal

<What the next session should accomplish. One short paragraph.>

## Done

- <Already decided or shipped. Paths, not pasted bodies.>

## Next

- <Ordered next actions.>

## Artifacts

- <path or URL> — <one-line why it matters>

## Suggested skills

- `<skill-name>` — <why the next agent should invoke it>

## Open questions

- <gap, or "none">
```

## PRD

Save as `~/.agents/prds/<slug>.md`. Same heading contract as a Jira export so `plan-implementation` can `markdown slice` it.

```markdown
# <slug> — <title>

**Source:** local handoff
**WORK-ID:** <slug>
**Created:** <YYYY-MM-DD>

---

## Description

<Problem, who it affects, and the intended change. Facts from this conversation only.>

---

## Acceptance Criteria

- [ ] <Verifiable criterion the user stated. Do not mark extras as _(inferred)_; those become implicit-requirements ticks or TBD at plan time.>

---

## Comments (0)

---

*Persisted from conversation on <YYYY-MM-DD>*
```

Optional H2s when the conversation actually had them (do not invent): `## Non-Goals`, `## Constraints`. Put unanswered product decisions in Description as a short TBD list — do not invent ACs to fill gaps.

If later comments exist (follow-up chat merged in), use `## Comments (<count>)` and `### Comment local-1 — <who> — <date>` so slice `--sections comments` still works.
