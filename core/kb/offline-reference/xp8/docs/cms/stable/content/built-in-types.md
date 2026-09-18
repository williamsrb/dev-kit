<!-- src:https://developer.enonic.com/docs/cms/stable/content/built-in-types generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/built-in-types.md

# Built-in content types

Enonic XP ships with a set of concrete content types that are ready to use as-is. Unlike custom [content types](docs/cms/stable/content/content-types.md), they are not declared in your app — they are always available and cannot be redefined.

> **Tip:** This page covers the generic types under the `base` namespace. Types in the `portal` namespace are documented in the [pages and sites](docs/cms/stable/pages.md) section.

## Folder (base:folder)

Folders are containers for organizing child content. They have no data properties beyond their name and display name.

super-type

base:structured

is-abstract

false

is-final

false

allow-child-content

true

### Output

```JSON
{
  "_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "_name": "articles",
  "_path": "/site/articles",
  "type": "base:folder",
  "displayName": "Articles",
  "data": {}
}
```

### GraphQL

Most queries treat folders as regular `Content` — the Content interface covers what folders expose. Use the typed fragment only when you need to make the query type-explicit:

```graphql
{
  guillotine {
    getChildren(key: "/site") {
      displayName
      _path
      type
      ... on base_Folder {
        _id
      }
    }
  }
}
```

## Shortcut (base:shortcut)

Shortcuts reference or redirect to another content item. Optional key-value parameters are appended to the redirect URL.

super-type

base:structured

is-abstract

false

is-final

true

allow-child-content

true

### Output

```JSON
{
  "_id": "b2c3d4e5-...",
  "_name": "latest",
  "_path": "/site/latest",
  "type": "base:shortcut",
  "displayName": "Latest post",
  "data": {
    "target": "f3076b5c-ea45-4c8b-8c06-1f87b8d8cdd9",
    "parameters": [
      { "name": "utm_source", "value": "internal" }
    ]
  }
}
```

### GraphQL

```graphql
{
  guillotine {
    get(key: "/site/latest") {
      displayName
      ... on base_Shortcut {
        data {
          target {
            _id
            _path
            displayName
          }
          parameters {
            name
            value
          }
        }
      }
    }
  }
}
```

The `target` field is a content reference and resolves to the full target content when queried.

## Unstructured (base:unstructured)

Unstructured content permits storing any properties without a declared form. Because it has no schema, Content Studio has no default editor for it — unstructured items are typically created and updated via API.

super-type

base:structured

is-abstract

false

is-final

true

allow-child-content

true

Use cases are narrow: items whose properties vary per instance but still need editorial management, publishing, permissions, or versioning.

> **Tip:** For data that does not need editorial workflows, consider using [XP’s NoSQL storage](docs/platform/stable/storage.md) instead.

### Output

```JSON
{
  "_id": "c3d4e5f6-...",
  "_name": "telemetry-2026-04-19",
  "_path": "/site/telemetry/telemetry-2026-04-19",
  "type": "base:unstructured",
  "displayName": "Telemetry snapshot",
  "data": {
    "collectedAt": "2026-04-19T12:00:00Z",
    "metrics": {
      "requests": 42301,
      "errors": 12
    },
    "tags": ["nightly", "prod"]
  }
}
```

### GraphQL

Because the schema is not known at build time, Guillotine cannot generate typed fields for unstructured content. Use `dataAsJson` to retrieve the entire data payload:

```graphql
{
  guillotine {
    get(key: "/site/telemetry/telemetry-2026-04-19") {
      displayName
      type
      dataAsJson
    }
  }
}
```
