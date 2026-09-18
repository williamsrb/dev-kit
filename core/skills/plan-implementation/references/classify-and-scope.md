# Classify and scope

## Step 3 — Process offline data and classify

### 3a. Process comments (from the offline file)

Comments refine acceptance criteria — they are **not** dumped raw into the project spec (except absorbed intent):

- Ignore automated CI/CD, deploy bot, and status-change comments (author name contains "Bot", "GitLab", "GitHub", "Jenkins", "Bamboo", or similar)
- Look for requirement changes, clarifications, or new conditions
- If a comment **clearly extends or supersedes** the description (later, explicit), treat it as authoritative and update acceptance criteria
- If comments **conflict with each other**, or with the description with **no clear later winner**, record a **TBD** item — do not pick a silent winner
- Mark criteria inferred or updated from comments with `_(from comments)_`

### 3b. Classify the task type

Analyze the issue title, description, and labels and pick **exactly one** category. This value goes in the `Type` field of the generated document and determines which reference file to load.

| Category | When to use | Reference file |
|---|---|---|
| **New Component** | Task creates a brand-new component, part, layout, macro, or page template | `references/new-component.md` |
| **Existing Component Change** | Task modifies, fixes, or extends a component that already exists in the project | `references/change-existing.md` |
| **API Integration** | Task involves connecting to or consuming an external/internal API, webhooks, data fetching, or service integration | `references/api-integration.md` |
| **Performance / Security** | Task focuses on optimizing performance or hardening security | `references/performance-security.md` |

If the task fits more than one category, pick the **primary** intent. If truly ambiguous, default to **Existing Component Change**.

**Load the matching reference file now** — you will need its guidance to fill the `Suggested Technical Approach` and `Implementation Steps` sections.

### 3c. Consult Enonic offline docs (when relevant)

If the task involves Enonic XP, CMS, platform APIs, or React4XP, **prefer offline LLM-dense docs** over live web fetches.

1. Pick the catalog row(s) that match the project/stack (XP 7 vs XP 8; React4XP 5.x legacy / 6.x / stable 7.x).
2. Open that catalog’s `llm-index.md` under `~/.agents/kb/offline-reference`. If it is a chooser (rows ending in `llm-index.md`), open the matching subtree index, then the page.
3. Use those pages when drafting `Suggested Technical Approach` and `Implementation Steps`. Cite offline paths (e.g. `~/.agents/kb/offline-reference/xp8/docs/code/stable/libraries/lib-content.md`), not only URLs.
4. Skip this step only when the task is clearly unrelated to Enonic/React4XP.

| When | Skill | Routing index | Content root |
|------|-------|---------------|--------------|
| XP **7** backend (libs, controllers, framework, schemas) | `develop-xp7-backend` (`xp7-backend`) | `~/.agents/kb/offline-reference/xp7/llm-index.md` | `~/.agents/kb/offline-reference/xp7/{development,framework,api}/` |
| XP **8** / stable (platform, CMS, code kit) | `develop-xp8` (`xp8-docs`) | `~/.agents/kb/offline-reference/xp8/llm-index.md` | `~/.agents/kb/offline-reference/xp8/docs/{platform,cms,code}/stable/` |
| React4XP **5.x** (XP 7, legacy maintenance only) | `develop-react4xp-v5` (`react4xp-v5`) | `~/.agents/kb/offline-reference/react4xp-5.x/llm-index.md` | `~/.agents/kb/offline-reference/react4xp-5.x/learn/react4xp-tutorial/5.x` |
| React4XP **6.x** (XP 7, new React4XP work) | `develop-react4xp-v6` (`react4xp-v6`) | `~/.agents/kb/offline-reference/react4xp-6.x/llm-index.md` | `~/.agents/kb/offline-reference/react4xp-6.x/{learn/react4xp-tutorial,docs/react4xp}/6.x/` |
| React4XP **stable / 7.x** (XP 8 default) | `develop-react4xp-v7` (`react4xp-v7`) | `~/.agents/kb/offline-reference/react4xp-stable/llm-index.md` | `~/.agents/kb/offline-reference/react4xp-stable/{learn/react4xp-tutorial,docs/react4xp}/stable/` |

**Version hints:** XP 8 / `platform/stable` → XP8 + React4XP stable (7.x / `develop-react4xp-v7`). XP 7 new React4XP → React4XP 6.x (`develop-react4xp-v6`). XP 7 existing 5.x apps → React4XP 5.x maintenance only (`develop-react4xp-v5`). If unclear and the project already has React4XP files, infer from `package.json` / React4XP major or existing skill conventions; default to the version already used in the workspace.

### 3d. Check for a prototype component (New Component and Existing Component Change only)

