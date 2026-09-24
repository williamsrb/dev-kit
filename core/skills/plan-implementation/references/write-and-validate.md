# Write and validate

## Step 5 — Generate the Markdown

Use the template below. Fill in all fields from the **offline copy** (and classification / prototype checks / TBD harvest above).
The output file must always be written in English, regardless of the language used in the PRD or by the user. `<ISSUE-KEY>` in the template is the `<TASK-ID>` (Jira key or kebab slug).
**TBD is required** in every plan (jira: checklist items or `- TBD: none`; local: `- TBD: none` plus **Local PO decisions** after auto-select). Do not omit the heading. **jira:** do not write guessed product decisions as ACs/FRs. **local:** auto-selected choices **are** ACs/FRs, marked `_(local PO: …)_`.
**Implicit requirements are required** in every plan (tick-list checkboxes or `- Implicit: none`). Classify with `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Do not write tick-list extras as ACs/FRs. **local:** auto-tick `[x]` extras that belong in this delivery.

```markdown
# <ISSUE-KEY>: <Task Title>

| Field    | Value              |
|----------|--------------------|
| Type     | <task category — see classification rules below>   |
| Assignee | <assignee>         |

---

## Overview

<2-3 sentences summarizing what this task is about, the problem it solves, and who it affects.>

---

## User Stories

### US-001: <Short title>
**Description:** As a <user type>, I want <action> so that <benefit>.

**Acceptance Criteria:**
- [ ] <Specific, verifiable criterion from the ticket — mark `_(from comments)_` if sourced from comments. Do not mark extras as `_(inferred)_`; those go to Implicit requirements or TBD.>
- [ ] ...

<Repeat US-00N blocks as needed. Each meaningful user-facing behavior should have its own story.>

---

## Functional Requirements

- **FR-1:** <Explicit system behavior or constraint>
- **FR-2:** <...>

> Derived from the description, acceptance criteria, and comments. Number them for easy reference in the implementation plan.

---

## Non-Goals

> What this task explicitly does NOT include. Helps prevent scope creep.

- <Out-of-scope item>
- <...>

When the user (or an elevated comment) says an element is out of scope except for a narrow change (e.g. “order only”), list **all** forbidden dimensions — not only copy/URL: **position/alignment, typography/styling, markup/classes**. See `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md`.

---

## Constraints (user exclusions)

> Optional but **required** when the user gave an exclusion. Highest priority over Figma-inferred ACs.

- <Element E: only <allowed delta C>; do not change position, typography, markup beyond that delta>

---

## TBD (ask analyst before implement)

> **jira:** Unanswered gaps for the analyst **before implementation**. Copy this checklist to Slack/Jira. Do not encode these as requirements. If this list is not `TBD: none`, do not start Implementation Steps until the analyst answers or the user says to **implement with these assumptions**. Phrase each item with `write-analyst-message` — one decision, product language, why it blocks, **2-3 options with the recommendation first**. See `~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md`.
>
> **local:** Product-owner record. Harvest, reason, auto-select the recommended option, encode into AC/FR/Constraint (`_(local PO: …)_`). After resolve this list is `- TBD: none` plus **Local PO decisions**. Do not ask. Do not hard-stop. Do not use `write-analyst-message`.
>
> Decided exclusions belong in Constraints / Non-Goals, not here.

<If no gaps, or local and all resolved:>

- TBD: none

<jira or local, when a gap passed the high-confidence test (classify-and-scope.md § 3f) — decided, not a coding stop:>

### High-confidence decisions

- **<decision>:** (a) <chosen>. Source: <ticket AC / chat / code path / How-to / doc>. Alternatives lose because <one line>.

<local, after auto-select — audit trail only; not a coding stop:>

### Local PO decisions

- **<decision>:** (a) <chosen>. <one-line reason from PRD / code / sister / How-to>

<jira, if gaps exist — one checklist item per gap; never leave this section missing:>

- [ ] **<question phrased as a decision the analyst can answer without opening the repo>**
  - Blocks: <why this blocks the page/feature they own — product language>
  - **(a) Recommended — <option>.** <one-line reason>
  - (b) <option>. <consequence>
  - (c) <option>. <consequence — omit if only two real choices exist>

