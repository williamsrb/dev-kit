<!-- src:https://developer.enonic.com/docs/cms/stable/content/references generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/references.md

# References

Content items often link to other content — an article to its author, a product to a gallery of images, a page to a related collection. Enonic models these links as **references**: typed pointers stored on the source content as the content ID (UUID) of the target.

References are first-class in XP: they are indexed, queryable in both directions, and resolved automatically as typed fields in the GraphQL API. A front-end developer can follow a reference in the same query that fetches the parent content, without a second round trip.

## Creating references

References are produced by any form item that links to other content:

- [ContentSelector](docs/cms/stable/schemas/form-items/contentselector.md) — generic reference to one or more content items.

- [ImageSelector](docs/cms/stable/schemas/form-items/imageselector.md) — reference to image media.

- [MediaSelector](docs/cms/stable/schemas/form-items/mediaselector.md) — reference to any media (images, documents, video, audio).

- [HtmlArea](docs/cms/stable/schemas/form-items/htmlarea.md) — embedded references inside rich text (links and images).

Each of these stores the target’s content ID rather than a path, so references stay valid when content is moved or renamed.

## Storage shape

A reference field stores the content ID directly on the source content. Single-occurrence fields store a string; multi-occurrence fields store an array.

Single reference

```JSON
{
  "author": "f3076b5c-ea45-4c8b-8c06-1f87b8d8cdd9"
}
```

Multiple references

```JSON
{
  "related_articles": [
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "b2c3d4e5-f6a7-8901-bcde-f23456789012"
  ]
}
```

Internally, XP also aggregates all outbound references to a dedicated `_references` index entry, which is what makes inbound lookup and reference-integrity checks possible at query time.

## Outbound references

**Outbound references** are the references a content item makes to other content — an article to its author, a product to its images. This is the common case, and Guillotine inspects your content type schemas and turns every reference field into a typed field that resolves to the referenced content. There is no need to issue a second query to fetch the target — drill into the reference field directly.

```graphql
{
  guillotine {
    get(key: "/articles/hello-world") {
      displayName
      ... on com_example_myproject_Article {
        data {
          author {
            displayName
            ... on com_example_myproject_Person {
              data {
                name
                about
              }
            }
          }
        }
      }
    }
  }
}
```

Response

```JSON
{
  "data": {
    "guillotine": {
      "get": {
        "displayName": "Hello World",
        "data": {
          "author": {
            "displayName": "Django Reinhardt",
            "data": {
              "name": "Django Reinhardt",
              "about": "Belgian-Romani jazz guitarist."
            }
          }
        }
      }
    }
  }
}
```

For multi-occurrence reference fields, the resolved field is a list of content items rather than a single one.

## Inbound references

**Inbound references** are the references that other content items make to a given content item. Inbound resolution answers "what links to this?" — useful for related-content listings, citation lists, or detecting orphaned media.

To find inbound references, run a `queryDsl` search for content whose `_references` index entry contains the target’s content ID. Because every outbound reference is indexed into the source’s `_references` field, a single term query finds every item pointing at the target regardless of which form field carries the reference:

```graphql
{
  guillotine {
    queryDsl(
      query: {
        term: {
          field: "_references",
          value: { string: "183d310b-e9e8-4336-a5a4-4bf1c1c40353" }
        }
      }
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
          "_id": "f7f00e52-b025-4bef-8358-3c4c57604c99",
          "displayName": "Tutorials",
          "type": "base:shortcut"
        },
        {
          "_id": "d8190c73-14ad-4654-aee5-bb83410a3687",
          "displayName": "Quickstart",
          "type": "com.company:landing-page"
        }
      ]
    }
  }
}
```

## Indexing and integrity

Every outbound reference is indexed under the `_references` field at the source content. The reverse direction (inbound) is resolved at query time by searching that index for matches pointing at the target ID — there is no second copy on the referenced content.

Reference integrity has a few practical consequences:

- **Moving or renaming** referenced content does not break references — IDs are stable across path changes.

- **Publishing** a content item that references unpublished content will surface as a publish-time dependency. Content Studio prompts the editor to include the dependencies.

- **Deleting** content that is the target of inbound references is blocked by default. The deletion will fail until the inbound references are removed or the operation is forced.

- **Querying** by the `_references` field works exactly like any other indexed field — you can filter, sort, and aggregate on references in the [Query DSL](docs/cms/stable/querying.md).
