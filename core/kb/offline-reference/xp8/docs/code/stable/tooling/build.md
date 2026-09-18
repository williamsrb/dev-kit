<!-- src:https://developer.enonic.com/docs/code/stable/tooling/build generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/tooling/build.md

# Building apps

This section explains the details of the Enonic XP build system

> **Note:** Upgrading from XP 7? See [the Upgrading guide](docs/code/stable/upgrade.md).

## Main builder

Enonic apps and libraries use [Gradle](https://gradle.org/) as the main build tool.

Gradle is used because Enonic apps are packaged and deployed as .jar (Java) files in the end.

Builds run on Gradle 9.x — bundle a Gradle Wrapper of version 9.5.0 or later in your project.

> **Tip:** Enonic supports popular TypeScript/JavaScript tooling such as TSUP, NPM and webpack to run on top of Gradle. [Try one or our Starters](https://market.enonic.com/starters) to see it in action.

The Gradle build files are described below

### gradle.properties

This file specifies common project-wide properties: project identity and the XP version. App display and vendor metadata live in `enonic.yaml` (see below).

Sample gradle.properties file

```properties
# Gradle Project settings
projectName = vanilla (1)
version = 1.0.0-SNAPSHOT (2)

# XP App values
appName = com.acme.example.vanilla (3)
xpVersion = 8.0.0 (4)

# Settings for publishing to a Maven repo
group = com.acme.example (5)
```

| ****1** | Project name — used for the output file (this produces an app file called `vanilla-<version>.jar`). |
| --- | --- |
| ****2** | Version — important metadata, used to identify different releases of an app. |
| ****3** | `appName` must be unique across all apps. It is also stored as a namespace in CMS content created by the app. |
| ****4** | Minimum version of XP required for the app. Typically also used to resolve which XP core libraries to depend on from `build.gradle`. |
| ****5** | Maven group used when publishing the artifact. |

### build.gradle

This is the main build file. It controls available build settings, dependencies and more.

Sample build.gradle file

```groovy
plugins { (1)
    id 'com.enonic.xp.app'
}

repositories { (2)
    mavenCentral()
    xp.enonicRepo()
}

dependencies { (3)
    implementation xplibs.api.script
    implementation xplibs.api.portal
    include xplibs.content
    include xplibs.portal
}
```

| ****1** | Apply the [Enonic Gradle plugin](https://developer.enonic.com/docs/enonic-gradle-plugins). The plugin version is managed in `settings.gradle` (see below) — don’t pin it here. |
| --- | --- |
| ****2** | Maven repos Gradle resolves dependencies from. `xp.enonicRepo()` is a shortcut to the Enonic repository. |
| ****3** | Dependencies on libraries. `api.script` is the entry point for server-side script APIs. |

> **Note:** Don’t set `java.toolchain.languageVersion`, `sourceCompatibility`, or `targetCompatibility` in `build.gradle`. The XP Gradle plugin selects the correct Java toolchain automatically — manual settings can conflict with what the plugin expects.

### settings.gradle

Apply the settings plugin in `settings.gradle`. It wires up the `xplibs` version catalog and the Enonic-specific Gradle conventions.

Sample settings.gradle

```groovy
plugins {
    id("com.enonic.xp.settings") version "4.0.0"
}
```

## Dependencies

Easily include standard Enonic libraries or 3rd party dependencies in your app via the dependencies section.

Each dependency must be prefixed with a scope for specific building instructions. The available scopes are:

Include

Standard scope when adding Enonic libraries to your project. Resource files in the library are merged into your app. Files in your app overwrites files with the same name in the library. Dependencies of the library are transitively included.

Implementation

Typically used for Java dependencies. Does not automatically include transitive dependencies, meaning you must explicitly declare transitive dependencies.

Webjar

Custom Enonic scope that extracts the content of the specified Webjar - [https://www.webjars.org/](https://www.webjars.org/) - placing it into the assets folder, using the version number as root folder

## Libraries

If you are building **a library** (not an application), you don’t need the `com.enonic.xp.app` plugin. Apply `com.enonic.xp.base` instead — it gives you the `xp.enonicRepo()` shortcut and the XP version catalog without the application packaging behavior.

Sample build.gradle for a library

```groovy
plugins {
    id 'java'
    id 'maven-publish'
    id 'com.enonic.xp.base'
}

repositories {
    mavenCentral()
    xp.enonicRepo()
}
```

> **Note:** `com.enonic.xp.base` is only needed if your library uses XP dependencies and you want the `xp.enonicRepo()` shortcut. A pure Java library with no XP types doesn’t need it.

Sample gradle.properties for a library

```properties
group = com.mycompany.lib
projectName = mylib
version = 1.0.0-SNAPSHOT
xpVersion = 8.0.0
```

`appName` and the `enonic.yaml` file are application-only — libraries don’t need either.

## Compiler

Java 25 is bundled with the XP 8 distribution and is the minimum version required for building and running XP 8 applications. The XP Gradle plugin selects the correct toolchain automatically, so you typically don’t need to configure a JDK explicitly.

When building outside Enonic CLI, set `JAVA_HOME` to a Java 25 (or later) installation — for example, the JDK bundled with the XP distribution — so Gradle can locate it.

JAVA_HOME

Defines the location of the JDK.

To set the environment variable, use one of the following approaches:

Linux/MacOS

```
export JAVA_HOME=/path/to/xp-distro/jdk
```

Windows

```
set JAVA_HOME=c:\path\to\xp-distro\jdk
```

## Building

Builds are initialized via the Gradle Wrapper. This is a file located in your projects root: `gradlew` for Linux/MacOS and `gradle.bat` for Windows.

The wrapper will download all necessary files to execute your build.

Using Enonic CLI, simply run the following command from your project folder:

Enonic CLI

enonic project build

To manually trigger Gradle builds, make sure `JAVA_HOME` is defined, and run the following command:

OSX/Linux

`./gradlew build`

Windows

`gradlew.bat build`

The build will place any output artifacts (app or library files) into your project’s `build/libs/` folder.

## Deploying

To deploy an app to your sandbox:

Enonic CLI

`enonic project deploy`

To do this manually, make sure XP_HOME is defined and execute the following command

Linux/MacOS

`./gradlew deploy`

Windows

`gradlew.bat deploy`

This command copies the artifact (application file) into your sandbox' `$XP_HOME/deploy` folder. XP will then automatically install and start it.

> **Note:** XP apps deployed via file are presented with a small blue icon in the `Applications` admin tool.

## Dev Mode

> **Tip:** Using dev mode is generally recommended, as it saves time by providing real-time updates of your app

By running your sandbox in `dev` mode, it will automatically detect and load changes to your application source files, including JavaScript modules and schemas. It does this by reading the files directly from the application project folder instead of using the compiled application file.

Enonic CLI

`enonic sandbox start --dev`

Linux/MacOS

`$XP_INSTALL/bin/server.sh dev`

Windows

`$XP_INSTALL/bin/server.sh dev`

> **Warning:** Dev mode should never be used in production. Doing so may cause both security and performance issues.

In addition to running XP in dev mode, your application may contain files that require compilation (including transpilation). This means that must build the files for every change. For instance, if you use TypeScript, these files won’t be picked up by default.

XP projects support this out of the box. Simply run:

Enonic CLI

`enonic project dev`

> **Tip:** Development mode also disables some of XP’s caching mechanisms. To make the development workflow as smooth as possible, XP tries to invalidate caches for your static assets. This is to prevent you from getting stale resources so that what you see in the browser is always as up to date as possible.
