<!-- src:https://developer.enonic.com/docs/code/stable/fundamentals/apps generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/fundamentals/apps.md

# Apps

An **Enonic app** is the unit of code you deploy to XP. It is a self-contained bundle that the platform installs, starts, configures, and tears down — and many apps coexist inside a single XP instance. This page covers what an app actually is at runtime, how XP runs several of them at once, and the lifecycle and configuration model around them.

## What is an app

An app is a software package — JavaScript/TypeScript modules, descriptors, schemas, assets — bundled and deployed together. Content Studio, the Headless API, and every webapp or site extension you write are all apps built with the Enonic Development Kit. XP itself is just the runtime that hosts them.

Each app is identified by an **app key** (e.g. `com.example.myapp`). The key is the namespace under which the app’s services, components, schemas, and configuration are reached.

## Bundles and module isolation

Every app deploys as its own bundle. The CommonJS module cache is scoped to the app: when code in app A calls `require('/lib/greet')`, it loads the `greet` module **from app A’s bundle**, never from app B. There is no shared global namespace and no implicit module sharing between apps.

The exception is **platform libraries** — modules whose path begins with `/lib/xp/` (e.g. `/lib/xp/content`, `/lib/xp/portal`). These are provided by XP itself and resolve identically from any app.

Composition between apps therefore happens at the **platform level**, not in JavaScript:

- A site can list multiple apps in its descriptor; each contributes components, mappings, processors, and contributions that the site service merges at request time.

- Admin tools and admin extensions from any installed app are listed in the admin Launcher and may mount each other through declared interface points.

- Universal APIs from any app are reachable under `/api/:`, and can be mounted as service points beneath sites, webapps, and admin tools belonging to other apps.

What apps cannot do is reach into another app’s private modules. Cross-app integration goes through the platform’s contracts (descriptors, mappings, events, APIs) — never through `require()`.

## Lifecycle

An app’s life inside XP follows a fixed sequence:

Install

The app bundle is uploaded to the cluster and registered. Installation alone does not run any of your code.

Start

XP starts the app on every cluster node. If the bundle contains [`main.ts`](docs/code/stable/fundamentals/main.md) at `src/main/resources/main.ts`, it is loaded and its top-level code runs once per node. Any `__.disposer()` registrations made during start are remembered for the stop phase.

Running

The app is reachable. HTTP functions, event listeners, scheduled tasks, components, and admin tools all become live. Modules are loaded lazily on first `require()` and cached for the lifetime of the deploy.

Stop

Before uninstall (or before a redeploy of a new version), XP stops the app on every node. Registered disposers are invoked. After stop, no further requests reach the app’s code.

Uninstall

The bundle is removed from the cluster.

The platform calls `main.ts` exactly once per app start, per node. Top-level code in any other module runs once on first `require()` and is then cached — see [Runtime: Loading and caching](docs/code/stable/fundamentals/runtime.md#loading_and_caching).

## Redeploy and module cache

Redeploying an app is conceptually a stop followed by a start with the new bundle. The module cache is invalidated, every module is re-loaded on first use, and `main.ts` runs again. Top-level state held in module variables does not survive a redeploy — treat it as ephemeral.

This makes hot iteration cheap during development (drop a new bundle on the file system; XP picks it up) and keeps the running model simple in production (no partial-update edge cases).

## Installation methods

Apps reach an XP instance through one of three channels:

Via CLI

Push the app via the management API using the Enonic CLI. The standard path for CI/CD pipelines and remote deploys.

Via Admin Console

Install manually through the **Applications** admin tool. Useful for installing from Enonic Market or uploading a JAR by hand.

Via the file system

Drop the JAR into the XP `deploy/` folder. Used during development and for specialized deployment scenarios. File-system deploys are local to a single node and override apps installed via the other channels.

For deployment, scaling, and isolation details that are platform-level rather than developer-level, see the [XP platform documentation](https://developer.enonic.com/docs/platform).

## Configuration

Each app may read configuration from a `.cfg` file (e.g. `com.example.myapp.cfg`) placed in the XP configuration directory. Configuration is a simple key/value text format and is exposed to the app at runtime through the platform’s configuration APIs.

The file format, location, and reload behavior are documented in the [XP platform documentation](https://developer.enonic.com/docs/platform/xp8/config).
