<!-- src:https://developer.enonic.com/docs/code/stable/web/webapps generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/webapps.md

# Webapps

The webapp service handles requests on the endpoint `:/webapp//*`.

## Introduction

Enonic is capable of delivering web applications natively, without the need for a 3rd party infrastructure. The webapp service provides a flexible platform for building applications of all kinds, from simple static sites to dynamic applications with server-side rendering, real-time updates, and more.

## Request pipeline

The webapp pipeline is executed as a subset of the [common pipeline](docs/code/stable/web.md#common_request_pipeline):

webapp.ts

Invokes the webapp’s matching HTTP function based on the request method.

Universal API

The webapp may optionally mount contextual [APIs](docs/code/stable/web/apis.md) which become available within the same URL space (e.g. `:/webapp//_/:`). These are mounted via the webapp descriptor.

> **Tip:** Visit the [Universal API section](docs/code/stable/web/apis.md#universal_apis) for details on how to implement these.

## Implementation

To turn an application into a webapp, place an implementation at `/src/main/resources/webapp/webapp.ts` that exports one function per HTTP method it handles (`GET`, `POST`, etc.) — see [HTTP functions](docs/code/stable/web/request-response.md).

Once deployed, the webapp is reachable at `:/webapp//` (e.g. `localhost:8080/webapp/my.webapp/`).

> **Note:** For anything beyond a couple of static endpoints, use the [router library](https://market.enonic.com/vendors/enonic/router-lib) for method dispatch, parameter extraction, and pattern matching.

## Descriptor

A webapp descriptor is **optional**. A webapp consisting of just `webapp.ts` runs without one.

The descriptor **can be used to mount [Universal APIs](docs/code/stable/web/apis.md) as service points**. Place a `webapp.yaml` alongside `webapp.ts` and list the APIs in its `apis:` field:

src/main/resources/webapp/webapp.yaml

```yaml
kind: "WebApp"
apis:
  - "ws"
  - "app:graphql"
```

Each listed API becomes reachable as a service point at `:/webapp//_/:`. See [Universal API: Service point](docs/code/stable/web/apis.md#service-point) for the full mounting rules.

## WebSocket and SSE

A webapp can act as a WebSocket channel or a Server-Sent Events stream, like any other HTTP function in XP. But we generally recommend contextually mounting WebSocket and SSE APIs via the [API service](docs/code/stable/web/apis.md) instead of using the webapp service directly.

## Tracing

Each webapp request emits a `renderApp` trace event with the application key and request path, observable through XP’s standard tracing infrastructure.
