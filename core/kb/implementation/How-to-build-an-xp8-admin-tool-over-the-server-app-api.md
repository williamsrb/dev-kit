---
id: how-to-build-an-xp8-admin-tool-over-the-server-app-api
when_skills: [run-plan]
read: section
prose: caveman-lite
---

# How to build an XP 8 admin tool over the `server:app` API

Mount the platform's own Applications API in your own admin tool instead of reimplementing install /
start / stop / uninstall. Confirmed against `xp` `v8.0.4` (commit `76e1806d30ee`) and built as
`io.x99.app.applications`.

## Scope

Any XP 8 admin tool that must manage installed applications. Also the reference for the endpoint
paths and JSON shapes, which are **not** in the public docs — `server:app` is a `@Component`
property key, not a versioned contract. Re-verify on every XP upgrade.

## Prerequisites

- `xpVersion = 8.0.4` pinned in `gradle.properties`.
- Tool descriptor lists the API under `apis:` and `role:system.admin` under `allow:`.
- Runtime deps: `xplibs.portal`, `libs.lib.asset`, `libs.lib.mustache`. No Java, no `xplibs.auth`.

## Procedure

1. **Mount it.** `mount=management` on the API does *not* block admin-tool use.
   `SlashApiHandler.verifyRequestMounted` switches on mount context: the `CONNECTOR` case checks
   `apiDescriptor.getMount()`, the `ADMIN_TOOL` case checks only
   `mountContext.adminTool().getApiMounts().contains(descriptorKey)`. Listing it is sufficient:

   ```yaml
   kind: "AdminTool"
   allow:
     - "role:system.admin"
   apis:
     - "asset"
     - "server:app"
   ```

   Reachable at `/admin/<app-key>/<tool-name>/_/server:app/<path>`.

2. **Build URLs in the controller**, one per endpoint:
   `portal.apiUrl({api: 'server:app', path: 'installUrl'})`.

3. **Endpoints** (`ApplicationApiHandler.handle`, dispatch switch). All POST except `/events`:

   | Path | Body | Response |
   |---|---|---|
   | `GET /events` | — | SSE |
   | `/install` | multipart, item name **`file`** | `ApplicationInfoJson` |
   | `/installUrl` | `{"URL": "...", "sha512": "..."}` | `ApplicationInfoJson` |
   | `/start` `/stop` `/uninstall` | `{"key": ["app.key", ...]}` | `{"results":[{"id":…,"success":…}]}` |

4. **Three shape traps.**
   - `installUrl` takes **uppercase `URL`** (`@JsonProperty("URL")` on `ApplicationInstallParams`).
     A bare string is accepted for `key` too, via `ACCEPT_SINGLE_VALUE_AS_ARRAY`.
   - Action results are keyed by **`id`**, not `key`, and a failure returns **HTTP 200** with
     `success: false`. Read the body, never the status.
   - `install` / `installUrl` return `ApplicationInfoJson` whose display field is **`title`**; the
     SSE list returns `ApplicationJson` whose display field is **`displayName`**. Same data,
     different property name.

5. **SSE, not polling.** There is no list endpoint. On `SseEventType.OPEN` the handler joins the
   client to group `server:app:events` and sends **one event named `list`** carrying
   `{"applications":[…]}`. After that it forwards `installed` / `state` / `uninstalled`, each
   carrying a single app (`uninstalled` carries only `{"key":…}`). `state` is `"started"` /
   `"stopped"`.

6. **Inherit the two install gates**, do not reimplement them. pid
   `com.enonic.xp.server.management.app` (`AppManagementConfig`) declares exactly two properties:

   | Property | Default | Violation |
   |---|---|---|
   | `installUrl.allowedUrls` | `https://*` | **409** `URL is not in the installUrl allowlist` |
   | `installUrl.checksumRequired` | `true` | **409** `SHA512 checksum is required for installUrl` |

   Malformed checksum → **400** `Invalid SHA512 checksum`; mismatch → **400**
   `Checksum validation failed`. An empty `allowedUrls` disables `/installUrl` entirely. Surface
   these bodies **verbatim** — they are the user's only explanation. Going through a Java
   `ScriptBean` on `ApplicationService` bypasses all of them.

   Two operational facts about this pid:

   - **Your app cannot set it.** It is a platform pid, not the app's own
     `<appName>.cfg`, so `app.config` never reaches it. The most a repo can ship is a sample
     `com.enonic.xp.server.management.app.cfg` for an operator to copy into `$XP_HOME/config/`.
   - **No restart needed.** `ApplicationResourceService.activate(AppManagementConfig)` is annotated
     `@Activate @Modified`, so a config change re-runs it and rebuilds the `ApplicationLoader` in
     place.

   `checksumRequired = true` makes a paste-a-URL form unusable without a hand-computed
   `sha512sum`, which is the usual reason to turn it off. Treat the two properties as a pair: once
   the checksum is off, `allowedUrls` is the only gate, and `https://*` with `checksumRequired =
   false` lets any system admin install arbitrary unverified code from anywhere.

