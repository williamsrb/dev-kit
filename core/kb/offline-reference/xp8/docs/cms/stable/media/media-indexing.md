<!-- src:https://developer.enonic.com/docs/cms/stable/media/media-indexing generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/media/media-indexing.md

# Media indexing

When a file is uploaded to XP, its textual content and embedded metadata are extracted and indexed automatically using [Apache Tika](https://tika.apache.org/). The contents of PDFs, Word documents, spreadsheets, presentations, and other text-bearing files become searchable alongside regular editorial content — no extra configuration required.

## What gets indexed

- **Readable text content** — Tika extracts the readable text from text-bearing formats (the words inside a PDF, Word document, spreadsheet, etc.) and stores it in the attachment’s `text` field. That text is added to the `_alltext` index, the default target for full-text search queries.

- **Standard fields** — mime type, file size, and original file name are stored in the attachment fields and searchable for every media type.

- **Additional fields** — `media:image` content has several standard fields, as well as mixins under `x.media.*` (EXIF, IPTC, and XMP mapped to `imageInfo`, `cameraInfo`, `gpsInfo`), making camera settings, GPS coordinates, and dimensions directly queryable. See [Image content type](docs/cms/stable/media/image.md#automatic-metadata-extraction) for the full field catalogue.

> **Note:** Apart from images, built-in media types do not produce structured metadata. Tika extracts only the readable content — not file metadata — so properties such as document page counts or video durations are not captured and cannot be searched.

## Full-text search example

A full-text query matches the extracted content of every media item alongside editorial text fields. The query below finds all content — including PDFs, Word documents, and any regular content type — where indexed text contains the word "quarterly":

```graphql
{
  guillotine {
    queryDsl(
      query: { fulltext: { fields: ["_alltext"], query: "quarterly" } },
      first: 20
    ) {
      _id
      displayName
      type
    }
  }
}
```

Response

```JSON
{
  "data": {
    "guillotine": {
      "queryDsl": [
        {
          "_id": "a1b2c3d4-...",
          "displayName": "Q1 report.pdf",
          "type": "media:document"
        },
        {
          "_id": "e5f6g7h8-...",
          "displayName": "Quarterly review",
          "type": "com.example.myapp:article"
        }
      ]
    }
  }
}
```

To restrict a search to media only, add a `type` filter (see [Querying](docs/cms/stable/querying.md) for the full DSL reference):

```graphql
{
  guillotine {
    queryDsl(
      query: {
        boolean: {
          must: [
            { fulltext: { fields: ["_alltext"], query: "quarterly" } },
            { matchAll: {} }
          ]
        }
      },
      contentTypes: ["media:document", "media:spreadsheet", "media:presentation"],
      first: 20
    ) {
      _id
      displayName
      type
    }
  }
}
```
