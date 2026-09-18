<!-- src:https://developer.enonic.com/docs/code/stable/fundamentals/runtime generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/fundamentals/runtime.md

# Runtime

What powers your Enonic app at execution time — the JVM-hosted JavaScript engine, the module system, the threading model, and the cluster-aware machinery you get for free.

## Execution model

Enonic XP runs on top of the Java Virtual Machine. Your app’s TypeScript and JavaScript files are executed by an embedded JavaScript engine, with full access to the JVM through the [Java bridge](docs/code/stable/fundamentals/java-bridge.md). There is no Node.js, no separate JS process, and no inter-process bridge — server-side JS runs inside the same JVM as the platform itself.

Two engines are available:

Nashorn

The default engine. Stable, production-ready, ships with every XP install. All XP releases since 7.x have shipped Nashorn.

GraalVM JavaScript

Available as an experimental alternative. Currently not recommended for production.

> **Note:** XP ships Nashorn as the default server-side JavaScript engine. GraalVM JavaScript is also available but is currently experimental and not recommended for production use.

### Language level

Nashorn implements ECMAScript 5.1, with only a subset of later (ES2015+) features. Server-side code must therefore run within that baseline: modern syntax and APIs beyond what the engine supports are not available at runtime unless your build down-levels or polyfills them. The official starters transpile to a conservative target (ES2015) for this reason. See [TypeScript](docs/code/stable/fundamentals/typescript.md) for the build step.

## Modules and bundling

Each `.ts` or `.js` file in your app is a module under the [CommonJS module specification](https://wiki.commonjs.org/wiki/Modules/1.1). Modules export values via `exports`, and consume other modules via `require()`. Paths are rooted at the app bundle, not the filesystem — `require('/lib/greet')` loads `src/main/resources/lib/greet.ts` from the same app.

Platform libraries are referenced by name (for example, `require('/lib/xp/content')`). See [Functions: Modules and the bundle](docs/code/stable/fundamentals/functions.md#modules_and_the_bundle) for the full path-resolution rules and bundle boundaries.

TypeScript is supported as the authoring language; the build step transpiles to JavaScript before deployment. See [TypeScript Definitions](docs/code/stable/fundamentals/typescript.md).

## Loading and caching

XP loads each module **once per app deploy** and caches it. Subsequent `require()` calls and subsequent triggers reuse the cached module — the file is not re-read or re-parsed. Top-level code in a module therefore runs exactly once per deploy.

This makes module top-level a natural place for one-time setup (requiring libraries, computing constants), but a poor place for mutable state. Treat anything declared outside a function body as immutable after load. For state that must survive between invocations, use a repo node, the `cache` library, or another explicit persistence mechanism.

See [Functions: Loading and caching](docs/code/stable/fundamentals/functions.md#loading_and_caching) for the implications on each function type.

## Threading

The runtime is multithreaded. The platform serves requests, dispatches events, and runs background tasks concurrently across multiple threads, taking advantage of multi-core CPU architectures. There is no single event loop — each request, task, or event listener runs on a worker thread from a managed pool.

Two consequences for your code:

- **Module-level state is shared across threads.** Cached modules are visible to every thread executing within the app. If two requests both call `require('/lib/cache')`, they receive the same module instance. Treat top-level state as read-only.

- **Implementations are reentrant.** A function may be invoked concurrently with itself. Don’t accumulate state in module-level variables across invocations.

## Clustering

XP can run as a single node or as a cluster of nodes sharing the same data. The runtime is cluster-aware out of the box:

- **Events** fire across the cluster. A listener registered on any node receives events published from any other node. See [Events](docs/code/stable/fundamentals/events.md).

- **Scheduled jobs** are distributed. A scheduled job runs on one cluster node per fire — XP coordinates so the same job doesn’t execute twice. See [Scheduler](docs/code/stable/background/scheduler.md).

- **Repositories** are replicated. Content writes propagate to all nodes; reads can target any node.

Apps deployed to a cluster are installed and started on every node. The runtime guarantees the same module-loading and caching semantics on each node — your app sees a consistent execution environment regardless of which node serves a given request.

## What you get for free

Apps run inside a fully equipped platform. The runtime gives you, without extra setup:

- **Persistence** — content, nodes, repositories, blobs, all queryable and clusterable.

- **HTTP routing** — the [Portal](docs/code/stable/web/request-response.md) dispatches incoming requests to four services (`/api`, `/admin`, `/site`, `/webapp`); you provide the implementations.

- **Identity & access management** — pluggable [ID providers](docs/code/stable/web/id-providers.md), role-based permissions, audit logging.

- **Cluster-wide events** — see [Events](docs/code/stable/fundamentals/events.md).

- **Background work** — [tasks](docs/code/stable/background/tasks.md) and [scheduled jobs](docs/code/stable/background/scheduler.md).

- **Localization** — see [Localization](docs/code/stable/fundamentals/i18n.md).

- **Java interop** — see [Java bridge](docs/code/stable/fundamentals/java-bridge.md).

Compatibility

An app built against any XP release runs unchanged on every patch and minor release within the same major version. Major version upgrades are documented separately — see [Upgrading](docs/code/stable/upgrade.md).
