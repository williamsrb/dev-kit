<!-- src:https://developer.enonic.com/docs/code/stable/web/sites generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/sites.md

# Sites

Serving content driven sites using XP apps. The service responds at `:8080/site///`. Combine with Vhosts for custom domains and paths.

> **Note:** For hands on tutorials on building native Enonic XP sites, visit [React4XP tutorial](https://developer.enonic.com/learn/react4xp/stable) or the [My first site tutorial](https://developer.enonic.com/docs/my-first-site).

## Introduction

As an alternative to using 3rd party front-end frameworks like Next.js, the site service is purpose-built for delivering content-driven websites, and is closesly linked to the CMS features of the platform.

> **Tip:** Visit the [CMS documentation](https://developer.enonic.com/docs/cms/xp8) for details on Content Modelling and schemas. This section focuses on implementing site rendering via Enonic apps.

### Usage

To activate the site service, you will need a site descriptor in your app.

src/main/resources/cms/site.yaml

```yaml
kind: "Site"
mappings: (1)
  - controller: "/lib/preview.js"
    order: 50
    match: "type:'(?!media:).*'"
apis:
  - "ws"  (3)
  - "app:graphql" (4)
```

| ****1** | A mapping to take over the request for all non-media content items, and render a preview. |
| --- | --- |
| ****2** | Contextually mounts an API in the same application on the site’s underscore endpoint. |

> **Note:** You will also need implementations of [Mapping function](docs/code/stable/web/sites/mappings.md) or [component functions](docs/code/stable/web/sites/components.md) to start rendering.

## Site Request pipeline

The site pipeline is executed as a subset of the [common pipeline](docs/code/stable/web.md#common_request_pipeline):

This section describes the standard pipeline involved in processing a page request, e.g. `:8080/site///`.

Render component

If a component is matched, the matching component implementation is invoked to render it — also directly addressable via the [component endpoint](docs/code/stable/web/sites/components.md#direct-rendering). The result may include nested components, which are resolved and rendered iteratively (via component placeholders) until all placeholders are resolved and rendered.

Universal APIs

Sites support contextual APIs mounted in the same URL space. They are are available on the `/_/:` path. APIs are mounted via the site descriptor.

> **Note:** The image and attachment APIs are implicitly mounted by the site service, and are available at `/*/media:image*`* and `/`*`/media:attachment` respectively. Use portal library functions to generate URLs for these, and they will be served with the appropriate caching and optimizations.

Mappings

Use path or content-based [site mappings](docs/code/stable/web/sites/mappings.md). Each mapping will trigger a function, acting as a filter or a controller (returning a response directly). Filters will iteratively execute until a controller is reached, or the mappings are exhausted. If no mapping matches, the request continues to the default page rendering step.

Render page

Looks up the content at the path and resolves the page implementation and config (optionally via a page template) or returns a matching 404 if not found. 401 if protected, and 403 if user lacks permissions.

> **Note:** The content types `base:shortcut` is automatically handled with a `307 Temporary Redirect`, and `portal:fragment` is only rendered when referend from another page.

**Implementation resolution:**

- Implementation set directly on the content.

- Implementation set on a page template for the content. If the page template is unavailable (e.g. deleted), the page resolver treats it as if no page template was set.

- Implementation set on the first page template found in `{site}/_templates` that supports the content’s type.

If no implementation is found, the response status is `404 Not Found`.

> **Note:** In `inline` rendering mode the status is `418` instead of `404`, so Content Studio can switch to alternative rendering. In `edit` rendering mode the status is `200` instead of `404`, to allow Content Studio to render the in-place component selector.

**Component rendering:**

Once the page component is rendered, the rendering iteratively continues until all nested components placeholders are resolved and rendered.

Text/html processors

For `text/html` responses, any [response processors](docs/code/stable/web/sites/processors.md) defined in the site descriptor are executed. Processors may manipulate the result, for instance by adding [page contributions](docs/code/stable/web/sites/contributions.md). Once all processors are done, available `pageContributions` in the response object are merged into the html response body.

Response filters

Finally, any filters registered via through a mapping iteratively execute their response processing step before the response is returned from the pipeline.

## One site, multiple apps

Sites may be powered by multiple apps. The apps may even collaborate on processing and responding to a single request. I.e. via filters APIs and response processors. This allows you to modularize functionality across multiple apps, and reuse apps across sites. Visit Enonic Market for existing apps and inspiration: [https://market.enonic.com/apps](https://market.enonic.com/apps)
