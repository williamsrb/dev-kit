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

Use this structure for chat QA reports. Do not stylistically compress the fence.

```markdown
## QA validation

**Requirement:** <one-sentence restatement>

**Delivery scope:** staged | unstaged | branch diff vs main/master

**Verdict:** PASS | PASS WITH NOTES | FAIL

### Fixes applied
- <file>: <what changed and why> — or "None"

### Requirement fit
- <finding>
- **ACs:** `<AC text>`: PASS | FAIL | n/a — one bullet per plan AC (or "n/a — no plan ACs")
- **User scope exclusions:** PASS | FAIL (<element>: allowed delta vs actual deltas) — or "n/a"
- **Implicit requirements:** PASS | FAIL | n/a — unticked extras absent; ticked extras present; DOs shipped — or "n/a — Implicit: none"

### Impact on other features
- <finding>

### Code quality
- <finding>

### Less-code-is-better
- <finding — include net diff impact if fixes reduced delivery size>

### AI slop (deslop)
- <finding — comments / defensive / any-cast / nesting — or "None">

### Performance
- <finding> — or "None"

### Security
- <finding> — or "None"

### Tests
- <finding> — or "n/a"

### Follow-up
- Run `enonic-staged-validation-commit-message` (Enonic backend JS) or `generic-staged-validation-commit-message` (other stacks) next — both validate **and fix** syntax/semantics/lint, then draft the commit message. For message-only, use `staged-commit-message`.
- Review artifact path (review mode): `.tasks/<KEY>-review.md` or `tasks/<KEY>-review.md` — or "n/a"
- Escalate to Bugbot / Security Review built-ins only if requested or clearly needed
- <optional action items if FAIL or PASS WITH NOTES>
```

## Reporting rules

- Be concise. Bullets over long prose.
- Separate confirmed facts from assumptions.
- List every source edit under **Fixes applied** (file + brief reason).
- If validation is incomplete, say so.
- If no fixes were needed, say `None` under **Fixes applied**.
- Re-run delivery diff commands after fixes so the report reflects final state.
- Verdict is **post-fix**: **FAIL** only if a Blocker remains; unfixed Concerns → **PASS WITH NOTES**; Notes / less-code nits / AI slop / Impeccable polish never **FAIL**.
- Blocker/Concern bullets include the one-line evidence certificate (`Premise → Path → Verdict`). Notes use `Premise → Improvement → Fix`.
- One finding per root cause; extra sites as `also applies: path:line`.
- Do not report linter-owned, formatter-owned, pre-existing untouched debt, speculative, unread-code, or generated/vendor candidates.
