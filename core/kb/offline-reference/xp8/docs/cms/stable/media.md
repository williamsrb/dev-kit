<!-- src:https://developer.enonic.com/docs/cms/stable/media generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/media.md

# Media

Media are content items where an uploaded file is the primary payload. Every file uploaded to Enonic becomes its own content item — with a path, a content type, permissions, versioning, indexing, and API access — just like any other content.

## Introduction

Because media are content, everything documented under [Content](docs/cms/stable/content.md) applies: they live in [projects](docs/cms/stable/projects.md), can be [referenced](docs/cms/stable/content/references.md) by other items, queried alongside regular content, and published through the normal [lifecycle](docs/cms/stable/content/lifecycle.md).

What makes them different is the presence of an attached file. On upload, Enonic inspects the file’s mime type and assigns the appropriate concrete media type — `media:image`, `media:document`, `media:video`, and so on. See [Media content types](docs/cms/stable/media/media-types.md) for the full list.

## Anatomy

A media item bundles two things in a single content record:

- **The content item itself** — standard [content properties](docs/cms/stable/content.md#standard-properties), plus editorial fields specific to the media type (for images: `caption`, `altText`, `artist`, `copyright`, `tags`).

- **One or more attachments** — the actual binary files, stored on the content item under the top-level `attachments` array.

**Every media has at least one attachment** — the original uploaded file. The content’s `data.media.attachment` field points to it by name, and the attachment itself is always tagged with `label: "source"`. This labelling keeps the original upload identifiable even when additional attachments are added later by editors or other apps.

Example JSON for a media:document

```JSON
{
  "_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "_name": "q1-report.pdf",
  "_path": "/site/files/q1-report.pdf",
  "type": "media:document",
  "displayName": "Q1 report",

  "data": {
    "media": {
      "attachment": "q1-report.pdf"       (1)
    }
  },

  "attachments": [                        (2)
    {
      "name": "q1-report.pdf",
      "label": "source",                  (3)
      "mimeType": "application/pdf",
      "size": 238764,
      "binary": "q1-report.pdf",
      "text": "Quarterly earnings overview..."
    }
  ]
}
```

| ****1** | **data.media.attachment** — name of the primary attachment, always present. Concrete media types may add editorial fields alongside — for example, `media:image` adds `caption`, `altText`, `artist`, `copyright`, and `tags`. See [Image](docs/cms/stable/media/image.md#standard-fields) for the image-specific fields. |
| --- | --- |
| ****2** | **attachments** — the actual binary files. For text-bearing formats (PDF, Word, etc.) the extracted `text` is stored here and contributes to full-text search. |
| ****3** | **label: "source"** — always set on the attachment created from the original upload, so the primary file stays distinguishable from any additional attachments. |

> **Note:** Editorial fields and indexing behavior vary per type. See [Media content types](docs/cms/stable/media/media-types.md) for the list and [Media indexing](docs/cms/stable/media/media-indexing.md) for what gets extracted and searched per type.

## Media vs attachments

"Attachment" is a more general mechanism than "media": any content item — not just media — can carry attachments, added through the [AttachmentUploader](docs/cms/stable/schemas/form-items/attachmentuploader.md) form item.

|  | Media | Attachment |
| --- | --- | --- |
| **What it is** | A content item whose primary purpose is to hold a file. | A file stored inside any content item, secondary to its editorial data. |
| **Has own URL, permissions, lifecycle?** | Yes — it’s a full content item. | No — inherits from its parent content. |
| **Referenced from other content?** | Yes, by id — via ImageSelector, MediaSelector, or content references. | No — lives only inside its parent content. |
| **Indexed for search as a separate hit?** | Yes. | No — indexed alongside its parent. |
| **Typical use** | Shared assets: photos, PDFs, videos reused across the site. | Supporting files specific to one content item, e.g. a form submission’s uploads. |

In practice: if a file needs to be found, linked, published, or permissioned on its own, make it a media. If it only makes sense in the context of a single content item, attach it.

See [Attachments](docs/cms/stable/content/attachments.md) for the attachment-within-content pattern.

## Delivery and querying

Media binaries and data are delivered through dedicated APIs:

- [Image API](docs/cms/stable/apis/image.md) — URL-based delivery with on-the-fly scaling, cropping, and format conversion for `media:image`.

- [Attachment API](docs/cms/stable/apis/attachment.md) — raw file delivery for any attachment, including the primary attachment on non-image media types.

Editorial fields, mixin metadata, and delivery URLs are all available through the headless GraphQL API — see [Image](docs/cms/stable/media/image.md#querying-via-graphql) and [Media types](docs/cms/stable/media/media-types.md#querying-via-graphql) for worked examples.

## Further reading

- [Media content types](docs/cms/stable/media/media-types.md) — all built-in `media:*` types.

- [Image content type](docs/cms/stable/media/image.md) — the detailed reference for `media:image`, including standard fields and the full EXIF/IPTC/XMP → mixin mapping.

- [Media indexing](docs/cms/stable/media/media-indexing.md) — how file contents and metadata become searchable.
