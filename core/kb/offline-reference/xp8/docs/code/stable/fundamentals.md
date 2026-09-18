<!-- src:https://developer.enonic.com/docs/code/stable/fundamentals generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/fundamentals.md

# Fundamentals

The execution model and the core building blocks every Enonic app uses — regardless of whether it serves an API, a webapp or a site.

## What’s in this section

This section documents the parts of an app that are not tied to a specific HTTP service or background mechanism. Read the runtime overview first to understand what powers your code, then dip into the rest as needed.

Runtime

How XP executes server-side JavaScript — the JVM-hosted engine, threading model, clustering, and the platform features your code inherits for free.

TypeScript

TypeScript is the authoring language for Enonic apps — set it up first. How to install and use the official `@enonic-types` packages so your editor and build understand the platform APIs.

Types

The shared types that flow across the libraries — principals, binary streams, the content object, page components — defined once in `@enonic-types/core` and referenced from every library page.

Apps

What an Enonic app is, how XP runs many of them at once, and the install/start/stop/redeploy lifecycle. Covers bundle isolation, cross-app composition, and configuration.

Functions

How modules and exported functions form the building blocks of an app. Covers the CommonJS module system, the bundle boundary, module caching, and the framework contracts that bind specific exports to triggers (HTTP requests, events, scheduled times, lifecycle).

Main

The `main.ts` lifecycle hook — code that runs when your app starts and stops.

Globals

Global objects and functions available in every module — `app`, `log`, `require`, `resolve`, and friends.

Events

The cluster-wide pub/sub bus. Publish from anywhere — request handlers, tasks, `main.ts` — and subscribe to platform events (content writes, repo updates) or your own custom domain events.

Localization

Localizing text in your app and the schemas it deploys, using `phrases` files and the localization API.

Java bridge

Calling JVM code from JavaScript via the `__` global. Required reading for library authors and anyone integrating with existing Java codebases.

## How the parts relate

The runtime is the foundation: a JVM-based execution environment with a CommonJS module system, multithreading, clustering, and a platform’s worth of services attached. Functions are the units of code the runtime invokes — most of what you write is regular module code, with a smaller subset bound to framework contracts. `main.ts` is the lifecycle contract. Events are the cluster-wide pub/sub primitive, available from any function. Globals, TypeScript, the Java bridge, and localization are tools you reach for inside any function, regardless of which contract called it.

For HTTP-bound contracts (request handlers, filters, error handlers, websockets, SSE, ID providers), see [Web](docs/code/stable/web.md). For asynchronous background execution (tasks, scheduled jobs), see [Background](docs/code/stable/background.md).
