<!-- src:https://developer.enonic.com/docs/code/stable generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable.md

# XP8 - Enonic Development Kit

The Enonic Development Kit (EDK) is the combined server-side TypeScript framework and tools for Enonic app development.

## Audience

Developers looking to extend or customize Enonic XP or Content Studio, you’ve come to the right place.

## Introduction

XP is highly modular: a single instance hosts many apps side by side. Each app is a self-contained bundle that can contribute [content schemas](docs/code/stable/schemas.md), custom [APIs](docs/code/stable/web/apis.md), [admin tools](docs/code/stable/web/tools.md) and [extensions](docs/code/stable/web/extensions.md), [ID providers](docs/code/stable/web/id-providers.md), [webapps](docs/code/stable/web/webapps.md), or full [websites](docs/code/stable/web/sites.md) — all powered by the same JS/TS runtime and the same standard [libraries](docs/code/stable/libraries.md).

Code in TypeScript, build and deploy your [Enonic app](docs/code/stable/fundamentals/apps.md) with full access to XP’s persistence, clustering, identity, scheduling, and HTTP machinery — powered by the [XP runtime](docs/code/stable/fundamentals/runtime.md), without Node.js, without a separate JS process, and with cluster-aware semantics out of the box.

## Tutorials

> **Important:** For a hands-on introduction to development with Enonic XP, visit the [Learning section](https://developer.enonic.com/learn).

## Where to start

Tooling

The CLI, sandboxes, starters, build system, and CI/CD setup that get you building quickly.

Fundamentals

The runtime, the app model, the module system, lifecycle hooks, and the cluster-wide event bus.

Web

The shared request pipeline, primitives (request/response, filters, error handlers, websockets, SSE), ID providers, and the four services XP dispatches to.

APIs, Admin Tools and Extensions, Sites, Webapps

The four services exposed by XP — custom APIs, admin UIs and extensions, CMS-driven sites, and standalone web applications.

Background

Tasks and scheduled jobs for asynchronous work.

Libraries

The platform’s standard libraries — content, repos, identity, mail, and more.
