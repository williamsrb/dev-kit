<!-- src:https://developer.enonic.com/docs/code/stable/web/extensions generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/extensions.md

# Admin Extensions

Admin extensions are dynamic endpoints that plug into into existing [admin tools](docs/code/stable/web/tools.md) at their named interfaces.

## Introduction

The most common usage is rendering an embedded UI fragment, but an extension is basically a dynamic HTTP endpoint — it can equally well serve JSON, binary assets, or any other payload the host tool agrees to consume.

- Contributed by an app and discovered by the host admin tool through a string identifier called an **interface**.

- Mounts only into tools that publish a matching interface name. The reserved name `generic` matches any tool.

- Is served by the admin service through the `admin:extension` dispatcher API at `/admin///_/admin:extension/:/`.

- Returns whatever HTTP payload the host tool expects — HTML fragments for UI widgets, JSON for data feeds, binary assets, etc.

## Usage

To declare an extension, place a descriptor and an implementation under `src/main/resources/admin/extensions//`:

```files
src/main/resources/admin/extensions/
  my-extension/
    my-extension.yaml   (1)
    my-extension.ts     (2)
    my-extension.svg    (3)
```

| ****1** | Descriptor — see [below](#descriptor). |
| --- | --- |
| ****2** | HTTP function implementation for the extension URL. |
| ****3** | Optional SVG icon, served by the discovery endpoint. |

The folder name, descriptor base name, and implementation base name must all match ``.

## Descriptor

The descriptor is YAML only — `.yaml` and `.yml` are both accepted.

src/main/resources/admin/extensions/<extension-name>/<extension-name>.yaml

```yaml
kind: "AdminExtension"
title:                                (1)
  text: "My extension"
  i18n: "i18n.my-extension.title"
description: "My extension"           (2)
interfaces:                           (3)
  - "com.example.app.sidebar"
  - "com.example.myinterface"
allow:                                (4)
  - "role:system.authenticated"
config:                               (5)
  property_1: "value_1"
```

| ****1** | **title** — string, or `{ text, i18n }` for localization. Used wherever the host tool renders an extension list. |
| --- | --- |
| ****2** | **description** — string, or `{ text, i18n }`. |
| ****3** | **interfaces** — names of interface points the extension plugs into. The host tool must publish a matching name in its own `interfaces:` list. Use the reserved value `"generic"` to make the extension mountable from any admin tool. |
| ****4** | **allow** — principal keys granted access. `role:system.admin` is always permitted in addition to anything listed here. Required to expose the extension to non-admins. |
| ****5** | **config** — free-form key/value map readable from the implementation and surfaced in the discovery endpoint. |

## Implementation

The implementation lives at `src/main/resources/admin/extensions//.ts` and exports an [HTTP function](docs/code/stable/web/request-response.md) for each method the extension responds to. The response shape is determined by the host tool — UI widgets typically return HTML fragments, but a data-feed extension might return JSON, and an asset-serving extension might return binary content with the appropriate `contentType`.

Sample my-extension.ts

```typescript
exports.GET = (req) => {
    const contentId = req.params.contentId;
    return {
        body: `<div>Inspecting content ${contentId}</div>`,
        contentType: 'text/html'
    };
};
```

For anything beyond a couple of static endpoints, use the [router library](https://market.enonic.com/vendors/enonic/router-lib) for method dispatch, parameter extraction, and pattern matching.

## Extension URL

The URL at which an extension is reachable is a platform internal and may change between XP releases — **do not hard-code it**. Use `extensionUrl()` from [lib-admin](docs/code/stable/libraries/lib-admin.md#extensionurl); it resolves the URL based on the current admin tool context.

```typescript
const adminLib = require('/lib/xp/admin');

const url = adminLib.extensionUrl({
    application: 'com.example.app',
    extension: 'my-extension',
    params: { contentId: '123' }
});
```

(`widgetUrl()` exists for backward compatibility but is deprecated; use `extensionUrl()` in new code.)

Two preconditions still apply to every invocation:

- The host tool’s descriptor must include `"admin:extension"` in its `apis:` list, so the dispatcher is mounted under that tool.

- The interface match rule: unless the extension’s `interfaces:` list contains `"generic"`, at least one of its interfaces must also be present in the host tool’s `interfaces:` list — otherwise the request returns **404 Not Found**.

## Access control

Two checks are enforced:

- The caller must hold `role:system.admin.login`.

- The extension’s descriptor must permit the caller — `role:system.admin` is always permitted; otherwise the caller must match at least one principal in `allow:`.

## Discovery

The host tool typically queries `?interface=` to find which extensions are available to the current user at a given interface point. The response is a JSON array, one entry per allowed extension:

```json
[
  {
    "key": "com.example.app:my-extension",
    "title": "My extension",
    "description": "My extension",
    "iconUrl": "/admin/.../_/admin:extension?icon&app=com.example.app&extension=my-extension&v=...",
    "url": "/admin/.../_/admin:extension/com.example.app:my-extension",
    "interfaces": ["com.example.app.sidebar"],
    "config": { "property_1": "value_1" }
  }
]
```

The listing is filtered by the caller’s principals — extensions the caller cannot access are omitted.

## Interfaces

Interface names are free-form strings, not a closed enum. The contract is purely a string match between the extension’s `interfaces:` and the host tool’s `interfaces:`. To define a new interface point in your own admin tool, declare a stable name (e.g. `.`) in the tool’s descriptor and document the request/response shape your tool expects from extensions.

Each consuming admin tool defines its own set of interface names along with the request/response shape extensions must conform to — consult the host tool’s documentation for the contract.
