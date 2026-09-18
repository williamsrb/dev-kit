# Detect, inventory, and plan

### 1. Detect

First, **check the Enonic CLI is present** — read-only, install nothing yet:

```sh
command -v enonic && enonic --version
```

If it's absent, note it for the Plan (step 3) — installing it is a plan item, not something you do here (see Knowledge base / How-to-run-xp8migrator).
Then read these to understand the app:

- `gradle.properties` — current `xpVersion`, `appName`, `appDisplayName`, `vendorName`, `vendorUrl`, `projectName`, `version`
- `settings.gradle` — does it declare `com.enonic.xp.settings`? If absent, the upgrade adds it (this plugin is the central XP 8 plumbing)
- `build.gradle` — current `com.enonic.xp.app` plugin version (pinned in XP 7, versionless in XP 8), the `app{}` block contents (XP 7 wires
  metadata here; XP 8 leaves it empty), how `com.enonic.xp:lib-*` deps are written (XP 7 long-form vs. XP 8 `xplibs.*` aliases)
- `gradle/wrapper/gradle-wrapper.properties` — Gradle version (must be 9.x for plugin 4.x)
- `src/main/resources/application.xml` (XP 7) or `enonic.yaml` (already XP 8)
- `src/main/resources/site/` — if present, this is a site app. The whole tree migrates to `cms/` (see
  `~/.agents/kb/implementation/xp7-to-xp8-upgrade/manual-schemes-migration.md`).
- `src/main/resources/webapp/` — if present, includes a webapp
- `src/main/resources/admin/tools/`, `admin/widgets/` — admin surface (widgets become `admin/extensions/` in XP 8)
- `src/main/resources/apis/`, `services/`, `tasks/` — HTTP endpoints / background tasks
- `src/main/resources/idprovider/` — ID provider (rare)
- `src/main/resources/cms/` — already partially migrated? If both `site/` and `cms/` are present, the migration is incomplete.
- **Stray descriptors outside the above locations.** Run
  `find src/main/resources -name '*.xml' -not -path '*/site/*' -not -path '*/admin/*' -not -path '*/apis/*' -not -path '*/services/*' -not -path '*/tasks/*' -not -path '*/webapp/*' -not -path '*/idprovider/*' -not -path '*/import/*' -not -name 'application.xml'`.
  Files like `lib/<name>/<name>.xml` (Page descriptors stashed inside `lib/`) are silently skipped by `xp8migrator` and stay as XP 7 XML in
  the upgraded app. Surface any hits to the user during the plan step — choices are: (a) delete if vestigial, (b) move to the appropriate
  standard location and re-run the migrator, (c) hand-convert in place.

Don't assume only one of these. A single app can be all three (site app + admin tool + webapp).

### 2. Inventory

Build a list of every file that needs to change. Group by category — the user will scan this in step 3, and a flat dump of 50 file paths is
unreadable. Categories:

| Category        | What to look for                                                                                                                                                                  |
|-----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Settings plugin | `settings.gradle` — needs `com.enonic.xp.settings` plugin in XP 8 (drives every other build-file change)                                                                          |
| Build           | `gradle.properties`, `build.gradle` (plugin pin, `app{}` block, dependency form), `gradle/wrapper/gradle-wrapper.properties` (Gradle version), `package.json` (`@enonic-types/*`) |
| App descriptor  | `src/main/resources/application.xml`                                                                                                                                              |
| Site → CMS      | `src/main/resources/site/**/*.xml` — the entire tree relocates to `cms/` (`site.xml`, `styles.xml`, parts, layouts, pages, content-types, mixins, x-data, macros, form-fragments) |
| Admin tools     | `src/main/resources/admin/tools/*/*.xml`                                                                                                                                          |
| Admin widgets   | `src/main/resources/admin/widgets/*/*.xml` (renamed to `admin/extensions/` in XP 8)                                                                                               |
| Services        | `src/main/resources/services/*/*.xml` (descriptors migrate to YAML; `kind: "Service"`)                                                                                            |
| APIs            | `src/main/resources/apis/*/*.xml` (rare in XP 7)                                                                                                                                  |
| Tasks           | `src/main/resources/tasks/*/*.xml`                                                                                                                                                |
| Webapp          | `src/main/resources/webapp/webapp.xml` (if present)                                                                                                                               |
| ID provider     | `src/main/resources/idprovider/idprovider.xml` (if present)                                                                                                                       |
| Server config   | `logback.xml` anywhere in the project                                                                                                                                             |
| Code            | controllers using removed admin URL helpers, services that should migrate to APIs                                                                                                 |
| Cleanup         | leftover `src/main/resources/site/` after a successful migrator run (it leaves orphan `.js`/`.svg` files behind)                                                                  |

### 3. Plan

