<!-- src:https://developer.enonic.com/docs/code/stable/web/extensions/menuitem generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/extensions/menuitem.md

# Menu Item Extension for Content Studio

Menu Item is an admin extension that implements the `contentstudio.menuitem` interface.

> **Tip:** More details on what this looks like in the: [Content Studio menu item](https://developer.enonic.com/docs/content-studio/stable/workbench#menuitem).

## Introduction

Menu Item extensions add entries to the main menu in Content Studio. When the user selects one, the extension takes over the main view area and runs as a mini-application within Content Studio.

The **Navigator** (content browser) is a built-in menu-item. Other examples include the **GraphQL Playground** from [Guillotine](https://market.enonic.com/vendors/enonic/guillotine), and the **Archive** browser from [Content Studio+](https://market.enonic.com/vendors/enonic/content-studio-plus).

How it works:

Menu items work in context of the currently selected project. Content Studio fetches the extension when the user activates the menu item and renders the response inside a web component that isolates the menu item’s CSS and JS from the rest of the admin UI.

## Lifecycle

- **Discovery.** Content Studio populates the top-left menu with extensions declaring the `contentstudio.menuitem` interface, scoped to the active project.

- **Activation.** The user selects the menu item from the top menu.

- **Render.** Content Studio issues a `GET` to the extension URL and embeds the response in the main view’s web component.

## Descriptor

The descriptor is the same `AdminExtension` kind as any other extension; only the `interfaces:` list and the `config.context` key are specific to menu items. See [the parent descriptor reference](docs/code/stable/web/extensions.md#descriptor) for the shared fields.

src/main/resources/admin/extensions/my-menu/my-menu.yaml

```yaml
kind: "AdminExtension"
title: "My tool"
description: "Custom project-level tool"
interfaces:
  - "contentstudio.menuitem"          (1)
config:
  context: "project"                  (2)
```

| ****1** | **Interface name** — must be the exact string `contentstudio.menuitem` for Content Studio to discover the extension as a menu item. |
| --- | --- |
| ****2** | **context** — scopes the menu item within Content Studio. Use `"project"` for project-scoped tools — the same value used by the built-in **Archive** browser and **GraphQL Playground**. |

> **Tip:** To restrict the menu item to specific roles or principals, use the standard `allow:` field documented in [Building Admin Extensions](docs/code/stable/web/extensions.md) — for example, `allow: ["role:system.admin", "role:cms.admin"]` for admin-only tools.

## Request

Content Studio dispatches a `GET` to the extension URL when the user activates the menu item:

| Parameter | Description |
| --- | --- |
| `repo` | Repository id, e.g. `com.enonic.cms.default`. |

The standard XP request fields are available too: `req.user` for the active user, `req.locales` for i18n negotiation, and so on.

## Response

| Name | Type | Description |
| --- | --- | --- |
| status | integer | `2xx` on success; `404` if the request can’t be served. |
| contentType | string | Typically `text/html`. |
| body | string | HTML markup rendered inside the main-view web component (see notes below). |

The web component isolates the menu item’s CSS and JS from the rest of the admin UI:

- Selectors in your `` blocks don’t conflict with Content Studio’s styles.

- Content Studio’s styles don’t apply to the menu item’s contents either — start from base CSS rather than inheriting admin-UI defaults.

- `` tags execute in the menu item’s scope; queries like `document.querySelector` operate on the menu item’s own DOM.

## Sample implementation

The implementation exports `GET`. Content Studio calls it when the user activates the menu item and renders the response inside the main-view web component.

src/main/resources/admin/extensions/my-menu/my-menu.ts

```typescript
exports.GET = (req) => {
    return {
        status: 200,
        contentType: 'text/html',
        body: `<style>
  .panel { padding: 2rem; font-family: system-ui; max-width: 720px; }
  .panel h1 { margin-top: 0; }
</style>
<div class="panel">
  <h1>Welcome, ${req.user.displayName}</h1>
  <p>This is a custom Content Studio menu item.</p>
</div>`
    };
};
```

The implementation is a regular server-side XP module: `require('/lib/xp/content')`, `require('/lib/xp/project')`, and any other standard library are available, along with 3rd-party modules the app bundles.

For anything beyond a single static page — the built-in **Archive** browser and **GraphQL Playground** are good reference points — separate the HTML, CSS, and JS into asset files and reference them via `portal.assetUrl()` from `lib-portal`. The initial `GET` then becomes a thin shell that loads a bundled SPA, which drives the rest of the experience and makes its own HTTP calls back to the extension or to any mounted Universal APIs.
