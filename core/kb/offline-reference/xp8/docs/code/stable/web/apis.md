<!-- src:https://developer.enonic.com/docs/code/stable/web/apis generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/apis.md

# Universal APIs

A core feature of Enonic XP is the ability to build custom APIs and reuse them across the platform — aka the Universal API.

## Introduction

The Universal API is a powerful feature of the Enonic XP platform that lets developers create custom APIs. It enables applications to dynamically extend the platform’s API surface as they are installed.

## Request pipeline

A Universal API is not tied to a single URL — the same implementation is reachable as the [Web endpoint](#web-endpoint) (`/api/:`) and as a [service point](#service-point) inside the site, webapp, and admin services (`/_/:`). However it arrives, every request is gated the same way:

Access control

The API must be mounted on the location the request arrived through, and the caller must satisfy its `allow` list. Not mounted there returns **404**; a caller without access gets **401** or **403** (see the [descriptor](#descriptor)). The `allow` list is enforced on every request, regardless of endpoint.

<api-name>.ts

The matched API’s exported function for the request method (`GET`, `POST`, …) handles the request; subpaths arrive as `req.path`.

See [Where APIs are reachable](#where-apis-are-reachable) for the rules governing each mount point.

## Features

The main features of the Universal API are:

- Secure by default.

APIs are not mounted anywhere by default, so there is no risk of accidentally exposing an admin API on a site.

- Nobody can access an API without explicitly specifying access rights in the descriptor.

- APIs mount at a single, fixed location, never at arbitrary points along the URL.

- Headless friendly. APIs can be mounted under the `/api` endpoint, so they can be used by any client.

- Granular. Mounting must be explicitly specified in service descriptor files.

- Modular. APIs can be borrowed from other applications, so you can reuse existing APIs in your application.

## Usage

To create an API, place an implementation under `src/main/resources/apis/` in a folder matching its name, e.g. `src/main/resources/apis/myapi/myapi.ts`.

Example:

src/main/resources/apis/<api-name>/<api-name>.ts

```typescript
exports.GET = (req) => {
  return {
    body: {
      time: new Date()
    },
    contentType: 'application/json; charset=utf-8'
  };
};
```

### Subpath routing

A request to `/api/:/foo/bar` (or the equivalent service-point URL) reaches the same implementation; everything after the descriptor segment arrives as `req.path`. The implementation is free to dispatch on `req.path` any way it likes, but for anything beyond a couple of static endpoints, use the [router library](https://market.enonic.com/vendors/enonic/router-lib) for method dispatch, parameter extraction, and pattern matching.

### WebSocket and SSE

A custom API can act as a WebSocket channel or a Server-Sent Events stream, like any other HTTP function in XP. Return a `webSocket` or `sse` object from the request handler. See [WebSocket](docs/code/stable/web/websocket.md) and [SSE](docs/code/stable/web/sse.md) for the details.

## Descriptor

An API descriptor is required. It defines the API’s access control, the endpoints it is mounted on, and metadata such as title, description, and documentation URL.

Example of a full API descriptor:

src/main/resources/apis/<api-name>/<api-name>.yaml

```yaml
kind: "API"
title: "My API" (1)
description: "API for My App" (2)
documentationUrl: "https://developer.enonic.com/docs/api" (3)
mount: ["web"] (4)
allow: (5)
  - "role:system.admin"
  - "role:myapp.myrole"
```

| ****1** | **title** is the name of the API that will be shown in the UI. |
| --- | --- |
| ****2** | **description** is a short description of the API that will be shown in the UI. |
| ****3** | **documentationUrl** is a link to the API documentation that will be shown in the UI. |
| ****4** | By default, APIs are not mounted on the [Web endpoint](#web-endpoint). To enable it, add `"web"` to the `mount` list. |
| ****5** | APIs must list principals that have access to it. It is required to specify at least one principal. Use `role:system.everyone` to make the API public. |

> **Note:** A request to an API that is not mounted on the matched URL returns **404 Not Found** — the absence is indistinguishable from a missing API. A request by a principal not in the `allow` list returns **401 Unauthorized** if the configured ID provider asks for credentials, otherwise **403 Forbidden**. Calls to APIs mounted under `/admin/…​` additionally require the caller to hold `role:system.admin.login`, regardless of what the API’s `allow` list grants.

## Where APIs are reachable

A Universal API can be exposed through three **independent** axes — they don’t substitute for each other and any combination is valid:

- **Service point** — the API is mounted into a `site`, `webapp`, or `admin tool` service via that service’s descriptor.

- **Web endpoint** — the API opts in with `mount: "web"` and becomes reachable on the **Web** endpoint (the public XP port) under `/api/`.

- **Management endpoint** — the API opts in with `mount: "management"` and becomes reachable on the **Management** endpoint, which listens on its own port.

The `/api/` URL prefix is the same on both endpoints, but the two are served on **different ports**. The Management endpoint is not reachable through the Web endpoint and vice versa.

## Service point

In the `site`, `webapp`, and `admin` services, APIs are reachable as service points under the service’s URL space. The `_` segment separates the service’s content path from service paths (services, components, idprovider, and APIs):

- For the `site` service: `/site//_/:`

- For the `webapp` service: `/webapp//_/:`

- For the `admin` service: `/admin///_/:`

Each service descriptor declares the APIs it exposes via its `apis` list. For `webapp` and `admin` this is sufficient — the descriptor of the hosting application controls the mount. For `site`, two conditions must both hold:

- The application providing the site descriptor must be **configured on the site instance** Without this, the site descriptor’s `apis` list is not consulted at all for that site.

- That application’s site descriptor must list the API in its `apis` field.

The site mount is also limited to the **site root**: the path between `` and `/_/` must be the site’s root content path. Deeper content paths like `/site///some/page/_/:` do not resolve as APIs.

All three service descriptors use the same `apis:` list shape:

src/main/resources/cms/site.yaml

```yaml
kind: "Site"
apis:
  - "ws" (1)
  - "app:graphql" (2)
```

| ****1** | A bare name resolves to an API in the current application — here, `ws` defined in `src/main/resources/apis/ws/`. |
| --- | --- |
| ****2** | The `<app-key>:<api-name>` form mounts an API from a different application, letting the service borrow APIs deployed by other apps. |

The webapp and admin tool descriptors take the same `apis:` list:

src/main/resources/webapp/webapp.yaml

```yaml
kind: "WebApp"
apis:
  - "ws"
  - "app:graphql"
```

src/main/resources/admin/tools/<tool-name>/<tool-name>.yaml

```yaml
kind: "AdminTool"
apis:
  - "ws"
  - "app:graphql"
```

> **Note:** Wildcards and "expose all APIs from app X" rules are intentionally not supported here. Each API must be listed by its descriptor key. The reason is security: it prevents new or insecure APIs from being silently exposed on a service path when an app is upgraded or a new dependency is added. Publishing an additional API always requires an explicit change to the hosting descriptor.

## Web endpoint

The dedicated `/api` URL on the **Web** endpoint (the public XP port) exposes APIs independently of any service, so they can be consumed by any HTTP client:

- Generic API endpoint: `/api/:`

To opt in, an API must include `"web"` in its `mount` list (see [API descriptor](#descriptor)).

## Management Endpoint

> **Warning:** The `mount: "management"` feature is experimental and subject to change. The API shape, behavior, and configuration may change in future releases without the usual deprecation cycle. Avoid relying on it for production workloads.

> **Note:** The Management endpoint is for **advanced use only**. It is intended for extending XP’s management capabilities (cluster operations, internal tooling, infrastructure integrations) — not for regular application APIs.

An API can also be exposed on the **Management** endpoint by adding `"management"` to its `mount` list. The Management endpoint is a separate listener on its own port, distinct from the Web endpoint — use it for internal or operational APIs that should not be reachable from the public network.

src/main/resources/apis/<api-name>/<api-name>.yaml

```yaml
kind: "API"
title: "Cluster ops"
mount: ["management"]
allow:
  - "role:system.admin"
```

Both mounts can be combined: `mount: ["web", "management"]` makes the API reachable on both endpoints. The `allow` principal list is enforced on every request regardless of which endpoint served it.

## API discovery

`GET /api` (or `GET /api/`) returns a JSON index of every API mounted on the **endpoint that received the request**. Calling it on the Web endpoint lists APIs with `"web"` in `mount`; calling it on the Management endpoint lists APIs with `"management"` in `mount`. The response is a `resources` array, one entry per API:

```json
{
  "resources": [
    {
      "descriptor": "com.example.app:myapi",
      "application": "com.example.app",
      "name": "myapi",
      "title": "My API",
      "description": "API for my app",
      "documentationUrl": "https://example.com/docs",
      "mount": ["web"],
      "allowedPrincipals": ["role:system.admin", "role:myapp.role"]
    }
  ]
}
```

Behavior worth knowing:

- Service points (APIs mounted only under sites, webapps, or admin tools) do not appear in either listing.

- Both YAML-declared APIs and dynamically registered Java handlers are included.

- The listing is **not** filtered by the caller’s principals — clients see every API mounted on the endpoint and are expected to compare against the `allowedPrincipals` field themselves before invoking.

> **Note:** Discovery is intended for development. By default it is enabled only when XP runs in dev mode and disabled in production.

## apiUrl()

To safely generate an API URL, use the `apiUrl()` function from the [Portal library](docs/code/stable/libraries/lib-portal.md). It picks the right URL form based on the calling context — a service-point under the active service when called from a site, webapp, or admin tool, and `/api/` otherwise.

```typescript
const portalLib = require('/lib/xp/portal');

const url = portalLib.apiUrl({
    api: 'com.example.myapp:myapi', (1)
    path: '/items',                 (2)
    params: { id: '42' }            (3)
});
```

| ****1** | Descriptor key in `<app>:<api>` form. Required. |
| --- | --- |
| ****2** | Optional path appended after the API segment. Accepts a string or a string array. |
| ****3** | Optional query parameters. |

## Tracing

Each Universal API request emits a `universalAPI` trace event with the API descriptor key and response status, observable through XP’s standard tracing infrastructure.

## Reserved API application names

A few application names are reserved. This list includes but is not limited to:

- `media`

- `admin`

- `component`

- `attachment`

- `image`

- `asset`

- `service`

- `error`

- `idprovider`
