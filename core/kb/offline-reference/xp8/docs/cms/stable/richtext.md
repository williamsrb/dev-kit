<!-- src:https://developer.enonic.com/docs/cms/stable/richtext generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/richtext.md

# Rich text

Rich text is stored as author-edited HTML

## Editor

You may configure a rich text field in your schema using the [HtmlArea form item](#schemas/form-items/htmlarea.adoc). This provides a WYSIWYG editor in Content Studio, and stores the content as HTML with Enonic-specific markup for internal references. See the [HtmlArea](#schemas/form-items/htmlarea.adoc) documentation for details on configuration and output.

## Markup

The editor support common HTML elements out-of-the-box, such as , -,
,
, , ,  etc. In addition, it supports special handling of some elements which are stored as HTML but require customization in the front-end. These are:

- [Links](docs/cms/stable/richtext/links.md)

- [Images](docs/cms/stable/richtext/images.md)

- [Custom components (Macros)](docs/cms/stable/richtext/macros.md)

- [Styles](docs/cms/stable/richtext/styles.md)

## Raw format

Rich text is stored as HTML with Enonic-specific handling in some cases: Example of raw stored HTML:

```html
<h3>Welcome</h3>
<p>Read our <a href="content://f3076b5c-ea45-4c8b-8c06-1f87b8d8cdd9">latest post</a>.</p>
<figure><img src="image://a1b2c3d4-e5f6-7890-abcd-ef1234567890" /></figure>
[embed]<iframe src="https://www.youtube.com/embed/cFfxuWUgcvI" allowfullscreen></iframe>[/embed]
```

## Processed output

> **Tip:** Visit the [React SPA tutorial](https://developer.enonic.com/learn/react-spa/stable/rich-text) for hands-on examples of client-side rendering.

The HtmlArea field is queried with a `processHtml` argument, where `type` selects an `absolute` or `server`-relative URL and `imageWidths` controls the generated `srcset`. The `processedHtml` field returns the raw markup with each internal reference resolved and tagged with a `data-*-ref` attribute:

```graphql
{
  guillotine {
    get(key: "/articles/hello") {
      ... on com_example_myapp_Article {
        data {
          body(processHtml: {type: absolute, imageWidths: [600, 992]}) {
            raw
            processedHtml
          }
        }
      }
    }
  }
}
```

Response

```JSON
{
  "data": {
    "guillotine": {
      "get": {
        "data": {
          "body": {
            "raw": "<p>Read our <a href=\"content://f3076b5c-...\">latest post</a>.</p>",
            "processedHtml": "<p>Read our <a href=\"content://f3076b5c-...\" data-link-ref=\"e72f48b6-...\">latest post</a>.</p>"
          }
        }
      }
    }
  }
}
```

Beyond `raw` and `processedHtml`, the HtmlArea type also exposes the [special elements](#markup) as typed fields — `images`, `links` and `macros` — each carrying a `ref` that matches its `data-*-ref` attribute in `processedHtml`, so a front-end can resolve references without parsing the HTML. Each element’s page documents its typed field shape and response.

## Front-end integration

Rendering processed rich text in a front-end framework — mapping content URLs to routes, swapping image references for responsive `` tags, and rendering macros as components — is non-trivial to do by hand. See [Front-end integration](docs/cms/stable/frontend.md) for the toolkits Enonic provides.
