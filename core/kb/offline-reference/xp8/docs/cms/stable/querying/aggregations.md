<!-- src:https://developer.enonic.com/docs/cms/stable/querying/aggregations generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/querying/aggregations.md

# Aggregations

Aggregations summarize matching content into buckets and metrics — counts grouped by field value, numeric ranges, date histograms, statistics over a numeric field, and so on. They are the foundation for faceted search UIs, filter sidebars with counts, dashboards, and editorial reports.

> **Important:** Aggregations are only supported on Guillotine’s **`queryDslConnection`** field — not the plain `queryDsl` field. Use `queryDslConnection` whenever a query needs to return aggregations alongside hits.

> **Note:** Aggregations are computed over the result set the calling user can read — see [Querying](docs/cms/stable/querying.md) for the permission-filtering semantics that apply to every query. Anonymous and admin calls will see different bucket counts.

## Anatomy of an aggregation request

Aggregations are passed as a list of named expressions on the `aggregations` argument of `queryDslConnection`. Each expression has a `name` (which becomes the key in the response) and exactly one aggregation type:

```graphql
queryDslConnection(
  query: { ... }
  first: 0                    (1)
  aggregations: [
    { name: "byType", terms: { field: "type", size: 10 } }
  ]
) {
  totalCount
  edges { node { _id displayName } }
  aggregationsAsJson           (2)
}
```

| ****1** | Set `first: 0` if you only need the aggregations, not the hits. The connection still returns `totalCount`. |
| --- | --- |
| ****2** | Aggregation results come back as a single opaque JSON blob under `aggregationsAsJson`. The shape inside mirrors XP’s native aggregation result. |

## Bucket aggregations

Bucket aggregations group matching content into buckets and return a doc count per bucket.

### terms

Group content by the distinct values of a field. The most common aggregation, used for facet-style "count by content type", "count by tag", "count by author" queries.

```graphql
{
  guillotine {
    queryDslConnection(
      query: { matchAll: {} }
      first: 0
      aggregations: [
        { name: "byType", terms: { field: "type", size: 10, order: "_count desc" } }
      ]
    ) {
      totalCount
      aggregationsAsJson
    }
  }
}
```

Response

```JSON
{
  "data": {
    "guillotine": {
      "queryDslConnection": {
        "totalCount": 142,
        "aggregationsAsJson": {
          "byType": {
            "buckets": [
              { "key": "media:image",  "docCount": 87 },
              { "key": "portal:site",  "docCount": 12 },
              { "key": "base:folder",  "docCount": 9 }
            ]
          }
        }
      }
    }
  }
}
```

Parameters:

- **field** — indexed field to group by.

- **size** — maximum number of buckets to return (largest first).

- **order** — `_count desc` (default), `_count asc`, `_key asc`, or `_key desc`.

### range

Bucket numeric values into explicit ranges. Useful for price brackets, rating bands, file-size groupings, etc.

```graphql
aggregations: [
  {
    name: "priceBands",
    range: {
      field: "data.price",
      ranges: [
        { to: 50 },
        { from: 50, to: 100 },
        { from: 100 }
      ]
    }
  }
]
```

Each range is inclusive of `from` and exclusive of `to`. Omitting `from` matches everything below `to`; omitting `to` matches everything from `from` upward.

### dateRange

Like `range`, but for date/time fields. Accepts date math expressions (`now`, `now-10M`, `now+1d`).

```graphql
aggregations: [
  {
    name: "publishAge",
    dateRange: {
      field: "publish.first",
      format: "yyyy-MM-dd'T'HH:mm:ss.SSSZ",
      ranges: [
        { to: "now-1y" },
        { from: "now-1y", to: "now-1M" },
        { from: "now-1M" }
      ]
    }
  }
]
```

### dateHistogram

Bucket date values into fixed-width intervals — e.g. "publish count per month" for a time-series chart.

```graphql
aggregations: [
  {
    name: "publishesPerMonth",
    dateHistogram: {
      field: "publish.first",
      interval: "1M",
      format: "yyyy-MM",
      minDocCount: 0
    }
  }
]
```

