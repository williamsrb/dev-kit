<!-- src:https://developer.enonic.com/docs/cms/stable/querying generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/querying.md

# Content Querying

All content in Enonic XP is fully indexed and queryable. This page covers how content data is indexed, and how to query it using Query DSL.

> **Important:** Every query — and every aggregation built on top of one — is automatically filtered by the calling user’s read permissions. Hits, total counts, and aggregation buckets reflect only the content the caller is allowed to see. The same query run anonymously, as an editor, or with an admin token can produce different results. Plan accordingly: facets for public visitors won’t leak restricted content, but dashboards that need true totals must call as a sufficiently privileged user.

## How content is indexed

When content is created or updated, every property is automatically indexed. The CMS uses a schema-driven indexing system where each property is indexed according to its [value type](#value_types).

Content can be queried through the [GraphQL API](docs/cms/stable/apis/graphql.md) (Guillotine) or via Content API (Enonic apps) using [Query DSL](#dsl) — a JSON-based query structure.

## Value types

Every property stored in content has a value type that determines how it is indexed and how it can be queried. The value type is determined by the [form item](docs/cms/stable/schemas/form-items.md) used in your schema definition — each form item documents its value type in its Output section.

> **Important:** Query DSL value tags (`string`, `long`, `instant`, etc.) select which **typed index** to search against — not the domain type of the field. References, for example, are indexed as strings (the target’s content ID), so a term query for a reference uses `value: { string: "<content-id>" }` rather than a `reference` tag. The same applies to other domain concepts that map onto a primitive index type.

For full details on querying, value types and index behavior, see the [Storage reference documentation](docs/code/stable/storage.md).

### _alltext

The system automatically populates a special `_alltext` field by aggregating all text-analyzed properties (TextLine, TextArea, HtmlArea). This field enables broad fulltext search across all textual content without specifying individual field names.

### Index configuration

By default, content properties are indexed according to their value type. Content types can customize indexing behavior through index configuration to control:

- Which properties are indexed and how

- Whether a property should be included in `_alltext`

- Custom analyzer settings for specific properties

> **Note:** For details on index configuration, see the [XP indexing documentation](docs/platform/stable/storage/indexing.md).

## Query DSL (JSON queries)

The Query DSL is a JSON-based query format that provides a structured way to query content. It is especially useful when building queries programmatically.

### Basic structure

```JSON
{
  "query": { ... },    (1)
  "sort": { ... }      (2)
}
```

| ****1** | Query expression (filter, search, boolean compound). |
| --- | --- |
| ****2** | Sort expression. |

### Term expressions

#### term

Exact value match on a single field.

```JSON
{
  "term": {
    "field": "type",
    "value": {
      "string": "com.example:article"
    }
  }
}
```

Value types: `string`, `long`, `double`, `boolean`, `instant`, `dateTime`, `localDate`, `localTime`, `localDateTime`.

#### in

Match any of several values.

```JSON
{
  "in": {
    "field": "type",
    "values": [
      { "string": "com.example:article" },
      { "string": "com.example:blogpost" }
    ]
  }
}
```

#### like

Wildcard matching.

```JSON
{
  "like": {
    "field": "displayName",
    "value": "My*"
  }
}
```

#### range

Range query on a field.

```JSON
{
  "range": {
    "field": "data.rating",
    "gt": 3,
    "lte": 8
  }
}
```

Properties: `gt` (greater than), `gte` (greater than or equal), `lt` (less than), `lte` (less than or equal).

For date fields, use typed values:

```JSON
{
  "range": {
    "field": "data.publishDate",
    "gte": { "instant": "2025-01-01T00:00:00Z" }
  }
}
```

#### exists

Check that a field has a value.

```JSON
{
  "exists": {
    "field": "data.summary"
  }
}
```

#### pathMatch

```JSON
{
  "pathMatch": {
    "field": "_path",
    "path": "/my-site/articles/"
  }
}
```

### Fulltext expressions

#### fulltext

```JSON
{
  "fulltext": {
    "fields": ["_alltext"],
    "query": "headless cms",
    "operator": "OR"
  }
}
```

#### stemmed

```JSON
{
  "stemmed": {
    "fields": ["_alltext"],
    "query": "running quickly",
    "operator": "AND",
    "language": "en"
  }
}
```

#### ngram

```JSON
{
  "ngram": {
    "fields": ["_alltext"],
    "query": "eno",
    "operator": "AND"
  }
}
```

### Boolean (compound queries)

Combine multiple expressions using boolean logic.

```JSON
{
  "boolean": {
    "must": [                                          (1)
      {
        "term": {
          "field": "type",
          "value": { "string": "com.example:article" }
        }
      },
      {
        "fulltext": {
          "fields": ["_alltext"],
          "query": "headless",
          "operator": "OR"
        }
      }
    ],
    "mustNot": [                                       (2)
      {
        "term": {
          "field": "data.draft",
          "value": { "boolean": true }
        }
      }
    ],
    "filter": [                                        (3)
      {
        "exists": {
          "field": "data.publishDate"
        }
      }
    ]
  }
}
```

| ****1** | **must** — all expressions must match (AND). |
| --- | --- |
| ****2** | **mustNot** — none of these expressions may match (NOT). |
| ****3** | **filter** — must match, but does not affect relevance scoring. |

Also available: `should` — at least one expression should match (OR).

### Sorting (DSL)

```JSON
{
  "sort": [
    {
      "field": "data.publishDate",
      "direction": "DESC"
    },
    {
      "field": "displayName",
      "direction": "ASC"
    }
  ]
}
```

Geographic distance sort:

```JSON
{
  "sort": {
    "field": "data.location",
    "direction": "ASC",
    "type": "geoDistance",
    "value": {
      "lat": 59.9,
      "lon": 10.7
    }
  }
}
```

### Full DSL example

```JSON
{
  "query": {
    "boolean": {
      "must": [
        {
          "term": {
            "field": "type",
            "value": { "string": "com.example:article" }
          }
        },
        {
          "fulltext": {
            "fields": ["_alltext"],
            "query": "headless cms",
            "operator": "OR"
          }
        }
      ],
      "filter": [
        {
          "range": {
            "field": "data.publishDate",
            "lte": { "instant": "2025-07-01T00:00:00Z" }
          }
        }
      ]
    }
  },
  "sort": [
    {
      "field": "data.publishDate",
      "direction": "DESC"
    }
  ]
}
```

## Querying content via GraphQL

The [Guillotine](docs/cms/stable/apis/graphql.md) GraphQL API provides a `queryDsl` argument on the content query type, accepting the Query DSL format directly.

```graphql
{
  guillotine {
    queryDsl(
      query: {
        boolean: {
          must: [
            { term: { field: "type", value: { string: "com.example:article" } } }
            { fulltext: { fields: "_alltext", query: "headless", operator: OR } }
          ]
        }
      }
      sort: {
        field: "data.publishDate"
        direction: DESC
      }
      first: 10
    ) {
      displayName
      ... on com_example_Article {
        data {
          title
          summary
          publishDate
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
      "queryDsl": [
        {
          "displayName": "Headless CMS in practice",
          "data": {
            "title": "Headless CMS in practice",
            "summary": "Patterns for decoupled content delivery.",
            "publishDate": "2025-06-28"
          }
        },
        {
          "displayName": "Why we went headless",
          "data": {
            "title": "Why we went headless",
            "summary": "From monolith to API-first content.",
            "publishDate": "2025-05-12"
          }
        }
      ]
    }
  }
}
```

> **Note:** For complete Guillotine query documentation, see the [Guillotine documentation](https://developer.enonic.com/docs/guillotine).

## Common query patterns

### Content by type

```JSON
{
  "term": {
    "field": "type",
    "value": { "string": "com.example:article" }
  }
}
```

### Content by path

```JSON
{
  "like": {
    "field": "_path",
    "value": "/my-site/articles/*"
  }
}
```

### Published content only

```JSON
{
  "boolean": {
    "must": [
      {
        "range": {
          "field": "publish.from",
          "lt": { "instant": "2025-06-15T00:00:00Z" }
        }
      }
    ],
    "should": [
      {
        "range": {
          "field": "publish.to",
          "gt": { "instant": "2025-06-15T00:00:00Z" }
        }
      },
      {
        "boolean": {
          "mustNot": [
            { "exists": { "field": "publish.to" } }
          ]
        }
      }
    ]
  }
}
```

### Fulltext search with type filter

```JSON
{
  "boolean": {
    "must": [
      {
        "fulltext": {
          "fields": ["_alltext"],
          "query": "search terms",
          "operator": "OR"
        }
      }
    ],
    "filter": [
      {
        "in": {
          "field": "type",
          "values": [
            { "string": "com.example:article" },
            { "string": "com.example:page" }
          ]
        }
      }
    ]
  }
}
```

### Recently modified content

```graphql
{
  queryDsl(
    query: {
      range: {
        field: "publish.time",
        gt: { instant: "2025-06-01T00:00:00Z" }
      }
    }
    sort: { field: "publish.time", direction: DESC }
    first: 10
  )
  {
    _id
    displayName
    publish { time }
  }
}
```

### Content referencing another item

```JSON
{
  "term": {
    "field": "data.relatedArticle",
    "value": { "string": "content-id-here" }
  }
}
```

### Geolocation proximity

```JSON
{
  "sort": {
    "field": "data.location",
    "direction": "ASC",
    "type": "geoDistance",
    "value": {
      "lat": 59.9139,
      "lon": 10.7522
    }
  }
}
```
