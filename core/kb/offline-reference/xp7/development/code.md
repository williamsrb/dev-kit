<!-- src:https://developer.enonic.com/docs/platform/7.x/development/code generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC development/code.md

# Application development

Details on the project and code structure in Enonic apps and libraries

> **Tip:** Get started running. Use one of our [starters](https://market.enonic.com/starters) to bootstrap your development project.

## Languages

XP apps are powered by the [XP runtime](/docs/platform/7.x/runtime).

Enonic apps may consist of both server.-side and client-side code. They are primarily written in JavaScript/TypeScript.

Server-side JavaScript must uses XP’s [Javascript Framework](/docs/platform/7.x/framework)

Applications may optionally use Java. Developers with special requirements can take advantage of advanced platform capabilities such as exposing and consuming services from other applications within the same platform instance.

Learn more about [using Java in XP apps](/docs/platform/7.x/framework/java-bridge)

## Project structure

The example structure below includes the standard files and folders for an Enonic application (or library).

```files
sample-project/
  build.gradle
  gradle.properties
  gradlew
  gradlew.bat
  settings.gradle
  src/
    main/
      java/
      resources/
        application.svg
        application.xml
        admin/
          tools/
          widgets/
        assets/
        error/
        i18n/
        idprovider/
        main.js
        services/
        site/
          site.xml
          content-types/
          layouts/
          macros/
          mixins/
          pages/
          parts/
          processors/
          x-data/
        webapp/
        tasks/
    test/
      java/
```

Every file and folder has a specific function and purpose as described below:

### Build files

Enonic supports JS/TS based build tools, but relies on [Gradle](https://gradle.org/) as the main builder. The [TypeScript Starter](https://market.enonic.com/starters/typescript-starter) is a good place to set up a project.

Visit the [build system section](/docs/platform/7.x/development/build) for more details.

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

admin/widgets/

Admin widgets are essentially user interface components that can be embedded within other admin tools.

application.svg

Application icon in SVG format. Should be in a square format.

application.xml

Application information in XML format.

assets/

Standard folder for serving of static assets, such as css and javascript. Assets are served by the [asset service](/docs/platform/7.x/runtime/engines/asset-service).

error/error.js

The [HTTP error handler](/docs/platform/7.x/framework/error)

main.js

The application’s [main controller](/docs/platform/7.x/framework/main). Executed when an application starts and stops.

services/

Contains [Http service controllers](/docs/platform/7.x/runtime/engines/http-service)

i18n/

Short for internationalization, this folder contains [app localization files](/docs/platform/7.x/api/lib-i18n)

idprovider/

The application may implement an [ID Provider](/docs/platform/7.x/framework/idprovider#part) here.

tasks/

May contain [task controllers](/docs/platform/7.x/api/lib-task) for running asynchronous and background processing.

site/site.xml

Contains [site configuration schema](/docs/platform/7.x/cms/sites#site_xml), and declaring that the app can be added to projects and sites

site/content-types/

Contains [Content type](/docs/platform/7.x/cms/content-types) definitions.

site/processors/

For post processing of HTML response from pages built with the [Enonic JS framework](/docs/platform/7.x/framework).

site/layouts/

[Layout components](/docs/platform/7.x/cms/pages/layouts) are placed here.

site/mixins/

[Reusable schemas](/docs/platform/7.x/cms/schemas/mixins) are placed here.

site/macros/

[Rich text Macro components](/docs/platform/7.x/cms/macros) are placed here.

site/pages/

[Page components](/docs/platform/7.x/cms/pages) are placed here.

site/parts/

[Part components](/docs/platform/7.x/cms/pages/parts) are placed here.

site/x-data/

[X-data schemas](/docs/platform/7.x/cms/x-data) are defined here

webapp/webapp.js

[Webapp](/docs/platform/7.x/runtime#webapp_js) based on the Enonic JS framework are placed here.

### Java

/src/main/java/

Optionally place Java code here.

/src/test/java/

Optionally place Java tests here.

## Libraries

Enonic libraries are similar to applications, the main difference being that a library cannot be installed and started by itself.

> **Tip:** Check out [the library starter](https://market.enonic.com/starters/library-starter) if you are planning to build your own library.

A library may consist of the same files and functionality you would find in an application - such as Assets, Content Types and JS controllers.

Enonic libraries are added to your application by declaring a dependency in the [build file](/docs/platform/7.x/development/build#build.gradle).

The core functionality of XP is exposed via standard libraries. Check out the [Standard Libraries documentation](/docs/platform/7.x/api). You will also find additional libraries on [Enonic Market](https://market.enonic.com/libraries)
