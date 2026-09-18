<!-- src:https://developer.enonic.com/docs/code/stable/web/extensions/customselector generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/extensions/customselector.md

# Custom Selector Extension for Content Studio

Implements the `contentstudio.customselector` interface.

## Introduction

Provides a back-end for the [CustomSelector form item](https://developer.enonic.com/docs/cms/xp8/schemas/form-items/customselector) when used in Content Studio.

The CustomSelector form item fetches options from this extension whenever the user opens the dropdown, types in the search field, or when the content is loaded with pre-selected options. The extension receives the selected options and the search query as parameters and returns a list of matching options.

> **Tip:** Visit the [Building custom selectors](https://developer.enonic.com/learn/building-custom-selectors) tutorial for an extensive example of how to build and use a CustomSelector.

## Lifecycle

- **Fetch** Content Studio lazily invokes the extension when the user opens the dropdown or types in the search field.

- **Re-fetch.** If the user types in the search field or the content is loaded with pre-selected options, Content Studio repeats the `GET` for the new parameters.

## Descriptor

The descriptor follows the standard [AdminExtension](docs/code/stable/web/extensions.md#descriptor) pattern.

src/main/resources/admin/extensions/my-panel/my-panel.yaml

```yaml
kind: "AdminExtension"
title: "My Selector"
description: "Fetches custom options for selection"
interfaces:
  - "contentstudio.customselector"          (1)
```

| ****1** | **Interface name** — must be the exact string `contentstudio.customselector` for Content Studio to discover the extension. |
| --- | --- |

## Request

Content Studio dispatches a `GET` to the extension URL with the selected content as query parameters:

| Parameter | Description |
| --- | --- |
| `ids` | Array of item ids already selected in the CustomSelector. The service is expected to return the items with the specified ids. |
| `start` | Index of the first item expected. Used for pagination of the results. |
| `count` | Maximum number of items expected. Used for pagination of the results. |
| `query` | String with the search text typed by the user in the CustomSelector input field. |

In the implementation, all standard XP request fields are available too: `req.locales` for i18n negotiation, `req.user` for the active user, and so on.

## Response

The implementation returns an XP HTTP response with the following shape:

| Name | Type | Description |
| --- | --- | --- |
| status | integer | `2xx` on success; `404` if the content can’t be loaded. |
| contentType | string | `application/json`. |
| body | string | JSON-encoded [Body](#body). |

| Name | Type | Description |
| --- | --- | --- |
| total | integer | The total number of items available. |
| count | integer | The number of items returned in this response. |
| hits | [Hit](#hit)[] | An array of items matching the count. Each hit becomes a selectable option. |

| Name | Type | Description |
| --- | --- | --- |
| id | string | A unique string reference to the item. |
| displayName | string | The title shown in the dropdown when the item is selected. |
| description | string | Optional. Short description visible under the title. |
| iconUrl | string | Optional. URL to an icon image. |
| icon | [Icon](#icon) | Optional. Inline SVG markup. |

| Name | Type | Description |
| --- | --- | --- |
| data | string | The SVG content (raw markup). |
| type | string | The MIME type, typically `image/svg+xml`. |

Sample response body

```JSON
{
  "total": 10,
  "count": 2,
  "hits": [
    {
      "id": "1",
      "displayName": "Option number 1",
      "description": "Short description shown under the title",
      "iconUrl": "/some/path/images/number_1.svg"
    },
    {
      "id": "2",
      "displayName": "Option number 2",
      "description": "Inline SVG markup is used as icon",
      "icon": {
        "data": "<svg xmlns=\"http://www.w3.org/2000/svg\"/>",
        "type": "image/svg+xml"
      }
    }
  ]
}
```

## Sample implementation

Below is a minimal example that returns a static list of selectable options. In a real-world scenario, the implementation would often fetch from an external system or compute the options based on the request parameters.

src/main/resources/admin/extensions/my-selector/my-selector.ts

```typescript
exports.get = function (request) {
    return {
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
            hits: [
                {
                    id: 'norway',
                    displayName: 'Norway',
                    description: 'this is Norway'
                },
                {
                    id: 'france',
                    displayName: 'France',
                    description: 'this is France'
                },
                {
                    id: 'portugal',
                    displayName: 'Portugal',
                    description: 'this is Portugal'
                }
            ],
            count: 3,
            total: 3
        }),
    };
 }
```
