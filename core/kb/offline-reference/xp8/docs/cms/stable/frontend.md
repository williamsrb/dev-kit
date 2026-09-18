<!-- src:https://developer.enonic.com/docs/cms/stable/frontend generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/frontend.md

# Front-end integration

Enonic is a Headless CMS: it manages and delivers content through APIs and leaves rendering to your front-end. This page explains how the CMS output is consumed in a front-end and the toolkits Enonic provides to make it easier.

## Headless model

Content is queried through the [GraphQL API](docs/cms/stable/apis/graphql.md) (Guillotine), which returns structured, render-ready data:

- **Content** — content types, fields and references exposed as typed GraphQL fields.

- **Media** — URLs served by the [Image API](docs/cms/stable/apis/image.md) and [Attachment API](docs/cms/stable/apis/attachment.md).

- **Rich text** — a `processedHtml` string plus typed `images`, `links` and `macros` fields. See [Rich text](docs/cms/stable/richtext.md).

- **Pages** — the component tree of a page (parts, layouts and fragments). See [Sites and Pages](docs/cms/stable/pages.md).

A front-end fetches this data and maps it to its own components, routes and markup.

## Official toolkits

Enonic CMS can be used with any front-end framework. To avoid hand-writing the mapping, Enonic publishes and maintains:

- **Enonic React components** — render rich text, pages and components, with hooks for overriding how links, images and macros are rendered. See the [`@enonic/react-components` package](https://www.npmjs.com/package/@enonic/react-components).

- **Next.xp** — a Next.js integration providing page rendering, routing, preview and visual-editor support out of the box. See the [Next.xp documentation](https://developer.enonic.com/learn/next.xp/stable).

For the full list of supported toolkits, starters and examples, see the [Frameworks section](https://developer.enonic.com/docs/frameworks) and [Enonic templates and starters](https://developer.enonic.com/templates).

## Rolling your own

If you integrate a framework the official toolkits don’t cover, your renderer has to handle the Enonic-specific output:

- **Rich-text references** — resolve `content://` links to your routes, replace image references with responsive ``/`` tags served by the Image API, and render `editor-macro` placeholders. Each is keyed by a `ref` that matches a `data-*-ref` attribute in `processedHtml`. See [Links](docs/cms/stable/richtext/links.md), [Images](docs/cms/stable/richtext/images.md) and [Macros](docs/cms/stable/richtext/macros.md).

- **Pages** — walk the page component tree and map each part, layout and fragment descriptor to a component. See [Sites and Pages](docs/cms/stable/pages.md).

- **Images** — build Image API URLs with the appropriate scaling and `srcset`. See [Image API](docs/cms/stable/apis/image.md).

- **Visual editing** — to support the Content Studio page editor, emit the DOM markers it expects and initialize the [`@enonic/page-editor`](https://www.npmjs.com/package/@enonic/page-editor) module. See [Visual page editor](docs/cms/stable/pages/page-editor.md). The official toolkits handle this automatically.

> **Tip:** The [React SPA tutorial](https://developer.enonic.com/learn/react-spa/stable) is a hands-on walkthrough of consuming the APIs in a React front-end.
