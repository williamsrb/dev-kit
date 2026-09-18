<!-- src:https://developer.enonic.com/docs/code/stable/storage/querying generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/storage/querying.md

# Querying

## Query DSL

### Introduction

Enonic XP provides a Query DSL (Domain Specific Language) based on JSON to define queries. Usually query JSON object looks like syntax tree consisting of two types of operators:

- `Expression`: Provides a way to check particular fields for various native and analysed values.

- `Compound`: Provides a way to logically combine various expressions and compounds to fetch nodes based on complex conditions.

### Expressions

Each node field could be indexed in many ways according to its type and user mappings. By default, a query searches in base primitive value index of a field (number, string, boolean). To force search in a field’s advanced analysed index (like dates and geoPoints), a `type` of expression must be provided.

> **Note:** Search could be done by an expression with particular type only for analyzed fields with compatible [value type](docs/code/stable/storage/properties.md#value_types) and not prohibiting type mapping.

#### Value types

As said above, fields could be indexed in many ways. Which one will be used to make a search for an expression? By default, it depends on a specified JSON value type (string, number or boolean). But a developer can force a search by pointing 'type' expression property for some indices.

time

Time expression converts expression as [LocalTime](docs/code/stable/storage/properties.md#value_types) string and makes a search for a field indexed as 'string'.

dateTime

DateTime expression makes a search for fields indexed as 'datetime' (`Instant`, `LocalDate`, `LocalDateTime` [value types](docs/code/stable/storage/properties.md#value_types)). If time is not specified it will be set to zero. If timezone is not specified it will be set to UTC.

#### Expression types

term

Fetch nodes with exact value in a provided field.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| field | string | true | property name to search. |
| value | object | true | exact property value. |
| type | string | false | value [type](#value_types). |
| boost | number | false | multiplier for `_score` result value. |

**Request examples:**

Matches if the exact value in "myNumber" field.

```json
{
  "term": {
    "field": "myNumber",
    "value": 4.2
  }
}
```

Matches if the exact value and boost the score of the result.

```json
{
  "term": {
    "field": "myBoolean",
    "value": true,
    "boost": 2
  }
}
```

in

Fetch nodes if a provided field contains any of listed values.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| field | string | true | property name to search. |
| values | object[] | true | array of possible property values. All values must be of the same type. |
| type | string | false | value [type](#value_types). |
| boost | number | false | multiplier for `_score` result value. |

**Request examples:**

Matches if "myNumber" field contains any of the values.

```json
{
  "in": {
    "field": "myNumber",
    "values": [
      3.2,
      4.0,
      5
    ]
  }
}
```

> **Note:** You cannot mix values of different types in the same `in` expression.

Matches if "myDateTime" field contains any of the dateTime indexed values.

```json
{
  "in": {
    "field": "myDateTime",
    "type": "dateTime",
    "values": [
      "2015-02-26T12:00:00.030Z",
      "2015-02-26T12:00:00-02:23"
    ]
  }
}
```

like

Returns nodes that contain the field matching a wildcard pattern.

Supported wildcard operators:

- `*` - matches zero or more characters

- `?` - matches exactly one character

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| field | string | true | property name to search. |
| value | string | true | search string. |
| type | string | false | value [type](#value_types). |
| boost | number | false | multiplier for `_score` result value. |

**Request examples:**

Matches if "myString" field contains a value starts with 'start' .

```json
{
  "like": {
    "field": "myString",
    "value": "start*"
  }
}
```

Matches if "myString" field contains a value ends with 'end' .

```json
{
  "like": {
    "field": "myString",
    "value": "*end"
  }
}
```

Matches if "myString" field contains a value and boost the result hits.

```json
{
  "like": {
    "field": "myString",
    "value": "*middle*",
    "boost": 2.2
  }
}
```

Matches if "myString" field contains a value where '?' represents any single character, e.g. 'car', 'cat', 'can'.

```json
{
  "like": {
    "field": "myString",
    "value": "ca?"
  }
}
```

range

Matches the nodes with fields that have terms within a certain range. Index to search depends on the field and expression types.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| field | string | true | property name to search. |
| lt | object | false | less than. |
| lte | object | false | less than or equals. |
| gt | object | false | greater than. |
| gte | object | false | greater than or equals. |
| type | string | false | value [type](#value_types). |
| boost | number | false | multiplier for `_score` result value. |

- `gt` and `gte` cannot be used together.

- `lt` and `lte` cannot be used together.

- At least one range property must be specified.

- All specified properties must be of the same type.

**Request examples:**

Matches if "myNumber" field contains a number value less than 5, inclusive.

```json
{
  "range": {
    "field": "myNumber",
    "lte": 5
  }
}
```

Matches if "myString" field contains a string value from 'a' to 'd' (inclusive 'a') and boosts the result hits.

```json
{
  "range": {
    "field": "myString",
    "gte": "a",
    "lt": "d",
    "boost": 1.5
  }
}
```

Matches if "myDateTime" field contains a dateTime value from '2017-09-11T09:00:00Z' zulu time.

```json
{
  "range": {
    "field": "myDateTime",
    "type": "dateTime",
    "gt": "2017-09-11T09:00:00Z"
  }
}
```

pathMatch

The path-match matches a path in a same branch, scoring the paths closest to the given query path first. Also, a number of minimum matching elements that must match could be set.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| field | string | true | property name to search. |
| path | string | true | path value. |
| minimumMatch | number | false | number of minimum matching elements. |
| boost | number | false | multiplier for `_score` result value. |

**Request examples:**

Matches property '_path' with minimum 2 path elements

```json
{
  "pathMatch": {
    "field": "_path",
    "path": "/mySite/folder1/folder2/images",
    "minimumMatch": 2
  }
}
```

matchAll

Matches all nodes, giving them all a `_score` of '1.0'.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| boost | number | false | multiplier for `_score` result value. |

Matches all nodes

```json
{
  "matchAll": { }
}
```

Matches all nodes and boosts the score

```json
{
  "matchAll": {
    "boost": 2
  }
}
```

exists

Returns nodes that contain a value for a field.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| field | string | true | name of a field to check on existence. |

Matches all nodes

```json
{
  "exists": {
    "field": "displayName"
  }
}
```

#### String expressions

| Parameter | Type | Required | Description |  |
| --- | --- | --- | --- | --- |
| fields | string[] | true | List of propertyPaths to match. |  |
| query | string | true | A query string to match field value(s). Support the set of [operators](#query_operators). |  |
| operator | string | false | A default operator used if no explicit operator is specified in the query.                    `OR` | Any of the words in the query string matches (by default). |
| `AND` | All words in the query string matches. |  |  |  |

query operators:

- `+` signifies AND operation.

- `|` signifies OR operation.

- `-` negates a single token.

- `*` at the end of a term signifies a prefix query.

- `(` and `)` signify precedence.

- `“` and `”` wraps a number of tokens to signify a phrase for searching

- `~N` after a word signifies edit distance (fuzziness) with a number representing [Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance).

- `~N` after a phrase signifies slop amount (how far apart terms in phrase are allowed)

To use one of these characters literally, escape it with a preceding backslash (\).

> **Note:** You can boost - thus increasing or decreasing hit-score per field basis. By providing more than one field to the query by appending a weight-factor: ^N

fulltext

The fulltext expression is searching for words in a field, and calculates relevance scores based on a set of rules (e.g number of occurences, field-length, etc).

> **Note:** Only analyzed properties are considered when applying the fulltext function.

**Request examples:**

Matches if any of query’s words found in listed properties and boosts the match in '_name' field

```json
{
  "fulltext": {
    "fields": [
      "_name^3",
      "my.inner.analyzed.property",
      "custom.*"
    ],
    "query": "apple pork fish",
    "operator": "OR"
  }
}
```

Matches displayName field started with 'pork pie' words combination and negates 'apple' token

```json
{
  "fulltext": {
    "fields": "displayName",
    "query": "~apple pork+pie*"
  }
}
```

ngram

An edge n-gram is a sequence of n letters from a term. During ngram indexing, the term "foxy" is also indexed as: "f", "fo", and "fox".

When using the nGram search expression, we are able get matches, even if the search only contains parts of a term. This is for instance useful when creating autocomplete functionality. The max limit of the ngram tokenizer is 25 characters, meaning that search strings over 25 characters will not match. As such, ngram queries may successfully be combined with the fulltext search function or other query expressions, to both match fragments of words as well as full phrases.

> **Note:** Only properties analyzed as text are considered when applying the ngram expression. This includes, by default, all text-based fields in the content domain.

**Request examples:**

Matches properties within "myProp" contain words beginning with "fish" or "boat", e.g "fishpond" or "boatman".

```json
{
  "ngram": {
    "fields": [
      "displayName",
      "_name^3"
    ],
    "query": "fish boat"
  }
}
```

Analyzed child fields of "custom" contain words beginning with "lev" and "alg", e.g "Levenshteins Algorithm".

```json
{
  "ngram": {
    "fields": "custom.",
    "query": "lev alg",
    "operator": "AND"
  }
}
```

stemmed

The stemmed expression is similar to [Fulltext](#fulltext) except that it searches language optimized tokens instead of a source text. E.g. source text `The monkey loved bananas` will be transformed to `the`, `monkey`, `love`, `banana` tokens and they will be used for search.

> **Note:** Stemming is language-dependent, so [language](docs/code/stable/storage/indexing.md#languages) must be set either on the content or directly in the node indices via indexConfig.

special expression fields:

fields

Comma-separated list of [propertyPaths](#propertyPath) to include in the search. Only `_allText` field is currently indexed for stemming by default.

language

Content language that was used for stemming. List of [supported languages](docs/code/stable/storage/indexing.md#languages)

**Request examples:**

Matches any field value that contains any of the given words or their derivatives in English ("fishing", "cakes"…)

```json
{
  "stemmed": {
    "fields": "_allText",
    "query": "fish boat",
    "language": "en"
  }
}
```

### Compounds

Compound expressions wrap other compounds or expressions, either to combine their results and scores or to change their behaviour.

#### boolean

Boolean provides the way to combine logical operations on expressions. All sub-expressions can contain a single expression or an array.

Structure example

```json
{
  "boolean": {
    "should": {
        ...
    },
    "must": {
        ...
    },
    "mustNot": [
      {
        "boolean": {
          "should": {
              ...
          }
        }
      }
      ...
    ]
  }
}
```

must

All expressions must evaluate to true to include a node in the result.

Single expression

```json
{
  "boolean": {
    "must": {
      "term": {
        "field": "myNumber",
        "value": 2.4
      }
    }
  }
}
```

Array expression

```json
{
  "boolean": {
    "must": [
      {
        "term": {
          "field": "myNumber",
          "value": 2.4
        }
      },
      {
        "ngram": {
          "field": "displayName",
          "query": "fisk"
        }
      }
    ]
  }
}
```

should

One or more expressions must evaluate to true to include a node in the result.

'_path' OR 'displayName' must evaluate to true.

```json
{
  "boolean": {
    "should": [
      {
        "pathMatch": {
          "field": "_path",
          "path": "/fisk/a/b",
          "minimumMatch": 2
        }
      },
      {
        "like": {
          "field": "displayName",
          "value": "fol*der"
        }
      }
    ]
  }
}
```

mustNot

All expressions in the mustNot must evaluate to false for nodes to match.

'_path' expression must evaluate to true AND 'displayName' expression to false.

```json
{
  "boolean": {
    "must":
      {
        "pathMatch": {
          "field": "_path",
          "path": "/fisk/a/b",
          "minimumMatch": 2
        }
      },
    "mustNot":
    {
      "like": {
        "field": "displayName",
        "value": "fol*der"
      }
    }
  }
}
```

filter

Equivalent to [must](#must), but faster — `filter` skips relevance scoring, so matches don’t contribute to `_score`.

Any expression or compound documented above can be used inside `filter`; there is no filter-specific syntax.

'date_field' must be greater that the specified date and 'displayName' must start with 'my'

```json
{
  "boolean": {
    "filter": [
      {
        "range": {
          "field": "date_field",
          "type": "dateTime",
          "gt": "2017-09-11T09:00:00Z"
        }
      },
      {
        "like": {
          "field": "displayName",
          "value": "my*"
        }
      }
    ]
  }
}
```

> **Tip:** Migrating from the legacy [filters](docs/code/stable/storage/filters.md) API? See the [mapping table](docs/code/stable/storage/filters.md#legacy_filter_migration).

### Boosting

Any query operator result (expression or compound) can be boosted to change the relevance score of the nodes.

Positive boost

```json
{
  "boolean": {
    "should": [
      {
        "term": {
          "field": "myString",
          "value": "value 1"
        }
      },
      {
        "term": {
          "field": "myString",
          "value": "value 2",
          "boost": 2.0  (1)
        }
      },
      {
        "term": {
          "field": "myString",
          "value": "value 3",
          "boost": 0.5  (2)
        }
      }
    ]
  }
}
```

| ****1** | Positive boost, increasing the score. |
| --- | --- |
| ****2** | Negative boost, decreasing the score. |

To boost the bunch of expressions they could be wrapped by an inner boolean query:

```json
{
  "boolean": {
    "should": [
      {
        "boolean": {
          "should": [
            {
              "term": {
                "field": "field",
                "value": "a"
              }
            },
            {
              "term": {
                "field": "field",
                "value": "b"
              }
            }
          ],
          "boost": 2.2
        }
      },
      {
        "term": {
          "field": "field",
          "value": "c"
        }
      }
    ]
  }
}
```

> **Tip:** Avoid combining group boosting and single term boosting in the same expression.

## Sort DSL

It’s a way to place result nodes in specific order based on their property values. The sort is defined on a per property level, with special field name for `_score` to sort by relevance. Relevance is done by scoring each individual item based on how it matches your query.

Score sorting

```json
{
  "sort": {
    "field": "_score"
  }
}
```

> **Note:** Order defaults to DESC when sorting by `_score`, and ASC when sorting by anything else.

To change a direction of sorting use `direction` property:

Field sorting

```json
{
  "sort": {
    "field": "myField",
    "direction": "ASC"
  }
}
```

To sort by a few fields just set them in the right order: .Multi-field sorting

```json
{
  "sort": [
    {
      "field": "myFirstField",
      "direction": "DESC"
    },
    {
      "field": "mySecondField"  //Defaults to ASC
    }
  ]
}
```

### Locale-aware sorting

In addition to the default UNICODE sorting, text fields can be sorted using locale-aware collations, such as DUCET or language-specific collations. This allows for more natural sorting of text for specific languages.

> **Note:** Locale-aware sorting is only supported for text fields that are indexed with a language-specific analyzer. The language for sorting can be specified using the `language` property in the sort definition.

Field sorting

```json
{
  "sort": {
    "field": "myField",
    "direction": "ASC",
    "language": "no"
  }
}
```

### geoDistance

The geoDistance allows to order the results according to distance to a given geo-point.

| Parameter | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| field | string | geoPoint type property |  |  |
| direction | string | 'ASC' or 'DESC'. |  |  |
| location | object | A geoPoint from which the distance factor should be calculated                      `lat` | number | latitude |
| `lon` | number | longitude |  |  |

unit

string

The string representation of distance unit to use. Defaults to "m" or "meters".

- `"m" or "meters"`

- `"in" or "inch"`

- `"yd" or "yards"`

- `"ft" or "feet"`

- `"km" or "kilometers"`

- `"NM" or "nmi" or "nauticalmiles"`

- `"mm" or "millimeters"`

- `"cm" or "centimeters"`

- `"mi" or "miles"`

geoDistance sort example

```json
{
  "sort": [
    {
      "field": "myGeoPoint",
      "direction": "ASC",
      "location": {
        "lat": "90.0",
        "lon": "0.0"
      },
      "unit": "km"
    }
    ]
}
```
