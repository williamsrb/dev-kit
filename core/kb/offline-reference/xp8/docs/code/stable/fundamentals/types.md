<!-- src:https://developer.enonic.com/docs/code/stable/fundamentals/types generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/fundamentals/types.md

# Types

The shared types that flow across the Enonic libraries

## Introduction

This page is the canonical reference for the cross-library types.

principals, binary streams, the content object, page components, and more. They are defined once in the `@enonic-types/core` package and re-exported by the individual `@enonic-types/lib-*` packages, so the same `User`, `Content`, or `ByteSource` you receive from one library is the exact type another library accepts.

Library pages name them and link here rather than redefining them. For how to install and wire the type packages, see [TypeScript](docs/code/stable/fundamentals/typescript.md).

> **Note:** These are the TypeScript shapes of the runtime objects. The conceptual models behind them — the content model, the query language, form schemas — are documented in the [CMS](https://developer.enonic.com/docs/cms) and [XP platform](https://developer.enonic.com/docs/platform) docs, linked from the relevant types below.

## Principals and keys

Principal keys are branded string templates — a `User` key always reads `user::`, a group key `group::`, and a role key `role:`.

### PrincipalKey

A union of the three key kinds: `UserKey | GroupKey | RoleKey`.

### UserKey

Template string `user:${string}:${string}` — e.g. `user:system:alice`.

### GroupKey

Template string `group:${string}:${string}` — e.g. `group:system:editors`.

### RoleKey

Template string `role:${string}` — e.g. `role:system.admin`.

### PrincipalType

One of `'user'`, `'group'`, or `'role'`.

### Principal

A union of the three principal objects: `[User](#user) | [Group](#group) | [Role](#role)`. Use the `type` discriminant to tell them apart.

### User

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Always `'user'`. |
| key | [UserKey](#user-key) | The principal key. |
| displayName | string | Human-friendly name. |
| login | string | Login name. |
| idProvider | string | Key of the ID provider the user belongs to. |
| hasPassword | boolean | Whether the user has a password set. |
| email | string | **Optional.** Email address. |
| disabled | boolean | **Optional.** Whether the user is disabled. |
| modifiedTime | string | **Optional.** ISO timestamp of the last modification. |

### Group

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Always `'group'`. |
| key | [GroupKey](#group-key) | The principal key. |
| displayName | string | Human-friendly name. |
| modifiedTime | string | ISO timestamp of the last modification. |
| description | string | **Optional.** Group description. |

### Role

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Always `'role'`. |
| key | [RoleKey](#role-key) | The principal key. |
| displayName | string | Human-friendly name. |
| modifiedTime | string | ISO timestamp of the last modification. |
| description | string | **Optional.** Role description. |

## Binary and resources

### ByteSource

An opaque handle to a binary stream. You don’t read its fields directly — you pass it to library functions (for example `io.readText`, `io.getSize`, attachment and media APIs) that consume or produce binary data. Obtain one from `[lib-io](docs/code/stable/libraries/lib-io.md)` (`newStream`, a resource stream) or from content attachments.

### Resource

A handle to an application resource on the classpath, returned by `io.getResource`.

Methods

| Name | Type | Description |
| --- | --- | --- |
| exists() | boolean | Whether the resource exists. |
| getSize() | number | Size in bytes. |
| getTimestamp() | number | Last-modified time, in milliseconds since the epoch. |
| getStream() | [ByteSource](#byte-source) | The resource’s binary stream. |

### ResourceKey

Identifies an application resource by application key and path.

Methods

| Name | Type | Description |
| --- | --- | --- |
| getApplicationKey() | string | The owning application key. |
| getPath() | string | Resource path within the application. |
| getUri() | string | Full resource URI. |
| getName() | string | Resource name. |
| getExtension() | string | File extension. |
| isRoot() | boolean | Whether the key points at the application root. |

## Content model

### Content

The object returned by the content APIs. The conceptual content model is documented in the [CMS docs](https://developer.enonic.com/docs/cms); this is its runtime shape.

Properties

| Name | Type | Description |
| --- | --- | --- |
| _id | string | Unique content id. |
| _name | string | Content name (unique among siblings). |
| _path | string | Full content path. |
| type | string | Content type name (e.g. `portal:site`, `com.myapp:article`). |
| displayName | string | Human-friendly name. |
| data | object | The content’s data, shaped by its content type. |
| x | object | Extra data (mixins / x-data), keyed by application. |
| attachments | object | Map of attachment name to [Attachment](#attachment). |
| valid | boolean | Whether the content currently validates against its type. |
| hasChildren | boolean | Whether the content has child items. |
| creator | [UserKey](#user-key) | Principal that created the content. |
| createdTime | string | ISO creation timestamp. |
| owner | string | Principal key of the owner. |
| modifier | [UserKey](#user-key) | **Optional.** Principal that last modified the content. |
| modifiedTime | string | **Optional.** ISO timestamp of the last modification. |
| language | string | **Optional.** Language tag of the content’s locale. |
| childOrder | string | **Optional.** Sort order of children. |
| page | [Component](#component) | **Optional.** The page component tree (absent on fragments). |
| fragment | [Component](#component) | **Optional.** The fragment component (only on `portal:fragment` content). |
| publish | [PublishInfo](#publish-info) | **Optional.** Publishing schedule and history. |
| workflow | [Workflow](#workflow) | **Optional.** Workflow state. |
| validationErrors | [ValidationError](#validation-error)[] | **Optional.** Validation errors, when the content is invalid. |
| inherit | string[] | **Optional.** Which aspects are inherited in a layered project (`CONTENT`, `PARENT`, `NAME`, `SORT`). |
| originProject | string | **Optional.** Project the content was inherited from. |
| variantOf | string | **Optional.** Id of the content this is a variant of. |
| _score | number | **Optional.** Relevance score, present on query hits. |
| _sort | object[] | **Optional.** Sort values, present on sorted query hits. |

### Attachment

A binary attached to a content item.

Properties

| Name | Type | Description |
| --- | --- | --- |
| name | string | Attachment name (unique within the content). |
| size | number | Size in bytes. |
| mimeType | string | Media type. |
| label | string | **Optional.** Attachment label. |
| sha512 | string | **Optional.** SHA-512 hash of the binary. |

### PublishInfo

The publishing schedule and history of a content item. All fields are ISO-8601 timestamps.

Properties

| Name | Type | Description |
| --- | --- | --- |
| from | string | **Optional.** Time from which the content is published. |
| to | string | **Optional.** Time after which the content is no longer published. |
| first | string | **Optional.** Time the content was first published. |

### Workflow

Properties

| Name | Type | Description |
| --- | --- | --- |
| state | [WorkflowState](#workflow-state) | The current workflow state. |

### WorkflowState

One of `'IN_PROGRESS'`, `'PENDING_APPROVAL'`, `'REJECTED'`, or `'READY'`.

### ValidationError

Describes a single validation failure on a content item.

Properties

| Name | Type | Description |
| --- | --- | --- |
| errorCode | object | The error code: `{ applicationKey: string, code: string }`. |
| message | string \| null | A static, human-readable error message. |
| i18n | string \| null | The i18n localization key for the message. |
| args | array | **Optional.** Values substituted into the localized message. |

## Page and components

A content’s `page` (and a fragment’s `fragment`) is a tree of components. Every component carries a `type` discriminant — one of `'page'`, `'layout'`, `'part'`, `'text'`, or `'fragment'`. There is no separate `Page` type: the page-level node is a [PageComponent](#page-component).

### Component

A union of the five component kinds, discriminated by `type`: `[PageComponent](#page-component) | [LayoutComponent](#layout-component) | [PartComponent](#part-component) | [TextComponent](#text-component) | [FragmentComponent](#fragment-component)`.

### PageComponent

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Always `'page'`. |
| descriptor | string | Descriptor key of the page component (e.g. `com.myapp:main`). |
| config | object | The component’s configuration, shaped by the descriptor. |
| regions | object | Map of region name to [Region](#region). |
| path | string | Component path; always `/` for the page root. |
| template | string | **Optional.** Page template key, when the page uses a template. |

### LayoutComponent

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Always `'layout'`. |
| descriptor | string | Descriptor key of the layout. |
| config | object | The component’s configuration, shaped by the descriptor. |
| regions | object | Map of region name to [Region](#region) nested within the layout. |
| path | string | **Optional.** Component path within the page. |

### PartComponent

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Always `'part'`. |
| descriptor | string | Descriptor key of the part. |
| config | object | The component’s configuration, shaped by the descriptor. |
| path | string | **Optional.** Component path within the page. |

### TextComponent

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Always `'text'`. |
| text | string | The text (HTML) content. |
| path | string | Component path within the page. |

### FragmentComponent

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Always `'fragment'`. |
| fragment | string | Content id of the fragment being referenced. |
| path | string | Component path within the page. |

### Region

A named slot holding an ordered list of components.

Properties

| Name | Type | Description |
| --- | --- | --- |
| name | string | Region name. |
| components | [Component](#component)[] | The components placed in the region, in order. |

## Repository nodes

### Node

A stored repository node, as returned by the `lib-node` connection methods (`create`, `get`, `modify`, `move`, …). A node is its system properties merged with the caller’s own data: every non-underscore property is application data, and the underscore-prefixed system properties are:

| Name | Type | Description |
| --- | --- | --- |
| `_id` | string | Generated, unique node id. |
| `_name` | string | Node name, unique among its siblings. |
| `_path` | string | Full path to the node. |
| `_childOrder` | string | Child order expression (for example, `_ts DESC`). |
| `_manualOrderValue` | number | **Optional.** Numeric value used when siblings are ordered manually. |
| `_nodeType` | string | Node type; `data` for ordinary nodes. |
| `_permissions` | object[] | Access-control entries (`principal`, `allow`, `deny`) for the node. |
| `_indexConfig` | object | Index configuration controlling how the node’s data is indexed. |
| `_ts` | string | Timestamp of the node’s current version, as an ISO-8601 instant. |
| `_versionKey` | string | Key of the node’s current version. |

All other properties are the node’s own data. See the [XP platform node API](https://developer.enonic.com/docs/platform) for the full model.

## HTTP

### Request

The object passed to an HTTP function (`GET`, `POST`, filters, error handlers). Its fields — `method`, `path`, `params`, `headers`, `cookies`, `body`, and the rest — are documented in depth in [Web](docs/code/stable/web.md), the canonical home for the request/response model.

### Response

The object an HTTP function returns — `status`, `body`, `contentType`, `headers`, `cookies`, `pageContributions`, `redirect`, and more. All fields are optional. See [Web](docs/code/stable/web.md) for the full model and examples.

## Other

### ScriptValue

A lazy wrapper around a value crossing the Java/JavaScript boundary — used by APIs that accept arbitrary caller data (for example audit-log data, task config). Rather than fields, it exposes inspection methods: `isArray()`, `isObject()`, `isValue()`, `isFunction()`, `getValue()`, `getKeys()`, `hasMember(key)`, `getMember(key)`, `getArray()`, `getMap()`, `getList()`.

## Query and form types

### FormItem

A single item in a content type, mixin, or form-fragment schema. `FormItem` is a union discriminated by `formItemType`, with five kinds:

| formItemType | Description |
| --- | --- |
| `Input` | A data-entry field. Properties: `name`, `label`, `inputType` (names the editor — `TextLine`, `HtmlArea`, `ContentSelector`, …), `occurrences` (`{ minimum, maximum }`), `helpText`, `validationRegexp`, `default`, `config`. |
| `ItemSet` | A repeatable group of nested `items` (`FormItem[]`). Properties: `name`, `label`, `occurrences`, `items`, plus `helpText`. |
| `Layout` | A visual grouping that carries no data of its own. Properties: `name`, `label`, `items` (`FormItem[]`). |
| `OptionSet` | A set of selectable `options`, each with its own nested `items`. Properties: `name`, `label`, `occurrences`, `selection` (`{ minimum, maximum }`), `options`, `helpText`, `expanded`. |
| `FormFragment` | A reference to a reusable form fragment. Property: `name`. |

Every kind has a `name` and a `label`. For the full per-`inputType` configuration, see the [CMS schema docs](https://developer.enonic.com/docs/cms).

### Query DSL types

`QueryDsl`, `SortDsl`, `Filter`, `Aggregations`, and `Highlight` model the query DSL. They are documented with the storage layer rather than duplicated here — see the [XP storage and querying docs](docs/platform/stable/storage.md) and [Querying](docs/code/stable/storage/querying.md).
