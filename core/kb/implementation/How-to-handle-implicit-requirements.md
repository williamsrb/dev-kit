---
id: how-to-handle-implicit-requirements
when_skills: [plan-implementation, validate-plan, run-plan, validate-impl]
inputs: [PRD, plan ACs, Figma/sister-part extras]
outputs: [implicit.md, techlead Jira checkbox comment (jira), auto-ticked local list (local)]
stop_if: [encoding an implicit extra as an AC; implementing an unticked extra]
read: section
prose: caveman-lite
---

# Handle implicit requirements

An implicit requirement is a verifiable extra the implementer is tempted to add that the ticket ACs and comments do not state. Silent yes is what a techlead calls AI slop. Silent no is what they call incomplete. After delivery they may also call those extras **bugs** and bounce the ticket (JOT-270). Classify first. **jira:** put the grey zone on a techlead tick list before coding. **local:** auto-tick extras that belong; leave the rest `[ ]`.

This is not TBD. TBD is a missing **product** decision (copy, locale, URL, env, which component, ownership, Figma node, AC conflicts). Implicit extras are **engineering completeness**.

- **jira:** TBD goes to the analyst. Implicit extras go to the techlead tick list.
- **local:** There is no analyst and no techlead. The planner is the product owner and the techlead. Auto-select the recommended TBD path and auto-tick extras that belong. Do not ask. Do not block execution.

## Classify

| Bucket | Who decides | Plan | Implement |
|--------|-------------|------|-----------|
| Explicit AC / comment / user exclusion | already decided | User Stories / Constraints | yes |
| **DO** | nobody to ask | Implementation Steps / Definition of Done only | yes, always |
| **Tick** (grey zone) | techlead (jira) / planner as techlead (local) | `## Implicit requirements (techlead tick)` | jira: only if ticked; local: `[x]` after auto-select |
| **DON'T** | nobody | Non-Goals if tempting | never |
| **TBD** | analyst (jira) / planner as PO (local) | `## TBD` with 2–3 options | jira: hard-stop; local: auto-select recommended, then implement |

## DOs (always ship — not on the tick list)

Do these when the change type requires them, even with no AC:

- Wire the stack so the explicit AC can ship (register part/layout/page, processor, i18n labels, typed props).
- Reuse the prototype, existing helper, or sister pattern the AC needs. Do not duplicate it.
- Follow a recorded project How-to that matches this change type (empty-state guard, schema i18n, user exclusions).
- Keep user/chat exclusions. They beat Figma.
- Match surrounding file style. That is not an extra feature.

## DON'Ts (never — not on the tick list)

- Invent copy, locale, URL, env, component, or Figma node as a silent extra. That is TBD (jira: ask; local: auto-select via 3f, then encode). Do not hide it as a tick-list item.
- Drive-by refactors, new abstractions, extra locales, Storybook/docs, sister-bug fixes, tests in a layer that has none.
- Narrating comments, speculative try/catch, `any` casts. That is deslop, not a tick item.
- Figma deltas on an excluded element.
- Write inferred extras as `_(inferred)_` ACs or FRs.

## Tick list (techlead)

One checkbox per extra the ticket did not ask for but Figma, a sister part, or habit suggests. One line each. Examples:

- Hover, focus, or animation from a sibling Figma frame
- Empty illustration when the AC only describes the populated state, and no project How-to already requires the guard
- Extra CMS field or help text that would be nicer
- Optional sister-part field this ticket never named
- Extra breakpoint, loading chrome, or error toast not in the AC
- New CMS field or checkbox the ticket did not add (`is_headquarters` on JOT-270)
- Moving a constant into site config so editors can change it without a release
- Extracting a shared helper that also changes a sibling ticket's output
- Edge state that needs a deleted asset or empty config to reproduce

## Procedure — plan

1. Harvest extras while reading the PRD, Figma, and code. Classify with the tables above.
2. Write `implicit.md` (folder) or `## Implicit requirements (techlead tick)` (legacy file). Checklist or `- Implicit: none`.
3. Do not promote tick-list items into ACs or FRs. Do not put DOs on the tick list.
4. After the plan file is written:
   - **jira:** post when the list is non-empty. Do not wait for ticks to finish planning.
   - **local:** auto-tick `[x]` extras that belong in this delivery (same-component sibling states; completeness the AC cannot ship without looking broken). Leave `[ ]` for follow-up (new CMS editor contracts, cross-ticket helpers, optional chrome). Report `[x]`/`[ ]` in chat. Do not post. Do not wait.
5. **jira:** TBD remains the coding hard-stop. Implicit is not. **local:** auto-select TBD (recommended path) and auto-tick implicit. Neither blocks execution.

## Procedure — post (jira mode)

1. Body: `Tech lead — implicit requirements for <KEY>.` then `These are extras, not bugs and not blockers. Tick each item this delivery should include. Unticked items stay out of scope (follow-up).` then the `- [ ]` lines.
2. Run `python3 ~/.agents/skills/plan-implementation/scripts/post_implicit_requirements.py --issue <KEY> --file <implicit.md-or-plan>`. Markdown `- [ ]` becomes ADF task-list checkboxes. Do not use MCP. Do not post when the list is none.
3. The script creates the comment, or edits the stored `_Comment-id:` (backup first). It writes `_Comment-id: <id>` into the plan file. Report the id in chat, not in the Jira body.

## Procedure — implement / QA

1. Explicit ACs and DOs: implement.
2. Unticked tick-list items: out of scope. Missing them is not incomplete.
3. Ticked items (Jira checkbox, local `[x]`, or the user said "include X"): in scope.
4. QA: delivering an unticked item is scope creep (Concern; remove). Missing a DO the AC cannot ship without is a Blocker. Code-shape slop stays deslop.
5. Review extras after delivery: classify with the tables. Do not promote them to Blockers or rewrite the original ACs. If the techlead (or local PO) decides they come next, that is a **review-time tick** — follow-up increment or a new ticket, not a FAIL of the first delivery. See [How-to-handle-implicit-requirements-examples.md](How-to-handle-implicit-requirements-examples.md) (JOT-270).

## Pitfalls

- Do not mix TBD and implicit in one Jira comment.
- Do not wait for techlead ticks before coding the explicit AC.
- **jira:** do not treat silence on the tick list as approval.
- **local:** do not ask an analyst or techlead. Auto-select. Do not hard-stop for TBD or implicit.
- Do not post in local mode.
- One-line checkboxes only. Nested a/b/c is TBD, not a tick item.
- Do not encode a tick-list extra as `_(inferred)_` and then implement it.
- Do not treat "AC is only half met" as AC failure when the AC already has a hedge (`where practical`) and the practical half shipped.
- Do not bounce a ticket to To Do solely for implicit extras. That recasts a tick-list item as a bug.
- Worked sample: [How-to-handle-implicit-requirements-examples.md](How-to-handle-implicit-requirements-examples.md) (JOT-270 comments 531070 / 531187).
