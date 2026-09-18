---
name: write-analyst-message
description: "Draft analyst-facing comments, TBD questions, and Slack messages. Product language, not engineer logistics. Jira is one sink, not a requirement. | recommendedRole: implement | aliases: professional-communication, analyst-facing-message, draft-analyst-comment."
metadata:
  recommendedRole: implement
  aliases: professional-communication, analyst-facing-message, draft-analyst-comment
---
# Write analyst message

**Audience is the analyst/reporter**, not the implementer. They validate the
change against requirements and Figma. They do not need how it was built.

Keep this skill’s output in **normal professional prose** (token-efficiency carve-out).

Parent skills call this when drafting client-facing text:

| Parent | When to load this skill |
|--------|-------------------------|
| `plan-task-evidence` / `run-plan` on an evidence plan | E2 evidence comment body (Jira when `mode` is `jira`; otherwise paste/chat) |
| `plan-implementation` | TBD checklist the user will copy to the analyst |
| `plan-implementation` implicit-requirements comment | **Do not use this skill.** Techlead tick list, ADF checkboxes, not a/b/c options. See `How-to-handle-implicit-requirements.md`. |
| Any analyst-facing text (Jira, Slack, or paste) | Before posting or handing the copy over |

Do **not** use this skill for chat-to-user orchestration, commit messages,
KB How-Tos, or engineer-only reports.

## Core principle

Effective communication is not proving how much you know. It is making sure
the analyst receives the point and can decide.

## What-Why-How

Organize every analyst message with this frame:

| Component | Purpose | Evidence-post example |
|-----------|---------|------------------------|
| **What** | Outcome in product language | "The contact form on the live page now matches the approved design and sends mail to the configured recipient." |
| **Why** | Which requirement / AC this satisfies | "This covers the form, validation, and mail-delivery criteria." |
| **How** | Where they look — not how we coded it | Review URL + "in the screenshot, expand the form and check the Sent state." |

**How** means *how the analyst verifies*, never *how the code works*.

## Three golden rules

1. **Purpose in the first line** — mention + task id + what this comment is (evidence, question, limitation).
2. **Scannable** — headings, numbered evidence units, short paragraphs. No walls of text.
3. **Key message first** — outcome and AC status before setup, caveats, or optional details.

## Audience calibration

Before writing, answer:

1. **Who** — analyst/reporter (CMS, Figma, ACs). Not a developer.
2. **What detail they need** — what changed on the page or in Content Studio; what to look at in each image; whether each AC is met.
3. **Value for them** — can they accept the ticket, or do they still owe a decision?

| OK in the analyst body | Never in the analyst body |
|---------------------------|------------------------------|
| Review/live URL | Localhost, `~/.agents`, evidence-folder paths |
| Content Studio field names the editor uses | Processor, React, CSS class, breakpoint (`lg+`), HTTP status |
| "Look at the heading and the three cards" | Upload how-tos, mogrify, Playwright, storage-state, `fileId` |
| AC mapping ("AC3 — form starts collapsed") | Git SHAs, grep, Docker, `sendFormEmail`, internal service names |
| Known product limitation + how to reproduce on review | "Please attach from …", agent/auth setup, KB/plan paths |

Chat report-back to the user **does** include logistics. The analyst body does not.

## Writing rules

- **Active voice:** "The live page shows three cards" not "Three cards were rendered."
- **No filler:** "now" not "at this point in time"; "because" not "due to the fact that."
- **"So what?" test:** if a sentence does not help the analyst accept or reject the change, cut it or move it to chat.
- **Keep domain words they already use** (acceptance criteria, Content Studio, publish, Figma, review environment). Translate the rest — see [jargon.md](references/jargon.md).
- **One evidence unit = meaning + image.** The sentence above the screenshot says what to look for and which AC it proves. Never an orphan image or a gallery dump.
- **Changes summary** is the product outcome in 1–3 sentences. Not a changelog of files, libraries, or CSS.
- **TBD questions** are a **separate** comment (or Slack), never mixed into an evidence post. One decision each, in product language, with why it blocks and **2-3 options, recommended first and marked as the recommendation**. The analyst must be able to answer by picking a letter, without opening the repo. A bare "Assumption (not decided)" line is not an answer path — see `~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md`.
- **Implicit-requirements comments** are a **separate** techlead checkbox post after `plan-implementation`. Do not draft them with this skill. Do not mix them into TBD or evidence.
- **Respect, not praise.** Address the analyst by name and say why each finding matters to them. Respect comes from doing their thinking for them — precise answers, options, clear evidence — never from adjectives.
- **Never thank, praise, or grade the analyst.** No "thanks for reporting", no "good catch", no "that was the right call", no verdict on their judgment or their reasoning. They are doing their job; commenting on how well they did it is condescending and reads as filler. State what was found, what changed, and what the evidence shows.

## Checklist (before post / paste)

- [ ] First line states purpose (evidence / question / limitation)
- [ ] Outcome and AC status appear before caveats
- [ ] Headings + numbered units; no wall of text
- [ ] Each screenshot has a "look here / this proves AC…" line
- [ ] Review links are the captured live page (full path) plus Admin CS edit when CMS was in the run — not the env root
- [ ] Jargon check against [jargon.md](references/jargon.md)
- [ ] Action clear: accept, retest this URL, or (question comments only) answer this question
- [ ] Evidence comments contain **no questions** and no a/b/c option lists — that timing is wrong; TBD is a separate comment
- [ ] Question comments only: every question carries 2-3 options, recommendation first and marked
- [ ] Question comments only: default named where silence decides it ("without an answer we get (a)")
- [ ] Opens by name; no thanks, praise, or assessment of the analyst's work
- [ ] No backticks inside bold runs (Jira ADF breaks the bold — skip this check when the sink is not Jira)
- [ ] Tone professional, not cold, not engineer-telegram

## Evidence comment shape

Keep the existing ADF/markdown **sections** from `plan-task-evidence/templates.md`.
This skill only governs the **prose inside** them:

1. Mention + "evidence for `<TASK-ID>`."
2. **Changes summary** — What + Why (product language).
3. **Deployed testing environment** — the live page URL that was captured (full path), plus Admin (Content Studio edit URL) when CS shots are in the comment. Never the review host with no path.
4. **Evidence** — numbered How units (explanation, then image).
5. **Acceptance criteria** — met / not, mapped to evidence numbers.
6. **Additional relevant details** (optional) — product limitations as facts, how to reproduce on the deployed URL, fallback UX. **No questions.** If a decision is still open, say so in chat and post a separate TBD comment; do not append a/b/c options here.

Posting gates, upload/ADF mechanics, and all-pass-only remain in `plan-task-evidence` and apply when `mode` is `jira`. This skill does not change those. When `mode` is `local`, produce the same prose for chat/paste; do not require a Jira comment shape.

## Additional resources

- Before/after copy: [examples.md](references/examples.md)
- Term translations: [jargon.md](references/jargon.md)
- Question options and warmth: `~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md`
