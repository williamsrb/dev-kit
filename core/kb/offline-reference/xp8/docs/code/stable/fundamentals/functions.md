<!-- src:https://developer.enonic.com/docs/code/stable/fundamentals/functions generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/fundamentals/functions.md

# Functions

Every `.ts` or `.js` file in an Enonic app is a **module** whose exported functions are callable from anywhere else in the bundle. On top of this module system, the framework defines **contracts** that bind specific files — or specific exports within them — to triggers such as an HTTP request, an event, a scheduled time, or the app’s own lifecycle.

> **Tip:** Code examples throughout the documentation use TypeScript. Strip the type annotations for plain JavaScript.

## Modules and the bundle

Each source file is a CommonJS module. Declare the functions and values the module exposes on `exports`:

```typescript
// /lib/greet.ts
exports.hello = (name: string): string => `Hello, ${name}`;
```

Require the module from any other file in the app by its absolute path within the bundle:

```typescript
// /webapp/webapp.ts
const greet = require('/lib/greet');

exports.GET = () => ({
  body: greet.hello('World')
});
```

Paths are rooted at the app bundle — not the filesystem and not the running server. Platform libraries are required by name (for example, `require('/lib/xp/content')`). See [the `require` global](docs/code/stable/fundamentals/globals.md#require) for the full resolution rules.

The bundle is also the boundary: modules in one app cannot require modules in another app directly. Cross-app integration goes through XP’s explicit mechanisms — events, services, or shared content.

## Loading and caching

XP loads each module once per app deploy and caches it. Subsequent `require` / `import` calls and subsequent triggers reuse the cached module — the file is not re-read or re-parsed.

Two consequences worth knowing:

- **Top-level code runs exactly once per app deploy.** Use it for one-time setup — requiring libraries, building lookup tables, computing constants. Code outside a function body will not execute again until the app is redeployed.

- **Top-level state is immutable once cached.** Assigning to a top-level variable from inside a function is **not supported**. XP makes no guarantees about consistency across requests, threads, or cluster nodes — treat anything declared outside a function as read-only after load.

This applies to every module in the app, but it surfaces most visibly in implementation files: their top-level runs lazily at first trigger, so any setup work happens then. For state that must survive between invocations, use a repo node, the `cache` library, or another explicit persistence mechanism — never the module’s own top-level.

## Framework contracts

Most of what you write is regular module code your own files require and orchestrate. A smaller subset of files follow a **contract** the framework enforces: the file sits at a conventional location (or is pointed to by a descriptor), and the framework looks for specific named exports and invokes them when its trigger fires.

The pattern is the same across every contract:

- The file is placed at a conventional location, or registered via a descriptor.

- The file exports one or more named functions whose names match the contract.

- The framework resolves the file, calls the appropriate export when its trigger fires, passes the arguments defined by the contract, and handles the return value.

The [framework globals](docs/code/stable/fundamentals/globals.md) (`app`, `log`, `require`, etc.) are available inside every function — contract-bound or not. Context propagation, error handling, and the module system work identically across all function types.

## Types of contracts

HTTP functions

Respond to HTTP requests. Exports match HTTP methods (`GET`, `POST`, `DELETE`, `PATCH`, …) plus an `all` fallback. Receive a Request, return a Response.

Filters

Wrap downstream HTTP functions with pre- and post-processing in the site or webapp pipeline.

Error handlers

Invoked when an exception bubbles out of an HTTP function. Receive the error plus the original request, return a Response.

Event listeners

Subscribe to the cluster-wide event bus. Receive the event payload; return value is ignored.

Tasks

Fire-and-forget background jobs. Receive a `params` object, report progress.

Scheduled jobs

Run on a cron or interval schedule. Same shape as tasks.

Websocket handlers

React to websocket lifecycle events (open, message, close, error).

Main lifecycle

`main.js` hooks that run when your app starts and stops.

Page, part, and layout implementations export HTTP functions invoked by the site service when rendering content — see [components](docs/code/stable/web/sites/components.md).
