<!-- src:https://developer.enonic.com/docs/code/stable/web/sites/contributions generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/sites/contributions.md

# Page Contributions

Enables components, macros, and processors to contribute content to the response HTML header and/or footer.

## Introduction

Some pages and applications require specific scripts to be available within the HTML response of a page, typically placed within a specific location of the markup such as in the  section, or close to the body end tag.

Example use cases are:

- Let a part contribute JavaScript to the page’s `` section.

- Let a part contribute custom elements to the beginning of the ``.

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

The component or HTTP function must add a `pageContributions` property to the [HTTP response object](docs/code/stable/web/request-response.md#response).

Example response adding a script element to `headEnd`:

```typescript
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

```typescript
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

Page contributions are merged into the response markup during a specific step in the [site service](docs/code/stable/web/sites.md), called `Contributions filter`. It occurs after [page processors](docs/code/stable/web/sites/processors.md) and before [the site filters](docs/code/stable/web/sites/mappings.md).

> **Note:** Duplicate page contributions are automatically removed, so if multiple components contribute the same script, it will only be included once in the final response.
