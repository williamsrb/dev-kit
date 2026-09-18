<!-- src:https://developer.enonic.com/docs/code/stable/tooling/starters generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/tooling/starters.md

# Project and code structure

> **Tip:** Get started running. Use one of our [starters](https://market.enonic.com/starters) to bootstrap your development project.

> **Note:** Enonic apps are primarily written in **JavaScript/TypeScript**. However, thanks to the [XP runtime](docs/code/stable/fundamentals/runtime.md) being a polyglot, applications may contain Java, Kotlin, Scala, or any other language that compiles to Java bytecode.

## Project structure

The example structure below includes the standard files and folders in an Enonic application (or library).

```files
sample-project/
  build.gradle
  gradle.properties
  gradlew
  gradlew.bat
  settings.gradle
  src/
    main/
      resources/
        enonic.svg
        enonic.yaml
        admin/
          tools/
          extensions/
        apis/
        assets/
        error/
        i18n/
        idprovider/
        main.ts
        cms/
          cms.yaml
          site.yaml
          content-types/
          form-fragments/
          layouts/
          macros/
          mixins/
          pages/
          parts/
          processors/
          style/style.yaml
        webapp/
        tasks/
      java/
    test/
      java/
```

Every file and folder has a specific function and purpose as described below:

### Build files

Enonic supports JS/TS based build tools, but relies on [Gradle](https://gradle.org/) as the main builder. The [TypeScript Starter](https://market.enonic.com/starters/typescript-starter) is a good place to set up a project.

Visit the [build system section](docs/code/stable/tooling/build.md) for more details.

build.gradle

Main build file

gradle.properties

Build properties

gradlew | /gradlew.bat

Gradle wrapper file. Downloads and runs Gradle without having to install it manually.

settings.gradle

Mandatory file to boostrap the build process

### General resources

The majority of Enonic specific code is placed within `src/main/resources/`:

admin/tools/

Admin tools are defined here. Tools are administrative apps listed in the admin console menu.

admin/extensions/

Admin extensions are user interface components that can be embedded within admin tools (formerly known as widgets).

apis/

[Universal API](docs/code/stable/web/apis.md) implementations and descriptors.

enonic.svg

Application icon in SVG format. Should be in a square format.

enonic.yaml

Application descriptor (`kind: "Application"`).

assets/

Standard folder for static assets such as CSS and JavaScript. Serve them with the [lib-asset](https://developer.enonic.com/docs/lib-asset/stable) library, available on [Enonic Market](https://market.enonic.com).

error/error.ts

The [HTTP error handler](docs/code/stable/web/error.md).

main.ts

The application’s [main lifecycle](docs/code/stable/fundamentals/main.md). Runs when the application starts and stops.

i18n/

Short for internationalization, this folder contains [app localization files](docs/code/stable/libraries/lib-i18n.md).

idprovider/

The application may implement an [ID Provider](docs/code/stable/web/id-providers.md) here.

tasks/

May contain [task implementations](docs/code/stable/background/tasks.md) for asynchronous and background processing.

webapp/

Optional [webapp](docs/code/stable/web/webapps.md) entry point. Contains `webapp.ts` (implementation) and an optional `webapp.yaml` (descriptor).

cms/site.yaml

Site configuration — API mounts, processors, and mappings.

cms/cms.yaml

Site form and mixin references.

cms/content-types/

[Content type](https://developer.enonic.com/docs/cms/xp8/content/content-types) definitions.

cms/processors/

[Response processors](docs/code/stable/web/sites/processors.md) for post-processing the HTML response from sites.

cms/layouts/

[Layout components](https://developer.enonic.com/docs/cms/xp8/pages/parts).

cms/form-fragments/

Reusable form pieces (formerly known as `mixins`).

cms/macros/

[Rich-text macro components](https://developer.enonic.com/learn/next.xp/stable/macros).

cms/pages/

[Page components](https://developer.enonic.com/docs/cms/xp8/pages).

cms/parts/

[Part components](https://developer.enonic.com/docs/cms/xp8/pages/parts).

cms/mixins/

Extra metadata attached to content (formerly known as `x-data`).

cms/style/style.yaml

Custom styles for use in RichText component.

### Java

/src/main/java/

Optionally place Java code here.

/src/test/java/

Optionally place Java tests here.

## Apps vs Libraries

Enonic libraries are similar to applications, the main difference being that a library cannot be installed and started by itself.

> **Tip:** Check out [the library starter](https://market.enonic.com/starters/library-starter) if you are planning to build your own library.

A library may consist of the same files and functionality you would find in an application — such as assets, content types, and JS modules.

Enonic libraries are added to your application by declaring a dependency in the [build file](docs/code/stable/tooling/build.md#build.gradle).

The core functionality of XP is exposed via standard libraries. Check out the [Standard Libraries documentation](docs/code/stable/libraries.md). You will also find additional libraries on [Enonic Market](https://market.enonic.com/libraries)
