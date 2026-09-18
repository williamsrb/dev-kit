---
id: how-to-avoid-xp8-runtime-traps-in-migrated-js-controllers
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

# How to avoid XP 8 runtime traps in migrated JS controllers

Companion to [How-to-execute-an-xp7-to-xp8-app-upgrade-locally.md](How-to-execute-an-xp7-to-xp8-app-upgrade-locally.md)
and [xp7-to-xp8-upgrade/](xp7-to-xp8-upgrade/). Those cover build and descriptors. These are
failures that appear only **after** a green build, on the first real request.

## Scope

Plain-JS (non-TypeScript) XP 7 app migrated to XP 8.0.4. Verified on
`automatic-translation-app` (7.13.3 → 8.0.4, 2026-09-02) against the `logviewer` XP 8 reference.

## Pitfalls

### 1. ES6 destructuring is not implemented in the XP 8 script engine

`upgrade.md`'s widget-migration example is **TypeScript**, where `import {a, b} from '...'`
compiles away. Copying its shape into plain JS gives a 500 on first request:

```
com.example.automatictranslation:/admin/extensions/ata/ata.js:5:6
ES6 destructuring is not yet implemented
const { requestHandler, mappedRelativePath } = require('/lib/enonic/static')
      ^ (java.lang.RuntimeException)
```

Import the namespace instead:

```javascript
const Static = require('/lib/enonic/static')
// Static.requestHandler(...), Static.mappedRelativePath(...)
```

Template literals, arrow functions, `const`/`let`, `Array.prototype.filter/map` are all fine —
only destructuring (and array destructuring) fails. A build, a lint, and the JAR require-scan
all pass; nothing catches it before the request.

### 2. A module-level cached `Node.connect` handle dies on Jetty 12

A connection cached across requests is an extremely common XP 7 idiom:

```javascript
let connection = null
function initializeConnection() {
    if (!connection) connection = Node.connect({ repoId: '...', branch: 'master', ... })
}
```

On XP 8 (Jetty 12.1.x) the handle captures the local scope of the request that created it. The
**next** request's first node read then dereferences a recycled servlet request:

```
java.lang.NullPointerException: Cannot invoke "org.eclipse.jetty.server.Request.getSession(boolean)"
  because the return value of "org.eclipse.jetty.ee11.servlet.ServletApiRequest.getRequest()" is null
	at org.eclipse.jetty.ee11.servlet.ServletApiRequest.getSession(ServletApiRequest.java:578)
	at com.enonic.xp.web.impl.context.SessionWrapper.getAttribute(SessionWrapper.java:33)
	at com.enonic.xp.context.LocalScopeImpl.getAttribute(LocalScopeImpl.java:81)
	at com.enonic.xp.repo.impl.InternalContext.getSearchPreference(InternalContext.java:186)
	at com.enonic.xp.repo.impl.node.GetNodeByPathCommand.execute(GetNodeByPathCommand.java:23)
```

Misleading in two ways: the message names Jetty, not your cache, and the **first** request after
a redeploy succeeds (it is the one that populates the cache). Repository *creation*
(`Repo.get`/`Repo.create`) does not trip it — only a node read through the stale handle.

Fix: connect per call. Keep any repo bootstrap separate so it still runs once-ish.

```javascript
function connect() {
    ensureConfigRepo()
    return Node.connect({ repoId: CONFIG_REPO, branch: CONFIG_BRANCH, principals: ['role:system.admin'] })
}
```

Same rule applies to anything else that closes over request-scoped context (a `Context.run`
result holding a connection, a cached `Content` client).

### 3. `lib-router`'s `''` route does not match a trailing slash

`router.get('', handler)` answers `.../my-extension` with 200 and `.../my-extension/` with 404.
`extensionUrl()` returns the no-slash form, so Content Studio is fine — but any hand-built link,
redirect, or test that adds the slash gets a bare `{"status":404,"message":"Not Found"}` with
nothing in `server.log`. Register both:

```javascript
router.get('', renderPanel)
router.get('/', renderPanel)
```

### 4. `getMultipartStream` **does** work inside an admin extension

Worth recording because it is easy to assume otherwise: `lib-portal`'s multipart functions read
the live HTTP request, so a `FormData` POST dispatched through `lib-router` inside an
`AdminExtension` works unchanged from the XP 7 `services/` version. Verified end to end against
`lib-license` 4.0.0 — an invalid upload returns 400 from `validateLicense`, not a 500.

### 5. Let a missing repository degrade, not 500

XP 7's `Portal.getSiteConfig()` returned nothing in a context it did not like. The XP 8
replacement — an explicit `Context.run({repository, branch}, …)` around `Content.query` — throws
`RepositoryNotFoundException` instead, which surfaces to the caller as a 404/500. Any admin
surface that used to degrade to an empty list needs the try/catch put back:

```javascript
try {
    return Context.run({ repository: repo, branch: branch }, () => lookup(options))
} catch (err) {
    log.warning('Could not read app config from [%s/%s]: %s', repo, branch, err)
    return emptyResult(options)
}
```

### 6. CMS YAML key names the plan probably got wrong

Two keys that silently differ from the obvious camelCase guess (`docs/cms/stable/schemas/
form-items.md`, `.../i18n.md`, `.../form-items/field-set.md`):

| Wrong | Right |
|---|---|
| `helpText:` | `help-text:` |
| `occurrences: { minimum, maximum }` | `occurrences: { min, max }` |

Note the *runtime* `Input` object in `fundamentals/types.md` does use `occurrences:
{minimum, maximum}` — that is the read side, not the descriptor. Do not let one correct the other.

### 7. The container's own `gradlew deploy` makes `build/` root-owned

The dev image's `launcher.sh` runs `./gradlew clean deploy` as root inside the bind-mounted source
tree. Every later **host** build then dies at `processResources`:

```
Could not set file mode 775 on '.../xp/build/resources/main/tasks'
```

Either `make grant` (sudo chown back), or just build inside the container from then on:
`docker exec <app> sh -c "(cd /enonic-xp/source && ./gradlew build)"`.
