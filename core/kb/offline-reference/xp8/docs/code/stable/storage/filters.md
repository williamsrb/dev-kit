<!-- src:https://developer.enonic.com/docs/code/stable/storage/filters generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/storage/filters.md

# Filters

## Introduction

Filters work differently from [queries](docs/code/stable/storage/querying.md). When searching with a regular query, steps like sorting and scoring are done to produce the result.

These are relatively costly operations. A filter does none of these steps. A filter *only* removes nodes from the result - and is executed after the query statement, if it exists.

> **Warning:** Filters are deprecated and will be removed in future XP versions. Use [query filtering](docs/code/stable/storage/querying.md#_filter) instead — see the [mapping table below](#legacy_filter_migration) for how each filter type translates to the DSL.

## Migrating to the Query DSL

Each legacy filter has a direct equivalent inside `boolean.filter` (or `boolean.mustNot`) in the [Query DSL](docs/code/stable/storage/querying.md):

| Legacy filter | DSL equivalent |
| --- | --- |
| `exists` | [exists](docs/code/stable/storage/querying.md#exists) expression inside `filter` |
| `notExists` | [exists](docs/code/stable/storage/querying.md#exists) expression inside `mustNot` |
| `hasValue` | [in](docs/code/stable/storage/querying.md#in) expression inside `filter` |
| `ids` | [in](docs/code/stable/storage/querying.md#in) expression on the `_id` field inside `filter` |
| `boolean` | `boolean` compound (combine `must`, `mustNot`, `should`, `filter` as needed) |

### Syntax

Filters are defined using a DSL (Domain Specific Language) expressed in JSON.

Below is an example of a filter used in the content-API

Sample filter usage

```typescript
import { query } from '/lib/xp/content';

const result = query({
    start: 0,
    count: 2,
    query: "data.city = 'Oslo' AND fulltext('data.description', 'garden', 'AND')",
    filters: {
        boolean: {
            must: {
                exists: { field: 'modifiedTime' },
            },
            mustNot: {
                hasValue: {
                    field: 'myField',
                    values: ['cheese', 'fish', 'onion'],
                },
            },
        },
        notExists: {
            field: 'unwantedField',
        },
        ids: {
            values: ['id1', 'id2'],
        },
    },
});
```

If specifying several filters on root level, the filters are automatically joined with a boolean "must" clause, meaning all filters must match.

The following filters are supported:

### exists

The exists filter filter outs any document *not containing* any values in the given property.

field (string)

The property path

Sample use of exists filter

```json
{
  "start": 0,
  "count": 2,
  "filters": {
    "exists": {
      "field": "publish.from"
    }
  }
}
```

### notExists

The notExists filter removes nodes *containing* values in the given property.

field (string)

The property path

Sample use of notExists filter

```json
{
  "start": 0,
  "count": 2,
  "filters": {
    "notExists": {
      "field": "publish.from"
    }
  }
}
```

### hasValue

The hasValue filter matches if document contain any of the values given in the value list

field (string) The property path

values (object[]) Array of values to decide a match

Sample hasValue filter

```json
{
  "start": 0,
  "count": 2,
  "filters": {
    "hasValue": {
      "field": "product",
      "values" : [
        "plunge saw",
        "combination square",
        "router",
        "mitre saw"
      ]
    }
  }
}
```

### ids

The ids filter is a shorthand filter to filter on ids

values (string[]) Arrays of ids to match

Sample ids filter

```json
{
  "start": 0,
  "count": 2,
  "filters": {
    "ids": {
      "values": [
        "0123456789",
        "1234567890"
      ]
    }
  }
}
```

### boolean

The boolean filter combines functions in logical expressions

must (filter[])

All functions on the must array must evaluate to true for the filter to match

mustNot (filter[])

All functions in the mustNot array must evaluate to false for the filter to match

should (filter[])

One or more of the functions in the should array must evaluate to true for the filter to match

Sample boolean filter

```json
{
  "start": 0,
  "count": 2,
  "filters": {
    "boolean": {
      "must": {
        "exists": {
          "field": "modifiedTime"
        }
      },
      "mustNot": {
        "hasValue": {
          "field": "myField",
          "values": [
            "cheese",
            "fish",
            "onion"
          ]
        }
      }
    }
  }
}
```
