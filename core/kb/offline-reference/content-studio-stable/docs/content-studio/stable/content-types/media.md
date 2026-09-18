<!-- src:https://developer.enonic.com/docs/content-studio/stable/content-types/media generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/content-types/media.md

# Media

**Media** is a collection of content types that transform binary files — images, video, audio, documents — into content items.

## Introduction

Storing media as content means each file gets all the capabilities of a content item, including search indexing, permissions, and the same lifecycle as any other content (drafts, publishing, archiving, versions).

Content Studio identifies the media subtype from the file’s MIME type when uploading. Images get the most specialised UI (cropping, focal point — see [Image](docs/content-studio/stable/content-types/image.md)); other media types share a common set of metadata fields and rely on the browser for preview.

## Upload and replace

Media items are created by:

Clicking **New** action in the toolbar. .. Dragging files into the dialog .. Clicking the upload link in the media dialog.

The underlying file can be replaced after creation by dragging a new file onto the preview, or via the upload icon.

## Shared fields

All media content types share a small set of metadata fields:

- **Caption** — short description shown alongside the media.

- **Artist** — original author or creator.

- **Copyright** — licensing or attribution statement.

- **Tags** — free-text keywords for search and filtering.

The **Image** content type also includes a **Text** field for alternative text and picks up Exif metadata automatically from the source file.

## Referencing media

Media items can be referenced from rich-text fields, content selectors, and image inputs in the [Content Form](docs/content-studio/stable/editor/content-form.md). References are stored by content ID, so renaming or moving a media item keeps existing references intact.
