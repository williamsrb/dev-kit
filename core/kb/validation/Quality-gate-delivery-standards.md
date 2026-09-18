---
id: quality-gate-delivery-standards
when_skills: [validate-impl]
inputs: [delivery diff, plan AC / Constraints / Non-Goals]
outputs: [findings, fixes, verdict]
stop_if: [contract change required for a real fix]
read: section
prose: caveman-lite
---

# Delivery standards

Read headings as needed. Do not reload this whole file after the first pass unless a later step needs another section.

## Hard constraint on every fix

Never break existing contracts or the stated task requirements. No changes to public function signatures, exported module APIs, HTTP routes/status codes, schemas, content types, or persisted data formats. Fixes must stay behavior-preserving for every existing caller. If a real fix needs a contract change, report a Concern with a suggested follow-up. Do not apply it.

## User scope exclusions (Blocker)

Apply `How-to-respect-user-scope-exclusions.md`. Priority: explicit user/chat exclusions > plan Constraints/Non-Goals > Figma/PRD inference. Any property delta on excluded element E beyond allowed change C is a Blocker, including inherited parent layout.

## Fix policy

Apply fixes when they:

- Close a **Blocker** or **Concern**.
- Remove redundant code, dead branches, or single-use abstractions introduced in the delivery.
- Remove **AI slop** introduced in the delivery (unnecessary comments, abnormal defensive checks/try-catch on trusted paths, `any` casts used to bypass types, avoidable nesting). Keep behavior unchanged unless fixing a clear bug.
- Replace reinvented logic with an existing project function already used elsewhere.
- Fix obvious bugs in the delivery (undefined variables, broken braces, wrong format strings).

Do not apply fixes when they:

- Expand scope beyond the stated requirement.
- Refactor unrelated files outside the delivery.
- Add new abstractions "for future reuse."
- Require risky behavior changes without task context.
- Restyle comments or error handling on **untouched** pre-existing lines.
- Strip real validation on **untrusted** input (that is security, not slop).

When unsure between **inline** vs **extract helper**: prefer **inline** unless the same logic appears more than once in this delivery.

## Findings (class, evidence, verdict)

Classify each finding as **Blocker**, **Concern**, or **Note**. When between two classes, choose the lower one.

| Class | Means | Unfixed effect on chat verdict |
|-------|--------|--------------------------------|
| **Blocker** | Concrete failure: wrong result, crash, leak, vulnerability, broken contract, or exclusion violation | **FAIL** |
| **Concern** | Real but narrower defect, impact risk, or missing/weakened tests in a layer that already has tests | **PASS WITH NOTES** |
| **Note** | Bounded maintainability / less-code / AI slop / Impeccable polish; no concrete failure | Never **FAIL**. Notes alone still **PASS** |

Verdict is on the **post-fix** delivery. Notes and polish never flip **FAIL**.

### Evidence

- **Blocker / Concern:** one line `Premise: <observed fact at file:line> → Path: <caller/input/control flow> → Verdict: <resulting failure>`. No certificate → do not file it as Blocker/Concern.
- **Note:** one line `Premise: <observed fact at file:line> → Improvement: <specific benefit> → Fix: <bounded change>`.

Do not invent a runtime failure to promote a Note into a Concern.

### Do not report

Do not list (and do not "fix") candidates that are:

- Owned by follow-up lint/typecheck skills (syntax, unresolved imports, formatter, ESLint/tsc noise)
- Formatter-owned style
- Pre-existing debt on **untouched** lines, unless this diff breaks that code or a sibling path must mirror the new invariant
- Speculative (no concrete failure path and no valid Note premise)
- Dependent on code or frameworks not inspected in this run
- Generated or vendor files

Outside-diff findings belong in **Impact** (or a single Blocker/Concern), not as a drive-by refactor. A one-line caller/import fix remains allowed per `Quality-gate-delivery-scope.md`.

### One root cause

One finding per root cause. Further sites: `also applies: path:line`. Do not repeat the same bullet per file.

## Requirement fit

