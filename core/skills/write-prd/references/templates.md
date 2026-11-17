# PRD templates

Format standard (header order, section order, footer): `~/.agents/kb/implementation/How-to-format-a-prd.md`. These templates apply it.

Load only the template for the chosen type. Headings marked _(optional)_ appear only when the source gives content for them; in the written PRD drop both the _(optional)_ marker and the placeholder text. These templates are the one local PRD contract; `handoff` writes its PRD format through them. The `Description` / `Acceptance Criteria` / `Comments` H2s match Jira exports, so `agentctl markdown slice` and `plan-implementation` read local and Jira PRDs the same way.

When later input is merged into an existing PRD (a follow-up chat, a new note), use `## Comments (<count>)` with `### Comment local-<n> — <who> — <date>` so `--sections comments` still works.

Codes: user stories `US1…`, functional requirements `FR-001…`, success criteria `SC-001…`, open questions `Q1…`. Number in order; never reuse a code after a rewrite.

## Feature

```markdown
# <slug> — <title>

**Source:** <write-prd | local handoff>
**WORK-ID:** <slug>
**Type:** Feature
**Created:** <YYYY-MM-DD>
**Origin:** <chat | email from <role> | Slack thread URL | file path>

---

## Description

<Two or three short paragraphs: the problem, who has it, and the intended outcome. Facts from the source.>

### Context

- <Project, repo path, site/app, the affected area. Pointers only.>
- <Current behavior when it matters, with evidence: path:line, extract-kit spec FR, URL.>

---

## Requirement Changes

- **RC1** — Comment <id> — <who> — <YYYY-MM-DD>: <the change, one sentence>. Supersedes: <short quote or section, or "adds">.

<"None detected." when the source has no later change.>

Checked through: <last comment id | none>

---

## User Scenarios

### US1 — <title> (Priority: P1)

<One paragraph: who does what, and what they get.>

**Why this priority:** <One sentence.>
**Independent test:** <How to prove this story alone, on review or local.>

### US2 — <title> (Priority: P2)

…

---

## Acceptance Criteria

### US1

- [ ] **Given** <state>, **When** <action>, **Then** <observable result>.
- [ ] …

### US2

- [ ] …

---

## Requirements

- **FR-001**: System MUST <behavior>.
- **FR-002**: …

## Key Entities _(optional)_

- **<Entity>**: <what it is, key fields, relations>.

## Success Criteria _(optional)_

- **SC-001**: <Measurable outcome: count, time, ratio, exact value.>

## Edge Cases

- <Boundary, empty, failure, permission, locale, concurrency case and the expected behavior.>

## Non-Goals _(optional)_

- <Explicitly out of scope; operator exclusions verbatim.>

## Constraints _(optional)_

- <Stack, compatibility, design, legal, deadline facts that bound the solution.>

## Open Questions

- **Q1** <Question>. Options: (1) <recommended> — recommended, <why>; (2) <alternative>. Default if unanswered: <option>.

## Evidence

- <Source quotes (short), links, attachments, path:line, spec references that back the sections above.>

---

## Comments (0)

No comments.

---

## Attachments (<n>) _(optional)_

Directory: `~/.agents/prds/<slug>/attachments`

- `<file>` — <what it shows>

---

*Written by <write-prd | handoff> on <YYYY-MM-DD>*
```

## Bug

The stories here are the broken journeys. One story per distinct symptom; most bugs have one.

