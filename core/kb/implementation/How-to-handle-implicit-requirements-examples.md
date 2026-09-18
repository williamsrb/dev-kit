---
id: how-to-handle-implicit-requirements-examples
when_skills: [plan-implementation, validate-plan, run-plan, validate-impl]
inputs: [JOT-270 review comments 531070 and 531187]
outputs: [classification of review extras vs bugs]
stop_if: []
read: section
prose: caveman-lite
---

# JOT-270 — review extras called bugs

Worked sample for `How-to-handle-implicit-requirements.md`. Kaio Simonassi [531070](https://example.atlassian.net/browse/JOT-270?focusedCommentId=531070) (2026-09-14): "Three items to fix, moving back to To Do." Williams Ramos [531187](https://example.atlassian.net/browse/JOT-270?focusedCommentId=531187) (2026-09-14): extras, not defects against the original ACs.

Original AC5: "Office and subsidiary data is sourced from CMS content **where practical**." Offices already came from Content Studio. Ticket preferred existing office content; it did not add an office field.

| Review claim | Asked extra | Bucket | Why it is not a bug |
|--------------|-------------|--------|---------------------|
| 1. Silent `larvik` match | `is_headquarters` checkbox + `log.warning` on fallback | **Tick** (schema/field the ticket did not add) | Head office on review was Larvik as specified. New field is an editor contract plus a re-save of every office. |
| 2. "AC5 is only half met" | Repeating `TextLine` in `site.xml` for subsidiaries | **Tick** (CMS editor contract) | AC5 is "where practical". No subsidiary field existed. The seven names were the template default; which entities belong is TBD with the business (AC6). |
| 3. Shared `toJsonLd` + `<!--` | Extract helper; also change JOT-269 Article output | **Tick** / follow-up ticket | No Organization AC depends on it. Cross-ticket serialiser change. Record already rendered and validated. |
| Minor. Missing logo file | Skip URL when `myImageUrl` is false | **Tick** (edge state) | Needs a deleted asset. Review logo was a live Jotron file. |

AC6 (current social URLs / complete subsidiary list) stayed TBD with the business. Kaio already marked that as not a defect.

First delivery: not a FAIL, not Blockers. Techlead then decided the extras come next — that is a **review-time tick**, a follow-up increment, not a rewrite of the original AC set.
