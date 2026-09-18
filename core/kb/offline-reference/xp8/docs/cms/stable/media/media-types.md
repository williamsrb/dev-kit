<!-- src:https://developer.enonic.com/docs/cms/stable/media/media-types generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/media/media-types.md

# Media content types

Media types are the content types assigned automatically to uploaded files. They all live in the `media` namespace and share a common abstract parent.

## Abstract base type (base:media)

All media types inherit from the abstract `base:media` type, which defines the capabilities shared by every uploaded file — primarily the attached binary and the auto-extracted metadata covered in [Media indexing](docs/cms/stable/media/media-indexing.md).

super-type

base:content

is-abstract

true

is-final

false

allow-child-content

false

`base:media` is abstract and cannot be used directly; Enonic picks the correct concrete subtype based on the file’s mime type at upload time.

## Built-in media types

Enonic XP automatically detects the type of media files uploaded to the CMS, and assigns them a pre-defined content type. The media types are:

### Text (media:text)

Plain text files such as .txt, and .csv

### Data (media:data)

Miscellaneous binary file formats.

### Audio (media:audio)

Audio files.

### Video (media:video)

Video files.

### Image (media:image)

Bitmap image files.

### Vector (media:vector)

Vector graphic files like .svg

### Archive (media:archive)

File archives like .zip, .tar, and .jar

### Document (media:document)

Text documents with advanced formatting, like .doc, .odt, and .pdf

### Spreadsheet (media:spreadsheet)

Spreadsheet files like .xls, .xlsx

### Presentation (media:presentation)

Presentation files like .key and .ppt

### Code (media:code)

Files with computer code like .js, .c, .pl, and .java

### Executable (media:executable)

Application files such as .app, .exe and .jar

### Unknown (media:unknown)

Files that do not match any of the above

## Querying via GraphQL

Guillotine generates a typed GraphQL type for every media type. All types implement the `Content` interface and additionally expose media-specific fields:

- `mediaUrl(type: SERVER|ABSOLUTE)` — URL to the raw `source` attachment, served by the [Attachment API](docs/cms/stable/apis/attachment.md). Returns the original file unmodified — no transformations.

- `attachments` — list of attached files (the `source` binary is always present as one).

The `media_Image` type additionally exposes `imageUrl(scale: …​, format: …​, quality: …​)`, which routes through the [Image API](docs/cms/stable/apis/image.md) for scaling, cropping, and format conversion — see [Image content type (media:image)](docs/cms/stable/media/image.md) for the complete field reference and a worked GraphQL example.

### Listing mixed media

Use `getChildren` with inline fragments when a folder may contain different media types:

```graphql
{
  guillotine {
    getChildren(key: "/my-folder") {
      displayName
      type
      ... on media_Image {
        imageUrl(scale: "block(400,400)")
      }
      ... on media_Document {
        mediaUrl
      }
      ... on media_Video {
        mediaUrl
      }
    }
  }
}
```

See [Media indexing](docs/cms/stable/media/media-indexing.md) for how extracted text and metadata become searchable.
