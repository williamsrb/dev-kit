---
id: how-to-verify-an-xp8-site-app-at-runtime-without-content-studio
when_skills: [run-plan, upgrade-xp-app]
read: section
prose: caveman-lite
---

# How to verify an XP 8 site app at runtime without Content Studio

**Related:** [How-to-execute-an-xp7-to-xp8-app-upgrade-locally.md](How-to-execute-an-xp7-to-xp8-app-upgrade-locally.md),
[xp7-to-xp8-upgrade/manual-schemes-migration.md](xp7-to-xp8-upgrade/manual-schemes-migration.md)

## Scope

You upgraded a **site** app (parts, macros, response processors) to XP 8 and need to prove it
renders — not just compiles. A green `gradlew build` proves nothing about descriptor wiring,
`resolve()` roots, region names, or Thymeleaf output.

The blocker: Content Studio is a separate Market app. On an offline/air-gapped box it is not
installed, so there is **no UI to create a site**, and the `/admin/site/preview/...` and
`/admin/site/edit/...` routes do not exist either (`Admin application [site:preview] not found` —
those routes are Content Studio-owned in XP 8).

Verified on cookiebot-app (XP 7.11.1 → 8.0.4), 2026-08-25.

## Prerequisites

- A running XP 8 dev container with the app under test deployed to `$XP_HOME/deploy`.
- Ability to build and deploy a **second, throwaway** app. Keep it outside the repo
  (a scratchpad dir) — it is test scaffolding, not a deliverable.

## Procedure

### 1. Make Jetty reachable from outside the container

XP 8 dev mode binds Jetty to loopback (`Listening on [127.0.0.1:8080]`), so a published Docker
port reaches nothing. In `docker/dev/xp-home/config/com.enonic.xp.web.jetty.cfg`:

```properties
host = 0.0.0.0
```

Symptom without it: container healthy, logs clean, every `curl` returns exit 7 / http 000.

### 2. Fix `xp.suPassword` before you need to log in

XP 8 **dropped plaintext** (and md5/sha1) `xp.suPassword`. A carried-over XP 7
`system.properties` with `xp.suPassword = password` yields `Access Denied` on every login and a
login page offering "Create Admin User" (i.e. looks like *no user exists*). Use sha256/sha512:

```properties
# sha512 of "password" - dev only
xp.suPassword = {sha512}b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb980b1d7785e5976ec049b46df5f1326af5a2ea6d103fd07c95385ffab0cacbc86
```

### 3. Build a throwaway host app that supplies what the app under test lacks

A cookie/analytics-style site app usually ships no **page**, so nothing can render it. The host app
needs, at minimum:

- `cms/site.yaml` — **required**, even if empty (`kind: "Site"`). Without a site descriptor the app
  cannot be added to a site's `siteConfig` at all: `IllegalArgumentException: Unknown site
  descriptor: <appKey>`.
- `cms/pages/main/main.yaml` with `regions:` as a **list of strings** (see the regions correction in
  `manual-schemes-migration.md` — the object form silently breaks `portal.getContent()`).
- `webapp/webapp.yaml` + `webapp.js` to bootstrap content programmatically.

Includes needed for the bootstrap: `xplibs.portal`, `xplibs.content`, `xplibs.context`,
`xplibs.node`, `xplibs.project`, `xplibs.auth`.

### 4. Render regions with comment placeholders, not `data-portal-region`

`data-portal-region="main"` is **only** a page-editor marker. An empty region div renders empty
forever. XP 8 renders components from HTML **comment placeholders**:

```javascript
var content = portal.getContent()
var region = content.page.regions.main || { components: [] }
var placeholders = region.components
	.map(function (c) { return '<!--# COMPONENT ' + c.path + ' -->' })
	.join('\n')
```

This cost the most time to find: the page returned 200 with a correct-looking empty
`<div data-portal-region="main"></div>` and no error anywhere.

### 5. Bootstrap the project, site and page from the webapp

```javascript
// project first - com.enonic.cms.default does not exist until something creates it.
// Without Content Studio, nothing has.
projectLib.create({ id: 'default', displayName: 'Default', publicRead: true })  // in system-repo/master, role:system.admin