Present the plan as a numbered checklist grouped by category. For each item state **what** changes and **why** in one line. Then ask the
user to approve, modify, or skip individual items. Wait for explicit approval before any write.

The user can grant approval up-front in the same turn as the original request (e.g. "show plan then apply", "go ahead and fix it", "do
whatever it takes"). Treat that as approval — show the plan and proceed straight into execution. Pause for a fresh confirmation only when
the request was open-ended ("what do I need to change?", "can you upgrade this?") without an explicit "go ahead".

If Detect found the Enonic CLI missing, make **installing it the first plan item** (`npm install -g @enonic/cli`, or a platform fallback
from How-to-run-xp8migrator) — it's needed for the Validate and Deploy steps. Present it for approval like any other change; don't
pre-install it.

Example shape:

```
## XP 7 → XP 8 upgrade plan for <app-name>

Detected: JS site app, xpVersion 7.9.0, plugin 3.6.2, no settings plugin, `app{}` block has explicit name/displayName/vendor wiring, dependencies use long-form `com.enonic.xp:lib-*:${xpVersion}` coordinates, Gradle wrapper 8.5, no admin tools. Enonic CLI not found on PATH.

### Tooling (only if the Enonic CLI is missing)
0. Install the Enonic CLI — `npm install -g @enonic/cli` (or a platform fallback). Required for `enonic project build`/`deploy`; it's a machine-level dev tool that stays installed afterward.

### Build system (settings plugin + catalog)
1. `settings.gradle` — add the XP 8 settings plugin: `id("com.enonic.xp.settings") version "<latest>"`. This is the centerpiece of the XP 8 build; it supplies the `com.enonic.xp.app` plugin version and the `xplibs.*` catalog. Pick the latest released version (alpha/beta releases like `4.0.0-A3` / `4.0.0-B1` are fine — do not use `-SNAPSHOT`).
2. `build.gradle` — drop the `version '3.6.2'` pin from `id 'com.enonic.xp.app'`; in XP 8 the version is supplied by the settings plugin.
3. `build.gradle` — omit the `app { }` block (the verified XP 8 reference apps don't carry it). Keep `app { createDefaultDevTask = false }` only if the project's `dev` task differs from the plugin default (which runs `deploy --continuous -Penv=dev`) — e.g. a real `NpmTask` watch. If the existing `dev` task just reproduces the default, drop it and use the auto-registered one (see "Build files").
4. `build.gradle` — migrate Enonic library dependencies from `"com.enonic.xp:lib-X:${xpVersion}"` to `xplibs.X`. **Pure 1:1 rename — migrate every `include` as-is; never drop one as "unused" (XP `include`s aren't transitive, so app-source greps can't prove a dep unused; pruning is out of scope — see "Build files").**
5. `gradle/libs.versions.toml` (new file) — extract third-party `com.enonic.lib:*` deps (e.g. `lib-thymeleaf`, `lib-xslt`, `lib-asset`, `lib-static`) into a Gradle version catalog, and reference them as `libs.<alias>` in `build.gradle`. Skip if the app has zero or one such dep.
6. `gradle.properties` — bump `xpVersion` to the highest XP 8 version available (prefer stable; fall back to alpha/beta like `8.0.0-A3` / `8.0.0-B1`; `-SNAPSHOT` only as a last resort). Add `projectName` if missing (used by `settings.gradle`); leave `appName`/`version`/`group` in place. Display/vendor metadata moves to `enonic.yaml` (see *Application descriptor*).
7. `gradle/wrapper/gradle-wrapper.properties` — bump Gradle to 9.4.1 (plugin 4.x requires Gradle 9+). Run via `./gradlew wrapper --gradle-version 9.4.1`.

### Descriptors (run xp8migrator)
8. `src/main/resources/application.xml` → `enonic.yaml` (`kind: "Application"`, plus `title`/`vendorName`/`vendorUrl` imported from `gradle.properties`)
9. `src/main/resources/site/` → `src/main/resources/cms/` — the migrator splits `site.xml` between `cms/site.yaml` and `cms/cms.yaml`, moves `styles.xml` to `cms/style/style.yaml`, renames `x-data/` to `mixins/`, and converts every part/layout/page/content-type/macro to YAML with the right `kind:`. ~16 files touched.

### Validation
10. Run `enonic project build -f` — must pass before any file deletion. If it fails, the originals in `site/` and `application.xml` are still in place for diagnosis.

### Cleanup (only after the build is green)
11. Delete the originals: `rm -rf src/main/resources/site`, `rm src/main/resources/application.xml`, `rm ./migrator` (rationale in the Cleanup step).
12. Remove the duplicate `cms/styles/image.yaml` if the migrator emitted one (see the Cleanup step).
13. Optionally deploy — pick the sandbox and run mode *with the user* (see the Deploy step).

OK to proceed? Reply "go" to apply all, or list the numbers to skip.
```
