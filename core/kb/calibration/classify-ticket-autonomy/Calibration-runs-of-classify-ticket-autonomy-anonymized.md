# Calibration runs (anonymized)

Opaque ids `R<run>-<nn>`. The host file with Jira keys is not in this kit. Do not reverse-map these ids in shipped docs.

## Run 1 — 2026-09-23, 20 held-out tickets

**Method.** Tickets at In Review or later, from 9 projects, none cited in `SKILL.md`. Four agents classified **blind** copies (title, description, ACs; comments and status removed). Two independent agents labelled the real outcome from the full comment history: did a human have to act **before** review? Rework after review did not count.

**Result.** 14/20 agree. Human-in-the-loop recall 6/8, precision 6/10.

| Id | Truth | Verdict | Blockers | Note |
|-----|-------|---------|----------|------|
| R1-01 | A | A | | |
| R1-02 | H | H | review-reproducible | truth: fix and effort needed business sign-off |
| R1-03 | A | **H** | review-reproducible | blinding artifact: the reporter posted the production log analysis 4 min after creating the ticket |
| R1-04 | A | A | | |
| R1-05 | H | H | owner-decision | |
| R1-06 | A | **H** | other-owner, review-reproducible | Windows-only app. A human dev delivered it; the agent's machines cannot. Correct under the "environments we have access to" rule. The mock-first clause was missed (fixed) |
| R1-07 | A | **H** | other-owner, external-access, review-reproducible | as R1-06, plus a code-signing certificate |
| R1-08 | A | A | | |
| R1-09 | H | H | other-owner | |
| R1-10 | A | A | | |
| R1-11 | H | **A** | | missed: an AC is only verifiable on review once the paired backend ticket lands (fixed) |
| R1-12 | A | A | | |
| R1-13 | H | H | clear-spec, owner-decision, external-access | |
| R1-14 | H | H | external-access | vendor search-admin |
| R1-15 | A | A | | soft "best done after" ordering, correctly a pipeline precondition |
| R1-16 | H | H | other-owner | |
| R1-17 | A | **H** | external-access | credential rotation by hosting was a follow-up; the code fix was verifiable on review (fixed) |
| R1-18 | A | A | | |
| R1-19 | A | A | | |
| R1-20 | H | **A** | | missed: the auto-selected Reply-To contradicted the title's "as the sender", and the estimate request lived in comments the blind copy withheld (fixed: literal-wording rule) |

**Reading.** Of the 6 disagreements, two are accepted: R1-06 and R1-07 are correctly Human-in-the-loop for an agent pipeline. Two are blinding artifacts (R1-03, and part of R1-20): in real use the classifier sees comments that existed before work started. That leaves three real misses (R1-11, R1-20, R1-17), all addressed in `SKILL.md` on the same day. Those fixes are **not** re-validated. Re-run on a fresh held-out set before trusting them.

**Added after this run, not calibrated:** hard stops `real-money-or-identity`, `real-inbox` and `irreversible-operation` (2026-09-23). The 20 verdicts above use the older 9-criterion schema and no longer pass `autonomy.py check`.

**Open issues** (not yet encoded):

- Figma is often referenced only by URL, and `read-figma` needs a local `.fig`. Is a URL-only design `external-access`?
- Tickets whose spec lives in an attachment that was not downloaded.
- Pricing tickets: an unstated edge-case fallback fails test 4 (owner's call) even when the core rule is fully specified (R1-05).
- Blind calibration strips all comments. A fairer blind copy keeps comments posted before the first assignee comment.

## Run 2 — 2026-09-23, 20 fresh held-out tickets, 12 criteria

**Method.** As run 1, with three changes. None of the tickets overlaps run 1 or is cited in `SKILL.md`. The blind copy keeps comments posted before the assignee's first comment. Six tickets were picked for payment, email or delete signals, to exercise the hard stops. Labellers gave an OBSERVED label (a human acted before review) and a POLICY label (the hard stops, plus not reproducible on the agent's Linux/Docker/review environments). FINAL is HITL when either one is HITL. R2-20 is a port of R2-15, so those two are correlated.

**Result.** 14/20 agree. Human-in-the-loop recall 7/10, precision 7/10. Hard stops: all three policy-only tickets were caught (R2-06 and R2-03 payment and inbox, R2-18 national ID), plus R2-01.

| Id | Truth | Verdict | Blockers | Note |
|-----|-------|---------|----------|------|
| R2-01 | H | H | review-reproducible, real-money-or-identity | |
| R2-02 | A | **H** | owner-decision | borderline: the tech lead's QA list asked keep-or-drop; the developer settled it himself |
| R2-03 | H | H | real-money-or-identity, real-inbox | policy-only |
| R2-04 | A | A | | |
| R2-05 | H | H | review-reproducible | |
| R2-06 | H | H | real-money-or-identity | policy-only |
| R2-07 | H | **A** | | artifact: the tech lead's pre-work comment already supplied the decision and branch, so at classification time the input exists |
| R2-08 | A | A | | |
| R2-09 | H | H | owner-decision | "resolve before build" |
| R2-10 | A | **H** | owner-decision | correct by project policy: the AC contradicts the `AGENTS.md` link rule, which says to ask. The labeller did not know the rule |
| R2-11 | A | **H** | external-access | correct for an agent: new repo, CI and K8s env need hosting rights. A human developer had them |
| R2-12 | A | A | | |
| R2-13 | A | A | | |
| R2-14 | A | A | | |
| R2-15 | H | H | external-access | vendor whitelist |
| R2-16 | H | **A** | | artifact: the export holds the **rewritten** description, so the original ambiguity and the estimate approval are invisible |
| R2-17 | H | **A** | | real miss: the ticket offered "ideal vs minimum" and the owner picked the option the developer did not recommend (fixed: preference-ladder rule) |
| R2-18 | H | H | external-access, review-reproducible, real-money-or-identity | policy-only |
| R2-19 | A | A | | |
| R2-20 | A | A | | |

**Reading.** Raw agreement matches run 1 (14/20), but the misses changed kind. Two disagreements are correct by policy (R2-10, R2-11) and two are export artifacts (R2-07, R2-16). That leaves one real miss (R2-17) and one borderline over-block (R2-02). Treating the policy cases as correct gives 16/20.

**Fixes after run 2** (not re-validated):

- Delegated choices go to `auto_resolved`; listed-but-unpicked options are an `owner-decision`.
- A ticket that contradicts an ask-first project rule is an `owner-decision`.
- A deliverable that is infrastructure is `external-access` (hosting).
- Record every criterion one cause fails.
- `real-money-or-identity` is scoped to changes or reproduction paths through payment or identity.
- `real-inbox` blocks when review mail routing is unknown and a real recipient is in the flow.

**Calibration limits** found this run:

- Jira exports keep only the latest description, so a ticket clarified mid-flight looks clear in hindsight. Historic calibration under-measures `clear-spec`; live use does not have this problem.
- Some bot comments (commit-link mentions) slipped into blind copies. The scan skips them, but readers see the fix.
- Classifiers knew a cited eID example in `SKILL.md` and reused it on a sibling ticket (R2-18).
