<!-- src:https://developer.enonic.com/docs/code/stable/storage/aggregations generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/storage/aggregations.md

# Aggregations

## Introduction

With Aggregations, developers may extract statistical data from search results. Aggregations can be used for anything from data visualization to creating navigational UI’s.

Consider a query returning all nodes that have a property "price" less than, say, $100. Now, we want to divide the result nodes into ranges, say 0-$25, $25-$50 and so on. We also would like to know the average price for each category. This could be done by doing multiple separate queries and calculating the average manually, but this would be very inefficient and cumbersome. Luckily, aggregations solve these types of problems easily.

In some API functions it is possible to send in an aggregations expression object like the following:

Basic aggregation DSL

```json
{
"aggregations" : {
  "[name]" : {
    "[type]" : {
      ... body ...
    },
    "aggregations": {
      ... sub-aggregations ...
    }
  }
}
```

There are two different types of aggregations:

Bucket aggregations

A bucket aggregation places documents matching the query in a collection - a bucket. Each bucket has a key.

Metrics aggregations

A metric aggregation computes metrics over a set of documents.

Typically, you will divide data into buckets and then use metric aggregations to calculate e.g average values, sum, etc. for each bucket, if necessary.

## Aggregation types

### Term

The `terms` aggregation places documents into bucket based on property values. Each unique value of a property will get its own bucket. Here’s a list of properties:

field (string)

The property path.

size (int)

The number of bucket to return, ordered by the given orderType and orderDirection. Default to `10`.

order (string)

How to order the results, type and direction. Default to `_term ASC`.

minDocCount (int)

Only include bucket in the result if number of hits is `minDocCount` or more. This parameter is optional.

Types:

- `_term`: Alphabetic ordering of bucket keys.

- `_count`: Numeric ordering of number of document in buckets.

Sample term aggregation

```json
{
  "aggregations": {
    "categories": {
      "terms": {
        "field": "myCategory",
        "order": "_count desc",
        "size": 10
      }
    }
  }
}
```

Sample result from the above agg

```json
{
  "aggregations": {
    "categories": {
      "buckets": [
        {
          "docCount": 132,
          "key": "articles"
        },
        {
          "docCount": 101,
          "key": "documents"
        },
        {
          "docCount": 43,
          "key": "case-studies"
        }
      ]
    }
  }
}
```

### Stats

The stats-aggregations calculates statistics over numeric values extracted from the aggregated documents. The following statistics are supported:

`avg`, `min`, `max`, `count`, and `sum`

Here’s a list of properties:

field (string)

The property path.

Sample stats aggregation

```json
{
  "start": 0,
  "count": 0,
  "aggregations": {
    "products": {
      "terms": {
        "field": "data.product.category",
        "order": "_count desc",
        "size": 10
      },
      "aggregations": {
        "priceStats": {
          "stats": {
            "field": "data.product.price"
          }
        }
      }
    }
  }
}
```

Sample result from the above agg

```json
{
  "products": {
    "buckets": [
      {
        "key": "tv",
        "docCount": 123,
        "priceStats": {
          "count": 123,
          "min": 2599,
          "max": 87944,
          "avg": 7400,
          "sum": 578100
        }
      },
      {
        "key": "blu-ray player",
        "docCount": 42,
        "priceStats": {
          "count": 42,
          "min": 699,
          "max": 5999,
          "avg": 1548,
          "sum": 65016
        }
      },
      {
        "key": "reciever",
        "docCount": 12,
        "priceStats": {
          "count": 12,
          "min": 2999,
          "max": 26950,
          "avg": 5548,
          "sum": 66756
        }
      }
    ]
  }
}
```

### Min

An aggregation that computes the minimum of the values in the current bucket. Here’s the list of properties:

field (string)

The property path.

Sample min aggregation

```json
{
  "aggregations": {
    "minPrice": {
      "min": {
        "field": "data.product.price"
      }
    }
  }
}
```

Sample result from the above agg

```json
{
  "minPrice": {
    "value": 10
  }
}
```

### Max

An aggregation that computes the maximum of the values in the current bucket. Here’s the list of properties:

field (string)

The property path.

Sample max aggregation

```json
{
  "aggregations": {
    "maxPrice": {
      "max": {
        "field": "data.product.price"
      }
    }
  }
}
```

Sample result from the above agg

```json
{
  "maxPrice": {
    "value": 10
  }
}
```

### Value Count

An aggregation that counts the number of values that current document set has for a specific field. Here’s the list of properties:

field (string)

The property path.

Sample value count aggregation

```json
{
  "aggregations": {
    "countProductsWithPrice": {
      "count": {
        "field": "data.product.price"
      }
    }
  }
}
```

Sample result from the above agg

```json
{
  "countProductsWithPrice": {
    "value": 5
  }
}
```

### Range

The range aggregation query defines a set of ranges that represents a bucket.

Parameters

