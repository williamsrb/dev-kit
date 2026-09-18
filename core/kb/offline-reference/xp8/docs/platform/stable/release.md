<!-- src:https://developer.enonic.com/docs/platform/stable/release generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/release.md

# Release Notes

The headline features and themes for each XP feature release. For step-by-step upgrade instructions and the full breaking-change list, see [Upgrading to XP 8](docs/platform/stable/release/upgrade.md).

## XP 8

XP 8 is the largest release in 8 years. The runtime is rebuilt on a modern stack, the Universal API unifies how request handlers are written and called, and a long list of API rough edges has been cleaned up.

> **Important:** This release contains **Breaking changes when upgrading from XP7**. We have made every effort to minimize the impact of these, but please review the full list of breaking changes and migration steps in the [upgrade notes](docs/platform/stable/release/upgrade.md#breaking-changes) before upgrading. Several XP 7 concepts have also been renamed — see [A paradigm shift in naming](#naming).

### Stack update

The XP 8 core runs on a refreshed stack, including but not limited to: **Java 25**, **Jetty 12**, and **Hazelcast 5**. This also includes use of virtual threads for [tasks](docs/code/stable/background/tasks.md). The new stack provides better performance, stability, and security, and lays the foundation for future improvements.

### UI reloaded

XP 8 introduces a new admin UI built on the Enonic UI design system. The new UI is faster, more responsive, and provides a more consistent user experience across tools. The first tools to be migrated are the [XP menu](docs/platform/stable/admin.md) and the [Dashboard](docs/platform/stable/admin/dashboard.md). The remaining tools will be migrated in future releases.

### Universal API

Web APIs are now first-class citizens of Enonic XP. A uniform implementation pattern can be used to implement and expose APIs across the platform, including direct exposure via the brand new [/api](docs/platform/stable/endpoints/web.md#api) service endpoint.

Borrowing the manifest-and-mount pattern from Kubernetes, APIs are registered with a unique name and automatically integrated with the platform’s security and IAM. A matching set of libraries and tools makes it easy to [build custom APIs](docs/code/stable/web/apis.md) and call them from any context.

APIs can be exposed on custom URLs and domains via [virtual host configuration](docs/platform/stable/config/vhosts.md), but also contextually mounted within the admin and site services, allowing for flexible API design and organization.

### XP goes YAML

YAML replaces XML for all CMS schemas and app descriptors. This means content types, application definitions, ID providers, etc., are now all defined in YAML. YAML is a widely adopted format that is easier to read and write than JSON, especially for complex configurations - and it supports comments. The new YAML-based descriptors are more concise and maintainable, making life easier for developers. For the full documentation, visit the [schema system documentation](docs/code/stable/schemas.md).

Schemas are also now organized into [namespaces](docs/cms/stable/schemas/namespaces.md). Every schema is identified as `:`. When shipping schemas with an app, the app name is still the default namespace - but the namespace concept decouples schemas from apps, paving the way for schemas to be authored and managed independently.

### Simplified permissions

The permission model is stripped back to essentials in XP 8:

- **No more inheritance.** Every node carries its own explicit ACL. To apply the same ACL across a subtree, do it in a single hierarchical apply call — the old "inherit from parent" mechanic is gone.

- **Instant cross-branch effect.** Permission changes take effect on every branch a node exists in, immediately. No more publishing content just to push permissions through.

The underlying Node and Content APIs follow the same model. See [Permissions](docs/platform/stable/storage/permissions.md) for the full picture.

### Companion apps

The major Enonic apps have been refreshed alongside the platform and are ready for XP 8.

Content Studio

The editorial CMS interface. Migrated to the new Enonic UI design system, and continues to ship as a standalone application so it can release independently of the platform.

Guillotine

Auto-generates a GraphQL API directly from your content model. Updated for XP 8’s runtime and schema changes. Note that the XP 7-era `lib-guillotine` is no longer supported - it embedded the GraphQL engine in your own app, and was never a client library for the Guillotine app.

Data Toolbox

The developer-focused tool for inspecting repositories and nodes, and for managing dumps, snapshots, and exports. Updated for XP 8.

### Admin Extensions

The Widget API has been replaced by the Extensions API, better reflecting the actual capabilities. Visible tools live in the XP menu, while extensions, you guessed it, extend them - ranging from visual widgets to API-level functionality. The new API is more flexible and powerful.

Additionally, popular extensions such as Content Studio widgets are now wrapped as web components, for complete isolation and flexibility.

Visit the Dev kit documentation for [implementation details](docs/code/stable/web/extensions.md).

### Content and Node Libraries refresh

Years of incremental additions left overlap in the platform Content and Node APIs. XP 8 cleans them up:

- `move` and `rename` collapse into a single `move`

- `setChildOrder` and `reorderChildren` collapse into a single `sort`

- The legacy `hasChildren` content property is gone

- A new `patch` function applies changes across multiple branches in one call

- Language-aware `allText` configuration for multilingual full-text indexing

- Removal of the `inheritsPermissions` flag in favour of explicitly applied permissions

- Sort operations also honor [language-specific collation](docs/code/stable/storage/indexing.md#collation).

### Prometheus metrics

Metrics are now exposed in the open [OpenMetrics](https://github.com/prometheus/OpenMetrics/blob/main/specification/OpenMetrics.md) format - point your Prometheus, Grafana agent, or any compatible collector at the metrics endpoint to get first-class observability.

### Vhost context

Vhost configuration files now support declaration of context values - project, branch, principal - co-locating routing decisions with the vhost they belong to. This may also be used to customize application behaviour on a per-vhost basis. See [Virtual host context](docs/platform/stable/config/vhosts.md#virtual-host-context).

### Server Sent Events (SSE)

XP8 also implements support for Server Sent Events (SSE) across all [web services](docs/platform/stable/endpoints/web.md), enabling real-time streaming of data to clients without using WebSockets. This is particularly useful for building APIs and applications that require live updates, such as dashboards or notifications, but do not require the full duplex communication provided by WebSocket.

### Stricter identity validation

Identity keys, content IDs, names, and descriptors now follow consistent, deterministic validation rules: lowercase-only IDs, explicit regex per key type, and length caps that match what the system actually supports. The intent is to eliminate the class of bugs that came from quietly accepting characters that broke serialization, URLs, or filesystem paths downstream. The full ruleset lives in the [dev kit upgrade guide](docs/code/stable/upgrade.md#identity-keys).

### Security hardening

- Authentication no longer searches for the first matching user across all ID providers. Each request resolves against the vhost’s default ID provider, or the explicitly specified one.

- New passwords use `pbkdf2-sha512`. The legacy `md5` and `sha1` hashing algorithms have been retired, including for `xp.suPassword`.

### Smarter dumps and exports

Repositories can now be exported in full or in part - by branch and path - and repositories may be dumped and loaded individually.

Exports and dumps are written directly to ZIP archives, replacing the previous folder-based structure. The plain-file format and dry-run mode have been retired.

### Quality of life

A handful of smaller-but-pleasing improvements:

- Sessions can be persisted to the filesystem via `file` [storeMode](docs/platform/stable/config/system.md#sessionstore), surviving graceful restarts on standalone instances

- The admin home moved from `/admin/home` to a cleaner `/admin`

- HTTP function names now use the standard uppercase form: `GET`, `POST`, `PUT`, `DELETE`

- `request.locale` is available in the request object

- The dump location is configurable via [repository config](docs/platform/stable/config/system.md#repo)

- Dev mode is now enabled by default in the Enonic SDK, making it easier to get started with development and testing.

### A paradigm shift in naming

XP 8 renames or reframes several familiar XP 7 concepts. Use this map when reading XP 7-era documentation, examples, or AI-generated code — the old terms no longer apply, and in some cases have taken on new meanings:

| XP 7 | XP 8 | Comment |
| --- | --- | --- |
| Engines (site, webapp, admin) | [Services](docs/platform/stable/endpoints/web.md) | The term "engine" is retired |
| Controllers | [HTTP functions](docs/code/stable/web/request-response.md) | A module simply exports functions named after HTTP methods: `GET`, `POST`, etc. |
| HTTP Services (`/_/service/<app>/<name>`) | [Universal APIs](docs/code/stable/web/apis.md) | XP 7 HTTP services are replaced by the [Universal API](docs/platform/stable/endpoints/web.md#api) |
| JS/TS APIs (`lib-content`, `lib-node`, etc.) | [Libraries](docs/code/stable/libraries.md) | The term "API" now primarily refers to web APIs. Platform JS/TS APIs are referred to as *libraries* |
| Assets service | [lib-asset](https://developer.enonic.com/docs/lib-asset/stable) | The built-in asset service is replaced by a library |
| Widgets | [Admin extensions](docs/code/stable/web/extensions.md) | Now part of the Admin Extensions API |
| Mixins | [Form fragments](docs/cms/stable/schemas/form-fragments.md) | Reusable form definitions |
| X-data | [Mixins](docs/cms/stable/content/mixins.md) | The term "mixin" now refers to what XP 7 called x-data |
| Input types and sets | [Form items](docs/cms/stable/schemas/form-items.md) | `TextLine`, `ItemSet`, `FieldSet`, etc. are all form items - regardless of the value they produce |
| Schemas scoped by app (`<app-key>:<name>`) | Schemas scoped by [namespace](docs/cms/stable/schemas/namespaces.md) (`<namespace>:<name>`) | The app name is still the default namespace when shipping schemas with an app |
| `site/` resource folder | [`cms/`](docs/code/stable/schemas.md) | CMS resources now live in `src/main/resources/cms` |
| `site.xml` descriptor | [`cms.yaml`](docs/code/stable/schemas.md) and [`site.yaml`](docs/code/stable/web/sites.md) | Site descriptor is now split in two, and written in YAML. |
| `displayName` (in descriptors) | [`title`](docs/code/stable/schemas.md) | Avoids confusion with content display name property |
| `delete` (in JS libraries) | [`deleteContent`](docs/code/stable/libraries/lib-content.md), `deleteProject`, etc. | Context-specific method names |
| `lib-guillotine` | *Discontinued* | Use the [Guillotine app](https://market.enonic.com/vendors/enonic/guillotine) instead. `lib-guillotine` embedded the GraphQL engine in your own app - it is not, and never was, a client library for the Guillotine app |

> **Warning:** Note the double rename: the word **mixin** changed meaning between versions. An XP 7 *mixin* is an XP 8 *form fragment*, while XP 7 *x-data* is now called *mixin*. When working with XP 7-era material — or AI assistants trained on it — always verify which meaning applies.

The complete map, with migration details, lives in the [dev kit upgrade guide](docs/code/stable/upgrade.md).
