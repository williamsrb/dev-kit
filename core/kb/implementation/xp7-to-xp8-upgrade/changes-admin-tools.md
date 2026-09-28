---
id: xp7-to-xp8-changes-admin-tools
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

### Admin tools

> Also handled by `xp8migrator`. The hand-edit shape below matters for review (and for fixes the migrator may not auto-apply, like the
> system-API list).

`src/main/resources/admin/tools/<name>/<name>.xml` → `<name>.yaml`.

```yaml
kind: "AdminTool"
title:
  text: "My Dashboard"
  i18n: "admin.tool.dashboard.title"
description:
  text: "Application dashboard"
  i18n: "admin.tool.dashboard.description"
allow:
  - "role:system.admin"
apis:
  - "admin:extension"   # always include — replaces admin:widget
  - "admin:event"
  - "admin:status"
  # plus any custom APIs this tool calls
```

Two gotchas:

1. **`title` and `description` accept either a plain string or a `{ text, i18n }` object.** Use the object form when the XP 7 XML carried an
   `i18n=` attribute worth preserving. *(Corrected 2026-08-24: an earlier revision of this file claimed plain strings NPE in
   `AdminToolMapper`. Disproved on XP 8.0.4 — the `logviewer` and `forwarding` admin tools both ship plain-string `title:`/`description:`
   and load fine. Do not rewrite a working plain string on the strength of that claim.)*
2. **`apis:` is strictly enforced.** A tool can only call APIs it declares — calls to undeclared APIs fail at runtime with
   `API [<app>:<name>] is not mounted`. List every API the tool talks to, including the system APIs (`admin:extension`, `admin:event`,
   `admin:status`). For APIs contributed by an `include`d lib (e.g. `lib-asset`'s `asset` API), use the **bare name** (`"asset"`) —
   the lib's `apis/` are merged into your JAR at build time and mount under your app's key, not the lib's. Confirm with
   `unzip -l build/libs/<app-name>.jar | grep apis/`.

In XP 8 every admin tool is shown on the launcher menu. If you have a tool that should *not* appear there, convert it to an API instead (
move `admin/tools/<name>/` to `apis/<name>/`).

In admin tool **controllers**:

- `portalLib.assetUrl`, `widgetUrl`, etc. work the same.
- The admin lib lost `getAssetsUri()`, `getBaseUri()`, `getLauncherPath()`. Replace with `extensionUrl({ application, extension })` and
  `getHomeToolUrl()`.
- **Confirm against the source for your pinned version before editing.** On current `master` the only `/lib/xp/admin` exports are
  `getToolUrl`, `getHomeToolUrl`, `getInstallation`, `getVersion`, `widgetUrl` (deprecated), and `extensionUrl` — `getLauncherUrl()` is
  gone, and the launcher script is no longer injected at all. Treat that as illustrative and verify against the `lib-admin` source **at the
  tag matching your `xpVersion`** (`…/modules/lib/lib-admin/src/main/resources/lib/xp/admin.ts`), not `master`. The same applies to other
  libs (`lib-portal`, `lib-content`, etc.) — see <https://github.com/enonic/xp/tree/master/modules/lib/>.
- The default Admin Home path is now `/admin` (was `/admin/home`).

In admin tool **HTML templates** (Mustache/Thymeleaf): the launcher script is no longer injected — replace the old launcher include with a
`widgetUrl()` call, and deliver tool config as inline JSON instead of a service fetch.
