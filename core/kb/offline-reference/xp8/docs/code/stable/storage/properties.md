<!-- src:https://developer.enonic.com/docs/code/stable/storage/properties generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/storage/properties.md

# Properties

## Introduction

Properties contain the actual data inside a [node](docs/code/stable/libraries/lib-node.md). Properties use a key-value format

The key must be unique within the node, and the value must have a specific [valueType](#value_types), such as `String`, or `GeoPoint`.

## Property anatomy

Examples of what a property might look like:

```properties
mytext = "a string"
mynumber = 1
```

Some characters are illegal in a property key. Here’s a list of illegal characters:

- `_` is system reserved prefix

- `.` is the path separator.

- `[` and `]` are array index indicators.

Properties may also be nested, making the key a path. Elements in the path are separated by `.` (dot).

Here’s an example of properties with arrays and nested properties.

```properties
first-name = "Thomas"
cities = ["Oslo", "San Francisco"]
city.location = geoPoint('37.785146,-122.39758')
person.age = 39
person.birth-date = localDate("1975-17-10")
```

In the example above, the property `person` is of the [value type](#value_types) `Set`. Sets are special in the way that they don’t hold actual values, but rather act as containers for other properties.

## Value types

Each property has a specific value type. These are the primitive data types in the XP storage The value type enables the data storage to handle both validation and [indexing](#indexing) of the property.

Below is the complete list of all supported value-types.

| Value Type | Example | Default indexing | Comment |
| --- | --- | --- | --- |
| String | My String | text | String of characters within UTF charset |
| BinaryReference | a-binary-reference | text | Handle for accessing a binary |
| Boolean | true | text | A value representing `true` or `false` |
| Double | 11.5 | number, text | Double-precision 64-bit IEEE 754 floating point. |
| GeoPoint | 59.9090442,10.7423389 | geoPoint, text | Represents a geographical point on earth, given in latitude and longitude. |
| Instant | 2015-03-16T10:00:02Z | datetime, text | A single point on the time-line (may include subsecond up to 9 digits). |
| LocalTime | 10:00:03 | text | A time representation without date or timezone(nor subsecond). |
| LocalDate | 2015-03-16 | datetime, text | A date representation. Will be indexed with UTC timezone offset. |
| LocalDateTime | 2015-03-16T10:00:02 | datetime, text | A date-time representation without timezone. Will be indexed with UTC timezone offset. |
| Long | 1234 | number, text | 64-bit two’s complement integer. |
| Reference | 0b7f7720-6ab1-4a37-8edc-731b7e4f439e | text | Holds a reference to other nodes in the same repository. |
| Set |  | Not indexed | Holds sub properties as it’s value |
| XML | <some>xml</some> | text | Any valid XML |

## Indexing

When a node is persisted, its property values are indexed instantly. A single property can be indexed multiple times — each index is referred to as an *index mapping*. The default mapping XP applies to a property depends on its value type (see the **Default indexing** column above).

The available mappings:

text

Default mapping for any value type. Stores the value for exact match.

number

Effectively handles any numeric value.

datetime

Handles any date value.

geoPoint

Supports earth-based geographical locations.

ngram

Indexes all substrings from 2 to 25 characters of a string. Accessed via the `nGram` query function.

analyzed

Splits a string into tokens for free-text search. Used by the `fulltext` query function.

stemmed

Language-optimised version of `analyzed`. Tokens are reduced to their stem so plural and gender-specific endings still match.

path

Indexes path elements (split on `/`) as separate tokens.

orderby

Generated automatically for every indexed property. Used to sort text and numbers in a natural way.

XP also maintains a system property called `_allText` that aggregates the text content of all indexed string properties on a node — useful for "search everything" queries.

Applications can override the default mappings per property via the `_indexConfig` system property. For the full configuration reference — config options, templates, property-path patterns, and the language list for stemming — see [Indexing](docs/code/stable/storage/indexing.md).

## System Properties

In order to separate system defined properties from user defined properties, `_` (underscore) has been reserved as a starting character for the system properties.

### Core properties

| System Property | Value Type | Indexing | Comment |
| --- | --- | --- | --- |
| _id | String | string | Holds the unique id of the node, typically a UUID |
| _name | String | string | Holds the name of the node. Must be unique within its scope (nodes with same parent) |
| _parentPath | String | string | Reference to parent node path |
| _path | String | path, string | Dynamic property resolved from parent path + node name |
| _childOrder | String | string | Default ordering of children when using getChildren() |
| _manualOrderValue | Long | number, string | Numeric order value used for the builtin manual ordering |

### Versioning properties

| _state | String | string | Used for keeping state of a node in a branch |
| --- | --- | --- | --- |
| _ts |  | datetime, string | The last time this node was modified |
| _versionKey |  | string | For every change to a node, a unique versionKey is generated |

### Indexing properties

| System Property | Value Type | Indexing | Comment |
| --- | --- | --- | --- |
| _nodeType | string | string | Used to create collections of nodes in a repository |
| _indexConfig | string | Not indexed | Node specific index configuration |
| _allText | String | string, analyzed, ngram | Aggregates text across other string properties in the node |
| _references | Reference | string | Aggregates all reference properties in the node |

Node permissions are also flattened into indexed `*permissions**` system properties at write time. See [Permissions — Querying by permission](docs/code/stable/storage/permissions.md#_querying_by_permission) for the full list and usage.
