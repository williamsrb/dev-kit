---
name: develop-react4xp-v5
description: "Maintain legacy Enonic React4XP 5.x on XP 7. Use for existing 5.x apps. Prefer develop-react4xp-v6 for new XP 7 work; develop-react4xp-v7 for XP 8. | recommendedRole: implement | aliases: react4xp-v5, react4xp-5.x."
metadata:
  recommendedRole: implement
  aliases: react4xp-v5, react4xp-5.x
  cliDependencies:
    required: [agentctl, rg, python3, enonic, npm]
    optional: [docker]
---
## Local documentation search first

Run `agentctl docs search '<focused query>' --db ~/.agents/.cache/offline-docs.sqlite --json`. Open only the best matching source path; fall back to the routing index when no result is relevant.

# React4XP 5.x Development (legacy)

## When to use

Apply this skill for **React4XP 5.x** (docs under `/learn/react4xp-tutorial/5.x`) **maintenance only** on **XP 7**:
- Existing 5.x apps — bugfixes and small changes
- React4XP app setup and starter structure (legacy)
- XP controller rendering with `/lib/enonic/react4xp`
- `componentRegistry` and `dataFetcher` registrations
- Content type, page, part, layout, and page template rendering
- Rich text (`processHtml`) and macro rendering
- Build/runtime behavior (`enonic dev`, production build, hydration/SSR)

Routing:
- **XP 8 / React4XP stable (7.x)** → `develop-react4xp-v7`
- **XP 7 / new React4XP** → `develop-react4xp-v6` (6.x)
- **XP 7 / legacy 5.x maintenance only** → this skill

React4XP 5.x is **XP 7 exclusive** and **legacy**. Do not start new React4XP apps on 5.x.

## Documentation lookup order (prefer offline)

Docs live under `~/.agents/kb/offline-reference/react4xp-5.x` (not under this skill).

1. Route via `~/.agents/kb/offline-reference/react4xp-5.x/llm-index.md` (leaf index; this catalog is not a folder chooser).
2. Read files under `~/.agents/kb/offline-reference/react4xp-5.x/learn/react4xp-tutorial/5.x...`.
3. Online: https://developer.enonic.com/learn/react4xp-tutorial/5.x

Refresh (from this skill directory; default output is the KB path above):

```bash
python3 scripts/sync-react4xp-docs.py
```

## Default approach

1. Confirm project is an XP app and locate React4XP structure under `src/main/resources/react4xp/`.
2. Keep backend-first wiring correct before UI polish:
   - Register view in `componentRegistry.tsx`
   - Register processor in `dataFetcher.ts` when data shaping is needed
3. Prefer typed props and explicit component data contracts.
4. Ensure rendering works in both Content Studio edit mode and live mode.
5. Validate with dev build and a quick runtime sanity check.

## Standard file map

Use these as defaults unless the project already defines alternatives:
- `src/main/resources/react4xp/entries/App.tsx`
- `src/main/resources/react4xp/componentRegistry.tsx`
- `src/main/resources/react4xp/dataFetcher.ts`
- `src/main/resources/react4xp/components/**`
- `src/main/resources/site/*.ts` (XP controllers)
- `react4xp.config.js`

## Implementation workflow

Copy this checklist when executing tasks:

```md
React4XP Task Progress
- [ ] Identify rendering target (content/page/part/layout/macro)
- [ ] Implement or update React view component
- [ ] Implement or update processor (if needed)
- [ ] Register in componentRegistry/dataFetcher
- [ ] Verify SSR/edit-mode-safe behavior
- [ ] Run build/dev checks and report results
```

### 1) Setup and baseline

- For new apps, use Enonic CLI starter flow (`starter-react4xp`).
- In `App.tsx`, keep `@enonic/react-components/utils/initPublicPath` when lazy loading/chunks are used.
- Keep global styles and shared wrappers in `entries/App.tsx` and shared components.

### 2) Wiring rules

- Content type views: `componentRegistry.addContentType('<app>:<type>', { View })`
- Page views: `componentRegistry.addPage('<app>:<page>', { View })`
- Part views: `componentRegistry.addPart('<app>:<part>', { View })`
- Layout views: `componentRegistry.addLayout('<app>:<layout>', { View })`
- Macro views: `componentRegistry.addMacro('<macro-name>', { View })`

- Processor registration mirrors component registration:
  - `dataFetcher.addContentType(...)`
  - `dataFetcher.addPage(...)`
  - `dataFetcher.addPart(...)`
  - `dataFetcher.addLayout(...)`
  - `dataFetcher.addMacro(...)`
  - `dataFetcher.addCommon(...)` for globally needed props only

### 3) Rich text and macros

- Process HTML fields with `processHtml(...)` in processor code.
- Render processed output with `<RichText ... />`.
- Register macro processors + macro views together to avoid partial rendering.

### 4) Page composition

- Pages and layouts should usually render regions with `Region`.
- Keep region names aligned with CMS component definitions.
- Use page templates for editorial composition; remember hard-coded content-type rendering takes precedence for that content type.

### 5) Controller rendering and SSR/hydration

- Prefer `React4xp.render(entry, props, request, options)` in controllers for standard flows.
- Pass `request` when possible so mode detection and client activation behavior are correct.
- Treat Content Studio edit mode as SSR/static-safe mode; avoid client-side behavior assumptions there.
- Use `ssr`/`hydrate` options intentionally and consistently.

### 6) Build and config guardrails

- Dev: `enonic dev`
- Production build: `enonic project build`
- Optional server simulation: `enonic sandbox start --prod`
- Tune `react4xp.config.js` via `entryDirs` and `chunkDirs` only when needed.
- Add custom `webpack.config.react4xp.js` only for concrete loader/plugin/runtime needs.

## Output expectations

When completing a React4XP task:
- State which registry/fetcher entries were added/changed
- State which XP/React files were touched
- Note edit-mode vs live-mode behavior implications
- Include commands run and verification result

## Additional resources

- Offline docs: `~/.agents/kb/offline-reference/react4xp-5.x/README.md`
- For new XP 7 React4XP work, use `develop-react4xp-v6` instead
- Detailed notes: [reference.md](reference.md)
- Concrete patterns: [examples.md](examples.md)
- Utility checks:
  - `scripts/check-react4xp-structure.py`
  - `scripts/check-enonic-commands.py`
