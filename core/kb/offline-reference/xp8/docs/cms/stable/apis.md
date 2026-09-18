<!-- src:https://developer.enonic.com/docs/cms/stable/apis generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/apis.md

# APIs

Enonic exposes content over HTTP under a common `/api/` prefix. The GraphQL API is the primary interface for headless delivery, while the Image and Attachment APIs serve media directly.

Custom **Functions** let you extend this surface with your own endpoints and background jobs.

## Which API do I use?

| You want to… | Use |
| --- | --- |
| Query or mutate content | [GraphQL API](docs/cms/stable/apis/graphql.md) |
| Render or transform images | [Image API](docs/cms/stable/apis/image.md) |
| Serve raw file downloads | [Attachment API](docs/cms/stable/apis/attachment.md) |
| Expose custom HTTP endpoints or run tasks | [Custom API](#custom-functions) |

## Authorization

Enonic provides a common authorization mechanism across all APIs, providing granular access control down to individual requests and content items.

Requests are evaluated in the context of the authenticated principal, and content permissions apply to every query — users only see content they are allowed to read.

By default, APIs are accessible to unauthenticated users with `READ` permission for `role:system.everyone`. To access protected content, authenticate requests by passing a bearer token in the `Authorization` header:

```bash
curl -X POST https://api.example.com/graphql \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ guillotine { get(key: \"/site/articles/hello\") { displayName } } }"}'
```

Unauthenticated requests run as the anonymous user and can still access content granted `READ` permission for `role:system.everyone`.

Visit the [security documentation](docs/platform/stable/security.md) for details on users, roles, and permissions in XP.

## GraphQL API

The GraphQL API is Enonic’s primary headless interface, provided by [Guillotine](https://market.enonic.com/vendors/enonic/guillotine) — a separately versioned app that exposes your content as a typed GraphQL schema. Content types, mixins, references, pages, and media are all reachable from a single endpoint, with per-user authorization enforced by XP’s IAM.

Default endpoint: `/api/guillotine:graphql`

See [GraphQL API](docs/cms/stable/apis/graphql.md) for endpoint details, authentication, and usage patterns.

## Image API

The Image API delivers and transforms bitmap images on the fly — resize, crop, format conversion, and quality adjustments — directly from URL parameters. It is the standard way for front-ends to load responsive image variants without pre-generating them.

Default endpoint: `/api/media:image/`

See [Image API](docs/cms/stable/apis/image.md) for URL structure, parameters, and caching behavior.

## Attachment API

The Attachment API serves the original, unprocessed bytes of any content attachment — documents, archives, video, audio, or any non-image media. Use it when you need the file as it was uploaded.

Default endpoint: `/api/media:attachment/`

See [Attachment API](docs/cms/stable/apis/attachment.md) for URL structure and download semantics.

## Management API

XP also exposes a web API for management. It is not part of the customer-facing content delivery and is not used by front-end clients. It requires administrator privileges to access.https://developer.enonic.com/docs/cli[Enonic CLI] is the default client that communicates with it.

- [Management API](docs/platform/stable/endpoints/management.md) — deploy applications, and run dumps, exports, and snapshots (port `4848`, administrator only).

## Custom API

Beyond the built-in APIs, you can implement your own custom **APIs** using Typescript functions deployed via Enonic apps.

You may:

- expose custom HTTP endpoints under `/api/:/`

- run scheduled or on-demand background tasks

- react to content events (publish, modify, delete) via listeners

- integrate with external systems, perform complex data processing, or implement custom business logic

See the [Enonic Development Kit](https://developer.enonic.com/docs/code) for how to scaffold, build, and deploy custom APIs.