Parameters:

- **interval** — `1M`, `1w`, `1d`, `1h`, etc.

- **format** — output format for bucket keys.

- **minDocCount** — set to `0` to include empty intervals (useful for sparse time series); default omits empty buckets.

### geoDistance

Bucket content by distance from a reference point. Useful for proximity-driven listings ("within 1 km", "1–5 km", "5–20 km", "beyond 20 km") against a `GeoPoint` field.

```graphql
aggregations: [
  {
    name: "byDistance",
    geoDistance: {
      field: "data.location",
      origin: { lat: 59.91, lon: 10.75 },
      unit: "km",
      ranges: [
        { to: 1 },
        { from: 1, to: 5 },
        { from: 5, to: 20 },
        { from: 20 }
      ]
    }
  }
]
```

Parameters:

- **field** — a `GeoPoint`-typed field.

- **origin** — the reference point as `{ lat, lon }`.

- **unit** — `km`, `m`, `mi`, etc.

- **ranges** — distance brackets, with the same `from`/`to` semantics as numeric `range`.

## Metric aggregations

Metric aggregations return a single number rather than a bucket list.

### stats

Returns count, min, max, average, and sum for a numeric field in a single aggregation.

```graphql
aggregations: [
  { name: "ratingStats", stats: { field: "data.rating" } }
]
```

Response

```JSON
{
  "ratingStats": {
    "count": 87,
    "min": 1,
    "max": 5,
    "avg": 3.94,
    "sum": 343
  }
}
```

### min, max, count

When you only need one of the metrics from `stats`, the dedicated aggregations are slightly cheaper and produce a smaller response.

```graphql
aggregations: [
  { name: "newest", max:   { field: "modifiedTime" } },
  { name: "oldest", min:   { field: "createdTime" } },
  { name: "totalCount", count: { field: "_id" } }
]
```

## Sub-aggregations

Bucket aggregations can nest further aggregations inside each bucket — e.g. "for each content type, the most-used author". In Guillotine, nest with the `subAggregations` field on the parent aggregation entry.

```graphql
aggregations: [
  {
    name: "byType",
    terms: { field: "type", size: 10 },
    subAggregations: [
      { name: "byAuthor", terms: { field: "data.author", size: 5 } }
    ]
  }
]
```

The response nests bucket lists under each parent bucket:

```JSON
{
  "byType": {
    "buckets": [
      {
        "key": "com.example:article",
        "docCount": 34,
        "byAuthor": {
          "buckets": [
            { "key": "alice", "docCount": 18 },
            { "key": "bob",   "docCount": 11 }
          ]
        }
      }
    ]
  }
}
```

## Reading the response

Because aggregations come back as a single `aggregationsAsJson` field, the GraphQL response is opaque to typed selection — bucket keys, doc counts, and metric values are **not** introspectable as typed fields. Parse the JSON in your client and address aggregations by their `name`:

```javascript
const { aggregationsAsJson } = result.data.guillotine.queryDslConnection;
const buckets = aggregationsAsJson.byType.buckets;
buckets.forEach(b => console.log(b.key, b.docCount));
```

## Limitations and notes

- Aggregations are not available on the plain `queryDsl` field — use `queryDslConnection`.

- Combine aggregations with filtering by passing a regular `query` argument; aggregations are computed over the matched set, not the entire repository.

- Bucket counts reflect only content the calling user can read — public, editor, and admin calls produce different totals. See [Querying](docs/cms/stable/querying.md).

- Set `first: 0` (or a small page size) when you only need aggregations; doc-list rendering is independent of aggregation cost.

- Aggregate field paths follow the same dotted-path convention as DSL queries (e.g. `data.author`, `publish.first`, `data.contact_info.label`).

See the [XP aggregation reference](docs/code/stable/storage/aggregations.md) for the underlying DSL semantics, and the [Guillotine documentation](https://developer.enonic.com/docs/guillotine) for the full GraphQL schema.
