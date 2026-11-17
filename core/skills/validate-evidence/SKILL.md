---
name: validate-evidence
description: "Validate the evidence a run captured for a task (screenshots, local folder, and the tracker comment when one was posted) against its evidence plan and acceptance criteria. Report only: no capture, no posting, no tracker writes. Jira is the only supported tracker. Use after run-plan on an evidence plan, before or after the tracker post."
metadata:
  recommendedRole: impl-review
  reviewOf: run-plan
  aliases: evidence-validate, review-evidence, qa-evidence
  cliDependencies:
    required: [agentctl, identify, python3]
    optional: [tesseract, ollama]
  localModels:
    preferred: granite3-moe:3b
    available: [granite3-moe:3b, qwen3.5:2b, gemma4:e4b]
---

## Local deterministic first

`python3 scripts/gate-evidence-folder.py <TASK-ID>` (path relative to this skill dir) runs presence, pixel size, stamp, whitespace-overlay and OCR-token checks over every planned shot and prints bounded JSON. Do not loop those checks by hand. `agentctl plan progress <TASK-ID> --kind evidence --json` lists the planned shots; its `done` is inferred from files on disk, so it is a claim to check, not a result. Use `agentctl evidence inspect` for a single shot, `tesseract-cli` for OCR, never a vision model for OCR.

# Validate Evidence

Independent check of evidence that already exists. Answers: does it prove the acceptance criteria, are the shots good, and, when a tracker comment was posted, is that comment honest and intact. Evidence can sit only in the local folder (`mode` local, or Jira run not yet posted) or also in a Jira comment. Both are in scope; the tracker half runs only when something was posted or the mode is `jira`.

**Report only.** This skill does not capture, retake, open a browser, edit images, post, edit, delete or upload to the tracker, or rewrite a comment draft. Its single write is recording failed steps as `pending` in the evidence progress file so `run-plan` retakes them. Run it in a fresh session, on a different model than the one that captured (`impl-review`).

## Not this skill

| Need | Use |
|------|-----|
| Write the evidence plan | `plan-task-evidence` |
| Review the evidence plan document | `validate-plan` (kind evidence) |
| Capture or retake shots, post the comment | `run-plan` on the evidence plan |
| Draft or rewrite analyst-facing comment text | `write-analyst-message` |
| Review the delivery diff | `validate-impl` |

