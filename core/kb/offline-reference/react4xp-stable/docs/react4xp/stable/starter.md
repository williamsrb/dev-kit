<!-- src:https://developer.enonic.com/docs/react4xp/stable/starter generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC docs/react4xp/stable/starter.md

# React4XP starter

The React4XP starter is a ready-to-run Enonic XP application that wires together the [library](docs/react4xp/stable/library.md), the `@enonic/react4xp` build tool and a working Hello world page.

Most of this reference describes React4XP relative to "the starter setup" - the conventions and default values below are what that refers to.

Source: [github.com/enonic/starter-react4xp](https://github.com/enonic/starter-react4xp) | [Enonic Market](https://market.enonic.com/starters/react4xp-starter)

> **Tip:** For a guided, hands-on walkthrough of building an app from the starter, use the [React4XP tutorial](https://developer.enonic.com/learn/react4xp-tutorial). This page documents **what the starter contains** and **which defaults it sets**.

## Creating a project

```bash
enonic project create -r starter-react4xp
```

The [Enonic CLI](https://developer.enonic.com/docs/enonic-cli) clones the starter, renames the app, and sets up a sandbox. Then build and deploy:

```bash
enonic project deploy
```

No separate `npm install` step is needed - the Gradle build runs it (see [Build pipeline](#build-pipeline)).

| Enonic XP | 8.0.1 or later |
| --- | --- |
| Node | 24.16.0 or later |
| npm | 11.13.0 or later |

> **Note:** The starter’s `master` branch targets **XP 8** and **React4XP 7.x** (React 19). The `6.x` branch holds the React4XP 6 line for XP 7, which uses the older *site/* directory with `site.xml` descriptors instead of the YAML descriptors described below.

## Project structure

```
react4xp.config.js              (1)
webpack.config.react4xp.js      (2)
tsdown.config.ts                (3)
build.gradle                    (4)
gradle.properties
package.json
src/main/resources/
├── enonic.yaml                 (5)
├── assets/                     (6)
├── cms/
│   ├── cms.yaml
│   ├── site.yaml               (7)
│   ├── app.ts                  (8)
│   └── component.ts            (9)
├── react4xp/
│   ├── entries/
│   │   └── App.tsx             (10)
│   ├── componentRegistry.tsx   (11)
│   ├── dataFetcher.ts          (12)
│   ├── components/
│   │   └── hello/              (13)
│   ├── constants.ts
│   ├── utils/
│   └── tsconfig.json
└── types/
    └── AppProps.ts
```

| ****1** | React4XP build configuration - entries and chunks. See [react4xp.config.js](docs/react4xp/stable/build.md#react4xp.config.js). |
| --- | --- |
| ****2** | Webpack/RSpack customization. See [webpack.config.react4xp.js](docs/react4xp/stable/build.md#webpack.config.react4xp.js). |
| ****3** | `tsdown` config for server-side TypeScript and browser assets - everything **except** `.tsx`, which `@enonic/react4xp` owns. |
| ****4** | XP app plugin plus the `npmBuild` and `react4xp` Gradle tasks. |
| ****5** | Application descriptor (title, vendor). |
| ****6** | Static and client-only assets, served through `lib-asset`. |
| ****7** | Site descriptor with the catch-all request mapping and mounted APIs. |
| ****8** | The app function - handles all page rendering. See [App.ts](docs/react4xp/stable/app.md). |
| ****9** | Component function enabling drag-and-drop in the visual page editor. |
| ****10** | The one and only React4XP [entry](docs/react4xp/stable/entries.md). |
| ****11** | Maps content types and components to React components. |
| ****12** | Maps content types and components to server-side data processors. |
| ****13** | Example component: `Hello.tsx`, `Hello.module.css` and `HelloProcessor.ts`. |

## Defaults the starter sets

These are the values the rest of this reference assumes.

| Setting | Value | Reference |
| --- | --- | --- |
| `entryDirs` | `['entries']` | Entries are picked up from *src/main/resources/react4xp/entries/* - see [entryDirs](docs/react4xp/stable/build.md#entryDirs) |
| `chunkDirs` | unset | Everything else under *react4xp/* bundles into the single `react4xp.*.js` chunk - see [chunkDirs](docs/react4xp/stable/build.md#chunkDirs) |
| `globals` | empty | `react` and `react-dom` only - see [Chunks](docs/react4xp/stable/chunks.md) |
| `externals` | empty | Nothing excluded from the bundle |
| Entry count | 1 (`App.tsx`) | The whole site renders through one entry - see [Single-entry architecture](#single-entry) |
| Webpack rules | CSS, CSS modules, Sass, fonts | Added on top of the built-in JSX/TSX rules - see [webpack.config.react4xp.js](docs/react4xp/stable/build.md#webpack.config.react4xp.js) |

The starter ships no `.cfg` file - all [application config](docs/react4xp/stable/config.md) options fall back to their defaults (SSR and hydration both enabled).

## Single-entry architecture

The starter does not create one entry per part or page. It registers a single entry, *entries/App.tsx*, and renders the whole content tree through it:

src/main/resources/react4xp/entries/App.tsx

```TypeScript
const App: React.FC<AppProps> = ({component, data, common, meta}) => {
    const compMeta: MetaData = meta as MetaData;
    compMeta.componentRegistry = componentRegistry;   (1)
    return <BaseComponent component={component} data={data} common={common} meta={compMeta}/>;  (2)
};
```

| ****1** | The registry tells `BaseComponent` which React component to use for each content type or component descriptor. |
| --- | --- |
| ****2** | `BaseComponent` from [`@enonic/react-components`](https://www.npmjs.com/package/@enonic/react-components) walks the component tree and renders each node. |

Two registries drive this, and adding a component means adding an entry to each:

src/main/resources/react4xp/componentRegistry.tsx

```TypeScript
export const componentRegistry = new ComponentRegistry();

componentRegistry.addContentType('portal:site', {View: Hello});
```

src/main/resources/react4xp/dataFetcher.ts

```TypeScript
export const dataFetcher = new DataFetcher();

dataFetcher.addContentType('portal:site', {processor: helloProcessor});
```

The `dataFetcher` runs server-side and produces the props; the `componentRegistry` maps them to a React component. The processor never runs in the browser:

src/main/resources/react4xp/components/hello/HelloProcessor.ts

```TypeScript
export const helloProcessor: ComponentProcessor<PageDescriptor> = (params) => {
    const title = params.content?.displayName || params.content._name || 'Display name not set';
    return {
        title: title,
        initialCount: 0,
    };
};
```

### Site mapping

The single entry works because the site descriptor routes every request to one function:

src/main/resources/cms/site.yaml

```YAML
kind: "Site"
mappings:
  - controller: "/cms/app.js"
    order: 10
    pattern: "/r4xp5.*"
    invertPattern: true          (1)
  - controller: "/cms/component.js"
    service: "component"
    order: 10
apis:
  - "asset"
  - "react4xp"                   (2)
```

| ****1** | Matches everything **except** the internal React4XP routes. |
| --- | --- |
| ****2** | Mounting the `react4xp` API is required on XP 8 - see [Mount the API](docs/react4xp/stable/library.md#mount-api). |

See [App.ts](docs/react4xp/stable/app.md) for the function itself.

## Build pipeline

`enonic project deploy` runs Gradle, which drives two independent npm builds:

| Gradle task | What it does |
| --- | --- |
| `npmBuild` | Runs `tsdown` - compiles server-side `.ts` to CommonJS/ES5 for XP’s JS engine, and browser assets under *assets/* to ESM |
| `react4xp` | Runs `@enonic/react4xp’s own RSpack/Webpack pipeline for all `.tsx` entries and chunks |

Both feed *build/resources/main*, and `jar` depends on both. The division matters: **`.tsx` files belong to the React4XP build, everything else to `tsdown`**. Server-side `.ts` files inside *react4xp/* - `dataFetcher.ts`, processors, utils - are server code and are compiled by `tsdown`.

Useful scripts:

| Command | Purpose |
| --- | --- |
| `npm run watch` | `./gradlew -t deploy` - rebuild and redeploy on change |
| `npm run rewatch` | Clean, deploy, then watch |
| `npm run check` | Type-check both TypeScript projects and lint |
| `npm run browserSync` | Proxy localhost:8080 with automatic browser reload |
| `npm test` | Jest, configured for both server and client environments |

### TypeScript projects

The starter keeps three separate `tsconfig.json` files, because the three targets have incompatible requirements:

| File | Scope |
| --- | --- |
| *src/main/resources/tsconfig.json* | Server-side code running in XP’s JS engine |
| *src/main/resources/react4xp/tsconfig.json* | `.tsx` React components - DOM + ES2015 libs, `jsx: react` |
| *src/main/resources/assets/tsconfig.json* | Browser-only assets |

Inside React code, `/****`** resolves to *src/main/resources/react4xp/* and `/lib/xp/`** to the `@enonic-types` packages, so imports like `/types/AppProps` and `/lib/enonic/react4xp` work without relative paths.

## What the starter does not include

Deliberately out of scope - the starter is a foundation, not a template gallery:

- **No content types, pages, parts or layouts.** The *cms/* subdirectories are empty placeholders. The Hello example is registered against the built-in `portal:site` content type.

- **No Guillotine/GraphQL setup.** Earlier starter versions shipped a ready-mapped Guillotine API; data now flows through the `dataFetcher` instead.

- **No styling framework.** Only CSS modules and Sass support in the webpack config.

- **No production config.** Add a `.cfg` file yourself to tune [SSR, hydration and globals](docs/react4xp/stable/config.md).

## Version compatibility

| Starter ref | React4XP | Enonic XP | React |
| --- | --- | --- | --- |
| `master` (branch) | 7.x | 8.0.1+ | 19 |
| `6.x` (branch) | 6.1.0 | 7.16.1+ | 19 |
| `v5.1.0` (tag) | 5.1.0 | 7.13.3+ | 18 |

The 6.x and 7.x lines are maintained as branches and were never tagged; `v5.1.0` is the last tagged starter release. Older tags exist back to `v0.2.8` (XP 7.0.0) but are not supported.

> **Note:** The 5.x starter predates the `componentRegistry`/`dataFetcher` model - it ships a Guillotine-based setup (`lib-guillotine`) instead, and builds with webpack rather than RSpack. Treat it as reference for legacy projects only.

For moving an existing app between these, see [Upgrade notes](docs/react4xp/stable/upgrade.md).
