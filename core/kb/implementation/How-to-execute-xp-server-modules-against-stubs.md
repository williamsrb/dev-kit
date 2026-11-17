# How to execute XP server modules against stubs

## Scope

Runtime-shape proof for a pure-ish XP server module (`lib/modules/**`, e.g. a JSON-LD builder) when no sandbox, jar or deploy is available. Stronger than reading, weaker than served HTML. Used on client PROJ-256 / PROJ-271 (DECISIONS R43, R118).

## Prerequisites

- An image and volume that hold the app's `node_modules` (esbuild ships with tsup). client: image `leanon/enonic-ci:7.14-node20`, volume `client-cold-xp-node-modules`.
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

Proves what react4xp SSR puts in the HTML (card counts, whether a control renders, an `href`) without a jar. client PROJ-266 (R121).

- Volume `client-cold-proto-node-modules` has `esbuild`, `react`, `react-dom`; no `jsdom`, so client effects (fetch, maps, clicks) cannot run this way.
- `build.cjs`: `esbuild.build({ entryPoints: ['/scratch/entry.tsx'], bundle: true, platform: 'node', format: 'cjs', jsx: 'automatic', nodePaths: ['/proto/node_modules'], loader: { '.scss': 'empty', '.css': 'empty', '.svg': 'text' }, plugins: [alias] })`, where the alias plugin maps `^@/` with `b.resolve('/proto/src/' + path.slice(2), { kind, resolveDir: '/proto' })`.
- `entry.tsx` imports the component from `/proto/src/components/<Name>`, `renderToString`s each props case, and regex-counts markers in the string.

```bash
docker run --rm -v <worktree>/prototype:/proto:ro -v client-cold-proto-node-modules:/proto/node_modules:ro \
  -v <scratch>:/scratch -w /scratch --entrypoint node leanon/enonic-ci:7.14-node20 /scratch/build.cjs
```

## Variant: the extractkit oracle loader (plain Node, no esbuild, 2026-10)

`steps/enonic/oracle/loader.js` runs one case against legacy XP JavaScript with Node built-ins only: `node loader.js <resource-root> <case.json>` prints one JSON line. It hooks `Module._resolveFilename` and `Module._load` for absolute requests (`/lib/...`): a file under the root is loaded, anything else becomes a recording Proxy stub. The case expression is evaluated inside the target module's scope (a `module.__oracleEval` appended to its source), so internal functions and prototype methods are reachable. Procedure to write a case:

1. Read the module for the exact call (constructor arguments, `prototype` method). Work the expected value out from the spec text, by hand.
2. Run the case through the loader or `extractkit step report.oracle`. A `platform` result names the first unstubbed call: `/lib/xp/content.getSite`, `/lib/xp/context.get`, `Java.type(com.example.RequestContext).get`. Add it to the case `stubs` with the smallest value the code reads, run again, repeat. One case may need three or four stubs.
3. Outbound calls: list `/lib/http-client.request` and `/lib/xp/mail.send` in `record`; give the HTTP call a response through `stubs`. A header under a credential-looking key is captured as `<masked>`; write `<masked>` in `expected` and limit the comparison with `fields` (`url`, `method`, `headers`) when the serialization of the body is not in the spec.

Pitfalls: Nashorn globals must exist (`__LINE__`, `__FILE__`, `Java`, `__`, `resolve`, `app`, `log`); a legacy module that wraps `Java.type` in another call makes the stub name `Java.type(<class>).<method>`; avoid expected values with floating-point noise (`250.75 * (33.3 / 100)` is `83.49974999999999` in JS, not `83.49975`); an expression that throws is a `fail`, a load error or a timeout is `not-evaluable`. `/lib/http-client` is not on disk in the legacy repo, so it is always a stub.