| Name | Type | Details |
| --- | --- | --- |
| field | string | The property path |
| ranges | [NumericRange](#numeric_range)[] | The range-buckets to create |

Sample range aggregation

```json
{
  "price_ranges": {
    "range": {
      "field": "price",
      "ranges": [
        {
          "to": 50
        },
        {
          "from": 50,
          "to": 100
        },
        {
          "from": 100
        }
      ]
    }
  }
}
```

Sample result from the above agg

```json
{
  "price_ranges": {
    "buckets": [
      {
        "docCount": 2,
        "key": "a",
        "to": 50
      },
      {
        "docCount": 4,
        "from": 50,
        "key": "b",
        "to": 100
      },
      {
        "docCount": 4,
        "from": 100,
        "key": "c"
      }
    ]
  }
}
```

### geoDistance

The geoDistance aggregation needs a defined range to split the documents into buckets. Only documents with properties of type 'GeoPoint' will be considered in the `geoDistance` aggregation buckets.

Parameters

| Name | Type | Details |
| --- | --- | --- |
| field | string | The property path |
| origin | [Origin](#origin) | The GeoPoint from which the distance is measured. |
| ranges | [NumericRange](#numeric_range)[] | The range-buckets to create. |
| unit | string | The measurement unit to use for the ranges. Legal values are either the full name or the abbreviation of the following: km (kilometers), m (meters), cm (centimeters), mm (millimeters), mi (miles), yd (yards), ft (feet), in (inch) or nmi (nauticalmiles or NM). |

Sample geoDistance aggregation

```json
{
  "aggregations": {
    "distance": {
      "geoDistance": {
        "field": "data.cityLocation",
        "unit": "km",
        "origin": {
          "lat": "90.0",
          "lon": "0.0"
        },
        "ranges": [
          {
            "from": 0,
            "to": 1200
          },
          {
            "from": 1200,
            "to": 4000
          },
          {
            "from": 4000,
            "to": 12000
          },
          {
            "from": 12000
          }
        ]
      }
    }
  }
}
```

Sample result from the above agg

```json
{
  "aggregations": {
    "distance": {
      "buckets": [
        {
          "key": "*-1200.0",
          "doc_count": 3
        },
        {
          "key": "1200.0-4000.0",
          "doc_count": 4
        },
        {
          "key": "4000.0-12000.0",
          "doc_count": 5
        },
        {
          "key": "12000.0-*",
          "doc_count": 1
        }
      ]
    }
  }
}
```

> **Note:** At the time of writing, there is only one way of find out which result belongs to which bucket: By also sorting the result on geoDistance, and matching the order to the number of each bucket. In a future version, there will easier ways of doing this.

### dateRange

The dateRange aggregation query defines a set of date-ranges that represents a bucket. Only documents with properties of type 'DateTime' will be considered in the `dateRange` aggregation buckets.

Parameters

| Name | Type | Details |
| --- | --- | --- |
| field | string | The property path |
| format | string | The date-format of which the buckets will be formatted to on return. Defaults to `yyyy-MM-dd’T’HH:mm:ss.SSSZ`. |
| ranges | [DateRange](#date_range)[] | The range-buckets to create. Follows a special [Date-math expression](#date_math_expression). |

Sample dateRange aggregation

```json
{
  "my_date_range": {
    "dateRange": {
      "field": "date",
      "format": "MM-yyy",
      "ranges": [
        {
          "to": "now-10M"
        },
        {
          "from": "now-10M"
        }
      ]
    }
  }
}
```

Sample result from the above agg

```json
{
  "my_date_range": {
    "buckets": [
      {
        "key": "*-12-2017",
        "docCount": 2,
        "to": "2017-12-01T00:00:00Z"
      },
      {
        "key": "12-2017-*",
        "docCount": 4,
        "from": "2017-12-01T00:00:00Z"
      }
    ]
  }
}
```

#### Date-math expression

The range fields accepts a date-math expression to calculate the time-spans.

- Now minus a day: `now-1d`

- The given date minus 3 days plus one minute: `2014-12-10T10:00:00Z||-3h+1m`

- Range describing now plus one day and thirty minutes, rounded to minutes: `now+1d+30m/m`

### dateHistogram

The date-histogram aggregation query defines a set of bucket based on a given time-unit. For instance, if querying a set of log-events, a `dateHistorgram` aggregations query with interval `h` (hour) will divide each log event into a bucket for each hour in the time-span of the matching events. Here’s a list of properties:

field (string)

The property path.

interval (string)

The time-unit interval for creating bucket. Supported time-unit notations:

- `y` = Year

- `M` = Month

- `w` = Week

- `d` = Day

- `h` = Hour

- `m` = Minute

- `s` = Second

format (string)

Output format of date string.

minDocCount (int)

Only include bucket in result if number of hits ⇐ `minDocCount`.

Sample dateHistogram aggregation

```json
{
  "by_month": {
    "dateHistogram": {
      "field": "init_date",
      "interval": "1M",
      "minDocCount": 0,
      "format": "MM-yyy"
    }
  }
}
```

Sample result from the above agg

```json
{
  "by_month": {
    "buckets": [
      {
        "docCount": 8,
        "key": "2014-01"
      },
      {
        "docCount": 10,
        "key": "2014-02"
      },
      {
        "docCount": 12,
        "key": "2014-03"
      }
    ]
  }
}
```

## Types

### Date range

Defines a range to create a bucket for. `from` value will be included in the bucket, `to` will be excluded. Values in `from` and `to` follow a special [Date-math expression](#date_math_expression).

Fields

| Name | Type | Details |
| --- | --- | --- |
| from | string | inclusive from |
| to | string | exclusive to |

### Numeric range

Defines a range to create a bucket for. `from` value will be included in the bucket, `to` will be excluded.

Fields

| Name | Type | Details |
| --- | --- | --- |
| from | number | inclusive from |
| to | number | exclusive to |

Examples:

```json
{
  "to": 50 (1)
}
```

| ****1** | The bucket will contain minus infinity unto 49.999 |
| --- | --- |

```json
{
  "from": 50, (1)
  "to": 100 (2)
}
```

The bucket will contain

| ****1** | 50 |
| --- | --- |
| ****2** | unto 99.999 |

```json
{
  "from": 100 (1)
}
```

| ****1** | The bucket will contain 100 unto infinity |
| --- | --- |

### Origin

The GeoPoint from which the distance is measured.

Fields

| Name | Type | Details |
| --- | --- | --- |
| lat | number | Latitude |
| lon | number | Longitude |
