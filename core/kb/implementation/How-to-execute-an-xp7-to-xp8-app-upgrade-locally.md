---
id: how-to-execute-an-xp7-to-xp8-app-upgrade-locally
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

# How to execute an XP 7→8 app upgrade locally

Companion to [How-to-run-xp8migrator.md](How-to-run-xp8migrator.md) and
[xp7-to-xp8-upgrade/](xp7-to-xp8-upgrade/). Those cover *what* to change. This covers the
mechanical failures you hit while actually running the upgrade on a workstation.

## Scope

JS-only XP 7 app → XP 8.0.4, `com.enonic.xp.settings` 4.x, Gradle 9.x. Verified on
`forwarding-app-xp` (XP 7.3.0 → 8.0.4, 2026-08-24) against the `logviewer` XP 8 reference.

## Prerequisites

- A JDK **21 or newer** on the machine (see pitfall 1). `/usr/lib/jvm/java-25-openjdk-amd64`
  on Ubuntu-family boxes.
- Docker, if the repo carries a `Makefile` + `docker/dev/` toolchain.

## Procedure

### 1. Bump the Gradle wrapper before anything else

The wrapper task cannot run on the old distribution: Gradle 5.x/6.x refuses to start on
Java 17+. Do **not** try `./gradlew wrapper --gradle-version 9.6.1` from a 5.2.1 wrapper.

Two-step instead — hand-edit `distributionUrl`, then let the *new* Gradle regenerate the
jar and scripts properly:

```sh
# 1. edit gradle/wrapper/gradle-wrapper.properties by hand
#    distributionUrl=https\://services.gradle.org/distributions/gradle-9.6.1-bin.zip
# 2. now the wrapper downloads 9.6.1 and runs the task on it
JAVA_HOME=/usr/lib/jvm/java-25-openjdk-amd64 ./gradlew wrapper --gradle-version 9.6.1
```

Step 2 is not optional — step 1 alone leaves a stale `gradle-wrapper.jar`, `gradlew`, and
`gradlew.bat`. Step 2 rewrites all four files and adds the modern
`networkTimeout` / `retries` / `validateDistributionUrl` keys.

### 2. Build with an explicit JAVA_HOME

```sh
JAVA_HOME=/usr/lib/jvm/java-25-openjdk-amd64 ./gradlew clean build
```

### 3. Reconcile dependencies at JAR level, filtering example files

```sh
unzip -o build/libs/<app>.jar -d /tmp/jar >/dev/null
grep -rhoE "require\(['\"]/lib/[^'\"]+" /tmp/jar \
  | sed -E "s/require\(['\"]//" | sort -u
```

Then, for each `/lib/<name>` you cannot account for, check whether the *only* files
requiring it live under an `examples/` directory (see pitfall 3).

## Pitfalls

### 1. `com.enonic.xp.settings` 4.x needs a JVM ≥ 21, and says so at the wrong moment

With Java 17 on PATH the build dies during **settings-plugin resolution**, long before any
compile step, and the message names the plugin rather than the JDK:

```
Could not resolve com.enonic.gradle:xp-gradle-plugin:4.2.0.
  Required by:
      settings file 'settings.gradle' > com.enonic.xp.settings:com.enonic.xp.settings.gradle.plugin:4.2.0
   > Dependency requires at least JVM runtime version 21. This build uses a Java 17 JVM.
```

This is distinct from the XP plugin's Java **toolchain** default of 25, which governs
compilation, not the Gradle daemon. Both exist; only this one blocks resolution.

### 2. The JAR require-scan surfaces four false alarms

A clean XP 8 JS app scan returns entries the app never wrote:

| Entry | Verdict |
|---|---|
| `/lib/xp/common`, `/lib/xp/value` | **Real.** Shipped inside the `xplibs.*` jars as `lib/xp/common.js` / `value.js`. Already satisfied — no include to add. |
| `/lib/xp/testing`, `/lib/xp/repo.js` | **Noise.** Required only from bundled `lib/xp/examples/**` and `lib/examples/thymeleaf/render.js` — documentation files that never execute. `lib/xp/testing.js` is not even present in the JAR. |

So always filter before concluding a dependency is missing:

```sh
grep -rlE "require\(['\"]/lib/xp/admin" /tmp/jar | grep -v "/examples/"
```

Skipping the `grep -v` makes the scan claim you need `xplibs.admin` when nothing at runtime
touches it. That in turn makes the "never drop an include" rule in
[xp7-to-xp8-changes.md](xp7-to-xp8-upgrade/xp7-to-xp8-changes.md) look violated when it is not.
The reverse check (every include has ≥1 caller) is the reliable half.

### 3. XP 8 emits an unversioned archive name by default

`gradle.properties` may say `version = 3.0.2`, but the plugin writes
`build/libs/<projectName>.jar` — **not** `<projectName>-3.0.2.jar`. Any XP 7-era glob like
`build/libs/<app>-*.jar` in a plan, script, or CI job silently matches nothing.

Corollary: `app { keepArchiveFileName = true }` (present in some XP 8 reference apps) is
redundant — that is already the default. It is not the reason the name is unversioned.

