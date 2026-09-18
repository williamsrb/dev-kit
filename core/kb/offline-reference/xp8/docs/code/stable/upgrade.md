<!-- src:https://developer.enonic.com/docs/code/stable/upgrade generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/upgrade.md

# Upgrading Enonic apps from XP7 to XP8

This section describes the steps required to upgrade an XP application from 7.x to 8.0

> **Note:** To run this upgrade automatically with an AI coding agent, use the [Enonic AI Agents Skills](https://github.com/enonic/ai-enonic-marketplace) repository — it includes a skill that drives Claude Code (or a compatible agent) through the procedure below. The skill reads this page as its source, so the steps documented here are authoritative whether you upgrade by hand or via an agent.

## Terminology and concept changes

XP 8 renames or reframes several XP 7 concepts — "engine" is retired in favour of **service**, controllers become plain **functions**, services become **Universal APIs**, and more. When migrating, or when reconciling older XP 7-era examples or AI-generated code with current conventions, consult the full map in the release notes: [A paradigm shift in naming](docs/platform/stable/release.md#naming).

The actionable directory, descriptor, and method renames are detailed in the steps below.

## Preparations

Before you start the upgrade procedure:

- Make sure you have [Enonic CLI](https://developer.enonic.com/docs/enonic-cli/stable) installed

- Check out the project source code to a local folder i.e. myapp/

- Ensure you have an XP8 sandbox for the application using Enonic CLI

```
enonic project sandbox
```

## App migrator tool

The [xp8migrator](https://github.com/enonic/xp8migrator) is a small CLI that converts an XP 7 project’s XML descriptors into the XP 8 YAML form. Run it from your project root.

### Linux / macOS

```sh
curl -fsSL https://raw.githubusercontent.com/enonic/xp8migrator/main/migrator-install.sh | sh
./migrator
```

### Windows

```powershell
irm https://raw.githubusercontent.com/enonic/xp8migrator/main/migrator-install.ps1 | iex
.\migrator.exe
```

The `migrator` binary can be removed after a successful migration.

## Build system

The standard build system must be updated.

### Gradle Wrapper

XP 8.0 standardizes on the use of Gradle 9.x. We recommend bundling Gradle wrapper of version 9.5.0 or later in your project.

For simple installations, from your project root, run:

```
./gradle wrapper --gradle-version 9.5.0
```

This will install or update your project with a new Gradle wrapper.

Please refer to Grade documentation for more details [https://docs.gradle.org/current/userguide/gradle_wrapper.html#sec:upgrading_wrapper](https://docs.gradle.org/current/userguide/gradle_wrapper.html#sec:upgrading_wrapper)

### build.gradle

If you are upgrading **an application**, you need to use a version greater or equal to '4.0.0' of the XP Gradle plugin (*com.enonic.xp.app*).

The new plugin no longer requires the `app {}` section in *build.gradle* Read more about it in the plugin documentation.

> **Note:** Syntax for adding plugins to Gradle may have changed for your project, we recommend the following updates to your build files:

build.gradle sample

```groovy
plugins {
    id 'com.enonic.xp.app'
}

repositories {
    mavenCentral()
    xp.enonicRepo()
}

dependencies {
    implementation xplibs.api.script
    include xplibs.content
    include xplibs.portal
}
```

> **Note:** The default `dev` task is now registered automatically by the plugin. If your project defines its own `dev` task, either remove it to use the default, or set `createDefaultDevTask = false` in the `app {}` section to keep your custom task.

> **Note:** Remove any `java.toolchain.languageVersion` (and `sourceCompatibility` / `targetCompatibility`) configuration from your `build.gradle`. The XP Gradle plugin sets the correct Java toolchain automatically — manual settings can conflict with what the plugin expects.

### gradle.properties

The new plugin only uses `appName` and `xpVersion` properties.

`displayName`, `url`, `vendorName` and `vendorUrl` must be moved to the new *src/main/resources/enonic.yaml*

> **Note:** `displayName` is now called `title` in *enonic.yaml*).

gradle.properties sample

```properties
# Gradle Project settings
projectName = myproject
version = 1.0.0-SNAPSHOT

# XP App values
appName = com.acme.something.myproject
xpVersion = 8.0.0
```

> **Note:** `appName` is only used for application projects, as well as `app` config in `build.gradle`

### settings.gradle

For the plugin to work, you must add the following to your *settings.gradle*:

settings.gradle sample

```groovy
plugins {
    id("com.enonic.xp.settings") version "4.0.0"
}
```

### Library upgrade

If you are upgrading **a library**, you don’t need to use *com.enonic.xp.app* plugin or have `app {}` section in *build.gradle*. Below is a sample content of *build.gradle* and *gradle.properties* files for a library:

build.gradle sample

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

> **Note:** You only need to use *com.enonic.xp.base* plugin if you are using XP dependencies and need to shortlink to Enonic repo via *xp.enonicRepo()* shortcut

gradle.properties sample

```properties
group=com.mycompany.lib
projectName=mylib
xpVersion=8.0.0
version=1.0.0-SNAPSHOT
```

### TypeScript definitions (`@enonic-types`) for apps and libraries

If your project uses TypeScript, update all `@enonic-types` packages in `package.json` to XP 8 compatible versions. This applies to both applications and libraries.

XP 7

```json
{
  "devDependencies": {
    "@enonic-types/global": "^7.0.0",
    "@enonic-types/lib-content": "^7.0.0"
  }
}
```

XP 8

```json
{
  "devDependencies": {
    "@enonic-types/global": "^8.0.0",
    "@enonic-types/lib-content": "^8.0.0"
  }
}
```

### Verify

After completing the steps above, you should now be able to test that your build is working, using the Enonic CLI:

```
enonic project deploy
```

This command proxies the Gradle wrapper, but also connects with the project sandbox. You may also use `enonic project build` to build without deploying

> **Note:** Projects containing Java code might get build errors at this point, otherwise the build should complete successfully.

## JDK

Java 25 is bundled with XP 8.0.0, and is the minimum required version for building and running XP8 applications.

## Testing API

If you are using Enonic testing API (`com.enonic.xp:testing`), you’ll need to add Junit 5 dependency with the corresponding platform launcher.

```groovy
dependencies {
testImplementation "com.enonic.xp:testing:${xpVersion}"
testImplementation(platform("org.junit:junit-bom:6.0.1"))
testImplementation 'org.junit.jupiter:junit-jupiter'
testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
}

test {
    useJUnitPlatform()
}
```

> **Warning:** Junit 4 is not supported in XP 8.0.0

## API Deprecations and Breaking Changes

### Default context

In XP8 the contextual repository and branch may return null if they are not set explicitly. Previously the default context was set with `com.enonic.cms.default` repository and `draft` branch.

**Symptom.** Code that previously relied on the implicit defaults — typically `contextLib.run({ …​ }, callback)` without a `branch:` or `repository:` field — now throws at runtime, e.g. `Error: branch is required`. The same applies to `node.connect({ …​ })` calls that don’t pass `branch` / `repoId`.

**Fix.** Set `branch` (and `repository`, where relevant) explicitly on every `run` or `connect` call that needs to operate against a known repo and branch.

```typescript
// Before — relied on default 'draft' branch
import {run} from '/lib/xp/context';
run({}, () => doStuff());

// After — branch (and usually repository) set explicitly
import {run} from '/lib/xp/context';
run({repository: 'com.enonic.cms.default', branch: 'draft'}, () => doStuff());
```

### Roles

The legacy role `role:cms.cm.app` (display name "Content Manager App") is deprecated. Fresh XP 8 installs no longer create this role, and it is no longer added to the default ACLs of content, issue, or archive root nodes when new projects are initialized.

Existing installations upgrading from XP 7 keep the role definition and any pre-existing ACEs that reference it. Those entries are harmless but obsolete and should not be relied on going forward. Apps that previously granted `cms.cm.app` to a user or group should switch to the per-project role hierarchy that XP 8 manages per content project:

- `role:cms.project..owner`

- `role:cms.project..editor`

- `role:cms.project..author`

- `role:cms.project..contributor`

- `role:cms.project..viewer`

> **Note:** Legacy dumps (model 8) imported into XP 8 are upgraded to model 9 automatically. During that upgrade, `cms.cm.app` is stripped from the legacy `com.enonic.cms.default` repository ACLs and replaced with the per-project role hierarchy. No manual action is required for that case.

### Identity keys, names, and IDs

XP 8 tightens the validation rules for identity keys, node/content names, and IDs. Apps that programmatically generate these values (custom ID providers, importers, migration scripts, etc.) must produce values matching the rules below.

All identity keys must satisfy the following common rules:

- must not be an empty string

- must not be a single underscore `_`, dot `.`, or double dot `..`

- must not include `/` or `\`

- must not include any whitespace characters, except the regular space `U+0020`

- must not start or end with the space character `U+0020`

#### Node, Content, and Issue names and IDs

- Names follow the common rules above.

- IDs are limited to 256 bytes/characters and no longer accept uppercase letters: `[a-z0-9_.:-]+`

#### IdProviderKey and PrincipalKey

Follow the common rules with the additional restriction of not including the space character `U+0020`, nor any of: ``, `:`, `"`, `|`, `?`, `*`, `&`, `'`.

#### DescriptorKey

Applies to:

- All CMS schema descriptor keys, including MacroKey

- Task key

- API key

- HTTP service key

- Admin Tool key

- Admin Extension key

Additional restrictions:

- must not include any of: ``, `:`, `"`, `|`, `?`, `*`, `&`, `'`

- must not include the space character `U+0020`

- limited to 64 characters

#### ApplicationKey

- must match the regex `\w(?:\.\w+)*+`

- limited to 63 characters

#### RepositoryId

- must match the regex `[a-z0-9][a-z0-9._-]*`

- limited to 63 characters

#### Branch

- must match the regex `[a-z0-9][a-z0-9.-]*`

- limited to 63 characters

#### ProjectName

- must match the regex `[a-z0-9][a-z0-9_-]*`

- limited to 48 characters

### Application Descriptor

The `application.xml` descriptor must be converted to `enonic.yaml`.

> **Tip:** Use the [xp8migrator](https://github.com/enonic/xp8migrator) tool to automate the conversion of XML descriptors to YAML.

XP 7 - application.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<application xmlns="urn:enonic:xp:model:1.0">
  <description>My app description</description>
</application>
```

XP 8 - enonic.yaml

```yaml
kind: "Application"
description: "My app description"
```

### Admin Tools

Admin Tool descriptors must be converted from XML to YAML.

XP 7 - admin/tools/main/main.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<tool xmlns="urn:enonic:xp:model:1.0">
  <display-name>My Admin Tool</display-name>
  <description>An admin tool</description>
  <allow>
    <principal>role:system.authenticated</principal>
  </allow>
</tool>
```

XP 8 - admin/tools/main/main.yaml

```yaml
kind: "AdminTool"
title: "My Admin Tool"
description: "An admin tool"
allow:
- "role:system.authenticated"
```

### Widgets / Admin Extensions

Widgets are now part of the Admin Extensions API. The `admin/widgets` directory has been renamed to `admin/extensions`, and descriptors must be converted from XML to YAML.

XP 7 - admin/widgets/settings/settings.xml

```xml
<widget xmlns="urn:enonic:xp:model:1.0">
  <display-name>Settings</display-name>
  <description>Configure Projects</description>
  <interfaces>
    <interface>contentstudio.menuitem</interface>
  </interfaces>
</widget>
```

XP 8 - admin/extensions/settings/settings.yaml

```yaml
kind: "AdminExtension"
title: "Settings"
description: "Configure Projects"
interfaces:
- "contentstudio.menuitem"
```

> **Note:** Unlike the `widgets` API in XP 7, the `admin:extension` API is not automatically mounted on admin tools. It must be explicitly mounted in the admin tool descriptor in order for extensions to work.

> **Warning:** In admin extensions, use `lib-static` instead of `lib-asset`. Both `lib-asset` and admin extensions are implemented as Universal APIs, so serving assets from an extension via `lib-asset` will not work without additional configuration. `lib-static` + is designed specifically for serving static files from admin extensions and does not require any additional configuration.

Example of mounting admin:extension API in an admin tool

```yaml
kind: "AdminTool"
title: "My Admin Tool"
allow:
- "role:system.admin"
apis:
- "admin:extension"
```

### Task

Task descriptors must be converted from XML to YAML.

> **Note:** Task descriptor forms do not support form-fragments.

XP 7 - tasks/mytask/mytask.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<task xmlns="urn:enonic:xp:model:1.0">
  <description>Background job</description>
  <form>
    <input type="Long" name="count">
      <label>Number of items to process</label>
      <default>42</default>
      <occurrences minimum="1" maximum="1"/>
    </input>
  </form>
</task>
```

XP 8 - tasks/mytask/mytask.yaml

```yaml
kind: "Task"
description: "Background job"
form:
- type: "Long"
  name: "count"
  label: "Number of items to process"
  occurrences:
    min: 1
    max: 1
  default: 42
```

### ID Provider

ID Provider descriptors must be converted from XML to YAML.

XP 7 - idprovider/idprovider.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<id-provider xmlns="urn:enonic:xp:model:1.0">
  <mode>MIXED</mode>
  <form>
    <input name="appClientId" type="TextLine">
      <label>Client ID</label>
      <occurrences minimum="1" maximum="1"/>
    </input>
  </form>
</id-provider>
```

XP 8 - idprovider/idprovider.yaml

```yaml
kind: "IdProvider"
mode: "MIXED"
form:
- type: "TextLine"
  name: "appClientId"
  label: "Client ID"
  occurrences:
    min: 1
    max: 1
```

### Authentication scope

Authentication no longer searches across ID providers for the first matching user. A request resolves against the vhost’s default ID provider, or an ID provider you specify explicitly. If your app relied on cross-provider lookup, configure the relevant vhosts explicitly in your XP deployment.

### Site descriptor split

The `site.xml` descriptor has been split into two separate files in XP 8:

- `site.yaml` - contains processors, mappings, and apis

- `cms.yaml` - contains mixin references (previously x-data) and the site form configuration

Additionally, the `site` directory has been renamed to `cms`.

XP 7 - site/site.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<site xmlns="urn:enonic:xp:model:1.0">
  <x-data name="myapp:my-mixin"/>
  <form>
    <input type="TextLine" name="some-name">
      <label>Textline</label>
      <occurrences minimum="0" maximum="1"/>
    </input>
  </form>
  <processors>
    <response-processor name="filter1" order="10"/>
  </processors>
  <mappings>
    <mapping controller="/controllers/preview.js" order="50">
      <match>type:'.*:person'</match>
    </mapping>
  </mappings>
</site>
```

XP 8 - cms/site.yaml

```yaml
kind: "Site"
processors:
- name: "filter1"
  order: 10
mappings:
- controller: "/controllers/preview.js"
  order: 50
  match: "type:'.*:person'"
apis:
 - "apiname" # belongs to the current application
 - "com.enonic.app.myapp:apiname"
```

XP 8 - cms/cms.yaml

```yaml
kind: "CMS"
mixin:
- name: "myapp:my-mixin"
  optional: false
form:
- type: "TextLine"
  name: "some-name"
  label: "Textline"
  occurrences:
    min: 0
    max: 1
```

#### Filter mappings now chain

In XP 7, when several `filter` mappings matched the same request, only the lowest-`order` filter ran and `next()` went straight to rendering; higher-order matches were silently dropped. In XP 8, all matching filters run as a chain in ascending `order`, and rendering happens after the last `next()`. A filter that does not call `next()`, or a `controller` mapping that wins on `order`, still short-circuits the chain.

### Page descriptor

XP 7 - site/pages/main/main.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<page xmlns="urn:enonic:xp:model:1.0">
  <display-name>Main</display-name>
  <description>Contains a single main region</description>
  <form/>
  <regions>
    <region name="main"/>
  </regions>
</page>
```

XP 8 - cms/pages/main/main.yaml

```yaml
kind: "Page"
title: "Main"
description: "Contains a single main region"
form: []
regions:
- "main"
```

### Layout descriptor

XP 7 - site/layouts/2-column/2-column.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<layout xmlns="urn:enonic:xp:model:1.0">
  <display-name>2 columns</display-name>
  <description>Provides left and right regions</description>
  <form/>
  <regions>
    <region name="left"/>
    <region name="right"/>
  </regions>
</layout>
```

XP 8 - cms/layouts/2-column/2-column.yaml

```yaml
kind: "Layout"
title: "2 columns"
description: "Provides left and right regions"
form: []
regions:
- "left"
- "right"
```

### Part descriptor

XP 7 - site/parts/my-part/my-part.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<part xmlns="urn:enonic:xp:model:1.0">
  <display-name>My Part</display-name>
  <description>A simple part</description>
  <form>
    <input name="title" type="TextLine">
      <label>Title</label>
      <occurrences minimum="1" maximum="1"/>
    </input>
  </form>
</part>
```

XP 8 - cms/parts/my-part/my-part.yaml

```yaml
kind: "Part"
title: "My Part"
description: "A simple part"
form:
- type: "TextLine"
  name: "title"
  label: "Title"
  occurrences:
    min: 1
    max: 1
```

### Content type descriptor

XP 7 - site/content-types/article/article.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<content-type xmlns="urn:enonic:xp:model:1.0">
  <display-name>Article</display-name>
  <super-type>base:structured</super-type>
  <form>
    <input name="title" type="TextLine">
      <label>Title</label>
      <occurrences minimum="1" maximum="1"/>
    </input>
  </form>
</content-type>
```

XP 8 - cms/content-types/article/article.yaml

```yaml
kind: "ContentType"
superType: "base:structured"
title: "Article"
form:
- type: "TextLine"
  name: "title"
  label: "Title"
  occurrences:
    min: 1
    max: 1
```

### Mixins renamed to Form Fragments

Mixins (XP 7) have been renamed to Form Fragments in XP 8. The `mixins` directory should be renamed to `form-fragments`.

XP 7 - site/mixins/address/address.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mixin xmlns="urn:enonic:xp:model:1.0">
  <display-name>Address</display-name>
  <form>
    <input type="TextLine" name="street">
      <label>Street</label>
      <occurrences minimum="0" maximum="1"/>
    </input>
  </form>
</mixin>
```

XP 8 - cms/form-fragments/address/address.yaml

```yaml
kind: "FormFragment"
title: "Address"
form:
- type: "TextLine"
  name: "street"
  label: "Street"
  occurrences:
    min: 0
    max: 1
```

### X-data renamed to Mixin

X-data has been renamed to Mixin in XP 8. The `x-data` directory should be renamed to `mixins`, and descriptor files updated accordingly.

XP 7 - site/x-data/myattachment/myattachment.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<x-data>
  <display-name>My Attachment</display-name>
  <form>
    <input name="myAttachment" type="AttachmentUploader">
      <label>My Attachment</label>
      <occurrences minimum="1" maximum="1"/>
    </input>
  </form>
</x-data>
```

XP 8 - cms/mixins/myattachment/myattachment.yaml

```yaml
kind: "Mixin"
title: "My Attachment"
form:
- type: "AttachmentUploader"
  name: "myAttachment"
  label: "My Attachment"
  occurrences:
    min: 1
    max: 1
```

### Macro descriptors

Macro descriptors must be converted from XML to YAML.

XP 7 - site/macros/my-macro/my-macro.xml

```xml
<macro>
  <display-name>Current user</display-name>
  <description>Shows currently logged user</description>
  <form>
    <input name="defaultText" type="TextLine">
      <label>Default text</label>
    </input>
  </form>
</macro>
```

XP 8 - cms/macros/my-macro/my-macro.yaml

```yaml
kind: "Macro"
title: "Current user"
description: "Shows currently logged user"
form:
- type: "TextLine"
  name: "defaultText"
  label: "Default text"
  occurrences:
    min: 0
    max: 1
```

### Styles

Style descriptor must be converted from XML to YAML.

XP7 - site/styles.xml

```xml
<styles css="styles/styles.css" xmlns="urn:enonic:xp:model:1.0">
  <image name="editor-image-skyscraper">
    <display-name>Skyscraper (9:21)</display-name>
    <aspect-ratio>9:21</aspect-ratio>
  </image>
  <image name="editor-image-sepia">
    <display-name>Old photo</display-name>
    <filter>sepia(25)</filter>
  </image>
</styles>
```

XP 8 - cms/style/style.yaml

```yaml
kind: "Style"
styles:
  - name: "editor-image-skyscraper"
    type: "Image"
    label: "Skyscraper (9:21)"
    aspectRatio: "9:21"
    editor:
      css: |
        <Here you should specify the CSS selectors for this style from the styles/styles.css file.>
  - name: "editor-image-sepia"
    type: "Image"
    label: "Old photo"
    filter: "sepia(25)"
    editor:
      css: |
        <Here you should specify the CSS selectors for this style from the styles/styles.css file.>
```

The `styles/styles.css` file must be removed.

### DateTime and Instant input types

The XP 7 `DateTime` input type with `true` has been split into a separate `Instant` type in XP 8. `DateTime` is now used exclusively for local date-time values (without timezone), while `Instant` represents a point in time.

XP 7 - DateTime with timezone (XML)

```xml
<input name="publishDate" type="DateTime">
  <label>Publish date</label>
  <config>
    <timezone>true</timezone>
  </config>
</input>
```

XP 8 - Instant (YAML)

```yaml
- type: "Instant"
  name: "publishDate"
  label: "Publish date"
```

XP 7 - DateTime without timezone (XML)

```xml
<input name="eventDate" type="DateTime">
  <label>Event date</label>
</input>
```

XP 8 - DateTime (YAML)

```yaml
- type: "DateTime"
  name: "eventDate"
  label: "Event date"
```

### Script Globals

`resolve` function no longer uses `src/main/resources/site` as its first root folder. Only `src/main/resources` is used as the root. If your scripts relied on resolving paths relative to the `site` folder, update them to use full paths from the resources root.

### HTTP functions

HTTP function method names were changed to uppercase to avoid conflicts with JavaScript reserved words and imported library methods.

The lowercase method names (`get`, `post`, `delete`, etc…​) are deprecated but still supported for backward compatibility. It is recommended to migrate to the new uppercase names (`GET`, `POST`, `DELETE`, etc…​).

> **Note:** The `all` function remains lowercase and has not been changed to uppercase.

XP 7 (deprecated but still works in XP 8)

```javascript
exports.get = function(req) {
    return {
        body: 'Hello World',
        contentType: 'text/plain'
    };
};

exports.post = function(req) {
    // Handle POST
};

exports.delete = function(req) {
    // Handle DELETE
};

exports.all = function(req) {
    // Handle all other methods
};
```

XP 8 (recommended)

```javascript
exports.GET = function(req) {
    return {
        body: 'Hello World',
        contentType: 'text/plain'
    };
};

exports.POST = function(req) {
    // Handle POST
};

exports.DELETE = function(req) {
    // Handle DELETE
};

exports.all = function(req) {
    // Handle all other methods
};
```

### System libraries

#### lib-admin

`getAssetsUri` method is removed. This method was never in use since XP 7.

`getBaseUri` method is removed. Use `getHomeToolUrl` instead as a drop-in replacement.

`getLocale` method is removed without replacement. This method was causing issues when first user preference did not match any localization files and English was chosen as default.

`getLocales` method is removed. Use `request.locales` instead.

`getPhrases` method is removed. Use `lib-i18n` `getPhrases` instead.

`getLauncherUrl` and `getLauncherPath` methods are removed. Launcher is a widget now and available via widgets API.

`lib-admin` no longer depends on `lib-portal`. You need to explicitly add `lib-portal` dependency to your project if you are using it.

XP 7

```groovy
dependencies {
    include "com.enonic.xp:lib-admin:${xpVersion}"
}
```

XP 8

```groovy
dependencies {
    include xplibs.admin
    include xplibs.portal
}
```

#### lib-node

`_inheritsPermissions` node property is removed. It can only be used as an argument in `create` method - to copy permissions from the parent node.

`setRootPermissions` method is removed. Use `applyPermissions` instead.

`modify` method is deprecated. Use `update` instead.

`editor` of deprecated `modify` method can no longer edit node permissions. Use separate call to `applyPermissions` method instead.

#### lib-content

Reading the project’s root content (path `/`) via `lib-content` (`get`, `getByPath`, etc.) now returns `null`. The root is reserved for the platform; use `lib-project` for project metadata (`get({id})`, `list()`) and create/move content under named paths only.

`move` and `rename` methods are merged into a single `move` method.

`setChildOrder` and `reorderChildren` methods are merged into a single `sort` method.

The `hasChildren` property has been removed from content.

`setPermissions` method is removed. Use `applyPermissions` instead.

`applyPermissions` method applies permissions on published and draft content simply.

`editor` of deprecated `modify` method can no longer edit content permissions. Use separate call to `applyPermissions` method instead.

`modify` method is deprecated. Use `update` instead.

`modifyMedia` method is deprecated. Use `updateMedia` instead.

`delete` method is renamed to `deleteContent` to avoid conflicts with the JavaScript reserved word. The old `delete` export is still available for backward compatibility, but it’s recommended to use the new name directly.

XP 7

```typescript
import {delete as deleteContent} from '/lib/xp/content';
```

XP 8

```typescript
import {deleteContent} from '/lib/xp/content';
```

#### lib-project

`delete` method is renamed to `deleteProject` to avoid conflicts with the JavaScript reserved word. The old `delete` export is still available for backward compatibility, but it’s recommended to use the new name directly.

XP 7

```typescript
import {delete as deleteProject} from '/lib/xp/project';
```

XP 8

```typescript
import {deleteProject} from '/lib/xp/project';
```

**`readAccess: { public }` → `publicRead: boolean`.** `create({readAccess: {public: true}})` is now `create({publicRead: true})`. The `Project` shape returned by `get` / `list` / `create` carries `publicRead` instead of `readAccess.public`. The nested-object form has been removed entirely; there is no backward-compat shim.

**`modifyReadAccess` → `setPublicRead`.** Same flat shape:

```typescript
// XP 7
import {modifyReadAccess} from '/lib/xp/project';
modifyReadAccess({id: 'p', readAccess: {public: true}});

// XP 8
import {setPublicRead} from '/lib/xp/project';
setPublicRead({id: 'p', publicRead: true});
```

**`modify` now takes an `editor` function** instead of optional setter-style fields. Fields the editor doesn’t touch are left unchanged; setting `description`, `language`, or `siteConfig` to `null` clears them. `displayName` cannot be cleared.

```typescript
// XP 7
import {modify} from '/lib/xp/project';
modify({id: 'p', displayName: 'New name', language: 'no'});

// XP 8
import {modify} from '/lib/xp/project';
modify({
    id: 'p',
    editor: (project) => {
        project.displayName = 'New name';
        project.language = 'no';
        return project;
    }
});
```

#### lib-repo

`delete` method is renamed to `deleteRepo` to avoid conflicts with the JavaScript reserved word. The old `delete` export is still available for backward compatibility, but it’s recommended to use the new name directly.

XP 7

```typescript
import {delete as deleteRepo} from '/lib/xp/repo';
```

XP 8

```typescript
import {deleteRepo} from '/lib/xp/repo';
```

`create` method `settings` param is removed. This was a direct exposure of internal implementation details.

#### lib-scheduler

`delete` method is renamed to `deleteJob` to avoid conflicts with the JavaScript reserved word. The old `delete` export is still available for backward compatibility, but it’s recommended to use the new name directly.

XP 7

```typescript
import {delete as deleteJob} from '/lib/xp/scheduler';
```

XP 8

```typescript
import {deleteJob} from '/lib/xp/scheduler';
```

#### lib-cluster

`isMaster` method is deprecated. Use `isLeader` instead.

#### lib-i18n

`localize` method no longer accepts `application` parameter - because application load order is not guaranteed, trying to load foreign application localization might fail. Required localize phrases should be copied over the applications instead.

Methods no longer use the undocumented `/site/i18n/phrases` bundle location by default. Only the standard `/i18n/phrases` location is used. If your application relied on `/site/i18n/phrases`, move the files to `/i18n/phrases` or use your own custom bundle location.

#### lib-task

`submitNamed` method is removed. Use `submitTask` instead.

`submit` method is removed. Use `executeFunction` instead.

#### lib-auth

`login` method `idProvider` parameter now defaults to `system` if not provided, instead of trying all available id providers. It is also not possible to specify multiple values anymore. This change ensures consistent id provider selection during login.

### lib-context

`run` method `context.user.idProvider` parameter now defaults to `system` if not provided, instead of trying all available id providers.

#### lib-export

**exportNodes**

`includeNodeIds` and `includeVersions` parameters are removed.

Exports are now stored as ZIP archives. The output file is named `{exportName}.zip` in the exports directory, replacing the previous folder-based structure.

> **Tip:** Folder-based exports from XP 7 should be converted to a ZIP archive before they can be imported in XP 8.

### Other libraries

#### lib-util

Lib util has been deprecated. If your app dependes on any of the methods from lib-util, you should migrate to using the corresponding standard TypeScript or JavaScript code where possible, or inline the relevant logic directly in your code.

Get more details at [https://github.com/enonic/lib-util/issues/196](https://github.com/enonic/lib-util/issues/196)

#### lib-guillotine

Lib guillotine has been deprecated for a long time, and is not supported for XP8. If your app uses lib-guillotine you need to migrate to the standard Guillotine app available on the Enonic Market: [https://market.enonic.com/vendors/enonic/guillotine](https://market.enonic.com/vendors/enonic/guillotine) before upgrading to XP8.

### HTTP Services

HTTP Services are now deprecated, but continues to work in XP 8. We recommend upgrading to Universal API instead.

Migrating to Universal API means the existing service endpoint URLs will change. Services were previously mounted under `/*/service//*`*, while Universal APIs are contextually available directly under `/`*`/:` in addition to the new `/api` mount point.

HTTP Services were "unsecure by default" by automatically mounting on admin tools, web-apps, and sites, while Universal APIs must be explicitly mounted via the respective descriptors where you need it.

Old services

```files
src/
  main/
    resources/
      services/
        coolservice/
          coolservice.xml
          coolservice.js
      myservice/
        myservice.js
        myservice.xml
```

New APIs

```files
src/
  main/
    resources/
      apis/
        coolservice/
          coolservice.yaml
          coolservice.js
        myservice/
          myservice.js
          myservice.yaml
```

Old service.xml

```xml
<service>
  <allow>
    <principal>role:system.admin</principal>
  </allow>
</service>
```

New api.yaml

```yaml
kind: "API"
allow:
  - "role:system.admin"
```

Use `portal.apiUrl()` instead of `portal.serviceUrl()` to generate URLs pointing to APIs.

Example of mounting "coolservice" API in an admin tool

```yaml
kind: "AdminTool"
title: "My Admin Tool"
allow:
  - "role:system.admin"
apis:
  - "coolservice"
```

### Assets service

The built-in assets service has been deprecated since XP 7.15. Replace it with one of:

- [lib-asset](https://developer.enonic.com/docs/lib-asset/stable) — best fit for site applications, where it integrates with the site service and content context.

- [lib-static](https://developer.enonic.com/docs/lib-static/stable) — designed for serving static files from contexts where lib-asset does not fit, such as ID providers and admin extensions.

### Widgets go Web Components

Dashboard and Context Panel Widgets were required to wrap their HTML with the `` tag. This requirement is now obsolete as widgets are now embedded as Web Components. However, this also means that each widget resides in its own Shadow DOM, so it no longer has access to styles in the main DOM of Content Studio. If your widget piggybacked on Content Studio’s styles, you’ll have to change the implementation so that the widget is using its own styles.

#### Assets

It’s no longer allowed to use `lib-asset` for generating URLs of widget assets, due to security reasons. Use [lib-static](https://developer.enonic.com/docs/lib-static/stable) (and `lib-router`) instead.

XP 7:

```typescript
import {render} from '/lib/mustache';
import {assetUrl} from '/lib/enonic/asset';

export function get() {
  const view = resolve('./widget.html');

  const params = {
    jsUri: assetUrl({
      path: 'js/extensions/widget.mjs'
    }),
    stylesUri: assetUrl({
      path: 'styles/extensions/widget.css'
    })
  };

  return {
    contentType: 'text/html',
    body: render(view, params)
  };
```

XP 8:

```typescript
import {render} from '/lib/mustache';
import {Request, Response} from '@enonic-types/core';
import {mappedRelativePath, requestHandler} from '/lib/enonic/static';
import Router from '/lib/router';

const STATIC_BASE_PATH = `/_static`;

type WidgetRenderer = (staticBaseUrl: string, req?: Request) => Response;

function createWidgetRouter(renderer: WidgetRenderer) {
  const router = Router();

  router.get('', (req: Request) => renderer(`${req.contextPath}${STATIC_BASE_PATH}`, req));

  router.get(`${STATIC_BASE_PATH}/{path:.*}`, (req: Request) => requestHandler(req, {
      index: false,
      root: '/asset',
      relativePath: mappedRelativePath(STATIC_BASE_PATH),
  }));

  return router;
}

const router = createWidgetRouter((staticBaseUrl: string, req: Request) => {
  const view = resolve('./widget.html');

  const params = {
      jsUri: `${staticBaseUrl}/js/widgets/widget.mjs`,
      stylesUri: `${staticBaseUrl}/styles/widgets/widget.css`
  };

  return {
      contentType: 'text/html',
      body: render(view, params)
  };
});

export const all = (req: Request) => router.dispatch(req);
```

### Javax to Jakarta

Most of the Java EE APIs have been migrated to Jakarta EE APIs. For instance `javax.servlet` is replaced with `jakarta.servlet`.

Jetty was updated to version 12.x and now uses Jakarta EE APIs.

### FasterXML Jackson JSON API

Java FasterXML Jackson JSON API is no longer a transitive dependency of XP Core API.

If you need to serialize or deserialize JSON in Java, you need to add the dependency to your project, preferably using a library different from XP internal one (FasterXML Jackson) to avoid conflicts.

We recommend using [https://github.com/FasterXML/jackson-jr](https://github.com/FasterXML/jackson-jr)

FasterXML Jackson Annotations `com.fasterxml.jackson.core:jackson-annotations` transitive dependency is still available in JAX-RS API.

### JAX-RS API

Java JAX-RS API is deprecated. It was not documented and used internally to implement legacy REST APIs.

If you have used JAX-RS API in your application, you need to migrate to the new XP 8 Universal API.

To know if you are using JAX-RS API, check for `com.enonic.xp:jaxrs-api` dependency in the project’s Gradle file.

### Dropwizard Metrics

Java Dropwizard Metrics is no longer available in XP Core API. Migrate to `com.enonic.xp.metrics` Core API.

### Java APIs

```
There are many changes in Java APIs, multiple classes were moved or renamed, as well as their methods. The intention was to keep the libraries as compatible as possible, while improving Java API design and removing unnecessary or confusing methods and classes.
```

The most noticeable changes are:

- Java methods and classes marked as `@Deprecated` were removed.

- Many classes and methods that were only used for internal implementation details and not intended for public use were removed.

- Methods that had names that could cause confusion with the libraries were renamed, for instance `ContentService.deleteWithoutFetch` renamed `ContentService.delete`.

- Classes that have direct replacement in Java 25 standard library were removed.

- `ContentService.update` method was split into 3 separate methods: `ContentService.update`, `ContentService.updateMedia` and `ContentService.updatePermissions`.

- Java Portal View Functions are no longer part of XP Core API. They were incorporated into lib-thymeleaf and lib-xslt libraries.

- `com.enonic.xp.page.DescriptorKey` moved to `com.enonic.xp.descriptor.DescriptorKey`.

- Concrete collection types like `LinkedList`, `HashMap`, etc. were replaced with corresponding interfaces like `List`, `Map`, etc.

- Javax Mail is no longer a transitive dependency of XP Core API.

- OSGi classes are no longer part of API. OSGi is still used internally in XP.