7. **Authorization is in the descriptors, not the service.** `installGlobalApplication` has no role
   check of its own; `requireSchemaAdminRole()` guards a virtual-app method, not install. Access is
   gated three times: `role:system.admin.login` to reach the admin service, the tool's `allow:`
   list, then the API's own `allowedPrincipals=role:system.admin`. A narrower role in `allow:`
   passes the tool and then fails the API with 403 — so `role:system.admin` is forced.

8. **Escape the config blob** with the same transform the shipped tool uses, before embedding it in
   `<script type="application/json">`:

   ```js
   JSON.stringify(cfg, null, 4).replace(/<(\/?script|!--)/gi, '\\u003C$1')
   ```

## Pitfalls

- **JDK 17 cannot build XP 8.** `com.enonic.xp.settings` 4.1.0 pulls
  `com.enonic.gradle:xp-gradle-plugin:4.1.0`, which requires JVM 21+. On a Java 17 default the
  failure reads `Could not resolve com.enonic.gradle:xp-gradle-plugin:4.1.0` — a resolution error,
  not a version error, so it looks like a repository problem. Fix:
  `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew build`.
- **Hide Uninstall for local apps.** `ApplicationServiceImpl.uninstallApplication` throws outright
  for a key in `localApplicationSet` (anything installed from `$XP_HOME/deploy`), so the action can
  only ever return `success: false`. `ApplicationJson` exposes `local` — use it.
- **No progress bar is possible through this API.** `ApplicationLoader` publishes `application` /
  `PROGRESS` events with `applicationUrl` and `progress`, but `ApplicationApiHandler.onEvent`
  filters on `application.cluster` only, so they never reach the `server:app` SSE group. You would
  have to also mount `admin:event`.
- **Cluster SSE scope is unverified.** `onEvent` also filters on `event.isLocalOrigin()`. Whether an
  install on another node reaches this node's stream was not tested, and single-node validation will
  not surface it.
- **Do not reuse `UploaderEl`** on XP 8.0.4 — see the F1a note below. A plain `<input type="file">`
  posting `FormData` to `/install` avoids the whole problem.

## XP 8.0.4 admin UI regression (F1a)

`$.camelCase is not a function` kills every `.simulate()` call in the 8.0.4 admin bundle. jQuery
dropped `jQuery.camelCase` from its public API in 3.5.0; 7.16.2 shipped a jquery-migrate block that
re-exposed the internal one, and 8.0.4 dropped that block while keeping the old jquery-simulate.
Three dead call sites: `UploaderEl.showFileSelectionDialog` (the Applications upload button and its
Space handler), `UploaderEl.handleKeyEvents` (Enter on the dropzone), and `Button.triggerAction`
(keyboard activation of buttons **across the admin UI**).

Not patchable at runtime: the bundle calls `jQueryFactory(window, !0)` — `noGlobal` is set and
nothing assigns `window.jQuery`. The fix belongs in `enonic/app-applications`, a system app.

Unaffected: URL + **Enter** in the Applications install input (`initUrlEnteredHandler` →
`installWithUrl`), and drag & drop onto `InstallAppDialog`'s own dropzone (code-plausible, untested).

## Verification pitfall

**An unauthenticated `curl` cannot prove an admin tool is mounted.** The admin auth filter runs
before tool resolution, so a nonexistent tool name returns the same **401** as a real one:

```
/admin/io.x99.app.applications/appinstaller     -> 401
/admin/io.x99.app.applications/nosuchtool       -> 401
```

Positive deploy evidence without credentials is limited to `server.log`:

```
ApplicationRegistryImpl  - Installed application <key> bundle <n>
ApplicationServiceImpl   - Local application [<key>] installed successfully
ApplicationRegistryImpl  - Started application <key> bundle <n>
ApplicationRegistryImpl  - Configuring application <key> bundle <n>
```

Descriptor errors surface lazily on first request, so a clean install log does **not** prove the
descriptor is valid. Anything past that needs a session cookie — and `xp.suPassword is not set` in a
sandbox means there is none to obtain. See
[[How-to-verify-an-xp8-site-app-at-runtime-without-content-studio]] for the login flow.
