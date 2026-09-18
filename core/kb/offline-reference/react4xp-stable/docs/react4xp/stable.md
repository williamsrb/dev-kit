<!-- src:https://developer.enonic.com/docs/react4xp/stable generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC docs/react4xp/stable.md

# React4XP 7 reference documentation

Server side React rendering for Enonic XP applications.

> **Tip:** **New to React4XP?** Visit our [React4XP tutorial](https://developer.enonic.com/learn/react4xp-tutorial) for a hands-on, guided introduction.

## Introduction

React4XP lets front-end developers build **Enonic XP applications with React**. React components are rendered [server-side](docs/react4xp/stable/ssr.md) and then [hydrated](docs/react4xp/stable/ssr.md#hydration) in the browser by default, so the same React code runs on both the server and the client (isomorphic rendering).

> **Note:** This documentation covers **React4XP 7.x**, which builds on **React 19** and requires **Enonic XP 8**.

## How React4XP is distributed

React4XP comes in two parts:

Library (lib-react4xp)

The Enonic XP library that does the rendering. It exposes the `render` and `processHtml` functions, the `DataFetcher` class and the `React4xp` object - all documented in the [Library reference](docs/react4xp/stable/library.md). Available on [Enonic Market](https://market.enonic.com/vendors/enonic/react4xp-lib) and [GitHub](https://github.com/enonic/lib-react4xp). Your React sources are compiled by the companion npm build tool `@enonic/react4xp` ([npm](https://www.npmjs.com/package/@enonic/react4xp)).

Starter (starter-react4xp)

A ready-to-run project that bundles the library, the `@enonic/react4xp` build integration, and a Hello world setup - so `enonic project create` gives you a working React4XP setup in one step. Documented in the [Starter reference](docs/react4xp/stable/starter.md); available on [Enonic Market](https://market.enonic.com/starters/react4xp-starter) and [GitHub](https://github.com/enonic/starter-react4xp).

A fully working demo application is available on [Enonic Market](https://market.enonic.com/vendors/enonic/react4xp-demo).

## In this reference

- [Starter](docs/react4xp/stable/starter.md) - the project layout, defaults and build pipeline the rest of this reference assumes.

- [Library reference](docs/react4xp/stable/library.md) - the `render` / `processHtml` functions and the `React4xp` object.

- [SSR engine](docs/react4xp/stable/ssr.md) - server-side rendering, [hydration](docs/react4xp/stable/ssr.md#hydration) and the rendering internals.

- [Configuration](docs/react4xp/stable/config.md), [Build](docs/react4xp/stable/build.md), [Chunks](docs/react4xp/stable/chunks.md) and [Entries](docs/react4xp/stable/entries.md) - compilation and runtime internals.

- [App.ts](docs/react4xp/stable/app.md) and [Macros](docs/react4xp/stable/macro-data.md) - the app function and macro data.

- [Release notes](docs/react4xp/stable/release.md) and [Upgrade notes](docs/react4xp/stable/upgrade.md).
