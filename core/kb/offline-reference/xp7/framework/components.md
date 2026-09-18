<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/components generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/components.md

# Component controllers

Special controllers used to render page components.

> **Note:** Component controllers are only used in context of the [Site Engine](/docs/platform/7.x/runtime/engines/site-engine)

## Introduction

> **Tip:** For a hands on introduction to rendering pages with the Enonic framework, visit the [My first site tutorial](https://developer.enonic.com/docs/my-first-site).

Component controllers are 1:1 aligned with their respective [page component definitions](/docs/platform/7.x/cms/pages) and must also be placed in specific locations within the code structure.

They have the same capabilities as regular [controller](/docs/platform/7.x/framework/controllers), you may take advantage of [page contributions](/docs/platform/7.x/framework/contributions), and the fact that they are always executed in the context of a content item.

> **Important:** Markup response from a component must have a single root element.

## Context

Component rendering is initiated by the [Site Engine](/docs/platform/7.x/runtime/engines/site-engine). The controllers are derived when a client requests a specific page via the site engine:

`HTTP request` → `/site///path/to/content` → `resolve component` → `execute controller`.

This means you will always have a specific content item in your context.

API functions such as [portalLib.getContent()](/docs/platform/7.x/api/lib-portal#getContent), and [portalLib.getComponent()](/docs/platform/7.x/api/lib-portal#getComponent) will automatically return values based on the context.

> **Tip:** Thanks to the site engine’s built-in access control you are also guaranteed that the current user has read permissions to the contextual content item.

## Page controllers

Page controlles must be placed next to your [page descriptor](/docs/platform/7.x/cms/pages) i.e. `src/main/resources/site/pages//`.

Sample page controller using the context

```javascript
const portal = require('/lib/xp/portal');

exports.get = function(req) {

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

## Part controllers

Part controlles must be placed next to your [part descriptor](/docs/platform/7.x/cms/pages/parts) i.e. `src/main/resources/site/parts//`.

Sample part controller using the form value

```javascript
const portal = require('/lib/xp/portal');

exports.get = function(req) {

  const config = portal.getComponent();
  return {
    body: `<div>
              <h1>${config.heading}</h1>
          </div>`
  };
};
```

## Layout controllers

Layout controlles must be placed next to your [layout descriptor](/docs/platform/7.x/cms/pages/layouts) i.e. `src/main/resources/site/layouts//`.

Sample layout using Thymeleaf to render two regions

```js
var portal = require('/lib/xp/portal');
var thymeleaf = require('/lib/thymeleaf');

exports.get = function (req) {
    var component = portal.getComponent();

    return {
        body: thymeleaf.render(resolve('./layout-two-column.html'), {
            leftRegion: component.regions["left"],
            rightRegion: component.regions["right"],
        })
    };

};
```

Thymeleaf view to render layout

```HTML
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

Component hierarcies are created via [regions](/docs/platform/7.x/cms/pages/regions). Rendering a region essentially boils down to rendering the components of that region.

To render a component, simply leave a component placeholder in your page or layout’s response markup. Component placeholders are then identified and rendered by the [component rendering](/docs/platform/7.x/runtime/engines/site-engine) step of the site engine.

As components may contain new regions, with new placeholders, this process will be repeated until there are no more placeholders left in the response.

### Component Placeholders

Placeholders are formatted as HTML comments - and includes the component path. Like this example:

``

For `text/html` responses, the site engine will look for component placeholders. For each placeholder, the component’s controller is executed and the output merged into the response.

### JavaScript example

A basic approach to rendering the main region of a page might look something like this:

Manually create component placeholders

```javascript
var portal = require('/lib/xp/portal');

exports.get = function(req) {

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
}
```

### Templating example

Using Thymeleaf templating, placeholder generation might look like this:

Page controller passing region to template

```javascript
var thymeleaf = require('/lib/thymeleaf');

exports.get = function(req) {

  var portal = require('/lib/xp/portal');

  // Get the contextual content item
  var content = portal.getContent();
  var mainRegion = content.page.regions["main"];

  // Render and return the result
  return {
    body: thymeleaf.render(view, mainRegion);
  };
}
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

## Fragments

Fragments essentially rendered via their existing controllers. However, as fragments are just subsets of a page, the will likely be rendered without any styling, header or footer.

To mitigate this, the recommended approach is adding a controller mapping to help spice up the visual appearance.

Add a [controller mapping](/docs/platform/7.x/framework/mappings) for the `portal:fragment` content type. This will then be executed every time a fragment is rendered.

site.xml

```XML
<mapping controller="/site/pages/default/default.js">
  <match>type:'portal:fragment'</match>
</mapping>
```

> **Note:** It can often be convenient to reuse your page controller, as this is already doing the job.

In the markup produced by the controller, leave a placeholder for the fragment:

``

The site engine will then render the fragment’s components here.

Using Thymeleaf, the placeholder may be generated with the following line of code:

```HTML
<div data-portal-component="fragment" data-th-remove="tag"/>
```

## Text controllers

Unlike the other components types, [Text components](/docs/platform/7.x/cms/pages/text) are built-in to XP. This includes a standard controller that will render the component.

> **Note:** Optionally bypass the built-in controller by running your own code rather than creating a placeholder for the text components.
