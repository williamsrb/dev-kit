<!-- src:https://developer.enonic.com/docs/cms/stable/apis/graphql generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/apis/graphql.md

# GraphQL API

The GraphQL API is Enonic’s primary headless API. It is provided by [Guillotine](https://developer.enonic.com/docs/guillotine), a separately versioned Enonic app that exposes your CMS content as a typed GraphQL schema.

## Location

By default, the API is available at:

```
8080:/api/guillotine:graphql
```

The exact public URL can differ per environment based on virtual host configuration, which is commonly used to expose the API on a friendlier path — for example `[https://api.example.com/graphql](https://api.example.com/graphql)`.

## Authorization

Guillotine uses XP’s IAM system for per-user authorization. Requests are evaluated in the context of the authenticated principal, and content permissions apply to every query — users only see content they are allowed to read.

Authenticate requests by passing a bearer token in the `Authorization` header:

```bash
curl -X POST https://api.example.com/graphql \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ guillotine { get(key: \"/site/articles/hello\") { displayName } } }"}'
```

Unauthenticated requests run as the anonymous user and can still access content granted `READ` permission for `role:system.everyone`.

## Schema

Guillotine generates a GraphQL schema dynamically from the content types, mixins, and x-data registered in the current project. Each [form](docs/cms/stable/schemas/forms.md) field maps to a typed GraphQL field (for example, `TextLine` → `String`, `ImageSelector` → `MediaImage`, `ItemSet` → a nested object type), so a front-end developer gets an accurate schema to query against without any manual mapping.

The schema also includes queries for [pages and components](docs/cms/stable/pages.md), [content hierarchies](docs/cms/stable/content.md), [full-text search](docs/cms/stable/querying.md), and references between items.

For the full schema reference, query syntax, and configuration options, see the [Guillotine documentation](https://developer.enonic.com/docs/guillotine).

## Extending the schema

Beyond the generated schema, an application can register a **Guillotine extension** to add custom queries, mutations, types, and resolvers that appear alongside Guillotine’s generated types — for example, to surface data from an external system or to expose a value that isn’t part of the content model.

An extension is declared in `src/main/resources/guillotine/guillotine.js`, which exports an `extensions` function describing the additional types and the resolvers that fetch their data. Once the app is deployed, the additions are served from the same endpoint and queryable like any other field.

For the descriptor format and resolver API, see the [Guillotine extension documentation](https://developer.enonic.com/docs/guillotine/stable/extending).

## Usage

Requests are standard GraphQL `POST` requests with a JSON body containing `query` and optional `variables`:

```bash
curl -X POST https://api.example.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ guillotine { get(key: \"/site/articles/hello\") { displayName } } }"}'
```

```JSON
{
  "data": {
    "guillotine": {
      "get": {
        "displayName": "Hello world"
      }
    }
  }
}
```

For hands-on examples querying content, pages, images, and more, see the [Developer 101](https://developer.enonic.com/learn/developer-101/stable) guide.
