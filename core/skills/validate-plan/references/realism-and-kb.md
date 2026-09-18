# Extra validations

Run **both** checks on every target (implementation and evidence). They are first-class gates, not footnotes.

Judge from disk: workspace / one sample worktree, sectioned PRD, and KB indexes — not model memory.

---

## Is realistic or hallucination?

A claim is **realistic** only when a local source backs it. Otherwise it is a **hallucination**.

### Procedure

1. Extract mechanical claims from the plan: file/dir paths, APIs/libs, component/part names, prototype paths and props interfaces, helpers (`myImageUrl`, …), URLs/hosts, counts, CMS widgets, example pages, auth realms, selectors, “already exists” / “does not exist”.
2. For each claim, name **one** source:
   - workspace `ls` / `rg` (or one sample worktree)
   - sectioned PRD / comment **id**
   - user/chat exclusion or decision
   - a specific KB page (next section)
3. No source → hallucination. Rewrite: measure and correct, mark **to be created**, or move to TBD. Do not invent a plausible path or API to fill the gap.
4. Product guesses (copy, locale, env, which component, Figma node, ownership) presented as AC/FR/step → hallucination. Fold into TBD; do not keep them as requirements.
5. Re-derive counts from the registration site, not a README — `~/.agents/kb/validation/How-to-validate-a-plan-document-for-internal-consistency.md`.

### Pass / fail

| Result | When |
|--------|------|
| **PASS** | Every mechanical claim is sourced, explicitly “to be created”, or TBD |
| **FAIL** | Invented files, APIs, URLs, counts, or product decisions remain written as fact |

**FAIL** after the rewrite attempt → cannot **GO**. Remaining invented requirements → **NO-GO**. Remaining invented steps that were stripped → **GO-WITH-FIXES**.

---

## Is using the KB properly?

The plan must **route** through the owned KB, not paraphrase framework folklore. Cite paths; do not paste KB bodies into the plan.

Catalog: `~/.agents/kb/offline-reference/README.md`. Always enter a catalog via its `llm-index.md` (chooser then subtree if nested), then open only the matching page/heading.

### Which KB for which claim

| Claim type | KB | Role |
|------------|----|------|
| XP / React4XP / lib / schema / CMS product behavior | `~/.agents/kb/offline-reference/{xp7,xp8,react4xp-5.x,react4xp-6.x,react4xp-stable,content-studio-stable,content-studio-5.x}/` | Official semantics. **No** write-back. |
| Site instrumentation (clicks, selectors, Guillotine, Data Toolbox, auth tips, URL patterns) | `~/.agents/kb/testing/_shared` and `~/.agents/kb/testing/<project>` | How we automate **this** site. Write-back only on evidence **execute**, not this skill. |
| User exclusions | `~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md` | Already a gate. |
| Analyst TBD phrasing | `~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md` | Options + recommendation first. |

Do **not** mix roles: testing How-tos are not API docs; offline-reference is not a screenshot script.

### Implementation

- If the task is Enonic/React4XP/CMS: Suggested Technical Approach and Implementation Steps must cite offline-reference pages actually opened via `llm-index.md` (stack from the project, not a guessed version).
- Skip the catalog only when the task is clearly unrelated to those stacks — state **n/a** and why.
- Sister-pattern paths must exist in **this** repo (or the named sister). A copied path from another app with no check is hallucination **and** a KB miss.

### Evidence

- **Sources** must list testing How-to path(s) **or** `none — gap for KB write-back on execute`.
- CMS create/edit/publish/layers/rich-text flows: offline-reference (Content Studio / XP) when the How-to is missing or thin.
- Invented click paths, Guillotine queries, or admin URLs with no How-to and no offline-reference page → **FAIL**.
- Do not treat `kb/testing` as a dump for screenshots or Jira comment prose.

### Pass / fail

| Result | When |
|--------|------|
| **PASS** | Right catalog for each in-scope claim; citations or explicit n/a/gap |
| **FAIL** | In-scope stack with no `llm-index` route; folklore APIs; testing vs offline-reference swapped; empty Sources on evidence steps that need a How-to |
| **n/a** | Task has no platform/instrumentation claims (state why) |

**FAIL** after the rewrite attempt (still unsourced platform behavior) → cannot **GO**.