<jira: name the default when silence decides it. When a gap needs no analyst decision (we can verify it ourselves), say so in the Blocks line instead of inflating their queue.>

---

## Implicit requirements (techlead tick)

> Extras the ticket did not state. Classify with `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Not TBD. Not ACs. DOs (stack wiring, recorded How-tos) go in Implementation Steps, not here.
>
> **jira:** Techlead ticks which ones this delivery should include. Unticked items stay out of scope.
> **local:** Planner is the techlead. `[x]` = in scope (auto-selected). `[ ]` = follow-up, out of scope. Do not wait. Do not post.

<If none:>

- Implicit: none

<If extras exist, one checkbox line per extra — never leave this section missing:>

- [ ] <extra behavior in one line — what it is, and why it is not in the AC>

---

## Already delivered (do not re-do)

<Required section. A re-run must be able to tell shipped work from open work without
re-reading the ticket. Empty is allowed on a first increment:>

- Nothing delivered yet. This is the first increment.

<On a rework / bounce / second increment, one ticked line per closed item, each
carrying its id (FR-n, AC-n, or Sn) so `agentctl plan progress` can read it:>

- [x] **FR-1** <what shipped, in one line> — `<SHA or release>`
- [x] **S3** <shipped step> — `<SHA>`

<Then, in one line each:>

**Open in this increment:** <only the ids that are executable work>.

**Regression guard — a re-check, not a re-proof:** <the cheap confirmation that the
closed items still hold. Accepted evidence stands; do not recapture it.>

Rules:

- Only ids on a `[x]` line count as closed. Prose is never inferred from.
- A closed item is not re-implemented, not refactored, and not re-evidenced.
- Do not tick an item because it looks done. Tick it because a named commit,
  release, or reviewer sign-off says so, and cite that.

---

## Implementation Plan

> This section is auto-generated. Review and adjust before using it as an implementation guide.

### Problem Understanding

<2-3 paragraphs analyzing what needs to be done, the problem context, and the expected impact.>

### Suggested Technical Approach

<Fill using the reference file loaded in Step 4b. Follow its "Suggested Technical Approach — content to generate" section exactly.>

<If a prototype component was found in Step 4d, add a "Prototype Component" sub-section:>

**Prototype Component**: `<prototype-component-path>`

The frontend component already exists as a prototype. The Enonic view must render this component — do not create a duplicate React component.

<If <prototype-props-interface> was found:>

**Props contract**: The prototype file exports `<prototype-props-interface>`. This interface is the authoritative source for the props the processor must return. Do NOT generate a separate `*Props` interface in the Enonic `.d.ts` file — use or re-export the prototype interface instead, and remove any auto-generated `*Props` interface if it already exists.

<End prototype section>

### Implementation Steps

<Fill using the reference file loaded in Step 4b. Follow its "Implementation Steps — content to generate" section. Reference FR numbers where applicable.>

**Every step carries a stable id.** Write each step as `- [ ] S<n> — <step>`, numbered
from S1 in document order. The id is the step's permanent name:

- Never renumber. Inserting a step between S2 and S3 gives S12 (next free number), not a
  reshuffle — a re-run matches recorded progress by id, and renumbering silently moves a
  tick onto a different step.
- Never reuse an id from a deleted step.
- A step already shipped is written `- [x] S<n> — …` and also listed under
  **Already delivered**.

Plans that predate this convention keep their bare numbered lists; `agentctl plan
progress` falls back to ordinal ids and flags them `unstable_ids`, which means an edit to
the steps invalidates recorded progress instead of mis-applying it. Prefer S-ids.

### Definition of Done

<Fill using the reference file loaded in Step 4b. Use its "Definition of Done checklist to include" section as the base, then add any criteria specific to this task's acceptance criteria.>

---

_Generated at: <current date and time in YYYY-MM-DD HH:MM format>_
_Source (jira): [<TASK-ID>](https://example.atlassian.net/browse/<TASK-ID>)_
_Source (local): local PRD_
_Offline copy: ~/.agents/prds/<TASK-ID>.md_

```

---

## Validate / fix-plan mode

Trigger: user asks to **validate the plan**, **fix the plan**, or Phase-1 multitask plan review.