## Context budget (token)

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md`. Allowlist: the evidence plan (`agentctl plan resolve <TASK-ID> --kind evidence`), the AC source that plan cites (prefer implementation AC and Constraints / Non-Goals headings from `agentctl plan resolve <TASK-ID>` via `agentctl markdown slice`), `evidence.progress.md`, the evidence folder, and the posted comment. Do not read the full PRD, the delivery diff, a worktree, or other tasks. Existing `~/.agents/prds/<TASK-ID>.md` is the task copy: do not re-fetch the issue (`plan-task-evidence` override 14).

## Knowledge base (mandatory)

Read before judging. Do not copy these into the report.

| Topic | Path |
|-------|------|
| Screenshot gate, failure table, OCR and whitespace pitfalls | `~/.agents/kb/testing/_shared/How-to-check-evidence-screenshots-before-jira.md` |
| Product concept and expected paint | `~/.agents/kb/testing/_shared/How-to-gate-evidence-on-the-product-concept.md` |
| Jira comment rules (jira, posted only) | `~/.agents/kb/testing/_shared/How-to-post-jira-evidence-comments.md` |
| Comment shape and the 16 overrides | `~/.agents/skills/plan-task-evidence/SKILL.md` § overrides, `templates.md` § "Jira evidence comment" |
| User scope exclusions | `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md` |

## Inputs

`<TASK-ID>` (Jira key or kebab slug) is enough. A user-supplied comment id or URL pins the posted comment. Run `agentctl plan context <TASK-ID>` and print its paths and `mode` before work. No evidence plan resolves: stop and hand off to `plan-task-evidence`. Several keys: one pass per key, then a one-line batch verdict.

## Workflow

```text
- [ ] 1. Resolve plan, mode, evidence folder; print paths
- [ ] 2. Read the KB rows above
- [ ] 3. Local checks (references/local-checks.md)
- [ ] 4. Decide posted state; tracker checks if jira (references/tracker-checks.md)
- [ ] 5. Verdict
- [ ] 6. Record failed steps as pending; report; stop
```

1. **Resolve.** `agentctl plan resolve <TASK-ID> --kind evidence`, then `agentctl plan context`. State `mode`, the evidence folder (`~/.agents/prds/<TASK-ID>/evidence`) and the AC source.
2. **Local checks.** Load [references/local-checks.md](references/local-checks.md) and run it in full. It applies in every mode.
3. **Posted state.** `mode` local: `Tracker: local only`, skip the tracker file. `mode` jira: load [references/tracker-checks.md](references/tracker-checks.md), find the evidence comment, and set `Tracker: not posted` or `posted (comment <id>)`. A missing token or unreachable API makes the tracker half `unverified`, never a pass. A tracker other than Jira is not supported: report the local half and say the tracker half was not checked.
4. **Verdict.** See below. A concept fail, a login-page shot, a wrong page or a shot that cannot be read is a failed step even when the gate script passes.
5. **Record.** For each failed step run `agentctl plan progress <TASK-ID> --kind evidence --set <FILE>=pending --note "validate-evidence: <reason>"`. Without this a bad file on disk still counts as captured. Never delete or overwrite a shot, and never touch the tracker.
6. **Report** per the template, then stop. Retakes are `run-plan` in a fresh session. Edits to a posted comment need the operator's explicit order, a backup first, and the same-day rule (`plan-task-evidence` overrides 8 and 9).

## Verdicts

| Verdict | Meaning |
|---------|---------|
| **PASS** | Every AC has a passing shot or a recorded cut; every gate clean; tracker half clean or n/a. When not posted: ready to post. |
| **FAIL** | Any failed shot, uncovered AC with no cut, concept missing, or posted comment that is duplicated, missing images, posted over a failed step, or claims what no shot shows. |
| **INCOMPLETE** | Nothing failed, but a check could not run (no token, API error, tool missing) or steps are still `pending`. Name each unrun check. |

A posted comment on a FAIL run is reported, not repaired. Do not post a partial or failing set; `plan-task-evidence` override 1 stands.

## Report template

Chat layout per Response formatting: no Markdown list syntax, markers with `&nbsp;` spacers, one spacer paragraph before 👉.

```markdown
**Verdict:** PASS | FAIL | INCOMPLETE. Task `<ID>`, mode `<jira|local>`, plan `<absolute path>`
**Tracker:** local only | not posted (post-ready | blocked) | posted (comment `<id>`, created `<date>`) | unverified (`<why>`)

## Blockers

&nbsp;&nbsp;&nbsp;&nbsp;🚫&nbsp;&nbsp;&nbsp; <what stops posting or sign-off>

## Coverage

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; AC1: `01-x.png`. <what the pixels show>

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; AC2: `02-y.png`. <deciding defect>

&nbsp;&nbsp;&nbsp;&nbsp;🔸&nbsp;&nbsp;&nbsp; AC3: cut in plan (`<reason>`) | no shot

## Shots (gate script + read)

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <n>/<total> pass gate and read

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; `03-z.png`: <not-stamped | overlay-suspect | text-not-found:… | wrong page | concept missing>

## Tracker (jira)

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; images resolve, one comment, hashes match local

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <duplicate | missing media | posted over failed step | claim without shot | lint finding>

## Not verified

&nbsp;&nbsp;&nbsp;&nbsp;🔸&nbsp;&nbsp;&nbsp; <check that did not run, and why>

## Recorded

&nbsp;&nbsp;&nbsp;&nbsp;🔹&nbsp;&nbsp;&nbsp; `agentctl plan progress … --set <FILE>=pending` for: <files>

&nbsp;

&nbsp;&nbsp;&nbsp;&nbsp;👉&nbsp;&nbsp;&nbsp; <next: "RETAKE" via `run-plan` in a fresh session, post the evidence, or operator decision on a posted comment>
```

Omit **Blockers** with no hard-stop and **Tracker (jira)** when local only. A section with nothing to report holds the plain line `None`.

## Final reply: next step (always last)

When any step was marked `pending` ("RETAKE"), put this block right after the 👉 line, as the last thing in the reply, with `<TASK-ID>` expanded (Jira key or slug). The operator pastes it into a fresh session. Skip it when `called_from` is set or `AGENTCTL_FACTORY` is set. All steps pass: no block; the workflow ends here.

```text
/run-plan ~/.agents/plans/<TASK-ID>/evidence.md
```
