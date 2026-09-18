# How to serve a root file (llms.txt, ads.txt, …) from an Enonic XP 7 site mapping

## Scope

Serving one fixed path at the site root (`/llms.txt`, `/ads.txt`, `/.well-known/x`)
from your own app, with a controller plus a `<mapping>` in `site/site.xml`. Not for
`robots.txt` / `sitemap.xml`, which are usually owned by third-party apps.

Worked example: jotron `/llms.txt` (JOT-290) — shipped under `services/`, bounced in
code review, relocated to `mappings/`.

## Prerequisites

- XP 7.x site app with `site/site.xml`.
- A build step that compiles server `.ts` → `.js` (tsup via `buildXpResources` in this
  repo). It compiles `mappings/` exactly as it compiles `services/`.

## Procedure

### 1. Put the controller under `mappings/`, never under `services/`

This is the trap. XP publishes **everything** under `src/main/resources/services/` at
`/_/service/<app.name>/<dir-name>` unconditionally — the mapping does not replace that
URL, it adds a second one. A root file placed in `services/` is then served at two
URLs with byte-identical bodies, which is duplicate content and usually the exact
problem the root file existed to solve.

Nothing inside the controller can suppress it: the service URL is published because the
directory exists, and the controller exports a bare `get()` with no access guard. A
`request.path` check is a runtime workaround for a layout mistake.

`mappings/` is not auto-published, so moving the file removes the second URL by
construction — no path check to write, nothing to regression-test beyond curling both
URLs once.

Verify with two curls, not by reading code:

```bash
curl -s  <host>/llms.txt                              | head
curl -sI <host>/_/service/<app.name>/llms-txt | head -1   # want 404
```

### 2. Point the mapping at the emitted `.js`

```xml
<mapping controller="/mappings/llms-txt/llms-txt.js" order="10">
    <pattern>/llms\.txt</pattern>
</mapping>
```

`.js` even when the source is `.ts` — the attribute names the packaged file, not the
source. Moving the controller changes only this attribute.

### 3. Patterns are full-match and are regexes

`<pattern>` is a regular expression matched against the whole site-relative path, not a
prefix. `/llms\.txt` claims that path and nothing else; a subtree needs `/docs/.*`.
Escape the dot, or `.` matches any character.

`order` defaults to 50 and the **lower** value wins when two apps on the same site map
the same path. Set it explicitly: a path unclaimed on a review site can be claimed by an
app that only exists on production. Check the path 404s on every environment first.

### 4. Set `contentType` and `Cache-Control` explicitly

```ts
return {
    status: 200,
    contentType: 'text/plain; charset=utf-8',
    headers: { 'Cache-Control': 'public, max-age=3600' },
    body: `${lines.join('\n')}\n`
}
```

The default content type is HTML, and an HTML body at a root-file path looks fine in a
browser and is useless to the consumer — content type is the decisive post-deploy check
because a mapping-precedence failure returns HTML.

### 5. Do not query the catalogue to build a five-line file

A root file is public, anonymous and uncached at the app level. Check what a shared
helper actually needs before threading a precomputed argument into it: jotron's
`isHiddenFromWebsite(content, hiddenPaths?)` short-circuits at its content-type check
for anything that is not a product or category, so the caller's `getHiddenPaths()` —
a `count: -1` query over the whole catalogue — was computed on every request and never
read. Calling it with one argument makes the list lazy, which for that caller means
never.

### 6. Log every dropped section, not the empty ones

The debugging failure for a config-driven file is silent: a resolver returns `null` for
missing content, wrong type, hidden content or no URL, and the section just disappears.
Log the **reason** and the site-config field name at `log.warning`, and wrap each
section in `try/catch` so one throw drops that section instead of 500-ing the file.

Do not log an **empty** field — leaving a section unconfigured is the documented way to
omit it, not a fault, and warning on it trains people to ignore the log.

## Pitfalls

- An empty `services/<name>/` directory left behind after the move is untracked noise,
  but a surviving controller file there re-publishes the second URL. Confirm the
  directory is gone, not just the mapping updated.
- `e.message` on a Nashorn-thrown Java exception can be `undefined`. Interpolate `${e}`
  (or `String(e)`) instead of `${e.message}`.
- Nashorn target: `const`, arrows, template literals, spread and optional chaining are
  fine if the shipped source already uses them; `Array.prototype.includes`,
  `Object.assign` and `async`/`await` are not — use `indexOf(x) !== -1`.
- Grepping `site.xml` and finding no mapping does not mean a URL is unhandled —
  content-path URLs render through the content's own `page.controller`.
