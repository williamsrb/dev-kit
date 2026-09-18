---
name: develop-react4xp-v7
description: "Build Enonic React4XP 7.x / stable on XP 8 (componentRegistry, pages/parts/layouts, SSR). Use for React4XP 7. Prefer v6 for new XP 7 work; v5 only for 5.x. | recommendedRole: implement | aliases: react4xp-v7, react4xp-7.x."
metadata:
  recommendedRole: implement
  aliases: react4xp-v7, react4xp-7.x
  cliDependencies:
    required: [agentctl, rg, python3, enonic, npm]
    optional: [docker]
---
## Local documentation search first

Run `agentctl docs search '<focused query>' --db ~/.agents/.cache/offline-docs.sqlite --json` when `agentctl` is available.

If it is not on `PATH`, do **not** browse the web as the first fallback. Route manually through the bundled offline index and open the returned local file:

```bash
rg -n -i '<focused terms>' ~/.agents/kb/offline-reference/react4xp-stable/**/llm-index.md
sed -n '1,240p' ~/.agents/kb/offline-reference/react4xp-stable/<path-from-index>
```

Only use the online documentation after the offline reference is missing, stale for the required version, or explicitly requested by the user. Record that reason in the response.

# React4XP 7.x (stable) Development

## When to use

Apply this skill for **React4XP stable / 7.x** (docs under `/learn/react4xp-tutorial/stable`), the default for **XP 8**:
- React4XP app setup and starter structure
- Controller rendering with `/lib/enonic/react4xp`
- `componentRegistry` and `dataFetcher` registrations
- Content type, page, part, layout, page templates, rich text/macros
- Build/runtime behavior, hydration/SSR

Routing:
- **XP 8 / new React4XP** → this skill (`develop-react4xp-v7`)
- **XP 7 / new React4XP** → `develop-react4xp-v6` (6.x)
- **XP 7 / legacy 5.x maintenance only** → `develop-react4xp-v5`

## Documentation lookup order (prefer offline)

Docs live under `~/.agents/kb/offline-reference/react4xp-stable` (not under this skill).

1. Route via `~/.agents/kb/offline-reference/react4xp-stable/llm-index.md` (chooser: `docs` / `learn`).
2. Read files under `~/.agents/kb/offline-reference/react4xp-stable/learn/react4xp-tutorial/stable...` (tutorial) and `.../docs/react4xp/stable/...` (API/reference).
3. Online: https://developer.enonic.com/learn/react4xp-tutorial/stable and https://developer.enonic.com/docs/react4xp/stable

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

- Offline docs: `~/.agents/kb/offline-reference/react4xp-stable/README.md`
