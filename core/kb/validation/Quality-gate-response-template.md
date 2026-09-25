---
id: quality-gate-response-template
when_skills: [validate-impl]
inputs: [post-fix findings]
outputs: [chat QA report]
stop_if: []
read: whole
prose: caveman-lite
---

# QA response template

Use this structure for chat QA reports. Do not stylistically compress the fence. The layout follows Response formatting (`response-formatting.mdc`): print the fence content as is, with no Markdown list syntax, and keep the blank line between items.

```markdown
**Verdict:** PASS | PASS WITH NOTES | FAIL. <one-sentence requirement restatement>

Delivery scope: staged | unstaged | branch diff vs main/master

## Blockers

&nbsp;&nbsp;&nbsp;&nbsp;🚫&nbsp;&nbsp;&nbsp; <file:line>: <Blocker that remains after fixes>. <Premise → Path → Verdict>

## Fixes applied

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; <file>: <what changed and why>

## Requirement fit

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; AC `<AC text>`: PASS

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; AC `<AC text>`: FAIL. <deciding evidence>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; AC `<AC text>`: n/a

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; User scope exclusions: PASS (<element>: allowed delta vs actual deltas)

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; User scope exclusions: FAIL. <element>: <extra delta>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; User scope exclusions: n/a

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; Implicit requirements: PASS (unticked extras absent; ticked extras present; DOs shipped)

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; Implicit requirements: FAIL. <deciding evidence>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; Implicit requirements: n/a

&nbsp;&nbsp;&nbsp;&nbsp;🔹&nbsp;&nbsp;&nbsp; <other requirement finding>

## Impact on other features

&nbsp;&nbsp;&nbsp;&nbsp;⚠️&nbsp;&nbsp;&nbsp; <finding>

## Code quality

&nbsp;&nbsp;&nbsp;&nbsp;🔹&nbsp;&nbsp;&nbsp; <finding>

## Less-code-is-better

&nbsp;&nbsp;&nbsp;&nbsp;🔹&nbsp;&nbsp;&nbsp; <finding, with net diff impact if fixes reduced delivery size>

## AI slop (deslop)

&nbsp;&nbsp;&nbsp;&nbsp;🔹&nbsp;&nbsp;&nbsp; <finding: comments / defensive / any-cast / nesting>

## Performance

&nbsp;&nbsp;&nbsp;&nbsp;⚠️&nbsp;&nbsp;&nbsp; <finding>

## Security

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <check>: <result>

## Tests

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <suite or command>: <result>

## Not verified

&nbsp;&nbsp;&nbsp;&nbsp;🔸&nbsp;&nbsp;&nbsp; <what was not run or not observable, and why>

## Follow-up

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; Next skill: `lint-and-draft-enonic-commit-message` (Enonic backend JS) or `lint-and-draft-generic-commit-message` (other stacks). Both validate **and fix** syntax/semantics/lint, then draft the commit message. For message-only, use `draft-commit-message`.

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; Review artifact (review mode): `.tasks/<KEY>-review.md` or `tasks/<KEY>-review.md`, or n/a

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; <action item if FAIL or PASS WITH NOTES>

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;👉&nbsp;&nbsp;&nbsp; <the one next action, with the reply keyword uppercase in double quotes when the operator must answer>
```

## Reporting rules

- Be concise. One item per line.
- Markers: ✅ PASS or verified, ⛔ FAIL, plain `•` for n/a and neutral items. Findings by class: 🚫 Blocker, ⚠️ Concern, 🔹 Note.
- Omit **Blockers** when none remain, and **Not verified** when everything ran. Every other section stays; a section with nothing to report holds the plain line `None`.
- Separate confirmed facts from assumptions.
- List every source edit under **Fixes applied** (file + brief reason). If no fixes were needed, write `None`.
- Re-run delivery diff commands after fixes so the report reflects final state.
- Verdict is **post-fix**: **FAIL** only if a Blocker remains; unfixed Concerns → **PASS WITH NOTES**; Notes / less-code nits / AI slop / Impeccable polish never **FAIL**.
- Blocker/Concern items include the one-line evidence certificate (`Premise → Path → Verdict`). Notes use `Premise → Improvement → Fix`.
- One finding per root cause; extra sites as `also applies: path:line`.
- Escalate to Bugbot / Security Review built-ins only if requested or clearly needed.
- Do not report linter-owned, formatter-owned, pre-existing untouched debt, speculative, unread-code, or generated/vendor candidates.
