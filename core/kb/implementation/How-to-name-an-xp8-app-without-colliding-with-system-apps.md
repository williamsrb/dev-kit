---
id: how-to-name-an-xp8-app-without-colliding-with-system-apps
when_skills: [run-plan]
read: section
prose: caveman-lite
---

# How to name an XP 8 app without colliding with a system app

`appName` in `gradle.properties` becomes the jar's `Bundle-SymbolicName`, and XP derives
`ApplicationKey` from that name. Reusing a shipped system app's name does **not** shadow it — it
destroys it. Verified against `xp` `v8.0.4` (commit `76e1806d30ee`).

## Scope

Any decision to name (or rename) an XP 8 application, especially when the intent is "replace" or
"override" a shipped admin tool.

## The five system apps in the 8.0.4 distro

`~/.enonic/distributions/enonic-xp-linux-sdk-8.0.4/system/40/`:

| Jar | `Bundle-SymbolicName` |
|---|---|
| `app-applications-8.0.4.jar` | `com.enonic.xp.app.applications` |
| `app-main-8.0.4.jar` | `com.enonic.xp.app.main` |
| `app-sdk-8.0.4.jar` | `com.enonic.xp.app.sdk` |
| `app-standardidprovider-8.0.4.jar` | `com.enonic.xp.app.standardidprovider` |
| `app-users-8.0.4.jar` | `com.enonic.xp.app.users` |

Read the name with `unzip -p <jar> META-INF/MANIFEST.MF | grep Bundle-SymbolicName`.

## Why the collision is destructive

1. `ApplicationRegistryImpl.install()` — for a key already in the registry it calls
   `doUninstall(existingApp)` **first**, then `context.installBundle(...)`. Replace, not shadow. The
   registry is a `ConcurrentMap<ApplicationKey, ApplicationAdaptor>`; system apps land in it via
   `configure()` when their bundles start.
2. `doInstallLocalApplication` (the `$XP_HOME/deploy` path used by `./gradlew deploy`) has **no
   system-app guard at all**. The `Cannot install system application globally` check in
   `doInstallGlobalApplication` inspects the **incoming** jar's `X-Bundle-Type` header, not the
   incumbent at that key — so a normal app (`X-Bundle-Type: application`) sails through.
3. **It is not restorable.** `ProvisionActivator.doStart()` provisions `system/` only when
   `context.getBundles().length == 1`, i.e. a fresh Felix cache. `uninstallLocalApplication` calls
   `doReinstallStoredApplication`, which reads the app repo — and `doInstallStoredApplication`
   rejects stored system apps, so they are never there. Removing your jar leaves the key empty and
   the shipped tool gone until the sandbox/instance bundle cache is wiped.

OSGi itself would permit both bundles (same BSN, different `Bundle-Version`); it is XP's own
key-indexed registry that forces the eviction.

## Procedure

1. Never set `appName` to a value in the table above, or to any `com.enonic.xp.*` name.
2. Use the vendor namespace already in the workspace. `logviewer` convention:

   ```properties
   group = io.x99.app
   projectName = applications
   appName = io.x99.app.applications
   ```

   `appName` = `group` + `.` + `projectName`. The app key appears in every admin tool URL
   (`/admin/<appName>/<toolName>`), so changing it later breaks bookmarks and any recorded evidence.
3. To supplement a shipped tool, ship a **second** tool under your own key. There is no supported
   override mechanism; the shipped tool stays visible.

## Pitfalls

- A repo directory named `applications-app` is not a reason to name the app
  `com.enonic.xp.app.applications`. Repo name and `appName` are unrelated.
- The failure is silent. Nothing in `server.log` says "you just evicted a system app" — you get the
  ordinary `Installed application <key> bundle <n>` line, and the shipped tool simply vanishes from
  the admin menu.
- Also applies in reverse: two of your own apps sharing an `appName` will evict each other.

See [[How-to-build-an-xp8-admin-tool-over-the-server-app-api]] for the tool that motivated this.
