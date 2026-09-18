<!-- src:https://developer.enonic.com/docs/react4xp/6.x/legacy-upgrade generated:2026-07-30T04:18:15Z format:llm-dense react4xp-6.x -->
#DOC docs/react4xp/6.x/legacy-upgrade.md

# Legacy mode upgrade

Version 6 is still compatible with how parts are rendered in version 5 (where each part is a separate entry).

This means you may perform a partial upgrade of your application, where you will not be using the Component Registry.

Follow the steps below:

## Upgrade XP

Set the XP version of your app to 7.15 or newer

gradle.properties

```properties
xpVersion = 7.15.1
```

## Upgrade package.json

- Use latest React4XP types

```json
"@enonic-types/lib-react4xp": "^6.0.0",
```

- Use latest React4XP runtime library

```json
"@enonic/react4xp":       "^6.0.0",
```

- Add global Enonic types (includes core transitively)

```json
"@enonic-types/global":   "^7.15.1",
```

```
NOTE: this brings in `@enonic-types/core`:
[source]
----
├─┬ @enonic-types/global@7.15.1
│ └── @enonic-types/core@7.15.1
----
```

- Add React component library

```json
"@enonic/react-components": "^6.0.0",
```

- Add small utility deps

```json
"clsx":             "^2.1.1",     // lightweight className helper
"core-js":          "^3.39.0",    // standard ES polyfills
```

- Add CSS-Modules typing & plugin

```json
"@types/css-modules":           "^1",
"typescript-plugin-css-modules": "^5",
```

- Remove obsolete CSS extractor

```json
// delete this line:
"mini-css-extract-plugin": "^2",
```

- Consolidate TypeScript checks Replace the old `verify:*` scripts with the new `check:*` suite:

```json
"scripts": {
  // remove these:
  "verify:types":                 "concurrently -r npm:verify:types:*",
  "verify:types:guillotineRequest":"npx tsc --noEmit -p tsconfig.guillotineRequest.json",
  "verify:types:react4xp":         "npx tsc --noEmit -p tsconfig.react4xp.json",
  "verify:types:xp":               "npx tsc --noEmit -p tsconfig.xp.nashorn.json",

  // add these in their place:
  "check":                        "concurrently -c auto -g --timings npm:check:types:*",
  "check:types:node":             "npx tsc --noEmit -p tsconfig.node.json",
  "check:types:react4xp":         "npx tsc --noEmit -p tsconfig.react4xp.json",
  "check:types:xp":               "npx tsc --noEmit -p tsconfig.xp.nashorn.json"
}
```

## Folder structure

The folder structure of your React4XP application can stay intact

This layout ensures XP can discover your React4XP assets (under react4xp/), site controllers (under site/), static files, and shared TS types.

## Upgrade Build.gradle

- Add schema, assets to your dependencies and update lib-react4xp

```groovy
    include "com.enonic.xp:lib-schema:${xpVersion}"
    include 'com.enonic.lib:lib-asset:1.0.1'
    include 'com.enonic.lib:lib-react4xp:6.0.0'
```

- Inject npm-based type-checks

```groovy
tasks.register('npmCheck', NpmTask) {
dependsOn npmInstall
args        = ['run','check']
environment = ['FORCE_COLOR':'true']
}
check.dependsOn npmCheck
```

- Enhance React4XP build task with NODE_ENV logic

```groovy
tasks.register('react4xp', NpmTask) {
    def envMode = project.hasProperty( 'env' ) ? ( project.property( 'env' ) == 'prod' ? 'production' : 'development' ) : 'production'
    args = [
        'run', 'build:react4xp'
    ]
    dependsOn( npmInstall )
    description 'Compile react4xp resources'
    environment = [

        ...
        'NODE_ENV': envMode
    ]

    ...
    println "Environment set to: $envMode"
```

- Pass `-Penv=dev` flag in the dev task

```groovy
tasks.register('dev', Exec) {
    if (System.getProperty('os.name').toLowerCase().contains('windows')) {
        commandLine 'gradlew.bat', 'deploy', '-Penv=dev', '-t'
    } else {
        commandLine './gradlew', 'deploy', '-Penv=dev', '-t'
    }
}
```

