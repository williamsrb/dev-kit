<!-- src:https://developer.enonic.com/docs/code/stable/web/extensions/liveview generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/extensions/liveview.md

# Live View Extension for Content Studio

LiveView is an admin extension that implements the `contentstudio.liveview` interface.

> **Tip:** More details on what this looks like in the: [Content Studio preview](https://developer.enonic.com/docs/content-studio/stable/workbench/preview).

## Introduction

LiveView extensions are used in Content Studio’s **Edit** and **Browse** views to render a preview of the currently selected content.

Content Studio has a single preview iframe panel. A LiveView extension may take control of this iframe, in order to render the currently selected content. Content Studio ships with three standard LiveView extensions out of the box:

- **Media** streams the binary files (`order: 50`)

- **XP** renders pages using the built-in site service (`order: 90`)

- **JSON** pretty-prints the content as JSON (`order: 100`, auto: "false")

You may add custom LiveView extensions that coexist with these — there is no override; widgets are listed side by side and ordered by `config.order`.

## Lifecycle

When a user selects a content item, until the preview pane shows something, Content Studio runs through the following cycle:

- **Discovery.** Before the user selects a content item, Content Studio populates the LiveView dropdown with extensions declaring the `contentstudio.liveview` interface. The built-in **Automatic** mode is always present at the top.

- **Content context.** The user selects a content item in the grid (or navigates straight to the **Edit** view). The selected content’s id, path, type, repository, branch and archive flag become the input to all subsequent steps.

- **Selection of widget.**

**Manual** — the user selects a specific widget. Whatever it returns is rendered as-is, regardless of status code. A `5xx` shows the server error page in the iframe; a `418` is a conventional status to show a "No preview available". This mode is useful when you want to see exactly what was returned.

- **Automatic** — Content Studio iterates the eligible LiveView extensions that have `auto: "true"`, in `order`, and sends a `HEAD` request to each. The first widget that responds with a `2xx` wins. Any non-`2xx` response — `418`, `404`, `5xx`, anything else — yields the turn to the next widget. If none was able to render, the preview pane shows "No preview available".

- **Render.** Content Studio issues a `GET` to the chosen LiveView extension with the same query parameters and embeds the response in the preview pane.

- **Re-probe.** If the user changes the selected content, switches branch, toggles archive view, or otherwise changes any of the request parameters, the cycle repeats from step 2.

## Descriptor

The descriptor is the same `AdminExtension` kind as any other extension; only the `interfaces:` and `config:` keys are specific to liveview widgets. See [the parent descriptor reference](docs/code/stable/web/extensions.md#descriptor) for the shared fields.

src/main/resources/admin/extensions/my-preview/my-preview.yaml

```yaml
kind: "AdminExtension"
title: "My preview"
description: "Custom preview for articles"
interfaces:
  - "contentstudio.liveview"          (1)
config:
  auto: "true"                        (2)
  order: "60"                         (3)
  allowContentType: "myapp:article"   (4)
  allowPath: "${site}/articles/*"     (5)
```

| ****1** | **Interface name** — must be the exact string `contentstudio.liveview` for Content Studio to discover the extension as a liveview widget. |
| --- | --- |
| ****2** | **auto** — `"true"` makes the widget eligible for **Automatic** mode. Default is off; widgets without this flag only run when picked manually. |
| ****3** | **order** — sort key in the dropdown and the **Automatic** probe sequence. Lower values appear first; the built-in **Automatic** widget itself sits at `0`. With `order: 60`, this widget is probed after the built-in **Media** widget (`50`) but before **Site rendering** (`90`). |
| ****4** | **allowContentType** — optional glob restricting the widget to specific content types. Matched client-side before the widget is even probed. Omit to accept any type. |
| ****5** | **allowPath** — optional glob restricting the widget to specific content paths. Supports the `${site}` variable, which expands to the path of the site the content belongs to. |

## Request

Content Studio probes the widget with `HEAD` to ask whether it can render this content; if the response is `2xx`, it follows up with `GET` for the payload. Both requests carry the same query parameters:

| Parameter | Description |
| --- | --- |
| `contentId` | Content UUID. Mutually exclusive with `contentPath` — Content Studio sends one or the other. |
| `contentPath` | Content path, e.g. `/mysite/articles/hello`. |
| `type` | Content type name, e.g. `media:image`, `portal:page`, `myapp:article`. |
| `repo` | Repository id, e.g. `com.enonic.cms.default`. |
| `branch` | `draft` or `master`. |
| `mode` | `preview` (default), `inline`, or `edit`. |
| `archive` | `"true"` if the selected content is in the archive. |
| `auto` | `"true"` when invoked from **Automatic** mode. Use to short-circuit work that only matters when the user has explicitly chosen the widget. |

## Response

| Name | Type | Description |
| --- | --- | --- |
| status | integer | In **Automatic** mode, `2xx` claims the iteration; any non-`2xx` (`418`, `404`, `5xx`, …) yields to the next eligible widget. In **Manual** mode, the body renders as-is regardless of status — except `418 I’m a teapot`, the conventional code for intentional skips, which shows "No preview available". |
| contentType | string | Interpreted by the iframe; may be anything an `iframe` can display. |
| body | string | The payload rendered in the iframe. Empty when using the `enonic-widget-data.redirect` mechanism. |
| headers | object | Standard HTTP headers plus the `enonic-widget-data` sidecar — see below. |

Because the iframe is hosted inside the admin UI, the response should set:

- `X-Frame-Options`: `SAMEORIGIN` — prevents the preview from being framed by a third party.

- `Content-Security-Policy` — restricts the resources the iframe is allowed to load. The exact policy depends on what the widget renders.

The `enonic-widget-data` header is a JSON-encoded sidecar that travels alongside the rendered body — a channel for the widget to surface UI messages or redirect the preview:

| Field | Type | Description |
| --- | --- | --- |
| messages | string[] | Optional. Strings shown as warnings in the preview pane. |
| redirect | string | Optional. URL to load in the iframe instead of the response body — Content Studio replaces the iframe contents with a fetch of this URL. |
| hasControllers | boolean | Optional. Capability flag that influences which preview-pane controls light up. |

> **Note:** Other fields in `enonic-widget-data` are silently ignored.

Constructing the sidecar header

```typescript
const widgetData = {
    messages: ['Article has no lead paragraph'],
    redirect: 'https://preview.example.com/foo',
    hasControllers: true
};
return {
    status: 200,
    contentType: 'text/html',
    headers: {
        'enonic-widget-data': JSON.stringify(widgetData)
    },
    body: '...'
};
```

## Sample implementation

The implementation must export `HEAD` and `GET`. `HEAD` answers the **Automatic** mode probe — return `2xx` to claim the content, anything else to decline. `GET` returns the response that drives the iframe, in one of two shapes:

- **Inline body** — the widget returns HTML (or JSON, or any payload an iframe can display) as the response body. Content Studio renders it directly inside the iframe.

- **Redirect** — the widget returns an `enonic-widget-data.redirect` URL and no body. Content Studio re-points the iframe at the external URL.

The two variants are equally first-class; the built-in **Site rendering** widget uses redirect, the **JSON** widget uses inline body.

### Inline body

Using the extension to render a custom preview right inside Content Studio, without involving any external services.

The implementation is a regular server-side XP module: `require('/lib/xp/content')` for the full Content API, plus any other standard library (`lib-portal`, `lib-node`, `lib-i18n`, `lib-io`, …​) and 3rd-party modules the app bundles. The widget can query related content, traverse children, fetch attachments, render aggregated views — anything an XP module can do.

src/main/resources/admin/extensions/my-preview/my-preview.ts

```typescript
const contentLib = require('/lib/xp/content');
const ALLOWED_TYPE = 'myapp:article';
const SECURITY_HEADERS = {
    'X-Frame-Options': 'SAMEORIGIN',
    'Content-Security-Policy': "default-src 'self'; style-src 'unsafe-inline'"
};

exports.HEAD = (req) => ({
    status: req.params.type === ALLOWED_TYPE ? 200 : 418
});

exports.GET = (req) => {
    if (req.params.type !== ALLOWED_TYPE) {
        return { status: 418 };
    }

    const content = contentLib.get({ key: req.params.contentId });
    if (!content) {
        return { status: 404 };
    }

    const { headline, lead, body } = content.data;

    return {
        status: 200,
        contentType: 'text/html',
        headers: {
            ...SECURITY_HEADERS,
            'enonic-widget-data': JSON.stringify({
                messages: lead ? [] : ['Article has no lead paragraph']
            })
        },
        body: `<!doctype html>
<html>
  <body style="font-family: system-ui; padding: 1rem;">
    <h1>${headline ?? content.displayName}</h1>
    ${lead ? `<p><strong>${lead}</strong></p>` : ''}
    ${body ? `<div>${body}</div>` : ''}
  </body>
</html>`
    };
};
```

`HEAD` returns `418` for any content that is not an article, so **Automatic** mode falls through to the next widget without doing any work. `GET` mirrors the same gate (so a manual invocation on a non-article also returns `418`), then loads the content and emits a small HTML view. The `enonic-widget-data` header surfaces a warning when the article has no lead paragraph.

### Redirect

For preview frontends hosted elsewhere — a Next.js, SvelteKit, or Astro app, a microservice, anything with its own URL — the widget delegates rendering and just hands Content Studio the URL to load:

src/main/resources/admin/extensions/my-preview/my-preview.ts

```typescript
const ALLOWED_TYPE = 'myapp:article';
const PREVIEW_BASE = 'https://preview.myapp.com';

exports.HEAD = (req) => ({
    status: req.params.type === ALLOWED_TYPE ? 200 : 418
});

exports.GET = (req) => {
    if (req.params.type !== ALLOWED_TYPE) {
        return { status: 418 };
    }

    const url = `${PREVIEW_BASE}/preview/${req.params.contentId}?branch=${req.params.branch}`;

    return {
        status: 200,
        headers: {
            'enonic-widget-data': JSON.stringify({ redirect: url })
        }
    };
};
```

The widget does no rendering itself — the external server is responsible for fetching the content (typically through the [GraphQL API](https://developer.enonic.com/docs/guillotine)) and setting its own `X-Frame-Options` / `Content-Security-Policy` headers so Content Studio’s iframe can load it. Pass through `branch` and any other request parameters the external preview needs to fetch the right version of the content.
