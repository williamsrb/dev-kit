<!-- src:https://developer.enonic.com/docs/cms/stable/content/attachments generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/attachments.md

# Attachments

Content items may optionally contain attachments - files that are uploaded and stored together with the content item.

## Intro

Attachments allow you to add files to content items, similar to how files are attached to an e-mail. Attachments can be added to content items via the AttachmentUploader input type, and are stored as part of the content item in the repository.

## Attachment vs Media

Media content items represent files as separate content items that, can be linked to, published and deleted individually. Attachments, on the other hand, are stored as part of the content item and do not have a separate existence. Attachments are not indexed as separate items. Attachments are ideal for files that are closely related to the content item and do not need to be managed separately, while media content items are better suited for files that need to be reused across multiple content items or managed independently.

Media items will typically contain one attachment, which is the file that was uploaded to create the media item.

## Storage and indexing

Attachments are stored as part of the content item in the repository, and are indexed together with the content item. Attachments are stored within the content’s `attachment` property. Each attachment is represented as a property-set (object) with the following properties:

size

Attachment size

label

Attachment label

mimetype

Attachment mime-type

name

Attachment name

binary

Attachment reference (defaults to file name)

text

Text extracted from the attachment, e.g., PDF files

Example of how attachments appear in the content data:

```JSON
{
  "attachments": [
    {
      "name": "document.pdf",
      "label": "source",
      "size": 238764,
      "mimeType": "application/pdf",
      "binary": "document.pdf",
      "text": "Extracted text content from the PDF..."
    },
    {
      "name": "photo.jpg",
      "label": "source",
      "size": 102400,
      "mimeType": "image/jpeg",
      "binary": "photo.jpg"
    }
  ]
}
```

You may query for attachments using the Content API, and also search for attachments based on their properties, e.g., `attachment.name` or `attachment.text` using Enonic’s Query API.

## Other use-cases

The attachment pattern is not limited to content items, but can also be used in other contexts where storing files within XP is desirable. If you have a use-case where you want to persist other data than content in XP’s NoSQL storage, the attachment pattern provides a simple and effective way to do so.

Visit the XP development documentation for more information on how to use attachments in other contexts than content items.
