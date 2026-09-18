---
id: how-to-respect-user-scope-exclusions
when_skills: [plan-implementation, validate-plan, validate-impl, run-plan]
inputs: [user/chat exclusions, plan Constraints/Non-Goals]
outputs: [Constraints, Non-Goals, Blocker vs allowed delta]
stop_if: [widening an excluded element to match Figma]
read: whole
prose: caveman-lite
---

# Respect user scope exclusions

## Priority (highest wins)

1. Explicit user / chat exclusions ("only change X", "do not change Y", "Y is another Jira")
2. Plan **Constraints** / **Non-Goals** that record those exclusions
3. Jira description / comments / Figma / inferred ACs

Never fix a plan or delivery toward a broader Figma/PRD reading that violates (1).

## Procedure — "order only" and similar deltas

If the allowed change is **order** (or another single delta) for element **E**:

| Allowed | Not allowed (unless the user asked) |
|---------|-------------------------------------|
| DOM / visual order of E relative to siblings | Horizontal alignment / side (left↔right) of E |
| Minimal wrapper needed solely to preserve order | Typography, underline, font-size, colors on E |
| | Extra markup on E (for example wrapping a label in `<span>`) beyond reorder |
| | Shared mixins/classes on E that change look |
| | Parent layout that **inherits** alignment/styling onto E (for example `align-items: flex-end` on a footer that contains E) |

Inherited layout counts. If a parent flex/grid rule moves or restyles E, that is still a change to E.

A mock that shows E on the right (or styled like a sibling) is not permission to change E when E is excluded. Freeze out-of-scope nodes to pre-change except the allowed delta.

Mark plan ACs: `_(user said)_` vs `_(inferred from Figma)_`. Inferred must not override user exclusions.

## Plan authoring

When the user (or a comment the user elevates) excludes an element except for a narrow change:

1. Put a **Constraints** bullet: element + allowed delta + forbidden dimensions (position, typography, markup, classes).
2. Mirror in **Non-Goals**. List position and styling when relevant, not only copy/URL.
3. Do not write ACs/FRs that require the forbidden dimensions.

## Plan validate / fix-plan

- **NO-GO** (or GO-WITH-FIXES that *narrow* the plan) if ACs/FRs expand an exclusion.
- Do not rewrite the plan to match a wider Figma reading when the user already constrained scope.

## Delivery QA

- Diff vs parent for excluded elements: any property delta beyond the allowed change is a **Blocker**.
- If plan ACs conflict with Constraints / user chat, **Constraints / chat win**. Flag plan drift as a Note. Do not fix the delivery toward the wrong AC.
- Prefer restoring pre-change placement/styles on E over expanding scope.

## Pitfalls

- Do not treat a Figma composition as a license to restyle an excluded element.
- Do not "complete" an AC that demands a forbidden delta. Fix toward the exclusion and note plan drift.