Do **not** hand-roll a review here. Read and follow `../validate-plan/SKILL.md` as a nested prerequisite (`called_from: plan-implementation`). That skill validates **and** rewrites the resolved plan (`agentctl plan resolve <TASK-ID>` — folder companions or an evidence plan when that is the target).

After the nested run: surface TBD and implicit in chat (same Step 6 rules). **jira:** non-empty TBD is not a plan NO-GO; it **is** a hard-stop before coding. **local:** leftover gaps must be auto-selected (recommended path) before this skill finishes; do not hard-stop. Non-empty implicit is not a coding hard-stop; post (jira) or report auto-ticks (local) if the nested run added items that were not posted.

---

## Step 6 — Save and confirm

1. Write the final content to `<plans-dir>/<TASK-ID>/` (run `agentctl plan init --kind implementation --issue <TASK-ID> --output <plans-dir>/<TASK-ID>` if the folder does not exist). Split Overview/Non-Goals/Constraints into `plan.md`, User Stories/FR into `requirements.md`, TBD into `tbd.md`, Implicit requirements into `implicit.md`, Implementation Plan into `implementation.md`, Validation into `validation.md`. A legacy `<TASK-ID>.md` may still be updated in place when that is the resolved entry. Keep only the `_Source` line that matches `mode`.
2. **Implicit-requirements comment (mandatory after the files exist):**
   - If the list is empty: say **Implicit: none**. Do not post.
   - If `mode` is `local` and the list is non-empty: report the auto-ticks in chat (`[x]` in scope, `[ ]` follow-up). Do not post to Jira. Do not wait for ticks.
   - If `mode` is `jira` and the list is non-empty: run `python3 ~/.agents/skills/plan-implementation/scripts/post_implicit_requirements.py --issue <TASK-ID> --file <implicit.md-or-legacy-plan>`. That posts ADF checkboxes for the techlead (creates, or edits the stored `_Comment-id:` after backup). The body states they are extras, not bugs or blockers. Do not use MCP. Do not mix TBD into this comment. Report the comment id in chat. Failure to post does not fail the plan — paste the list in chat.
3. Report to the user:
   - The absolute path of the generated file (and which agent plans dir was used)
   - Path of the offline copy used (`~/.agents/prds/<TASK-ID>.md`)
   - A 1-2 line summary of what was found in the task
   - Whether the file was **created** or **updated**
   - Whether any comments influenced the acceptance criteria
4. **TBD in the chat summary (mandatory — not a footnote):**
   - If TBD is empty: say **TBD: none**.
   - If `mode` is `jira` and TBD is non-empty: paste the TBD checklist (analyst-ready). Tell the user to take it to the analyst **before implementation**.
   - If `mode` is `local`: paste **Local PO decisions** (what was auto-selected and why). Say **TBD: none**. Do not tell the user to take it to an analyst.
5. **Hard-stop before coding (`jira` only):** if TBD is non-empty, **do not start implementation**. Wait for analyst answers, or an explicit **implement with these assumptions**. Silence is not acceptance. **local:** the plan is execution-ready after auto-select; do not hard-stop for TBD or implicit. Unticked implicit extras are out of scope; they are not a coding hard-stop. This skill’s success is the written plan file plus the TBD summary plus the implicit post-or-report — not code.

---

## Quality Notes

