<!-- src:https://developer.enonic.com/docs/cms/stable/pages/text generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/pages/text.md

# Rich text component

Visually add and edit rich text within a region.

## Introduction

Text are built-in components that require no further configuration. They are essentially pre-configured instances of the [HtmlArea input types](docs/cms/stable/schemas/form-items/htmlarea.md), adapted to work as components in the page editor.

## Usage

Below is an example of the Text component in action via the page editor. The blue box is a text component being edited:

## Rendering

> **Note:** Text components have specific requirements for styling and HTML output, and are optimized for use with Enonic’s front-end toolkits. When rolling your own integration, consider implementing a [part](docs/cms/stable/pages/parts.md) with an HtmlArea input instead, which gives you explicit control over both the form and the output.

## Querying via GraphQL

Text components appear in a page’s component list as `TextComponent`, with the rich text available as `value`. The same stored-vs-processed distinction applies as for regular [HtmlArea](docs/cms/stable/schemas/form-items/htmlarea.md) fields — see [HTML processing](docs/cms/stable/richtext.md#html-processing) for how `content://` links, image references, and macros are resolved.

```graphql
{
  guillotine {
    get(key: "/site/articles/hello") {
      page {
        regions {
          components {
            ... on TextComponent {
              path
              value
            }
          }
        }
      }
    }
  }
}
```
