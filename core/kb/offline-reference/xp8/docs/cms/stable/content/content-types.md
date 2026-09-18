<!-- src:https://developer.enonic.com/docs/cms/stable/content/content-types generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/content-types.md

# Content Types

Content types is the foundational schema type in Enonic XP. All content items must be based on a content type. Content types are used to define the sturcture and capabilities of a content items.

## Name

Every content type has a unique identifier in the following format `:`. Content types are either built-in, or custom defined by developers.

## Usage

Content types schemas are defined via YAML definitions. Below is an example content type definition:

```yaml
kind: “ContentType”  (1)
title: “Person”  (2)
displayNameLabel: “Full Name”  (3)
description: “Create a new person”  (4)
superType: “base:structured”  (5)
abstract: false  (6)
final: true  (7)
allowChildContent: true  (8)
allowChildContentType:  (9)
  - “base:folder”
  - “${app}:article-*”
form: []  (10)
```

| ****1** | **kind** identifies this as a ContentType schema. |
| --- | --- |
| ****2** | **title** (required) The human readable name of the content type. Optionally use localization to define a mapping to localize the value. The localization key must then be declared and localised in the resource bundle. |
| ****3** | **displayNameLabel** (optional) Enables you to override the default <Display Name> placeholder used in the content form. |
| ****4** | **description** (optional) Set a description that is shown when creating the content type. |
| ****5** | **superType** (required) Refers to one of the [base types](#base-types). You should normally use `base:structured`. |
| ****6** | **abstract** (optional; default: false) If true, you cannot create content with this content type. |
| ****7** | **final** (optional; default: false) If true, it is not possible to create new content types that “extend” this. |
| ****8** | **allowChildContent** (optional; default: true) If false, no content will be allowed to be created or moved under content of this content type (e.g. prevents child content under media) |
| ****9** | **allowChildContentType** (optional) If specified, only content of content types matching specified criteria will be allowed to be created or moved under content of this content type. The pattern matching used is the same as the one described in [MATCH](docs/cms/stable/schemas/form-items/contentselector.md#allowContentType). |
| ****10** | **form** (required) The custom [Form](docs/cms/stable/schemas/forms.md) definition for your content type. |

> **Note:** `allow-child-content-type` will not have effect if `allow-child-content` is set to `false`

## Querying via GraphQL

Guillotine generates a dedicated GraphQL type for every content type in the project. Each typed field mirrors the YAML form definition, so a front-end developer gets a schema that matches the content shape without any manual mapping.

### Type names

Guillotine sanitizes the content type name for GraphQL by replacing the namespace separator and any dashes with underscores:

| Content type | GraphQL type |
| --- | --- |
| `com.example.myproject:Artist` | `com_example_myproject_Artist` |
| `com.enonic.app.myapp:news-article` | `com_enonic_app_myapp_news_article` |
| `portal:site` | `portal_Site` |
| `media:image` | `media_Image` |
| `base:folder` | `base_Folder` |

### Untyped access

Every content item implements the `Content` interface, which exposes standard fields available without inline fragments. Use `dataAsJson` to get the form data as raw JSON — useful when the client does not care about the specific content type:

```graphql
{
  guillotine {
    get(key: "/artists/django-reinhardt") {
      _id
      _path
      displayName
      type
      dataAsJson
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
        "_id": "f3076b5c-ea45-4c8b-8c06-1f87b8d8cdd9",
        "_path": "/artists/django-reinhardt",
        "displayName": "Django Reinhardt",
        "type": "com.example.myproject:artist",
        "dataAsJson": {
          "name": "Django Reinhardt",
          "about": "Belgian-Romani jazz guitarist."
        }
      }
    }
  }
}
```

### Typed access

To access form fields as typed GraphQL fields, use an inline fragment on the generated type:

```graphql
{
  guillotine {
    get(key: "/artists/django-reinhardt") {
      displayName
      ... on com_example_myproject_Artist {
        data {
          name
          about
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
        "displayName": "Django Reinhardt",
        "data": {
          "name": "Django Reinhardt",
          "about": "Belgian-Romani jazz guitarist."
        }
      }
    }
  }
}
```

### Querying by content type

Use `queryDsl` with a `term` query on the `type` field to fetch all content of a given type. Combine with an inline fragment to return typed data:

```graphql
{
  guillotine {
    queryDsl(
      query: { term: { field: "type", value: { string: "com.example.myproject:artist" } } },
      first: 10,
      sort: { field: "displayName", direction: ASC }
    ) {
      _id
      displayName
      ... on com_example_myproject_Artist {
        data {
          name
        }
      }
    }
  }
}
```

See the [Guillotine documentation](https://developer.enonic.com/docs/guillotine) for the full list of queries, arguments, and DSL options.

## Icon

A content type may optionally have its own specific icon which is used to represent the content type in Content Studio. The icon can be assigned to the content type by supplying a PNG or SVG file with the same name as the content type i.e. `my-content-type.svg`.

## Abstract base type

Every content type extends `base:structured`, the abstract parent for all schema-driven content. It introduces the `form` mechanism and is the common foundation for custom content types.

super-type

base:content

is-abstract

true

is-final

false

allow-child-content

true

> **Note:** You may not specify a custom content type as a supertype, nor may you create circular dependencies between content types.

Media content has its own abstract parent (`base:media`) with a different set of capabilities — see [Media content types](docs/cms/stable/media/media-types.md).

## Built-in types

Enonic XP ships with a set of concrete, ready-to-use content types:

- [base:folder](docs/cms/stable/content/built-in-types.md#folder-base-folder), [base:shortcut](docs/cms/stable/content/built-in-types.md#shortcut-base-shortcut), [base:unstructured](docs/cms/stable/content/built-in-types.md#unstructured-base-unstructured) — generic structural types; see [Built-in content types](docs/cms/stable/content/built-in-types.md).

- `media:*` — concrete media types created automatically from uploaded files; see [Media content types](docs/cms/stable/media/media-types.md).

- `portal:site`, `portal:page-template`, `portal:fragment`, `portal:template-folder` — types supporting the pages concept; see [Sites and pages](docs/cms/stable/pages.md).

## Extend with mixins

You may dynamically extend both built-in and custom-defined content types through the use of [Mixins](docs/cms/stable/content/mixins.md).
