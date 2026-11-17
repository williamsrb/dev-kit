# Local checks

Run for every task, `jira` or `local`. Inputs: the evidence plan, its AC source, `evidence.progress.md`, `~/.agents/prds/<TASK-ID>/evidence/`.

## L1. Coverage

Build one table: AC → plan step → screenshot file → verdict.

- Every AC from the AC source has a proving step with a passing shot, or an entry under the plan's **Cut / impossible** with a reason. An AC with neither is uncovered: FAIL.
- A shot that proves no AC is a finding (`proves nothing`), not a failure. The plan's own **Goal** column says what each shot should prove.
- Files in the folder that the plan does not list (`orphans` in the script output) are reported. Do not delete them.
- `agentctl plan progress` marking a step `done` because the file exists is not a pass. Treat it as "captured", then judge it.
- Steps still `pending` or `blocked` leave the verdict at most INCOMPLETE.

## L2. Gate script

```bash
python3 ~/.agents/skills/validate-evidence/scripts/gate-evidence-folder.py <TASK-ID> \
  --expect 01-name.png='token from the step' --expect 01-name.png='second token'
```

Pick one to three tokens per shot from the plan's **Expected result** and **Goal**: field labels, a URL slug, the heading plus a field. Avoid tokens with a capital `I`, lowercase `l`, `1` or `0` next to each other (`AI crawler`, `llms.txt`): Tesseract confuses them, and a miss on such a token is an OCR artifact, not a bad shot. Check `ocr_text` with `agentctl evidence inspect <png> --ocr` before failing a shot on one token.

Reading the output (`failures` per shot):

| Failure | Meaning | Verdict |
|---------|---------|---------|
| `missing` | Planned file not on disk | FAIL |
| `unreadable` | `identify` cannot open it | FAIL |
| `not-stamped` | `agentctl image stamp --check` exit 1. Plan Execution E1 step 5 stamps every shot, in every mode | FAIL |
| `overlay-suspect` | Full-viewport white page with a few lines, or 6+ grid cells at 0.95 blank. Measured only after stamping: an unstamped capture reads 90%+ blank from its corner sample, so `overlay_suspect` is `null` there | FAIL after you read it |
| `text-not-found:<t>` | OCR did not find the token | FAIL only after the `ocr_text` check above |

A high `blank_percent` alone never fails a shot. A tight dialog or Inspect crop is mostly its own background by design.

## L3. Read every shot

Open each PNG yourself. Cap the long edge at 1280 in a sidecar copy when larger (`vendor-vision-image-preview`); never resize the original. Confirm:

- **Element:** the plan's target is in the frame, at a zoom where the labels are legible. A strip in one corner of an empty canvas is a wrong-zoom fail.
- **Page:** URL, locale, environment and content match the step. Compare with the plan's URL and testing base URL.
- **Not a login or error page.** A step that landed on a login page, a 403/404, or a consent banner covering the subject means the auth state expired: failed step, not evidence.
- **Nothing sensitive in frame:** tokens, passwords, personal data or customer emails visible in a shot that may reach a tracker. Blocker for a tracker-bound shot.
- **Stacked shots** carry a banner, a black bar and a label per part. A silent stitch looks like empty space.

## L4. Product concept

Restate the plan's **Product concept** and **Expected paint**. For every live or integration shot the paint (fields, player, widget, iframe content) must be in the pixels. A heading over an empty slot is a concept fail even when OCR and whitespace pass. Do not accept "backend only" or "empty is expected" unless the plan records an operator exclusion made in that session. Do not diagnose or fix here: name the missing paint and send it to `run-plan` with the console/CSP/fixture checklist from `How-to-gate-evidence-on-the-product-concept.md`.

## L5. Environment and content hygiene

- Evidence is captured on review or local, never production. A production host in a URL or visible in a shot is a defect.
- URLs name the page under test, not the environment root. A Content Studio shot names the edit URL.
- Persistent evidence content has the component's display name. A visible ticket key, `DELETE-ME`, or throwaway page name is a finding (override 4).
- Non-PNG artifacts the plan names (`.html`, `.json`) exist and are not empty.

## L6. Scope exclusions

Read the implementation plan's **Constraints** and **Non-Goals** (`agentctl markdown slice`). If a shot shows an excluded element changed beyond the allowed delta, that is a delivery defect, not an evidence defect: report it as a Blocker and route it to `validate-impl`. Never mark the AC covered by a shot that proves a forbidden change.

## L7. Honest negatives

An AC the run could not evidence must be stated as not covered, in the plan's cut list or the comment. A pass claimed for a step the progress file records as `blocked` or `pending` is a FAIL.
