---
id: xp7-to-xp8-changes-build-files
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

### Build files

> See `references/examples.md` for the full `xplibs.*` alias tables (every `com.enonic.xp:` library and API), worked `build.gradle`
> examples (site app with version catalog; TS app with custom `dev` task), and TypeScript wiring.

The XP 8 build is reorganized around the **`com.enonic.xp.settings` Gradle settings plugin**. Once it's in place, it supplies the
`com.enonic.xp.app` plugin version and the `xplibs.*` dependency catalog — both of which used to be set in the app's `build.gradle`. The
upgrade therefore *adds* lines to `settings.gradle` and *removes* lines from `build.gradle`.

**`settings.gradle`** — declare the settings plugin:

```diff
+plugins {
+    id( "com.enonic.xp.settings" ) version "<latest>"
+}
+
 rootProject.name = projectName
```

Pick the **latest released** 4.x version of the plugin (alpha/beta releases such as `4.0.0-A3` or `4.0.0-B1` are fine; do **not** use a
`-SNAPSHOT` suffix). The settings plugin and `com.enonic.xp.app` plugin ship together (the settings plugin supplies the app-plugin version),
but they do not track the XP runtime version — see the next paragraph.

**Verify the settings plugin version is actually published before pinning it.** The settings plugin's release cadence does NOT track XP's —
its `4.0.x` numbering is independent of `xpVersion=8.0.x`, and not every XP release ships with a matching settings plugin to the Gradle
plugin portal. Picking `4.0.0-B4` because `xpVersion=8.0.0-B4` will fail with
`Plugin [...] was not found ... could not resolve plugin artifact` if only `4.0.0-A3` / `4.0.0-B1` are live on plugins.gradle.org. Check
before committing to a version:

```sh
curl -s 'https://plugins.gradle.org/m2/com/enonic/xp/settings/com.enonic.xp.settings.gradle.plugin/' | grep -oE 'href="[^"]+/"'
```

Use the highest version that listing actually shows; it may lag the XP runtime version by one or more releases.

**`build.gradle`** — independent edits (the first three are driven by the settings plugin; the last by the Gradle 9 bump):

1. **Drop the version pin** on `com.enonic.xp.app`:

   ```diff
    plugins {
   -    id 'com.enonic.xp.app' version '3.6.2'
   +    id 'com.enonic.xp.app'
    }
   ```

   The settings plugin supplies the version. Pinning it at the app level conflicts with the settings plugin and is wrong for XP 8.

