# How to calibrate classify-ticket-autonomy

Re-calibrate after any change to the criteria, the hard stops, or `references/signals.json` in `~/.agents/skills/classify-ticket-autonomy/`. The skill itself carries no ticket keys. The precedent corpus and the keyed run log stay on the host.

## Files

- Host-local `Calibration-runs-of-classify-ticket-autonomy.md`: keyed run log plus the opaque-id table. Read it first; the open issues are the next things to encode.
- Shipped `Calibration-runs-of-classify-ticket-autonomy-anonymized.md`: same runs with ids `R<run>-<nn>` and no Jira keys.
- Host-local `Corpus-precedents-for-classify-ticket-autonomy.md`: the real tickets behind the skill's generic examples.

## Procedure

1. Pick 20 held-out tickets at In Review or later, from several projects. None may appear in either file above or in an earlier run. Include some with payment, email, identity, or delete signals so the hard stops are exercised.
2. Build blind copies: title, description, ACs, and the comments posted before the assignee's first comment. Drop status and bot comments.
3. Classify each blind copy with the skill. Every verdict must pass `autonomy.py check`.
4. Have two independent agents label the truth from the full history: OBSERVED (a human acted before review; rework after review does not count) and POLICY (a hard stop applies, or the work is not reproducible on the agent's environments). Truth is Human-in-the-loop when either label is.
5. Score agreement, Human-in-the-loop recall and precision. Sort each disagreement into accepted by policy, export artifact, or real miss.
6. Fix real misses in the skill using generic wording only. Put any ticket key you want to keep as a precedent into `Corpus-precedents-for-classify-ticket-autonomy.md`, never into the skill.
7. Append the run to host-local `Calibration-runs-of-classify-ticket-autonomy.md` as `## Run <n>`, mark fixes as not re-validated, assign `R<n>-nn` in the opaque-id table, and refresh the anonymized sibling (no Jira keys, no project prefixes).

## Known limits

- Jira exports keep only the latest description, so a ticket clarified mid-flight looks clear in hindsight. Historic runs under-measure `clear-spec`.
- Classifiers that have seen a precedent can reuse it on a sibling ticket. Keep sibling tickets of a listed precedent out of the held-out set.