Skip this step if the task type is **API Integration** or **Performance / Security**.

1. Run the following command from the project root to sync prototype assets:
   ```bash
   make copyComponents
   ```
2. Determine the component's kebab-case name from the issue title (same parsing as the reference files), then convert it to **PascalCase** for the prototype path. Examples: `hero` → `Hero`, `info-card` → `InfoCard`.
3. Check whether a frontend component file exists at:
   ```
   xp/src/main/resources/react4xp/components/prototype/<PascalName>/index.tsx
   ```
   Also check `index.jsx` and `index.js` if `index.tsx` is not found.
4. If a prototype file is found:
   - Record its path as `<prototype-component-path>`.
   - Read the file and check if it exports a TypeScript interface (e.g., `export interface <Name>Props { ... }`). If one is found, record it as `<prototype-props-interface>`.
5. This information is used in the Implementation Plan.

### 3e. Optional — Impeccable (design / frontend UI only)

**Skip by default.** Only consider when the task is clearly about **design or frontend UI** (visual layout, styling, UX copy on a surface, component presentation, landing/page look, responsive UI, motion, design-system tokens for a view). Skip for backend-only, API-only, CMS schema-only, infra, or non-UI refactors.

When it applies (optional, not mandatory):

1. Read the `impeccable` skill (`../impeccable/SKILL.md`) and run its session `context.mjs` if useful.
2. Prefer light planning cues over a full redesign: note which `/impeccable` commands fit later work (e.g. `shape`, `critique`, `audit`, `polish`, `typeset`, `layout`) and/or that `impeccable detect` can scan UI sources.
3. Fold at most a short **Design / UI (optional)** bullet into `Suggested Technical Approach` or `Definition of Done` — do not expand scope into a redesign unless the task asks for it.

Do **not** block the spec on Impeccable, invent DESIGN.md/PRODUCT.md requirements the task does not need, or run detect across the whole repo “just in case.”

### 3f. Harvest TBD (mandatory)

While reading the PRD, comments, Figma, and codebase, **collect gaps** — do not silently decide them. The implementer must not have to guess.

Record as TBD when any of these are true:

- Missing or contradictory acceptance criteria
- Unspecified copy, locale, env, URL, content type, or example page
- Ambiguous UX (order vs alignment, which breakpoint, which component)
- Analyst/comment conflicts (see 3a)
- Unknown CMS field / content-type mapping
- Missing design node or unmatched Figma
- Backend vs frontend ownership unclear
- Related-ticket dependency mentioned but not specified in this PRD (do **not** fetch sibling PRDs unless the user asked; list the gap)
- Anything else that would be a silent product decision

**Do not invent product decisions** to fill gaps. Each TBD item carries **2-3 options with the recommendation first** (see `~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md`) — none of them written as an AC/FR until the analyst confirms one.

**Not TBD:** decided user/chat exclusions. Those go in Constraints + Non-Goals only (`~/.agents/kb/validation/How-to-respect-user-scope-exclusions.md`).

Grep the PRD/comments for these; do not dump full comment threads.

### 3g. Harvest implicit requirements (mandatory)

Read `~/.agents/kb/implementation/How-to-handle-implicit-requirements.md` (Classify + DOs + DON'Ts + Tick list). Collect extras the ticket ACs/comments do not state.

- **DO** (stack wiring, recorded project How-tos, user exclusions, surrounding style) — Implementation Steps / Definition of Done. Not an AC. Not the tick list.
- **Tick** (Figma sibling states, extra CMS fields, sister-part optionals, extra chrome) — `## Implicit requirements (techlead tick)`. One checkbox line each. Not an AC/FR.
- **DON'T** (drive-by refactors, invented copy/locale, deslop, excluded Figma deltas) — Non-Goals if tempting. Never implement.
- **TBD** — still 3f. Do not put product gaps on the techlead tick list.

Do not write `_(inferred)_` ACs for tick-list extras. Empty list is allowed (`- Implicit: none`).

---

## Step 4 — Check if the plan / spec already exists

Check whether `<plans-dir>/<ISSUE-KEY>.md` already exists:

```bash
ls <plans-dir>/<ISSUE-KEY>.md 2>/dev/null
```

- **If it does not exist**: create the file from scratch using the template below
- **If it already exists**: read the current file, preserve the `## Implementation Plan` section if it has been manually edited by the user (check for content beyond the default template), and update the Jira-derived sections from the offline copy. Add `## TBD (ask analyst before implement)` and `## Implicit requirements (techlead tick)` if missing. If the file has `## Questions`, `## Open issues`, or similar, **fold those items into TBD** and remove the old heading — do not keep both.

Create the folder if needed:
```bash
mkdir -p <plans-dir>
```

---
