---
name: develop-react4xp-v6
description: "Build Enonic React4XP 6.x on XP 7 (componentRegistry, pages/parts/layouts, SSR). Use for new React4XP on XP 7. Prefer v7 for XP 8; v5 only for 5.x maintenance. | recommendedRole: implement | aliases: react4xp-v6, react4xp-6.x, xp7-react4xp, enonic-xp7-react4xp-development."
metadata:
  recommendedRole: implement
  aliases: react4xp-v6, react4xp-6.x, xp7-react4xp, enonic-xp7-react4xp-development
  cliDependencies:
    required: [agentctl, rg, python3, enonic, npm]
    optional: [docker]
---
## Local documentation search first

Run `agentctl docs search '<focused query>' --db ~/.agents/.cache/offline-docs.sqlite --json`. Open only the best matching source path; fall back to the routing index when no result is relevant.

# React4XP 6.x Development (XP 7)

## When to use

Apply this skill for **React4XP 6.x** (docs under `/learn/react4xp-tutorial/6.x`) on **XP 7**:
- Default choice for **new** React4XP work under XP 7
- React4XP app setup and starter structure
- Controller rendering with `/lib/enonic/react4xp`
- `componentRegistry` and `dataFetcher` registrations
- Content type, page, part, layout, page templates, rich text/macros
- Build/runtime behavior, hydration/SSR

Routing:
- **XP 8 / React4XP stable (7.x)** → `develop-react4xp-v7`
- **XP 7 / new React4XP** → this skill (`develop-react4xp-v6`)
- **XP 7 / legacy 5.x maintenance only** → `develop-react4xp-v5`

React4XP 5.x and 6.x are **XP 7 exclusive**. Do not use this skill as the default for XP 8.

## Documentation lookup order (prefer offline)

Docs live under `~/.agents/kb/offline-reference/react4xp-6.x` (not under this skill).

1. Route via `~/.agents/kb/offline-reference/react4xp-6.x/llm-index.md` (chooser: `docs` / `learn`).
2. Read files under `~/.agents/kb/offline-reference/react4xp-6.x/learn/react4xp-tutorial/6.x...` (tutorial) and `.../docs/react4xp/6.x/...` (API/reference).
3. Online: https://developer.enonic.com/learn/react4xp-tutorial/6.x and https://developer.enonic.com/docs/react4xp/6.x

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

- `src/main/resources/react4xp/entries/App.tsx`
- `src/main/resources/react4xp/componentRegistry.tsx`
- `src/main/resources/react4xp/dataFetcher.ts`
- `src/main/resources/react4xp/components/**`
- `src/main/resources/site/*.ts`
- `react4xp.config.js`

## Implementation checklist

```md
React4XP Task Progress
- [ ] Identify rendering target (content/page/part/layout/macro)
- [ ] Implement or update React view component
- [ ] Implement or update processor (if needed)
- [ ] Register in componentRegistry/dataFetcher
- [ ] Verify SSR/edit-mode-safe behavior
- [ ] Run build/dev checks and report results
```

## Additional resources

- Offline docs: `~/.agents/kb/offline-reference/react4xp-6.x/README.md`
