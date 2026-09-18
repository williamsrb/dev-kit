<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/imageselector generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/imageselector.md

# ImageSelector - input type

The ImageSelector is a specialized version of the [ContentSelector](docs/cms/stable/schemas/form-items/contentselector.md) that is limited to selecting images (content of type "media:image"), but also upload new images.

## Appearance

## Usage

```yaml
- type: "ImageSelector"
  name: "my_image"
  label: "My Image"
  occurrences:
    min: 0
    max: 1
  allowPath:  (1)
    - "${site}/*"  (2)
  treeMode: true
  hideToggleIcon: true
```

| ****1** | With the exception of `allowContentType` (which is not supported here) and `allowPath`, ImageSelector supports the same configuration options as [ContentSelector](docs/cms/stable/schemas/form-items/contentselector.md). |
| --- | --- |
| ****2** | By default, Image Selector displays all images from the root. If you want to limit images to the same site, use `allowPath: "${site}/*"` |

## Output

**Value type:** `Reference` — not included in `_alltext`

The stored value is the content ID of the selected image. Like [ContentSelector](docs/cms/stable/schemas/form-items/contentselector.md), the value is a reference to the image content item.

```JSON
{
  "my_image": "f3076b5c-ea45-4c8b-8c06-1f87b8d8cdd9"
}
```

Multiple occurrences

```JSON
{
  "my_image": [
    "f3076b5c-ea45-4c8b-8c06-1f87b8d8cdd9",
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  ]
}
```

## GraphQL

In the GraphQL API the reference is resolved to the referenced image content, so you can query its fields (and image URLs) in the same request. See [References](docs/cms/stable/content/references.md) for query examples.
