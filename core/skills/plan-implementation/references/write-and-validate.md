# Write and validate

## Step 5 — Generate the Markdown

Use the template below. Fill in all fields from the **offline copy** (and classification / prototype checks / TBD harvest above).
The output file must always be written in English, regardless of the language used in the PRD or by the user. `<ISSUE-KEY>` in the template is the `<TASK-ID>` (Jira key or kebab slug).
**TBD is required** in every plan (either checklist items or `- TBD: none`). Do not omit the heading. Do not write guessed product decisions as ACs/FRs.
**Implicit requirements are required** in every plan (tick-list checkboxes or `- Implicit: none`). Classify with `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Do not write tick-list extras as ACs/FRs.

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

> Unanswered gaps for the analyst **before implementation**. Copy this checklist to Slack/Jira. Do not encode these as requirements. If this list is not `TBD: none`, do not start Implementation Steps until the analyst answers or the user says to **implement with these assumptions**. Decided exclusions belong in Constraints / Non-Goals, not here. Phrase each item with `write-analyst-message` — one decision, product language, why it blocks, **2-3 options with the recommendation first**. See `~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md`.

<If no gaps:>

- TBD: none

<If gaps exist, one checklist item per gap — never leave this section missing:>

- [ ] **<question phrased as a decision the analyst can answer without opening the repo>**
  - Blocks: <why this blocks the page/feature they own — product language>
  - **(a) Recommended — <option>.** <one-line reason>
  - (b) <option>. <consequence>
  - (c) <option>. <consequence — omit if only two real choices exist>

<Name the default when silence decides it. When a gap needs no analyst decision (we can verify it ourselves), say so in the Blocks line instead of inflating their queue.>

---

## Implicit requirements (techlead tick)

> Extras the ticket did not state. Techlead ticks which ones this delivery should include. Unticked items stay out of scope. Classify with `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md`. Not TBD. Not ACs. DOs (stack wiring, recorded How-tos) go in Implementation Steps, not here.

<If none:>

- Implicit: none

<If extras exist, one checkbox line per extra — never leave this section missing:>

- [ ] <extra behavior in one line — what it is, and why it is not in the AC>

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

After the nested run: surface TBD and implicit in chat (same TBD hard-stop as Step 6). Non-empty TBD is not a plan NO-GO; it **is** a hard-stop before coding. Non-empty implicit is not a coding hard-stop; post or paste it if the nested run added items that were not posted.

---

## Step 6 — Save and confirm

1. Write the final content to `<plans-dir>/<TASK-ID>/` (run `agentctl plan init --kind implementation --issue <TASK-ID> --output <plans-dir>/<TASK-ID>` if the folder does not exist). Split Overview/Non-Goals/Constraints into `plan.md`, User Stories/FR into `requirements.md`, TBD into `tbd.md`, Implicit requirements into `implicit.md`, Implementation Plan into `implementation.md`, Validation into `validation.md`. A legacy `<TASK-ID>.md` may still be updated in place when that is the resolved entry. Keep only the `_Source` line that matches `mode`.
2. **Implicit-requirements comment (mandatory after the files exist):**
   - If the list is empty: say **Implicit: none**. Do not post.
   - If `mode` is `local` and the list is non-empty: paste the checkbox list in chat. Do not post to Jira.
   - If `mode` is `jira` and the list is non-empty: run `python3 ~/.agents/skills/plan-implementation/scripts/post_implicit_requirements.py --issue <TASK-ID> --file <implicit.md-or-legacy-plan>`. That posts ADF checkboxes for the techlead (creates, or edits the stored `_Comment-id:` after backup). The body states they are extras, not bugs or blockers. Do not use MCP. Do not mix TBD into this comment. Report the comment id in chat. Failure to post does not fail the plan — paste the list in chat.
3. Report to the user:
   - The absolute path of the generated file (and which agent plans dir was used)
   - Path of the offline copy used (`~/.agents/prds/<TASK-ID>.md`)
   - A 1-2 line summary of what was found in the task
   - Whether the file was **created** or **updated**
   - Whether any comments influenced the acceptance criteria
4. **TBD in the chat summary (mandatory — not a footnote):**
   - If TBD is empty: say **TBD: none**.
   - If TBD is non-empty: paste the TBD checklist (analyst-ready). Tell the user to take it to the analyst **before implementation**.
5. **Hard-stop before coding:** if TBD is non-empty, **do not start implementation**. Wait for analyst answers, or an explicit **implement with these assumptions**. Silence is not acceptance. Unticked implicit extras are out of scope; they are not a coding hard-stop. This skill’s success is the written plan file plus the TBD summary plus the implicit post-or-paste — not code.

---

## Quality Notes

- **Offline first**: Prefer `~/.agents/prds/<TASK-ID>.md`. Missing + `mode` jira → nested `download-jira-task`. Missing + `mode` local → nested `handoff` (PRD). Mark nested runs with `called_from: plan-implementation`.
- **Enonic offline docs**: For XP/React4XP work, route via Step 4c (`~/.agents/kb/offline-reference/…/llm-index.md` for XP7, XP8, React4XP v5, React4XP v6) before inventing API/framework details.
- **Language**: The generated Markdown file must always be in English, even if the PRD or user messages are in another language. Translate descriptions, comments, and criteria as needed.
- **Comments drive criteria**: Comments are the most recent source of truth for requirements when they clearly extend or supersede. Do not surface raw comments in the output — absorb their intent into the criteria. Comment conflicts with no clear winner go to **TBD**, not a silent pick.
- **Inferred extras**: Do not write `_(inferred)_` ACs for behaviors the ticket did not state. Classify with `How-to-handle-implicit-requirements.md`: DO → Implementation Steps; Tick → implicit checkbox; DON'T → Non-Goals; product gap → TBD.
- **TBD**: Every plan has `## TBD (ask analyst before implement)` after Constraints / Non-Goals and before Implicit requirements. Checklist items (question + Blocks + 2-3 options, recommendation first) or `- TBD: none`. Surface the list in chat. Non-empty TBD → hard-stop before coding unless the user explicitly accepts the recommended options. Draft TBD copy with `write-analyst-message` so the analyst can answer by picking a letter, without implementation context.
- **Implicit requirements**: Every plan has `## Implicit requirements (techlead tick)` after TBD and before Implementation Plan. Checkboxes or `- Implicit: none`. Post (jira) or paste (local) immediately after writing the plan. Unticked extras stay out of scope. Do not mix with TBD. Do not use `write-analyst-message` for this comment.
- **User stories**: Break the task into small, specific stories. Each should represent one user-facing behavior. Avoid mega-stories that bundle multiple unrelated behaviors.
- **Functional requirements**: Extract explicit system behaviors from the description and criteria. Number them (FR-1, FR-2, ...) so implementation steps can reference them precisely. Do not promote TBD assumptions into FRs.
- **Non-goals**: Always include at least one non-goal to clarify scope boundaries. Infer from context if not stated. When the user limits an element to a single delta (e.g. order only), Non-Goals + **Constraints** must forbid position, styling, and markup beyond that delta — see `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md`.
- **User exclusions win**: Explicit user/chat exclusions outrank Figma composition and inferred ACs. Mark `_(user said)_` vs `_(inferred from Figma)_`. Never encode an inferred layout that violates an exclusion. Exclusions are **not** TBD.
- **Implementation plan**: Be concrete and technical. Avoid vague statements like "implement the feature". Analyze the task context to suggest specific files, functions, or application layers likely to be affected.
- **Idempotency**: Running the skill twice on the same task should produce an equivalent file — do not duplicate sections or erase manual edits the user has made to the Implementation Plan.
- **Prototype component**: If a prototype file was found in Step 4d, the spec must instruct the implementer to use that file as the rendered component, not create a new one. The prototype file is the source of truth for the frontend implementation.
- **Prototype props interface**: If the prototype file exports a props interface, that interface is authoritative. The spec must explicitly state that any auto-generated `*Props` interface in the Enonic `.d.ts` should be removed or not created, and the prototype interface should be used (or re-exported) instead.
- **Impeccable (optional)**: Only for design/frontend UI tasks (Step 4e). Never required for general planning.
- **Auxiliary skills (optional)**: Use `find-skills` only for real capability gaps (not routine planning). Never invent session-only tooling when a quality skill exists.