- Every part of the stated requirement is addressed.
- Nothing beyond the requirement was added without justification. Justification is an explicit AC, a ticked implicit item, or a **DO** from `How-to-handle-implicit-requirements.md`. Unticked implicit extras are out of scope: delivering them is scope creep (Concern; remove). Missing them is not incomplete.
- A review comment that asks for a new CMS field, a shared helper across sibling tickets, or an edge state not in the AC is an implicit extra, not a Blocker, unless it falsifies an explicit AC. Do not FAIL the delivery or bounce the ticket to To Do for those. Classify with `How-to-handle-implicit-requirements.md`. If the techlead then ticks them, they are the next increment (JOT-270).
- User scope exclusions are respected. Violations are Blockers.
- Deleted or renamed artifacts have no remaining references.
- Config, routes, and shared modules stay consistent with the change.
- When the resolved implementation plan lists acceptance criteria, tick each AC as PASS / FAIL / n/a. Use only that plan's AC / validation companion. Do not open the PRD or evidence plan for this checklist.
- Missing a **DO** the AC cannot ship without (stack wiring, recorded project How-to) is a Blocker.

Flag gaps as Blocker, Concern, or Note. Then fix Blockers and safe Concerns in code.

## Impact on other features

Check imports/requires/exports, site mappings/services/cron/tasks, config keys, and shared constants left partially dead. State **PASS** only when unrelated features appear unaffected, or list concrete risks.

## Code quality

Review changed code for correctness, minimal localized scope, consistency with surrounding conventions, no redundant checks/wrappers/abstractions, no drive-by refactors, and AI slop (see **AI slop (deslop)**). Fix obvious quality issues in the delivery before reporting.

## Less-code-is-better

Prefer the smallest diff that fully solves the requirement, reuse of existing project functions, deleting dead code, and inline logic over one-off abstractions.

- Remove helpers used only once. Inline them at the call site.
- Remove duplicate blocks. Extract only if the same logic is used more than once in this delivery.
- Do not create reusable functions to be used only once.
- Future reusability is never the goal. Present-time reuse (same logic more than once in this delivery) is the only justification.

Flag and fix unnecessary code, scope creep, or over-engineering.

## AI slop (deslop)

Mandatory on every QA run. Inspect only the delivery diff (same staged / unstaged / branch-diff tier). Strip AI-generated artifacts that would not appear in surrounding human-written code.

Compare new hunks to the rest of the same file. If the file already comments densely, wraps every call in try/catch, or uses `any`, do not impose a different house style on this diff alone.

Focus (delivery hunks only):

- Extra comments: narrating, leftover, or denser than local style; commented-out code
- Defensive checks or try/catch that are abnormal for **trusted** code paths
- Casts to `any` / `as unknown as T` / `@ts-ignore` / `@ts-expect-error` used only to bypass type issues
- Deep nesting that should be early returns
- Other patterns inconsistent with the file and surrounding codebase

Guardrails: keep behavior unchanged unless fixing a clear bug; prefer minimal edits; do not deslop untouched lines, generated/vendor files, or lint-owned style; do not weaken real validation on untrusted input.

Default class **Note**. Promote only with an evidence certificate that shows a concrete failure path. In **qa** mode, fix when the edit is local and behavior-preserving. In **review** mode, report as Minor unless the user asked to fix.

## Performance

Within the delivery scope only, check and fix when safe:

- Queries/IO inside loops (N+1, repeated fetches) — hoist or batch when the fix stays local
- Unbounded result sets where surrounding code paginates or limits
- Repeated expensive computation of the same value
- Accidentally quadratic constructs when a map/set lookup is the obvious local fix
- Blocking work on hot paths the diff touches — flag it; only fix when the codebase already has the async/cached counterpart in use elsewhere

Flag as Blocker/Concern/Note like any other finding. Fix only when the change stays local and behavior-preserving.

## Security

Within the delivery scope only, check and fix when safe:

- Injection: user input concatenated into SQL/NoQL/DSL, shell, file paths (traversal), or HTML (XSS)
- Secrets: any credential, token, or API key hard-coded in the delivery — replace with the project's config mechanism and flag as **Blocker**
- AuthZ: new endpoints/services/handlers without the permission checks equivalent code in this project applies
- Unsafe deserialization or `eval`-like constructs on external input
- Sensitive data written to logs

Hard-coded secrets are always a Blocker regardless of fix feasibility.

## Tests

Only when the delivery changes behavior in a layer that **already has tests**:

- Missing coverage for the new behavior, or assertions weakened so they cannot fail, is a **Concern**.
- Do not invent a test suite or add a framework. Do not run `xp-testing` unless that layer is already under test.

If that layer has no tests: report `n/a` — not a finding.
