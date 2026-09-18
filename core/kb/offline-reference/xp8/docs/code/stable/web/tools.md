<!-- src:https://developer.enonic.com/docs/code/stable/web/tools generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/tools.md

# Admin Tools

Admin tools are custom adminitrative interfaces made availabe within the XP admin.

## Introduction

An admin tool are self-contained mini-applications that run within the XP admin.

- Secured via the same authentication and authorization as the rest of the admin.

- Listed in the XP menu with icon and name

- Can mount contextual [Universal APIs](docs/code/stable/web/apis.md) .

- Can connect to [Admin extensions](docs/code/stable/web/extensions.md) by declaring named interfaces that extensions implement.

- Mounts at `/admin//` — one URL per tool.

Access always requires the caller to hold `role:system.admin.login`. Per-tool access is then granted to anyone in `role:system.admin` or to any principal listed in the tool’s `allow:` field.

## Usage

To declare a tool, place a descriptor and an implementation under `src/main/resources/admin/tools//`:

```files
src/main/resources/admin/tools/
  my-tool/
    my-tool.yaml   (1)
    my-tool.ts     (2)
    my-tool.svg    (3)
```

| ****1** | Descriptor — see [below](#descriptor). |
| --- | --- |
| ****2** | HTTP function implementation for the tool URL. |
| ****3** | Optional SVG icon shown in the Launcher. The file must sit next to the descriptor and share its base name. |

The folder name, descriptor base name, and implementation base name must all match ``.

## Descriptor

The descriptor is YAML only — `.yaml` and `.yml` are both accepted, and `.yaml` wins if both are present.

src/main/resources/admin/tools/<tool-name>/<tool-name>.yaml

```yaml
kind: "AdminTool"
title: "Content Studio"          (1)
description: "Manage content"    (2)
allow:                           (3)
  - "role:system.authenticated"
apis:                            (4)
  - "admin:extension"
  - "content"
interfaces:                      (5)
  - "contentstudio.menuitem"
  - "contentstudio.contextpanel"
config:                          (6)
  property_1: "value_1"
```

| ****1** | **title** — string, or `{ text, i18n }` for localization. Shown in the Launcher. |
| --- | --- |
| ****2** | **description** — string, or `{ text, i18n }`. |
| ****3** | **allow** — principal keys (roles, groups, users) granted access. The implicit `role:system.admin` always has access regardless. Required to expose the tool to non-admins. |
| ****4** | **apis** — list of [Universal API](docs/code/stable/web/apis.md) descriptor keys mounted under this tool’s URL. Bare names refer to APIs in the same app; `<app>:<api>` form borrows from another app. APIs become reachable as service points at `/admin/<app-key>/<tool-name>/_/<app>:<api>`. |
| ****5** | **interfaces** — named interface points this tool exposes. Admin extensions whose `interfaces:` list intersects with this list are eligible to be mounted into the tool. Names are free-form strings — pick stable identifiers and document them. |
| ****6** | **config** — free-form key/value map readable from the implementation. |

Localized title/description

```yaml
title:
  text: "My tool"
  i18n: "i18n.my-tool.display-name"
```

## Implementation

The implementation lives at `src/main/resources/admin/tools//.ts` and exports an [HTTP function](docs/code/stable/web/request-response.md) for each method the tool should respond to.

Sample my-tool.ts

```typescript
exports.GET = (req) => {
    const view = resolve('my-tool.html');
    return {
        body: render(view, { user: req.user }),
        contentType: 'text/html'
    };
};
```

The implementation is the entry point for `/admin//` and any deeper path that does not match a service-point URL. For anything beyond a couple of static endpoints, use the [router library](https://market.enonic.com/vendors/enonic/router-lib) for method dispatch, parameter extraction, and pattern matching.

## URL

- Tool entry point: `/admin//`

- API service point under the tool: `/admin///_/:`

- Admin extension dispatcher under the tool: `/admin///_/admin:extension/:/`

Generate URLs from the implementation with the [Portal library](docs/code/stable/libraries/lib-portal.md): `adminUrl()` for the tool itself, `apiUrl()` for mounted APIs.

## Access control

The admin service enforces two checks:

- The caller must hold `role:system.admin.login`. Without this, the request never reaches the descriptor.

- The tool’s descriptor must permit the caller. `role:system.admin` is always permitted; otherwise the caller must match at least one principal in `allow:`.

A failed check returns **401 Unauthorized** if the configured ID provider asks for credentials, otherwise **403 Forbidden**.

## Mounting Universal APIs

Any API listed in `apis:` is mounted as a service point under the tool’s URL. The same API can simultaneously be mounted on the Web endpoint (`mount: ["web"]` in the API descriptor) — the two mounts are independent. See [Universal API: Service point](docs/code/stable/web/apis.md#service-point).

## Hosting admin extensions

A tool publishes the interface names it exposes in `interfaces:`. Any deployed admin extension whose own `interfaces:` list intersects with this set becomes eligible to be mounted into the tool, subject to the extension’s own `allow:` list. The reserved interface name `"generic"` matches any tool. See [Admin extensions](docs/code/stable/web/extensions.md) for the consumer side.

## Launcher

The XP admin Launcher lists every deployed tool the caller is allowed to access, using `title`, `description`, and the `.svg` icon from the descriptor. The default Launcher tool itself is `com.enonic.xp.app.main:home`, served at `/admin`.
