---
id: how-to-gate-evidence-on-the-product-concept
when_skills: [plan-task-evidence, run-plan]
inputs: [evidence plan or live page under test]
outputs: [named concept, expected paint, pass or diagnose-and-stop]
stop_if: [live/integration step marked pass while expected paint is absent]
read: whole
prose: caveman-lite
---

# How to gate evidence on the product concept

**Scope:** `_shared`
**Applies to:** every evidence **plan** and every evidence **execute**
**Related:** [How to check evidence screenshots before Jira](./How-to-check-evidence-screenshots-before-jira.md)

Whitespace, OCR of a heading, and a script-count overlay can all pass while the thing
the ticket is *for* never appears. That is not a pass.

Worked failure (PROJ-427 / PROJ-429, 2026-09-04): HubSpot integration. The plan
called an empty dummy slot a backend pass. Screenshots showed headings and
`hubspot-init.js` counts. No form fields. CSP blocked `js.hsforms.net`. The run
posted anyway. The operator rejected it.

## Infer the concept

One sentence a visitor or editor would use. Not the AC number.

| Ticket / page is about | Concept | Expected paint (examples) |
|------------------------|---------|---------------------------|
| HubSpot / form embed / signup widget | A working third-party form | Inputs + submit (or HubSpot iframe with those) |
| Video | A player | iframe/poster+play, not an empty box |
| Newsletter / SuperOffice | A subscribe control | Input+button or the SuperOffice iframe |
| Part / macro schema only (Inspect shot) | Editor can configure it | The named fields in Inspect / Insert dialog |

A **backend-only** ticket does **not** waive this on a live page that hosts the
integration. Script tags and `containerId` can still meet their own ACs. A live
shot of an empty slot is a **concept fail** until paint is proven or the
**operator in this session** excludes paint.

## Procedure

### Plan

Write a **Product concept** block in `evidence.md` (see the evidence template):

- Concept (one sentence)
- Expected paint (fields / iframe / player — not “heading visible”)
- Diagnose path if missing

Live-step **Expected result** must name the paint (e.g. `First name`, `Submit`),
not only HTTP 200 or a script count.

### Execute (every live / integration step)

1. Restate the concept and the expected paint before the shot.
2. After navigate, wait for that paint (DOM: iframe + field labels, or the
   native inputs). Headings alone are not paint.
3. **Read the screenshot.** If the form/player/widget is not in the pixels, the
   step failed — even if OCR found the section title.
4. If paint is missing, **do not** mark the step pass. Diagnose, then **stop
   posting**:

   | Check | How |
   |-------|-----|
   | Console | `browser_console_messages` level `error`. Keep CSP / `Refused to load` / script throws. Ignore ambient GTM / doubleclick / LinkedIn unless they are the concept. |
   | Network | Failed or blocked requests to the embed host (`hsforms.net`, `superoffice.com`, `youtube`, …). |
   | Fixture | Dummy GUID vs a real form/portal id. Region host mismatch (`js-eu1` vs `js.hsforms.net` for `na1`). Same HubSpot form twice on one page (HubSpot will not paint the duplicate). |
   | Consent | Cookiebot / banner blocking third-party script. |

5. Propose the smallest fix (add the blocked host to site CSP, swap the dummy
   id, publish site config only). Report that to the operator in chat. Do not
   invent a pass story (“empty is expected”, “frontend ticket”) unless they
   already excluded paint **in this session**.

## Pitfalls

- `js-eu1.hsforms.net` in `script-src` does not allow `js.hsforms.net`.
- HubSpot v2 also needs `'unsafe-inline'` on `style-src-elem` or styled-components throws and the form dies.
- OCR of “Get in touch” / “HubSpot Form” is the heading, not the form.
- A plan line that says “empty container is a pass” is stale for an integration
  page. Follow this file; ask if it conflicts with an operator exclusion.
- Schema/Inspect ACs may still be met. Record them. Do **not** post an all-pass
  evidence comment while the concept gate failed.

## Sample data

| Field | Example (HubSpot NA1) |
|-------|------------------------|
| Concept | Visitor sees a HubSpot form on the evidence page |
| Expected paint | Part: Name / Email / Message / Submit. Macro: First name / Download Now |
| First CSP host | `https://js.hsforms.net` in `script-src` |