## Upgrade webpack

webpack.config.react4xp.js

- Remove old CSS-extract plugin import and pull in Rspack core

Old:

```js
  // const MiniCssExtractPlugin = require('mini-css-extract-plugin');
  const rspack = require('@rspack/core');
```

- Swap out the loader reference in your SCSS rule

```js
// MiniCssExtractPlugin.loader,
rspack.CssExtractRspackPlugin.loader,
```

- Update your CSS-loader options to disable ES-module output

```js
{
loader: 'css-loader',
options: {
importLoaders: 1,
modules: { auto: true },
esModule: false
}
}
```

> **Note:** `esModule: false` makes the loader emit CommonJS rather than ES-module exports.

- Add a font-asset rule for WOFF/TTF/etc.

```js
config.module.rules = [

...

{
test: /\.(woff|woff2|eot|ttf|otf)$/i,
type: 'asset/resource'
},
]
```

- Replace the plugin instantiation with Rspack’s CSS extractor

```js
	config.plugins = [
		...(config.plugins || []),
		new rspack.CssExtractRspackPlugin({
			chunkFilename: '[id].[contenthash:9].css',
			filename: '[name].[contenthash:9].css',
		})
	]
```

## Upgrade to new types

- V6 uses @enonic/types-core so you need to replace the old js-utils Request with the new one.

- [Replace](#update-request) "Enonic.Xp.Http.Request" from '@enonic/js-utils/types/Request' with “Request” from @enonic/types-core.

## Make production build and deploy

```shell
enonic project build
```

```shell
enonic project deploy
```

You can also run the project in development mode, which will watch for changes and automatically deploy them to the sandbox:

```shell
enonic dev
```

```shell
enonic project dev
```

## Migrating parts

In react4xp v5 the example controller looks like this:

src/main/resources/site/parts/example/example.ts

```
import {render} from '/lib/enonic/react4xp';
import {getComponent} from '/lib/xp/portal';
import type {Enonic} from '@enonic/js-utils/types/Request';
import {toStr} from './toStr';

export function get(request: Enonic.Xp.Http.Request) {

    const component = getComponent();
    log.debug('component:%s', toStr(component));

    const props = {};

    const response = render(
        component,
        props,
        request,
        {
            ...
        }
    );

    return response;
}
```

V6 uses @enonic/types-core so you need to replace the old js-utils Request with the new one.

- Replace "Enonic.Xp.Http.Request" from '@enonic/js-utils/types/Request' with “Request” from @enonic/types-core.

This is how the upgraded component looks like: .src/main/resources/site/parts/example/example.ts

```
import {render} from '/lib/enonic/react4xp';
import {getComponent} from '/lib/xp/portal';
import {Request} from '@enonic-types/core';
import {toStr} from './toStr';

export function get(request: Request) {

    const component = getComponent();
    log.debug('component:%s', toStr(component));

    const props = {};

    const response = render(
        component,
        props,
        request,
        {
            ...
        }
    );

    return response;
}
```

So far in this tutorial we have used componentRegistry to render and dataFetcher to invoke the processor for all components.

Since our old component does not have any processor and is rendered outside componentRegistry we need to exclude it so it becomes available for XP. We do this by updating site.xml:

src/main/resources/site/site.xml

```
<?xml version="1.0" encoding="UTF-8"?>
<site>
  <form/>
  <mappings>
    <mapping controller="/site/app.js" order="10"> (1)
      <pattern invert="true">/r4xp5.*</pattern>
    </mapping>
    <mapping controller="/site/component.js" order="10"> (2)
      <service>component</service>
    </mapping>
  </mappings>
</site>
```

Now we can use the v5 component with react4xp v6, we just need to make sure the url contains `/r4xp5`

## Migrating pages and layouts

As this is a breaking change you need to follow the recommended [guide](docs/react4xp/6.x/upgrade.md#page-layout) for migrating pages and layouts as these are dependent on the component registry.
