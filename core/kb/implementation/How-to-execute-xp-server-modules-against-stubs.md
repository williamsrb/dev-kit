# How to execute XP server modules against stubs

## Scope

Runtime-shape proof for a pure-ish XP server module (`lib/modules/**`, e.g. a JSON-LD builder) when no sandbox, jar or deploy is available. Stronger than reading, weaker than served HTML. Used on jotron JOT-256 / JOT-271 (DECISIONS R43, R118).

## Prerequisites

- An image and volume that hold the app's `node_modules` (esbuild ships with tsup). jotron: image `leanon/enonic-ci:7.14-node20`, volume `jotron-cold-xp-node-modules`.
- A scratch dir outside the worktree for stubs, bundle and runner.

## Procedure

1. Stubs in `<scratch>/stubs/`: one CommonJS file per XP lib the module calls (`/lib/xp/portal`, `/lib/xp/content`), driven by globals the runner sets (`globalThis.__siteConfig`, `globalThis.__pageUrl`). One `generic.js` for every other `/lib/*` import the bundle pulls transitively (`/lib/cache`, `/lib/xp/i18n`, ...).
2. `build.cjs` using the esbuild JS API with an `onResolve` plugin (filter `^\/lib\/`): mapped stubs first; then `/work/src/main/resources<path>{.ts,/index.ts,.js,/index.js}`; anything else → `generic.js`. Bundle `platform: node`, `format: cjs`, then `require` a runner that loops scenarios and prints `JSON.parse(serialise(builder(...)))`.
3. Run read-only against the worktree:

```bash
docker run --rm -v <worktree>/xp:/work:ro -v <node_modules-volume>:/work/node_modules:ro \
  -v <scratch>:/scratch -w /scratch --entrypoint node <ci-image> /scratch/build.cjs
```

## Pitfalls

- esbuild `--alias:/lib/xp/portal=...` fails: "Invalid alias name". Leading-slash specifiers need the plugin.
- A `Proxy` generic stub breaks under esbuild's `__toESM` (no own keys, so named imports are `undefined` → "newCache is not a function"). Use a plain object with the names actually called (`newCache: () => ({ get: (k, f) => f() })`, `getSite`, `localize`, `query`).
- Module-scope side effects (a `newCache({})` at import time) run on `require`. The stub must satisfy them, not only the function under test.
- Check the serialised string, not only the object: an `undefined` property disappears from `JSON.stringify`, which is how "omit the key" behaviour is proven.

## Variant: server-render a prototype React component

Proves what react4xp SSR puts in the HTML (card counts, whether a control renders, an `href`) without a jar. jotron JOT-266 (R121).

- Volume `jotron-cold-proto-node-modules` has `esbuild`, `react`, `react-dom`; no `jsdom`, so client effects (fetch, maps, clicks) cannot run this way.
- `build.cjs`: `esbuild.build({ entryPoints: ['/scratch/entry.tsx'], bundle: true, platform: 'node', format: 'cjs', jsx: 'automatic', nodePaths: ['/proto/node_modules'], loader: { '.scss': 'empty', '.css': 'empty', '.svg': 'text' }, plugins: [alias] })`, where the alias plugin maps `^@/` with `b.resolve('/proto/src/' + path.slice(2), { kind, resolveDir: '/proto' })`.
- `entry.tsx` imports the component from `/proto/src/components/<Name>`, `renderToString`s each props case, and regex-counts markers in the string.

```bash
docker run --rm -v <worktree>/prototype:/proto:ro -v jotron-cold-proto-node-modules:/proto/node_modules:ro \
  -v <scratch>:/scratch -w /scratch --entrypoint node leanon/enonic-ci:7.14-node20 /scratch/build.cjs
```
