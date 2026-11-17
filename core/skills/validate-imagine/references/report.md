# Report and log

## Chat report

Layout per Response formatting: no Markdown list syntax, a blank line between items, markers with `&nbsp;` spacers. Omit **Blockers** when there is none; a section with nothing to report holds the plain line `None`. Tables are fine and carry no markers.

```markdown
**Verdict:** PASS | PASS WITH FIXES | FAIL. Lake `<absolute path>`. Mode: fix | report. Baseline: <verbatim brief | README one-liner (weak)>

## Blockers

&nbsp;&nbsp;&nbsp;&nbsp;🚫&nbsp;&nbsp;&nbsp; F1 <class>: <what remains and what it needs: a decision, or an `imagine` rerun>

## Concept trace

| Atom | Source layer | Status | Where |
|---|---|---|---|
| <atom> | brief / P0 / chat | honored / deviated (fixed) / absent (filled) / open | <file: section> |

## Fixes applied

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; F2 deviation, <file: section>: <what changed, toward which layer>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; F3 contradiction, <files>: <winner, sites updated>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; F4 incomplete, <file: section>: <what was filled, from what>

## Mechanical audit

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; before: <B> blocker, <M> major, <m> minor, <R> review. after: <B> blocker, <M> major, <m> minor

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; after: <what still fails and why>

## Exclusions

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; PASS: <excluded element: no trace left>

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; FAIL: <excluded element: where it remains>

## Open

&nbsp;&nbsp;&nbsp;&nbsp;🔸&nbsp;&nbsp;&nbsp; Assets to redo: <ids and reason each: failed | pending key | deviates from design | design value changed>

&nbsp;&nbsp;&nbsp;&nbsp;🔸&nbsp;&nbsp;&nbsp; Needs `imagine` rerun: <gap that needs an expansion wave>

&nbsp;&nbsp;&nbsp;&nbsp;❓&nbsp;&nbsp;&nbsp; <concept-level decision for the operator, with options>

## Not verified

&nbsp;&nbsp;&nbsp;&nbsp;🔸&nbsp;&nbsp;&nbsp; <audio/video/3D not reviewed; sources not opened; tools missing (`magick`, `ffprobe`)>

## Follow-up

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; Log: `<lake>/validation-log.md`. Undo copy: `<lake>/.validation/<run-id>/before/`.

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;👉&nbsp;&nbsp;&nbsp; <next step: redo assets with `imagine-design`, the operator decision, or the `imagine` rerun>
```

A decision for the operator with options uses the Option lists layout (exclusive options: keycaps, recommended first, O-codes).

## `validation-log.md` (in the lake)

A file, so plain Markdown. Append one section per run; never rewrite earlier runs.

```markdown
## Run <run-id> (<YYYY-MM-DD>, <fix|report>)

Baseline: <verbatim brief | weak>. Verdict: <verdict>. Audit before/after: <B/M/m> -> <B/M/m>.

### Concept trace
<the table>

### Findings
- F1 <class> <severity> <file: section>: <evidence>. Winner: <layer>. Fix: <applied: what | open: why>.

### Dismissed
- <review candidate>: <reason>

### Canon, design, registry changes
- <file: key>: <old> -> <new>. Why: <layer 1-3 point>.

### Redo list
- <asset id>: <reason>

### Not verified
- <item>
```

The snapshot in `.validation/<run-id>/before/` pairs with this run: `diff -ru .validation/<run-id>/before <lake>` shows every edit.
