---
id: how-to-smoke-test-an-xp8-admin-extension-without-content-studio
when_skills: [run-plan, upgrade-xp-app]
read: section
prose: caveman-lite
---

# How to smoke-test an XP 8 admin extension without Content Studio

Sibling of
[implementation/How-to-verify-an-xp8-site-app-at-runtime-without-content-studio.md](../implementation/How-to-verify-an-xp8-site-app-at-runtime-without-content-studio.md),
which covers **site** apps. This one covers `kind: "AdminExtension"` — context panels, custom
selectors, dashboard widgets — the XP 8 successors to `admin/widgets/`.

## Scope

You migrated an XP 7 widget to an XP 8 admin extension and need to prove the router, the
lib-static asset pipeline, the i18n threading and the action endpoints actually respond. Content
Studio is a separate Market app and is not installed on a bare dev container, so the extension's
normal host tool does not exist.

Verified on `automatic-translation-app` (XP 8.0.4, 2026-09-02).

## The blocker

An extension is only reachable through a host admin tool's `admin:extension` dispatcher, and only
when the interfaces match (`web/extensions.md`, "Extension URL"):

- the host tool's descriptor must list `"admin:extension"` in `apis:`
- unless the extension declares `interfaces: ["generic"]`, one of its interfaces must also appear
  in the host tool's `interfaces:` — otherwise **404**

Content Studio is the host that publishes `contentstudio.contextpanel` /
`contentstudio.customselector`, and you cannot edit its descriptor.

## Procedure

Temporarily borrow your **own** admin tool as the host. Two lines, then revert.

### 1. Add the dispatcher and the interface to your tool descriptor

```yaml
kind: "AdminTool"
title: "My Tool"
allow:
  - "role:system.admin"
apis:
  - "asset"
  - "admin:extension"     # <- temporary
interfaces:               # <- temporary
  - "contentstudio.contextpanel"
  - "contentstudio.customselector"
```

### 2. Rebuild and hot-deploy into the running container

```sh
docker exec <app> sh -c "(cd /enonic-xp/source && ./gradlew build -q)"
docker exec <app> sh -c "cp /enonic-xp/source/build/libs/*.jar /enonic-xp/home/deploy/"
sleep 15   # watch for "Started application <key> bundle N"
```

### 3. Hit the dispatcher URL

```
/admin/<appKey>/<toolName>/_/admin:extension/<appKey>:<extensionName>
```

Basic auth is rejected on `/admin` in XP 8, so drive it from a logged-in browser session
(`playwright-cli`) and call `fetch` from the page rather than curl:

```sh
playwright-cli -s=x open http://localhost:8080/admin      # log in as su via the form
playwright-cli -s=x --raw eval "fetch('<url>').then(r=>r.text().then(t=>r.status+' :: '+t))"
```

### 4. Assert the three things a green build cannot prove

| Check | How |
|---|---|
| Controller parses and runs | 200 and real HTML, not a `RuntimeException` about the script |
| lib-static serves the bundle | `GET <url>/_static/css/app.css` returns the file, 200 |
| Asset + action URLs are right | grep the returned HTML for `_static/` and your router subpaths |
| i18n came from `req.locales` | translated strings present instead of raw keys |
| A POST action responds | `FormData` / JSON `fetch` to `<url>/<subpath>`; assert the negative case (400) |

### 5. Revert the descriptor and redeploy

Restore the tool YAML, rebuild, redeploy, and confirm the extension URL now returns **404** from
your tool — that is the proof the temporary mount is gone, not a regression.

```sh
playwright-cli -s=x --raw eval "fetch('<url>').then(r=>r.status)"   # expect 404
```

## What this cannot prove

- Shadow-DOM behaviour: the web component is Content Studio's, so CSS isolation, whether an
  **external** script is panel-scoped, and the panel dropdown are all out of reach. Write the
  client script to work either way (resolve `document.currentScript.getRootNode()` once and query
  from it) instead of waiting for the answer.
- The `contentId` / `repo` / `branch` params Content Studio actually sends. Log
  `JSON.stringify(req.params)` and the `Referer` header from the extension so the answer lands in
  `server.log` the first time someone does run it under Content Studio.
- Anything needing real content, a third-party API key, or a valid license file.

## Pitfalls

- The base URL matches; a **trailing slash** does not, if the route is `router.get('', …)`.
  Test both.
- `com.enonic.cms.default` does not exist on a bare container — nothing creates it without
  Content Studio. An extension that resolves site config will fail there with
  `RepositoryNotFoundException`. That is the environment, not the code; assert on the degraded
  path instead.
- Each hot-deploy installs a new OSGi bundle. Batch edits; ~120 redeploys OOM-kills the JVM.