- **Offline first**: Prefer `~/.agents/prds/<TASK-ID>.md`. Missing + `mode` jira → nested `download-jira-task`. Missing + `mode` local → nested `handoff` (PRD). Mark nested runs with `called_from: plan-implementation`.
- **Enonic offline docs**: For XP/React4XP work, route via Step 4c (`~/.agents/kb/offline-reference/…/llm-index.md` for XP7, XP8, React4XP v5, React4XP v6) before inventing API/framework details.
- **Language**: The generated Markdown file must always be in English, even if the PRD or user messages are in another language. Translate descriptions, comments, and criteria as needed.
- **Comments drive criteria**: Comments are the most recent source of truth for requirements when they clearly extend or supersede. Do not surface raw comments in the output — absorb their intent into the criteria. Comment conflicts with no clear winner: **jira** → **TBD**; **local** → auto-select the recommended/later winner and record it as a Local PO decision.
- **Inferred extras**: Do not write `_(inferred)_` ACs for behaviors the ticket did not state. Classify with `How-to-handle-implicit-requirements.md`: DO → Implementation Steps; Tick → implicit checkbox; DON'T → Non-Goals; product gap → TBD (jira: ask; local: auto-select).
- **High-confidence auto-select**: A gap whose recommended option passes the four tests in `classify-and-scope.md` § 3f is decided in both modes. Encode it `_(high confidence: <source>)_`, record it under **High-confidence decisions**, and never ask it. Only gaps that fail a test become TBD questions.
- **TBD**: Every plan has `## TBD (ask analyst before implement)` after Constraints / Non-Goals and before Implicit requirements. **jira:** checklist items (question + Blocks + 2-3 options, recommendation first) or `- TBD: none`. Surface the list in chat. Non-empty TBD → hard-stop before coding unless the user explicitly accepts the recommended options. Draft TBD copy with `write-analyst-message`. **local:** auto-select the recommended path, encode as AC/FR/Constraint, `- TBD: none` plus **Local PO decisions**. Do not ask. Do not hard-stop. Do not use `write-analyst-message`.
- **Already delivered**: Every implementation plan has `## Already delivered`, required by
  `agentctl plan validate`. First increment: the one-line "nothing delivered yet". Rework:
  ticked ids with their SHA, an **Open in this increment** line, and a regression guard.
  This is what stops a re-run rebuilding shipped work — it is scope, decided at plan time,
  not run state. Run state is `progress.md` (`evidence.progress.md` for the evidence
  kind), owned by `run-plan`.
- **Step ids**: Implementation Steps use `S<n>` ids, never renumbered, never reused.
- **Implicit requirements**: Every plan has `## Implicit requirements (techlead tick)` after TBD and before Implementation Plan. Checkboxes or `- Implicit: none`. **jira:** post immediately after writing the plan; unticked extras stay out of scope. **local:** auto-tick extras that belong; report `[x]`/`[ ]` in chat; do not wait. Do not mix with TBD. Do not use `write-analyst-message` for this comment.
- **User stories**: Break the task into small, specific stories. Each should represent one user-facing behavior. Avoid mega-stories that bundle multiple unrelated behaviors.
- **Functional requirements**: Extract explicit system behaviors from the description and criteria. Number them (FR-1, FR-2, ...) so implementation steps can reference them precisely. **jira:** do not promote TBD assumptions into FRs. **local:** auto-selected Local PO choices **are** FRs, marked `_(local PO: …)_`.
- **Non-goals**: Always include at least one non-goal to clarify scope boundaries. Infer from context if not stated. When the user limits an element to a single delta (e.g. order only), Non-Goals + **Constraints** must forbid position, styling, and markup beyond that delta — see `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md`.
- **Environment boundary**: Review (or local) only. No AC, step, Validation line or Definition of Done item depends on production. Restate production-URL ACs on the review scenario and move the production wording to Non-Goals. Bugs run Scenario → Reproduce → Fix → Test after fix on review. See SKILL.md § Environment boundary.
- **User exclusions win**: Explicit user/chat exclusions outrank Figma composition and inferred ACs. Mark `_(user said)_` vs `_(inferred from Figma)_`. Never encode an inferred layout that violates an exclusion. Exclusions are **not** TBD.
- **Implementation plan**: Be concrete and technical. Avoid vague statements like "implement the feature". Analyze the task context to suggest specific files, functions, or application layers likely to be affected.
- **Idempotency**: Running the skill twice on the same task should produce an equivalent file — do not duplicate sections or erase manual edits the user has made to the Implementation Plan.
- **Prototype component**: If a prototype file was found in Step 4d, the spec must instruct the implementer to use that file as the rendered component, not create a new one. The prototype file is the source of truth for the frontend implementation.
- **Prototype props interface**: If the prototype file exports a props interface, that interface is authoritative. The spec must explicitly state that any auto-generated `*Props` interface in the Enonic `.d.ts` should be removed or not created, and the prototype interface should be used (or re-exported) instead.
- **Impeccable (optional)**: Only for design/frontend UI tasks (Step 4e). Never required for general planning.
- **Auxiliary skills (optional)**: Use `find-skills` only for real capability gaps (not routine planning). Never invent session-only tooling when a quality skill exists.