2. **Strip the `app { }` block.** XP 7 wired metadata through it; XP 8 reads metadata from `enonic.yaml` (`title`, `description`,
   `vendorName`, `vendorUrl`) — see the "Application descriptor" section below:

   ```diff
    app {
   -    name = "${appName}"
   -    displayName = "${appDisplayName}"
   -    vendorName = "${vendorName}"
   -    vendorUrl = "${vendorUrl}"
   -    systemVersion = "${xpVersion}"
    }
   ```

   **Omit `app { }` entirely by default** (the verified XP 8 reference apps don't carry it). Leaving it empty also works.

   **Only keep `app { createDefaultDevTask = false }` when the project's `dev` task does something the plugin's default `dev` task does
   *not* — not merely because a `dev` task is present.** When `createDefaultDevTask` is left on (its default), the plugin auto-registers a
   `dev` task (`com.enonic.gradle.xp.app.DevTask`) whose whole job is to run the continuous task — by default
   `./gradlew deploy --continuous -Penv=dev` (plus `-PxpHome=…` when set), i.e. redeploy on every source change. So compare the project's
   existing `dev` task against that:
    - **Functionally equivalent** (it just runs `deploy` / the build continuously in dev mode) → it's **redundant**: delete it *and* drop
      `createDefaultDevTask = false`, letting the auto-registered default take over (the `app { }` block is then empty — remove it).
    - **Genuinely different** (e.g. an `NpmTask` running `npm run watch` to drive a TS/bundler build, which the default deploy-continuous
      task can't do) → keep it, and keep `app { createDefaultDevTask = false }` so the two don't collide.

   Read the plugin source to see exactly what the default does before deciding:
   <https://github.com/enonic/xp-gradle-plugin/blob/master/src/main/java/com/enonic/gradle/xp/app/DevTask.java>.

3. **Migrate dependencies** to the `xplibs.*` catalog. The catalog has two namespaces:
    - **APIs** (`com.enonic.xp:*-api`) → `xplibs.api.<name>` (e.g. `portal-api` → `xplibs.api.portal`, `core-api` → `xplibs.api.core`,
      `admin-api` → `xplibs.api.admin`)
    - **Libraries** (`com.enonic.xp:lib-*`) → `xplibs.<name>` (e.g. `lib-content` → `xplibs.content`)

   ```diff
    dependencies {
   -    implementation "com.enonic.xp:portal-api:${xpVersion}"
   -    include "com.enonic.xp:lib-content:${xpVersion}"
   -    include "com.enonic.xp:lib-portal:${xpVersion}"
   +    implementation xplibs.api.portal
   +    include xplibs.content
   +    include xplibs.portal
        include "com.enonic.lib:lib-thymeleaf:3.0.0-B1"
    }
   ```

   Only `com.enonic.xp:` dependencies move to the `xplibs` catalog — third-party libraries (`com.enonic.lib:lib-thymeleaf`,
   `com.enonic.lib:lib-xslt`, `com.enonic.lib:lib-asset`, `com.enonic.lib:lib-static`, etc.) keep their full Maven coordinates **or** move
   to a separate Gradle version catalog (see step 5). See `references/examples.md` for the complete `xplibs` alias tables (6 APIs + 24
   libs).

   **The dependency conversion is a pure 1:1 rename — never drop an `include` as "unused" during the upgrade.** XP `include` dependencies
   are **not transitive**: bundled third-party JS libs can `require('/lib/xp/*')` modules that the app's own source never references (e.g.
   `lib-util`'s `getLocale.js` does `require('/lib/xp/admin')`, so an app that bundles `lib-util` needs `xplibs.admin` even with zero
   `/lib/xp/admin` calls of its own). Grepping app source is therefore **not** sufficient evidence that a dep is unused — the build will
   pass and the app will fail at runtime on the first page render. Convert every `include` line as-is; if the number of `include`s changed
   between XP 7 and XP 8 (other than the API/alias rename), you pruned something — put it back. Dependency pruning is post-upgrade work,
   **out of scope for this skill**, and must only be done after a JAR-level `require` scan (see the validation step).

   **`com.enonic.lib:lib-thymeleaf` requires a version bump for XP 8.** XP 7-era apps typically pin `2.1.1`, which is not compatible with
   XP 8. Bump it to the latest released `3.x` — `3.0.0-B1` at time of writing — which is published to the **public** repo (find the current
   one with the Maven-metadata check below). Surface this in the plan whenever the app declares `lib-thymeleaf:2.1.1` (or any other 2.x). A
   released `3.x` resolves through the plain `xp.enonicRepo()` — no dev channel needed. Only if no released `3.x` exists yet, fall back to
   `3.0.0-SNAPSHOT` (dev channel only): then **replace** the existing `xp.enonicRepo()` in `repositories { … }` with
   `xp.enonicRepo( "dev" )`
   (a superset that includes releases — swap it in, don't add it alongside), and don't hand-roll a raw
   `maven { url 'https://repo.enonic.com/snapshot' }` block. Watch for the same 2.x → 3.x transition across other `com.enonic.lib:*`
   libraries during the XP 8 alpha/beta window.

   **Check released artifacts, not the lib repo's `master` branch.** A lib's `master`-branch `gradle.properties` reflects *unreleased*
   development (e.g. `xpVersion = 8.1.0-SNAPSHOT`) and says nothing about what is installable today. Determine the latest released
   XP 8-compatible version from the published Maven metadata under <https://repo.enonic.com/public/>, or from Enonic Market — never from a
   GitHub branch:

   ```sh
   curl -s 'https://repo.enonic.com/public/com/enonic/lib/<lib-name>/maven-metadata.xml' | grep -oE '<version>[^<]+</version>'
   ```

   Pick the highest version compatible with the target `xpVersion` — during the XP 8 pre-release window that is often a `-Bn` beta
   (e.g. `lib-menu` `4.2.1` → `5.0.0-B1`, `lib-urlredirect` `3.0.1` → `4.0.0-B1`). If you then need to confirm a function or API the app
   calls, read the lib's source **at the matching release tag**, not `master` — master can be one or more XP majors ahead of the newest
   installable release.

4. **Extract third-party libraries into `gradle/libs.versions.toml`** (recommended for apps with two or more `com.enonic.lib:*` deps). The
   XP 8 reference apps centralize non-`com.enonic.xp` libs in a Gradle version catalog so versions are declared once and referenced as
   `libs.<alias>` in `build.gradle`:

   ```toml
   # gradle/libs.versions.toml
   [versions]
   thymeleaf = "3.0.0-B1"
   xslt      = "2.1.1"
   asset     = "2.0.0-RC1"

   [libraries]
   lib-thymeleaf = { module = "com.enonic.lib:lib-thymeleaf", version.ref = "thymeleaf" }
   lib-xslt      = { module = "com.enonic.lib:lib-xslt",      version.ref = "xslt" }
   lib-asset     = { module = "com.enonic.lib:lib-asset",     version.ref = "asset" }
   ```

   Then in `build.gradle`:

   ```diff
    dependencies {
        include xplibs.content
        include xplibs.portal
   -    include "com.enonic.lib:lib-thymeleaf:3.0.0-B1"
   -    include "com.enonic.lib:lib-xslt:2.1.1"
   -    include "com.enonic.lib:lib-asset:2.0.0-RC1"
   +    include libs.lib.thymeleaf
   +    include libs.lib.xslt
   +    include libs.lib.asset
    }
   ```

   The catalog file lives at `gradle/libs.versions.toml` (Gradle's default location — no extra wiring in `settings.gradle` needed). Aliases
   in `[libraries]` map dotted accessors in `build.gradle` (`lib-thymeleaf` → `libs.lib.thymeleaf`). This keeps version bumps in one place
   and is the pattern verified against `app-superhero-blog`.

   For apps with only one third-party dep (or zero), keep the inline coordinate — a catalog file is overkill.

5. **Remove top-level `sourceCompatibility` / `targetCompatibility`.** Older XP 7 build files often include:

   ```diff
   -sourceCompatibility = JavaVersion.VERSION_11
   -targetCompatibility = sourceCompatibility
   ```

   Gradle 9 dropped these as `Project` properties — leaving them in fails the build with
   `Could not set unknown property 'sourceCompatibility' for root project ... of type org.gradle.api.Project`. For JS-only XP apps (no
   `src/main/java`) they're vestigial and safe to delete outright. For apps with Java sources, prefer letting the XP plugin's toolchain
   convention handle it (see next bullet) over hand-rolling a `java { sourceCompatibility = ...; targetCompatibility = ... }` block.

6. **Don't add an explicit Java toolchain block — the XP plugin sets it.** The `com.enonic.xp.base` plugin (applied transitively by
   `com.enonic.xp.app`, and applied directly by XP 8 *libraries* like `lib-react4xp`) sets the Java toolchain to **version 25** as a
   convention default whenever the `java` plugin is applied. So a block like:

   ```groovy
   java {
       toolchain {
           languageVersion = JavaLanguageVersion.of(25)
       }
   }
   ```

   is redundant in XP 8 builds and should be removed during the upgrade. Keep an explicit toolchain block only if you need to *override* the
   convention to a different JDK version. Setting `sourceCompatibility`/`targetCompatibility` is also unnecessary — the toolchain handles
   both.

**`gradle.properties`:** bump `xpVersion` to the highest XP 8 version actually available, preferring **stable** over pre-release over
snapshot:

1. **Stable release** (e.g. `8.0.0`, `8.0.1`) — use this if any final XP 8 release exists. Check
   <https://repo.enonic.com/public/com/enonic/xp/core-api/>.
2. **Pre-release** (alpha / beta, e.g. `8.0.0-A3`, `8.0.0-B1`) — use the highest one published to the release repo if no stable exists.
3. **Snapshot** (e.g. `8.0.0-SNAPSHOT`) — only as a last resort, when nothing else is published. Snapshots resolve only through
   `xp.enonicRepo("dev")` (the same dev-channel swap the *Migrate dependencies* edit covers), so they work but move under your feet between
   rebuilds.

If the user is on the very old `7.x` series (< 7.16), warn that XP recommends going through 7.16.x first (see the
[instance upgrade guide](https://raw.githubusercontent.com/enonic/doc-xp/refs/heads/8.0/docs/release/upgrade.adoc)) — but the source-level
edits are the same. Add `projectName = …` if missing (`settings.gradle` reads it); keep `appName`, `version`, `group` (still consumed by
Gradle). Display/vendor metadata (`appDisplayName`, `vendorName`, `vendorUrl`, and the legacy unprefixed `displayName`) is handled in the
*Application descriptor* section below — it moves into `enonic.yaml`.

**`gradle/wrapper/gradle-wrapper.properties`:** plugin 4.x requires **Gradle 9+**. Pin to a current 9.x via the wrapper task (which also
refreshes `gradle-wrapper.jar`):

```sh
./gradlew wrapper --gradle-version 9.4.1
```

**JUnit Platform launcher (Gradle 9+).** If the app has JUnit 5 tests, Gradle 9 no longer auto-resolves
`org.junit.platform:junit-platform-launcher` onto the test runtime classpath — the test task (run as part of `enonic project build`) fails with
`Failed to load JUnit Platform. Please ensure that all JUnit Platform dependencies are available on the test's runtime classpath, including the JUnit Platform launcher.`
Add the launcher explicitly:

```diff
 dependencies {
     testImplementation 'org.junit.jupiter:junit-jupiter:5.11.4'
+    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
 }
```

The version is supplied transitively by `junit-jupiter`; pinning it is unnecessary.

**`JsonMapGenerator` moved package (test-only).** The concrete `JsonMapGenerator` helper class — commonly used in XP 7 unit tests to drive
`MapSerializable.serialize(MapGenerator)` — moved package and jar in XP 8:

| XP 7                                               | XP 8                                                |
|----------------------------------------------------|-----------------------------------------------------|
| `com.enonic.xp.script.serializer.JsonMapGenerator` | `com.enonic.xp.testing.serializer.JsonMapGenerator` |

Compile error: `cannot find symbol: class JsonMapGenerator ... package com.enonic.xp.script.serializer`. Fix is a one-line import update —
the class is in the `com.enonic.xp:testing` jar (already on the test classpath as `testImplementation`). The interfaces it works with (
`MapGenerator`, `MapSerializable`) stay in `com.enonic.xp.script.serializer` and don't move.
