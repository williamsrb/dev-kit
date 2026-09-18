<!-- src:https://developer.enonic.com/docs/react4xp/6.x/starter generated:2026-07-30T04:18:15Z format:llm-dense react4xp-6.x -->
#DOC docs/react4xp/6.x/starter.md

# React4XP starter

The React4XP starter is a ready-to-run Enonic XP application that wires together the [library](docs/react4xp/6.x/library.md), the `@enonic/react4xp` build tool and a working Hello world page.

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

| Enonic XP | 7.16.1 or later |
| --- | --- |
| Node | 22.15.1 or later |
| npm | 10.9.2 or later |

> **Note:** This page documents the starter’s `6.x` branch, which targets **Enonic XP 7** and **React4XP 6.x** (React 19). Create from it with `enonic project create -r starter-react4xp -b 6.x`. The `master` branch targets XP 8 and React4XP 7 - see the **7.x** documentation for that.

## Project structure

```
react4xp.config.js              (1)
webpack.config.react4xp.js      (2)
rspack.config.mjs               (3)
tsup.config.ts                  (4)
build.gradle                    (5)
gradle.properties
package.json
tsconfig.json
tsconfig.node.json              (6)
tsconfig.react4xp.json
tsconfig.xp.nashorn.json
src/main/resources/
├── application.svg
├── assets/                     (7)
├── site/
│   ├── site.xml                (8)
│   ├── app.ts                  (9)
│   ├── component.ts            (10)
│   ├── content-types/
│   ├── mixins/
│   ├── pages/
│   ├── processors/
│   └── x-data/
├── react4xp/
│   ├── entries/
│   │   └── App.tsx             (11)
│   ├── componentRegistry.tsx   (12)
│   ├── dataFetcher.ts          (13)
│   ├── components/
│   │   └── hello/              (14)
│   ├── constants.ts
│   └── utils/
├── services/
└── types/
    └── AppProps.ts
```

