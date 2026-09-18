---
id: how-to-write-analyst-questions-with-options
when_skills: [write-analyst-message, jira-task-spec, plan-implementation]
inputs: [open questions or TBD items for an analyst/reporter]
outputs: [Jira/Slack comment a person can answer by picking an option]
stop_if: [audience is the implementer or the user, not the analyst; the body is an evidence comment / E2 post; the body is an implicit-requirements techlead tick list]
read: whole
prose: caveman-lite
---

# Write analyst questions with options

The analyst decides. Give them choices, not a form.

**Not for evidence posts.** An evidence comment is the wrong time to ask anything — the analyst is checking the delivery. Do not follow this How-To when drafting E2. State shipped limitations as facts, or post a **separate** question comment after evidence.

**Not for implicit-requirements posts.** Those are techlead ADF checkboxes after `plan-implementation`. See `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Do not use a/b/c options there.

## Procedure

1. Open by name. Never thank, praise, or assess their work — no "thanks for reporting", no "the right call".
2. Outcome and recommendation before caveats.
3. Every question gets **2-3 options**, recommended first and marked, each with a one-line reason.
4. Keep the "why this blocks" line above the options.
5. Name the default when silence decides it: "without an answer we get (a)".
6. Say when a question needs no decision from them. Close with the smallest unblocking action.
7. Mirror the options into the plan's TBD so plan and ticket agree.

## Option shape

```markdown
### 1. <question phrased as a decision, plain language>

<what is at stake, why it blocks>

- **a) <recommended option>.** My recommendation. <reason>
- b) <option>. <consequence>
- c) <option>. <consequence>
```

## Pitfalls

- A bare `Assumption (not decided): …` is not an answer path. Options replace it; older plans still carry it, do not copy that shape forward.
- Do not paste this shape into an evidence comment. Evidence + TBD in one post is always wrong timing.
- Do not use this shape for implicit-requirements posts. Those are techlead ADF checkboxes, not analyst a/b/c.
- No filler options. Two real choices beat three with a decoy.
- Never bury or unmark the recommendation.
- Respect is doing their thinking, not adjectives — and never a compliment on their judgment.
- No backticks inside a bold run in Jira: the markdown-to-ADF conversion closes the bold at the code span and the heading renders half-bold. Verify the posted body.
