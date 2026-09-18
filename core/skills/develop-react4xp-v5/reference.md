# React4XP Reference Notes

## Canonical flow from tutorial

1. Setup sandbox and app from `starter-react4xp`.
2. Build baseline entry (`App.tsx`) and common props/styles.
3. Add content-type rendering and processors.
4. Add rich text processing and macro rendering.
5. Add page rendering with regions.
6. Add parts and optional part processors.
7. Add layouts and optional layout processors.
8. Use page templates for editorial composition.
9. Validate build/runtime and refine config.

## Key concepts

- **Single app shell**: React4XP centers around one React entry app (`entries/App.tsx`) and registry-based rendering.
- **Registry-driven rendering**: Rendering is selected by CMS descriptor keys (`app:key`) or macro names.
- **Data shaping boundary**: Processor code prepares serializable props; views render them.
- **Mode-aware behavior**: Edit mode prioritizes safe/static rendering behavior; live mode enables client activation.
- **Isomorphic rendering**: SSR + hydration are configured through controller render options and app config.

## API usage guidance

### `/lib/enonic/react4xp`

- Common import in XP controllers:
  - `const React4xp = require('/lib/enonic/react4xp');`
- Primary shorthand:
  - `React4xp.render(entry, props, request, options)`
- Use custom flow (`new React4xp(...)`) only when separate control of body/pageContributions is needed.

### `render` options worth deciding explicitly

- `id`, `body`: control rendering container behavior
- `pageContributions`: merge with existing contributions
- `ssr`, `hydrate`: choose SSR/client activation strategy
- `urlType`: choose URL format where relevant

## Recommended implementation defaults

- Use TypeScript for processors and component props.
- Keep processor outputs small and explicit.
- Use `addCommon` sparingly (global processor runs frequently).
- Prefer dedicated CSS modules per component except intentional global styles.
- Keep `componentRegistry` and `dataFetcher` updates in the same change to avoid broken rendering paths.

## Build/config notes

- `enonic dev` for iterative local development.
- `enonic project build` for optimized production build.
- `react4xp.config.js`
  - `entryDirs`: additional entry discovery folders
  - `chunkDirs`: bundle splitting by directory
- `webpack.config.react4xp.js` is optional extension point for custom loaders/plugins/polyfills.

## Common pitfalls

- View added but processor not registered (or vice versa)
- Descriptor key mismatch (`com.vendor.app:name` typo)
- Rich text rendered without `processHtml` preprocessing
- Macro view exists without macro processor/data handling
- Assumptions that edit mode behaves like live mode
- Overfetching in common processors and slowing all renders

## Quick verification checklist

```md
- [ ] `enonic dev` starts without compile errors
- [ ] Target content/page/part/layout renders in preview
- [ ] Rich text and macros render as expected
- [ ] No unexpected regressions in existing components
- [ ] Production build passes (`enonic project build`)
```