| ****1** | React4XP build configuration - entries and chunks. See [react4xp.config.js](docs/react4xp/6.x/build.md#react4xp.config.js). |
| --- | --- |
| ****2** | Webpack/RSpack customization. See [webpack.config.react4xp.js](docs/react4xp/6.x/build.md#webpack.config.react4xp.js). |
| ****3** | RSpack config for the client-side asset build. |
| ****4** | `tsup` config for server-side TypeScript and browser assets - everything **except** `.tsx`, which `@enonic/react4xp` owns. |
| ****5** | XP app plugin plus the `buildXpResources`, `react4xp` and `buildAssets` Gradle tasks. |
| ****6** | Three TypeScript projects - Node tooling, React4XP components and XP server code - each type-checked separately. See [Build pipeline](#build-pipeline). |
| ****7** | Static and client-only assets, served through `lib-asset`. |
| ****8** | Site descriptor with the catch-all mapping and the component service. |
| ****9** | The app function - handles all page rendering. See [App.ts](docs/react4xp/6.x/app.md). |
| ****10** | Component function enabling drag-and-drop in the visual page editor. |
| ****11** | The one and only React4XP [entry](docs/react4xp/6.x/entries.md). |
| ****12** | Maps content types and components to React components. |
| ****13** | Maps content types and components to server-side data processors. |
| ****14** | Example component: `Hello.tsx`, `Hello.module.css` and `HelloProcessor.ts`. |

## Defaults the starter sets

These are the values the rest of this reference assumes.

| Setting | Value | Reference |
| --- | --- | --- |
| `entryDirs` | `['entries']` | Entries are picked up from *src/main/resources/react4xp/entries/* - see [entryDirs](docs/react4xp/6.x/build.md#entryDirs) |
| `chunkDirs` | unset | Everything else under *react4xp/* bundles into the single `react4xp.*.js` chunk - see [chunkDirs](docs/react4xp/6.x/build.md#chunkDirs) |
| `globals` | empty | `react` and `react-dom` only - see [Chunks](docs/react4xp/6.x/chunks.md) |
| `externals` | empty | Nothing excluded from the bundle |
| Entry count | 1 (`App.tsx`) | The whole site renders through one entry - see [Single-entry architecture](#single-entry) |
| Webpack rules | CSS, CSS modules, Sass, fonts | Added on top of the built-in JSX/TSX rules - see [webpack.config.react4xp.js](docs/react4xp/6.x/build.md#webpack.config.react4xp.js) |

The starter ships no `.cfg` file - all [application config](docs/react4xp/6.x/config.md) options fall back to their defaults (SSR and hydration both enabled).

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

src/main/resources/site/site.xml

```XML
<?xml version="1.0" encoding="UTF-8"?>
<site>
  <form/>
  <mappings>
    <mapping controller="/site/app.js" order="10">
      <pattern invert="true">/r4xp5.*</pattern>   (1)
    </mapping>
    <mapping controller="/site/component.js" order="10">
      <service>component</service>   (2)
    </mapping>
  </mappings>
</site>
```

| ****1** | Matches everything **except** the internal React4XP routes. |
| --- | --- |
| ****2** | The `component` service mapping enables drag-and-drop in the visual page editor. |

React4XP’s assets are served by services that ship with the library, so nothing needs mounting - see [Asset serving](docs/react4xp/6.x/library.md#asset-serving).

See [App.ts](docs/react4xp/6.x/app.md) for the function itself.

## Build pipeline

`enonic project deploy` runs Gradle, which drives three independent npm builds:

| Gradle task | What it does |
| --- | --- |
| `buildXpResources` | Runs `tsup` over *src/main/resources* - compiles server-side `.ts` for XP’s JS engine |
| `react4xp` | Runs `@enonic/react4xp’s own RSpack/Webpack pipeline for all `.tsx` entries and chunks |
| `buildAssets` | Runs `tsup` over *assets/* - browser-only client code |

All three feed *build/resources/main*, and `jar` depends on all three. The division matters: **`.tsx` files belong to the React4XP build, everything else to `tsup`**. Server-side `.ts` files inside *react4xp/* - `dataFetcher.ts`, processors, utils - are server code and are compiled by `tsup`.

Useful scripts:

| Command | Purpose |
| --- | --- |
| `npm run watch` | `./gradlew -t deploy` - rebuild and redeploy on change |
| `npm run rewatch` | Clean, deploy, then watch |
| `npm run check` | Type-check all three TypeScript projects and lint |
| `npm run browserSync` | Proxy localhost:8080 with automatic browser reload |
| `npm test` | Jest, configured for both server and client environments |

### TypeScript projects

The starter keeps three separate TypeScript projects, because the three targets have incompatible requirements - `npm run check` type-checks each one:

| File | Scope |
| --- | --- |
| *tsconfig.xp.nashorn.json* | Server-side code running in XP’s Nashorn JS engine |
| *tsconfig.react4xp.json* | `.tsx` React components - DOM libs, `jsx: react` |
| *tsconfig.node.json* | Node-side build tooling and config files |

Inside React code, `/****`** resolves to *src/main/resources/react4xp/* and `/lib/xp/`** to the `@enonic-types` packages, so imports like `/types/AppProps` and `/lib/enonic/react4xp` work without relative paths.

## What the starter does not include

Deliberately out of scope - the starter is a foundation, not a template gallery:

- **No content types, pages, parts or layouts.** The *site/* subdirectories are empty placeholders. The Hello example is registered against the built-in `portal:site` content type.

- **No ready-made GraphQL queries.** `lib-guillotine` is on the classpath, but the starter renders through the `dataFetcher` rather than through Guillotine.

- **No styling framework.** Only CSS modules and Sass support in the webpack config.

- **No production config.** Add a `.cfg` file yourself to tune [SSR, hydration and globals](docs/react4xp/6.x/config.md).

## Version compatibility

| Starter ref | React4XP | Enonic XP | React |
| --- | --- | --- | --- |
| `master` (branch) | 7.x | 8.0.1+ | 19 |
| `6.x` (branch) | 6.1.0 | 7.16.1+ | 19 |
| `v5.1.0` (tag) | 5.1.0 | 7.13.3+ | 18 |

`v5.1.0` is the last tagged starter release; the 6.x and 7.x lines are maintained as branches. Older tags exist back to `v0.2.8` (XP 7.0.0) but are not supported.

To move from React4XP 5 to 6, see the [recommended upgrade](docs/react4xp/6.x/upgrade.md) or the [legacy mode upgrade](docs/react4xp/6.x/legacy-upgrade.md). For 6 to 7, switch to the **7.x** documentation.