// then, in context repository 'com.enonic.cms.default' branch 'draft':
contentLib.create({ name: 'mysite', parentPath: '/', contentType: 'portal:site',
	data: { siteConfig: [ { applicationKey: '<app under test>', config: { ... } },
	                      { applicationKey: '<host app>', config: {} } ] } })
```

Then attach the page via `contentLib.update` (`modify` is deprecated in XP 8):

```javascript
c.page = {
	type: 'page', descriptor: '<host>:main', config: {}, path: '/',
	regions: { main: { name: 'main', components: [
		{ type: 'part', path: '/main/0', descriptor: '<app>:<part>', config: {} },
		{ type: 'text', path: '/main/1', text: '<p>[<macroname>/]</p>' }
	] } }
}
```

The `text` component is how you exercise a **macro** without an HtmlArea field.
`portal.processHtml({ value: '<p>[macro/]</p>' })` works too, and is a useful cross-check.

### 6. Publish: set workflow READY at *node* level

`contentLib.publish` fails with `reason: "NOT_READY"` while workflow state is `IN_PROGRESS`, and
**`contentLib.update` resets workflow to `IN_PROGRESS` as a side effect of any edit** — so setting
`c.workflow` inside the same editor never sticks. Drop to `lib-node`:

```javascript
var repo = nodeLib.connect({ repoId: 'com.enonic.cms.default', branch: 'draft' })
var n = repo.get('/content/mysite/testpage')
repo.modify({ key: n._id, editor: function (x) { x.workflow = { state: 'READY' }; return x } })
```

Note the node path is prefixed with `/content`.

### 7. Reach the webapp — vhost rewrites `/webapp` away

A dev `com.enonic.xp.web.vhost.cfg` with `mapping.site.source = /` swallows `/webapp/...` and
rewrites it into the CMS repo, giving a confusing
`Repository with id [com.enonic.cms.default] not found`. Either add a `/webapp` mapping or
temporarily set `enabled = false`. **Restore it afterwards** — it is a repo file.

### 8. Assert on the live URL

`/site/<project>/master/<site>/<page>` renders with `req.mode === 'live'`. Echo `req.mode` into the
page body so the assertion is explicit rather than assumed.

## What you can and cannot prove this way

| Check | Provable | How |
|---|---|---|
| Response processor injects page contributions in `live` | yes | live URL, assert on `<head>` |
| Processor's negative branch (no config → no injection) | yes | flip `siteConfig`, republish, re-fetch |
| Part renders / renders fallback | yes | component placeholder in a region |
| Macro renders | yes | `text` component and/or `processHtml` |
| Thymeleaf major-version upgrade output | yes | inspect emitted attributes in the live HTML |
| Site config form **accepts** fields | yes | values round-trip into `portal.getSite().data.siteConfig` |
| Site config form **displays** labels/help-text | **no** | needs Content Studio |
| `preview` / `edit` / `inline` modes | **no** | Content Studio-owned routes in XP 8 |

An undeclared `siteConfig` property is a hard error, not a silent drop:
`IllegalArgumentException: No mapping defined for property <name> with value <v>`. That is a cheap
positive proof that the form in `cms/cms.yaml` is live and authoritative.

## Pitfalls

- **Redeploy churn OOM-kills the container.** Each `docker cp` into `deploy/` installs a new OSGi
  bundle; after ~120 bundles the JVM died with exit 137. Batch your edits, and expect one restart.
  Content survives in the named volume.
- Don't chase `key can not be empty` in your page data — it is almost always the `regions:`
  descriptor shape (step 3).
- `lib-content.get({key:'/'})` returns `null` on XP 8 by design; the project root is reserved. Only
  address named paths.
- Basic auth (`curl -u su:password`) is **not** accepted for `/admin`. Log in via `lib-auth.login`
  in your throwaway webapp and reuse the `JSESSIONID` cookie.
- Delete the throwaway app's jar from `deploy/` when done, or document that the sandbox's site
  references an app that is no longer built.