```markdown
# <slug> — <title>

**Source:** <write-prd | local handoff>
**WORK-ID:** <slug>
**Type:** Bug
**Created:** <YYYY-MM-DD>
**Origin:** <…>
**Severity:** <Blocker | Major | Minor | Trivial> _(<reason, or "reporter's label">)_

---

## Description

<What is broken, for whom, since when if known, and the business impact. Facts from the source.>

### Environment

- Reported on: <host/URL, app version, browser/device if relevant>
- Reproduce on: <review host or local> _(production symptoms are restated here)_

### Steps to reproduce

1. <Step with exact input, content item, user role.>
2. …

### Expected

<Correct behavior. Cite the reference: extract-kit spec FR, prior release, documented rule, or the reporter's statement.>

### Actual

<Observed behavior: error text, wrong value, screenshot/log reference.>

### Regression _(optional)_

<Last known good version or date, related change, if the source says so.>

---

## Requirement Changes

- **RC1** — Comment <id> — <who> — <YYYY-MM-DD>: <the change, one sentence>. Supersedes: <short quote or section, or "adds">.

<"None detected." when the source has no later change.>

Checked through: <last comment id | none>

---

## User Scenarios

### US1 — <the broken journey> (Priority: P1)

<Who is blocked and what they need to work again.>

**Independent test:** <Re-run the steps to reproduce on review; the Expected result appears.>

---

## Acceptance Criteria

### US1

- [ ] **Given** <reproduce setup on review>, **When** <the failing action>, **Then** <expected result>.
- [ ] **Given** <neighboring case that works today>, **When** <action>, **Then** <it still works>. _(regression guard)_

---

## Requirements

- **FR-001**: System MUST <correct behavior>.

## Edge Cases

- <Variants of the input that may hit the same defect.>

## Non-Goals _(optional)_

- <Cleanup of production data, unrelated defects seen while reproducing.>

## Open Questions

- **Q1** …

## Evidence

- <Reporter quote (short), error/log excerpt, screenshot or attachment names, path:line if already located.>

---

## Comments (0)

No comments.

---

## Attachments (<n>) _(optional)_

Directory: `~/.agents/prds/<slug>/attachments`

- `<file>` — <what it shows>

---

*Written by <write-prd | handoff> on <YYYY-MM-DD>*
```

## Report

For data extracts and research. The deliverable is a file or a written answer, so the criteria check the deliverable, not shipped behavior. If the request also needs new code (an endpoint, a scheduled export), the type is Feature.

```markdown
# <slug> — <title>

**Source:** <write-prd | local handoff>
**WORK-ID:** <slug>
**Type:** Report
**Created:** <YYYY-MM-DD>
**Origin:** <…>
**Requested by:** <role, not personal contact details>
**Due:** <date or "not stated">

---

## Description

<The decision or action this report supports, and who reads it.>

### Questions to answer

1. <Precise question; one metric or finding per line.>
2. …

### Scope

- Data sources: <system, repository, CMS project, API, logs, documents, web sources>
- Period: <from–to, timezone>
- Population and filters: <sites, locales, statuses, content types; inclusions and exclusions>
- Definitions: <each metric or term and how it is computed>

### Output

- Format: <CSV | XLSX | Markdown | doc | slides>, delivered to <path, Jira attachment, Slack>
- Shape: <one row per …; columns `a`, `b`, `c`; or the report outline>
- Audience language: <product language | technical>

---

## Requirement Changes

- **RC1** — Comment <id> — <who> — <YYYY-MM-DD>: <the change, one sentence>. Supersedes: <short quote or section, or "adds">.

<"None detected." when the source has no later change.>

Checked through: <last comment id | none>

---

## Acceptance Criteria

- [ ] Every question above has an answer backed by data or a cited source.
- [ ] The output matches the stated format and shape; <row count, totals or a spot check that proves completeness>.
- [ ] Method and sources are stated so the report can be reproduced.
- [ ] <Request-specific check.>

---

## Non-Goals _(optional)_

- <Questions deliberately not answered; follow-up analysis.>

## Constraints

- Read-only on source systems unless the request says otherwise.
- <Privacy: personal data excluded or aggregated; access limits.>

## Method _(optional)_

- <Known approach or constraints on method: read-only access, sampling, tools allowed.>

## Open Questions

- **Q1** …

## Evidence

- <The request quote (short), links to sources or prior reports.>

---

## Comments (0)

No comments.

---

## Attachments (<n>) _(optional)_

Directory: `~/.agents/prds/<slug>/attachments`

- `<file>` — <what it shows>

---

*Written by <write-prd | handoff> on <YYYY-MM-DD>*
```