**But the flag is NOT a no-op on the XP 7 plugin 3.x line.** Measured on `com.enonic.xp.app`
**3.4.0** / Gradle 8.3 / `xpVersion=7.11.1` (cookiebot-app, 2026-08-25), toggling that one line
changes the artifact filename:

| `app { keepArchiveFileName }` | `build/libs/` output |
|---|---|
| commented out / absent | `cookiebot-app.jar` |
| `= true` | `cookiebot-app-1.1.0.jar` (Gradle default `<name>-<version>.jar`) |

So on 3.x the flag *restores* the versioned name; on 4.x/XP 8 the unversioned name is the default
regardless. Consequence when reading a pre-upgrade XP 7 diff: a branch that merely uncomments
`keepArchiveFileName = true` silently **renames the deploy artifact**. Check any CI/deploy consumer
that hardcodes the filename (globs like `build/libs/*.jar` are safe; a literal `<app>.jar` is not)
before assuming the line is cosmetic.

### 4. Admin-tool `title:` may be a plain string

Contradicts an earlier claim in `xp7-to-xp8-changes.md` (since corrected) that plain strings
NPE in `AdminToolMapper`. On XP 8.0.4 a plain string is fine:

```yaml
kind: "AdminTool"
title: "Forwarding"
description: "Set up URL forwarding."
```

Use the `{ text, i18n }` object form when you have an i18n key to preserve, not because the
string form is illegal.

### 5. `xp8migrator` is skippable for small descriptor sets

Three descriptors (`application.xml`, `site/site.xml`, one admin tool) is below the threshold
where a `curl … | sh` install-and-execute earns its keep — especially when the plan already
spells out the target YAML. Hand-write them; the migrator's value is volume and edge cases
(content types, mixins, x-data, option sets), not four-line files.

## Sample data

Cold build against the CI image, which proves the GitLab job before pushing:

```sh
make coldBuild   # docker run --rm on leanon/enonic-ci:8.0.4-node24
```

Worth running even when the local `./gradlew build` is green — it is the only local check
that exercises the same image, JDK, and Enonic CLI the pipeline will use.

### 5. Syncing `docker/dev/xp-home/config/` by filename is not enough

Plans often express the config migration as an add/remove **file list** derived from
`diff <(ls ours) <(ls reference)`. That gets the file *set* right and leaves every shared file
carrying XP 7-era content. On cookiebot-app, 15 files present in both repos differed in content,
and two of those differences are functional, not cosmetic:

- `com.enonic.xp.web.jetty.cfg` — XP 8 dev mode binds loopback; needs `host = 0.0.0.0` or nothing
  outside the container can reach it.
- `system.properties` — XP 8 rejects a plaintext `xp.suPassword`; needs `{sha256}`/`{sha512}`.

Both fail *silently* in the sense that the server starts, logs clean, and the app installs fine.
So after syncing filenames, also diff the **contents** of shared files against the reference and
review each hit:

```sh
for f in $(ls ours/); do
  [ -f "ref/$f" ] && ! diff -q "ours/$f" "ref/$f" >/dev/null && echo "DIFFERS: $f"
done
```

Preserve your own uncommented values (vhost mappings, dos limits, mail host); take the reference's
values only where XP 8 changed a default or key name.

### 6. `./gradlew wrapper` fails on distribution-URL validation, not on the URL

The wrapper task can die even when the URL is correct and the distribution downloads fine:

```
> Task :wrapper FAILED
> Test of distribution url https://services.gradle.org/distributions/gradle-9.6.1-bin.zip failed.
  Please check the values set with --gradle-distribution-url and --gradle-version.
```

`services.gradle.org` answers `307 Temporary Redirect`, and the task's `validateDistributionUrl`
probe does not follow redirects. The download path *does* follow it — so `./gradlew --version`
already reports 9.6.1 while the `wrapper` task still refuses to regenerate the jar and scripts.

Fix — skip the probe for that one invocation, then put the key back so the file matches the
reference:

```sh
JAVA_HOME=/usr/lib/jvm/java-25-openjdk-amd64 ./gradlew wrapper --gradle-version 9.6.1 --no-validate-url
sed -i 's/^validateDistributionUrl=false$/validateDistributionUrl=true/' gradle/wrapper/gradle-wrapper.properties
```

`true` is safe to keep: only the wrapper *task* probes; the wrapper *script*'s own download does not.
Diff the result against the reference app's `gradle-wrapper.properties` — a correct regeneration is
byte-identical apart from nothing, including the `retries` / `retryBackOffMs` keys.

Do not "fix" this by reverting to a hand-edited properties file alone. That leaves the stale
`gradle-wrapper.jar`, `gradlew`, and `gradlew.bat` behind (pitfall in §1 above).

### 7. `enonic project clean` blocks on a sandbox prompt; `build -f` does not

`enonic project clean` opens an interactive sandbox picker and dies on EOF:

```
? A sandbox is required for your project, select one or create new:
Could not select sandbox:  ^D
```

`enonic project build -f` instead prints `No sandbox found, building without a sandbox...` and
proceeds. So for a JS-only app with no sandbox bound, `enonic project build -f` is the whole local
build gate — do not chain a `clean` in front of it in a non-interactive run. To force a cold build,
`rm -rf build/` first.
