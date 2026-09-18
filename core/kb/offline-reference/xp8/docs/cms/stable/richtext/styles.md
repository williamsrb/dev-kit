<!-- src:https://developer.enonic.com/docs/cms/stable/richtext/styles generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/richtext/styles.md

# Custom styles

XP supports definition of custom styles for use in rich text content.

## Introduction

Styles are used to add effects and styling to elements of the [Rich Text Editor](https://developer.enonic.com/docs/content-studio/stable/editor/rich-text-editor#custom_image_styles).

Each style is intended to be mapped to a corresponding front-end style (i.e. css class). Image styles additionally support instructions for the image service, enabling image crops and filters to be applied server-side.

> **Note:** At the moment, custom styles are only supported for Images.

## Descriptor

The `style.yaml` file declares the custom styles for your app.

Example style definition:

/src/main/resources/cms/style/style.yaml

```yaml
kind: "Style"
styles:
  - type: "image"  (1)
    name: "editor-image-cinema"
    label: "Cinema"
    aspectRatio: "21:9"  (2)
  - type: "image"
    name: "editor-image-sepia"
    label: "Old photo"
    filter: "sepia(25)"  (3)
    editor:  (4)
        css: |
            .editor-image-sepia {
                width: 100px;
                height: 100px;
            }
```

| ****1** | **type** (required) Currently only `image` styles are supported. |
| --- | --- |
| ****2** | **aspectRatio** (optional) Server-side crop ratio applied by the image service when the style is selected. |
| ****3** | **filter** (optional) Server-side image filter applied by the image service. See the image service documentation for the full list of available filters. |
| ****4** | **editor.css** (optional) This CSS will be injected into Content Studio’s rich text editor for an improved editor experience. Use the `\|` block scalar to embed the rule set directly in the descriptor. |

> **Note:** `aspectRatio` and `filter` are the only options available for server-side image processing.

## Built-in styles

By default, XP comes with a built-in image style called `Original (no image processing)`. By applying this style to an image, the original image file will be served, without any processing.
