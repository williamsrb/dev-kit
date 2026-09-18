<!-- src:https://developer.enonic.com/docs/code/stable/web/sites/components generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/sites/components.md

# Components

Explicit Page, part, and layout components rendereing.

## Introduction

> **Tip:** For a hands-on introduction tutorial, visit the [My first site tutorial](https://developer.enonic.com/docs/my-first-site).

A component implementation is created in the same folder as its [CMS component schema](https://developer.enonic.com/docs/cms/xp8/pages/page). It exports the same HTTP functions as any other endpoint, but is always executed in the context of a content item. It may also make use of [page contributions](docs/code/stable/web/sites/contributions.md).

> **Important:** Markup returned by a component must have a single root element.

## Context

The implementation gets invoked when a client requests a specific content item, which resolves to a page:

`HTTP request` → `/site///path/to/content` → `resolve component` → `invoke implementation`.

During the rendering, the specific content item will be available in the context, and API functions such as [portalLib.getContent()](docs/code/stable/libraries/lib-portal.md#getContent) and [portalLib.getComponent()](docs/code/stable/libraries/lib-portal.md#getComponent) automatically return values based on that context.

> **Tip:** The site service uses the underlying permissions of the content, which means the current user is guaranteed to have read permissions to the contextually rendered content item. Meaning you do not need to worry about permissions when rendering components.

## Pages

The page implementation lives next to its [Page schema](https://developer.enonic.com/docs/cms/xp8/pages/page) at `src/main/resources/cms/pages//.ts`.

Sample page implementation using the context

```typescript
const portal = require('/lib/xp/portal');

exports.GET = (req) => {
  const content = portal.getContent();
  return {
    body: `<html>
            <body>
              <h1>${content.displayName}</h1>
            </body>
          </html>`
  };
};
```

## Parts

A part implementation lives next to its [Part schema](https://developer.enonic.com/docs/cms/xp8/pages/parts) at `src/main/resources/cms/parts//.ts`.

Sample part implementation using the form value

```typescript
const portal = require('/lib/xp/portal');

exports.GET = (req) => {
  const config = portal.getComponent();
  return {
    body: `<div>
              <h1>${config.heading}</h1>
          </div>`
  };
};
```

## Layouts

The layout implementation lives next to its [Layout schema](https://developer.enonic.com/docs/cms/xp8/pages/parts) at `src/main/resources/cms/layouts//.ts`.

Sample layout using Thymeleaf to render two regions

```typescript
const portal = require('/lib/xp/portal');
const thymeleaf = require('/lib/thymeleaf');

exports.GET = (req) => {
    const component = portal.getComponent();

    return {
        body: thymeleaf.render(resolve('./layout-two-column.html'), {
            leftRegion: component.regions["left"],
            rightRegion: component.regions["right"],
        })
    };
};
```

Thymeleaf view to render layout

```html
<div class="row">
  <div data-portal-region="left">
    <div data-th-each="component : ${leftRegion.components}" data-th-remove="tag">
      <div data-portal-component="${component.path}" data-th-remove="tag" />
    </div>
  </div>

  <div data-portal-region="right">
    <div data-th-each="component : ${rightRegion.components}" data-th-remove="tag">
      <div data-portal-component="${component.path}" data-th-remove="tag" />
    </div>
  </div>
</div>
```

## Regions

Rendering a region essentially boils down to rendering the components of that region.

To render a component, leave a component placeholder in the page or layout’s response markup. Placeholders are then identified and iteratively rendered bys the site service. Components may contain new regions with new placeholders, so the process repeats until no placeholders remain in the response.

### Component placeholders

Placeholders are formatted as HTML comments and include the component path. For example:

``

For `text/html` responses exclusively, the site service looks for component placeholders. For each placeholder, the component’s implementation is invoked and the output merged into the response.

### Basic example

A basic approach to rendering the main region of a page might look like this:

Manually create component placeholders

```typescript
const portal = require('/lib/xp/portal');

exports.GET = (req) => {
  // Get components of the main region
  const content = portal.getContent();
  const components = content.page.regions["main"].components || [];

  // Render with placeholders
  return {
    body: `<html><head>Placeholder demo</head>
            <body>
              <main data-portal-region="main">
                ${components.map((c) => `<!--# COMPONENT ${c.path} -->`).join('\n')}
              </main>
            </body>
          </html>`
  };
};
```

### Templating example

Using Thymeleaf templating, placeholder generation might look like this:

Page implementation passing region to template

```typescript
const portal = require('/lib/xp/portal');
const thymeleaf = require('/lib/thymeleaf');

exports.GET = (req) => {
  // Get the contextual content item
  const content = portal.getContent();
  const mainRegion = content.page.regions["main"];

  // Render and return the result
  return {
    body: thymeleaf.render(view, mainRegion)
  };
};
```

Thymeleaf template creating placeholders

```html
<!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
    <h1>Page with placeholders</h1>
    <main data-portal-region="main">
      <div data-th-each="component : ${mainRegion.components}" data-th-remove="tag">
        <div data-portal-component="${component.path}" data-th-remove="tag" />
      </div>
    </main>
  </body>
</html>
```

## Direct component rendering

A single component can be rendered on its own — without rendering the surrounding page — through the contextual component endpoint:

`:8080/site////_/component/`

The component path is the region name and index, so `.../_/component/main/0` renders the first component of the page’s `main` region. In this mode only the **component rendering** step runs — page resolution, response processors, and contributions are skipped.

> **Note:** By exporting `POST` (or any other HTTP method) from the component implementation, the component can also act as its own backend.

A component can detect whether it is being rendered inline (as part of a page) or directly, via the request context — useful for returning JSON in direct mode while still producing HTML for inline rendering.

## Fragments

Fragments are rendered via their existing implementations. However, since a fragment is just a subset of a page, it may render without any styling, header, or footer.

To mitigate this, add a [site mapping](docs/code/stable/web/sites/mappings.md) for the `portal:fragment` content type. The mapped implementation then runs every time a fragment is rendered.

cms/site.yaml

```yaml
kind: "Site"
mappings:
- controller: "/cms/pages/default/default.ts"
  match: "type:'portal:fragment'"
```

> **Note:** Reusing your page implementation is often convenient, since it already does the job.

In the markup produced by the implementation, leave a placeholder for the fragment:

``

The site service then renders the fragment’s components there.

Using Thymeleaf, the placeholder may be generated with the following line:

```html
<div data-portal-component="fragment" data-th-remove="tag"/>
```

## Text components

> **Warning:** Text components have been deprecated in XP8 in favor of using regular parts with a text field. The built-in text component implementation will continue to work, but it is recommended to migrate to regular components.

Unlike other component types, text components are built-in to XP and include a standard rendering implementation.

> **Note:** Bypass the built-in implementation by running your own code instead of injecting a text component placeholder in your markup.
