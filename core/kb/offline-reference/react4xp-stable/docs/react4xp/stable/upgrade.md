<!-- src:https://developer.enonic.com/docs/react4xp/stable/upgrade generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC docs/react4xp/stable/upgrade.md

# Upgrade from XP 7 to XP 8

React4XP 7 runs on Enonic XP 8, which React4XP 6 applications runs on XP 7. Moving to React4XP 7 means upgrading the application itself from XP 7 to XP 8. This is a source-level upgrade, not an in-place version bump.

The upgrade has two parts:

- The standard **XP 7 to XP 8 application upgrade** - YAML descriptors, the new Gradle build and the code-level breaking changes. This is identical for any XP application and is covered by the generic guide.

- A handful of **React4XP-specific** changes on top - dependency versions, build tooling, the new types and mounting the React4XP API.

This page documents only part 2. Do the standard upgrade first, then apply the [React4XP specifics](#react4xp-specifics) below.

## Standard XP 7 to XP 8 upgrade

Upgrade the application to XP 8 exactly as you would any other XP app - convert the XML descriptors to YAML, move to the new Gradle build, and apply the code-level breaking changes. The complete, up-to-date procedure and breaking-change list live in the canonical guide, so follow that rather than repeating it here:

> **Tip:** [Upgrading to XP 8](https://developer.enonic.com/docs/code/stable/upgrade) - the generic XP 7 to XP 8 upgrade guide.

The fastest path through it is the **xp-app-upgrader** skill for [Claude Code](https://claude.com/claude-code).

```
/plugin marketplace add enonic/ai-enonic-marketplace
/plugin install enonic-skills@enonic-marketplace
```

Then, from your application’s project directory, ask Claude to upgrade it:

> **Note:** Neither the generic guide nor the skill covers the React4XP-specific steps below - apply them once the standard XP 8 upgrade builds cleanly.

## React4XP specifics

On top of the standard XP 8 upgrade, a React4XP application needs the following.

### Update the dependencies

Move to the version 7 React4XP packages and the XP 8 types.

package.json

```json
"@enonic/react4xp": "7.0.0",
"@enonic/react-components": "^7.0.0",
"@enonic-types/lib-react4xp": "^7.0.0",
"@enonic-types/global": "^8.0.3",
```

And the React4XP library in the Gradle build:

build.gradle

```groovy
dependencies {
    include 'com.enonic.lib:lib-react4xp:7.0.0'
}
```

> **Note:** `@enonic-types/global` 8 brings in `@enonic-types/core`, which replaces the old `@enonic/js-utils` request type - see [Update to the new types](#update-types) below.

### Mount the React4XP API

XP 8 serves React4XP’s compiled assets and SSR endpoints through a `react4xp` web API that must be mounted in the site descriptor - and in any webapp or admin tool that renders React4XP:

src/main/resources/cms/site.yaml

```yaml
kind: "Site"
apis:
  - "asset"
  - "react4xp"
```

### Switch to the new build tooling

React4XP 7 changes how the application is compiled:

- Server-side TypeScript is compiled with [tsdown](https://tsdown.dev) - add `tsdown` and `@swc/core` to `devDependencies`. React entries (`.tsx`) are still compiled by React4XP with Rspack.

- React4XP uses Rspack’s native CSS support, so the old `mini-css-extract-plugin` is gone. CSS Modules work out of the box for `**.module.css**`** and ``**`.module.scss` files.

> **Tip:** The easiest way to get the exact, up-to-date build configuration (`tsdown.config.ts`, `react4xp.config.js`, `webpack.config.react4xp.js` and the `tsconfig.json` files) is to copy them from the [React4XP starter](https://github.com/enonic/starter-react4xp).

Update the npm scripts so the build runs tsdown (server code and client assets) and React4XP (the `.tsx` entries), with the type checks split into the React4XP and server projects:

package.json

```json
"scripts": {
  "build":                "tsdown",
  "build:react4xp":       "npm explore @enonic/react4xp -- npm run build:react4xp",
  "check":                "concurrently -c auto -g --timings npm:check:types:*",
  "check:types:react4xp": "npx tsc --noEmit -p src/main/resources/react4xp/tsconfig.json",
  "check:types:server":   "npx tsc --noEmit -p src/main/resources/tsconfig.json"
}
```

### Update to the new types

React4XP 7 builds on `@enonic-types/core`. In your functions and processors, replace `Enonic.Xp.Http.Request` from `@enonic/js-utils/types/Request` with `Request` from `@enonic-types/core`.

## Build and deploy

Make a production build and deploy it to your sandbox:

```shell
enonic project build
```

```shell
enonic project deploy
```

You can also run the project in development mode, which watches for changes and automatically deploys them to the sandbox:

```shell
enonic dev
```
