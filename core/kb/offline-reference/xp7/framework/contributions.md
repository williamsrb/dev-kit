<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/contributions generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/contributions.md

# Page Contributions

Lets components, macros, and processors contribute content to the response HTML header and/or footer.

> **Note:** Only available in the [Site Engine](/docs/platform/7.x/runtime/engines/site-engine)

## Introduction

Some pages and applications require specific scripts to be available within the HTML response of a page, typically placed within a specific location of the markup such as in the  section, or close to the body end tag.

Example use cases are:

- Let a part contribute JavaScript to the page’s `` section.

- Let a part contribute custom CSS to the `` of that page.

- A layout might add a JavaScript tracker to the end of the `` of the page.

> **Note:** Page contributions will only be triggered if the response type is `text/html` (which is the default)

There are four positions in the result HTML where contributed content can be inserted:

headBegin

After the `` opening tag.

headEnd

Before the `` closing tag.

bodyBegin

After the `` opening tag.

bodyEnd

Before the `` closing tag.

## Usage

The component or controller must add a `pageContributions` property in the [HTTP response object](/docs/platform/7.x/framework/http#http-response).

Sample controller return adding a script element to `headEnd`.

```js
return {
  body: '<p>Some markup</p>',
  pageContributions: {
    headEnd: [
      "<script>My script</script>"
    ]
  }
};
```

Changing the `headEnd` to one of the other possible positions will affect where the code you contributed is merged in the response markup.

Sample with multiple contributions

```js
return {
  "body": "<div>...</div>",
  "pageContributions": {
    "headEnd": "value",
    "bodyEnd": [
      "value1", "value2"
    ]
  }
};
```

- Page Contributions are optional.

- Contribution values are treated as plain text.

- Values must be unique within each injection point, duplicates will be truncated.

- If the target tag does not exist in the response body, the contribution will be ignored. I.e. if there is no `` tag, the contributions to `headBegin` and `headEnd` will be ignored.

- For consistency, all positions are automatically treated arrays in the aggregated response object, even if there is only a single value.

## Contribution merging

Page contributions are merged into the response markup during a specific step in the [site engine](/docs/platform/7.x/runtime/engines/site-engine), called `Contributions filter`. It occurs after [page processors](/docs/platform/7.x/framework/processors) and before [the site filters](/docs/platform/7.x/framework/mappings).

> **Note:** Duplicate page contributions will automatically be removed, so developers do not have to worry about this.
