<!-- src:https://developer.enonic.com/docs/cms/stable/pages/page-editor generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/pages/page-editor.md

# Visual page editor

Content Studio offers a visual editing mode based on pages and components.

## Introduction

To support visual editing in Content Studio’s Page Editor, including drag’n drop, two things are required.

- The page DOM must include annotations for regions and components

- The page must load and initialize the page editor (available as a separate NPM module).

## Region annotations

Regions are represented by an element with the `data-portal-region` attribute, and a value matching the region name i.e. `main`.

Sample DOM annotating the main region

```html
<!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
    <h1>Hello region</h1>
    <div data-portal-region="main"/>
  </body>
</html>
```

> **Note:** For an empty region dropzone to appear in the editor, a target element must be provided, like in the example above.

## Component annotations

Components must be annotated with a special component-type annotation.

The available values are: `layout`, `part`, `text`, and `fragment`

Sample DOM annotating two components

```html
<!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
    <h1>Hello region</h1>
    <div data-portal-region="main">
      <div data-portal-component-type="text">..</div>
      <div data-portal-component-type="part">..</div>
    </div>
  </body>
</html>
```

## Hierarchies

Using layouts, you may create hierarchies of regions and components. For the page editor to work properly, the component elements must be be hierarchically structured within the page DOM.

The page editor uses this structure to identify the components by path.

Sample DOM structure with nested regions.

```html
<!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
    <h1>Hello region</h1>
    <div data-portal-region="main"/>
     <div data-portal-component-type="layout">
        <div data-portal-region="left"/>
        <div data-portal-region="center"/>
        <div data-portal-region="right"/>
     </div>
  </body>
</html>
```

## Page editor initialization

Beyond the DOM annotations above, the page must load and initialize the page editor so Content Studio can drive it. Enonic publishes this as the [`@enonic/page-editor`](https://www.npmjs.com/package/@enonic/page-editor) NPM package, which adds live-editing capabilities to an externally rendered front-end.

Install it in your front-end project:

```bash
npm install --save @enonic/page-editor
```

The package exposes a `PageEditor` object with one entry point per Content Studio mode — `initPreview()` for read-only preview, and `initEditor()` for the editable view:

```javascript
import {PageEditor} from '@enonic/page-editor';

// Read-only preview
PageEditor.initPreview();

// Editable view — resolveUrl maps a component path to the
// endpoint that returns its rendered HTML
PageEditor.initEditor({
  resolveUrl: ({view}) => `/components/${view.getPath()}`,
});
```

In edit mode the editor refreshes individual components in place rather than reloading the whole page, which is why `initEditor` needs `resolveUrl`. Additional options (such as triggering a full reload on head contributions, or sanitizing component HTML) are documented with the package.

> **Note:** See the [`@enonic/page-editor` documentation](https://github.com/enonic/npm-page-editor) for the full initialization API and options.

> **Tip:** The official [front-end toolkits](docs/cms/stable/frontend.md) wire this up for you. Reach for `@enonic/page-editor` directly when integrating a framework the toolkits don’t cover.
