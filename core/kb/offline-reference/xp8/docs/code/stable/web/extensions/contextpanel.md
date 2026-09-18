<!-- src:https://developer.enonic.com/docs/code/stable/web/extensions/contextpanel generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/extensions/contextpanel.md

# Context Panel Extension for Content Studio

Context Panel is an admin extension that implements the `contentstudio.contextpanel` interface.

> **Tip:** More details on what this looks like in the: [Content Studio context panel](https://developer.enonic.com/docs/content-studio/stable/workbench/contextpanel).

## Introduction

Context Panel extensions render supplementary information about the selected content, in the right side panel of Content Studio. They are ideal for contextual information or interactions relating the selected content.

How it works:

Content Studio fetches the extension when the user activates the panel and renders the response inside a web component that isolates the panel’s CSS and JS from the rest of the admin UI. Multiple Context Panel extensions coexist — the user picks which one is active from a dropdown, and the same extension is re-fetched whenever the selected content changes.

## Lifecycle

- **Discovery.** Content Studio populates the side-panel dropdown with extensions declaring the `contentstudio.contextpanel` interface.

- **Activation.** The user opens the panel and picks an extension (or the previously active one is restored).

- **Render.** Content Studio issues a `GET` to the extension URL with the selected content as parameters and embeds the response in the side panel’s web component.

- **Re-fetch.** If the user selects a different content, switches branch, or otherwise changes any of the request parameters, Content Studio repeats the `GET` for the new selection.

## Descriptor

The descriptor is the same `AdminExtension` kind as any other extension; only the `interfaces:` list is specific to context panels. See [the parent descriptor reference](docs/code/stable/web/extensions.md#descriptor) for the shared fields.

src/main/resources/admin/extensions/my-panel/my-panel.yaml

```yaml
kind: "AdminExtension"
title: "My panel"
description: "Show key facts about the selected content"
interfaces:
  - "contentstudio.contextpanel"          (1)
```

| ****1** | **Interface name** — must be the exact string `contentstudio.contextpanel` for Content Studio to discover the extension as a context panel. |
| --- | --- |

## Request

Content Studio dispatches a `GET` to the extension URL with the selected content as query parameters:

| Parameter | Description |
| --- | --- |
| `contentId` | Content UUID — the primary way to identify the selected content. |
| `repo` | Repository id, e.g. `com.enonic.cms.default`. |
| `branch` | `draft` or `master`. |

The standard XP request fields are available too: `req.locales` for i18n negotiation, `req.user` for the active user, and so on.

## Response

| Name | Type | Description |
| --- | --- | --- |
| status | integer | `2xx` on success; `404` if the content can’t be loaded. |
| contentType | string | Typically `text/html`. |
| body | string | HTML markup rendered inside the side-panel web component (see notes below). |

The web component isolates the panel’s CSS and JS from the rest of the admin UI:

- Selectors in your `` blocks don’t conflict with Content Studio’s styles.

- Content Studio’s styles don’t apply to the panel contents either — start from base CSS rather than inheriting admin-UI defaults.

- `` tags in the body execute in the panel’s scope; queries like `document.querySelector` operate on the panel’s own DOM.

## Sample implementation

The implementation exports `GET`. Content Studio calls it with the selected content’s id and renders the response inside the side-panel web component.

src/main/resources/admin/extensions/my-panel/my-panel.ts

```typescript
const contentLib = require('/lib/xp/content');

exports.GET = (req) => {
    const content = contentLib.get({ key: req.params.contentId });
    if (!content) {
        return { status: 404 };
    }

    return {
        status: 200,
        contentType: 'text/html',
        body: `<style>
  .panel { padding: 1rem; font-family: system-ui; font-size: 13px; }
  .panel dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.5rem 1rem; margin: 0; }
  .panel dt { font-weight: 600; }
  .panel dd { margin: 0; }
</style>
<div class="panel">
  <dl>
    <dt>Type</dt><dd>${content.type}</dd>
    <dt>Path</dt><dd>${content.path}</dd>
    <dt>Modified</dt><dd>${content.modifiedTime}</dd>
  </dl>
</div>`
    };
};
```

The implementation is a regular server-side XP module: `require('/lib/xp/content')` for the full Content API, plus any other standard library (`lib-portal`, `lib-i18n`, `lib-node`, …​) and 3rd-party modules the app bundles.

For non-trivial panels, separate the HTML, CSS, and JS into asset files and reference them via `portal.assetUrl()` from `lib-portal` — the response then becomes a small `` + `` shell that pulls in the bundled assets, keeping the implementation focused on data and the bundle focused on presentation.
