<!-- src:https://developer.enonic.com/docs/code/stable/storage/noql generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/storage/noql.md

# NoQL (legacy)

> **Warning:** NoQL is deprecated. Use the [Query DSL](docs/code/stable/storage/querying.md) for new code. This reference is kept for maintaining existing applications.

## Introduction

The Node Query Language (NoQL) is a SQL-inspired string format for querying nodes. It runs on the same query engine as the Query DSL, but is no longer the recommended entry point — the DSL is programmatically composable and covers the full feature set.

A NoQL statement is composed from two parts: [query](#query) and [sorting](#sort). The result is a set of identifiers for matching nodes; fetch the node data through a separate request. Selectors, joins, and update statements are not supported.

## Query

Queries are just one of the ways to access data in the storage. Developers may also access nodes by ID, path or by fetching child items. A query normally targets a single repository, but may also query multiple repositories at once.

There are two types of query’s format available in XP: String format and DSL (Domain Specific Language).

### Query DSL

Query DSL is an AST (Abstract Syntax Tree) expressed in JSON to define query expressions. See [documentation](docs/code/stable/storage/querying.md) for further explanation and examples.

### String Query

String queries are built from traditional expressions. For instance, the following query would return all nodes in the repo, where the property `weight` is greater than 10.

```
weight > 10
```

Expressions may be combined by using traditional logical operators such as AND, and OR. For instance, we could limit the result further:

```
weight > 10 AND fulltext('article', 'should have these words', 'AND')
```

In this case we are adding a so-called dynamic expression to the query. The fulltext() expression performs a free text search on the property `article` for the specified search string.

For both the integer comparison and fulltext expression to work, the weight, and article properties need to be [indexed](docs/code/stable/storage/indexing.md) properly.

If the query is empty, all nodes will be considered matches and returned.

The results matching a given query will be assigned a score. The scoring is for instance used to achieve relevance sorting.

### Syntax

The query syntax is based on SQL and looks very similar:

#### queryExpr

Grammar

```ebnf
queryExpr = [ constraintExpr ];
```

Empty query

If no queryExpression is given, all documents will be in the result.

#### constraintExpr

Grammar

```ebnf
constraintExpr = compareExpr
               | logicalExpr
               | functionExpr
               | notExpr ;
```

#### compareExpr

Grammar

```ebnf
compareExpr   = fieldExpr operator valueExpr ;
fieldExpr     = propertyPath ;
operator      = '=', '!=', '>', '>', '<', '<=', 'LIKE', 'NOT LIKE', 'IN', 'NOT IN' ;
valueExpr     = string | number | valueFunc ;
valueFunc     = geoPoint | instant | time | date | dateTime | localDateTime ;
geoPoint      =  '"' lat ',' lon '"' ;
instant       = 'instant(' string ')' ;
date          = 'date(' string ')' ;
time          = 'time(' string ')' ;
dateTime      = 'dateTime(' string ')' ;
localDateTime = 'localDateTime(' string ')' ;
```

Examples

```ebnf
user.myCategory = "articles"
user.myCategory IN ("articles", "documents")
user.myCategory != "articles"
user.myCategory LIKE "*tic*"
myPriority < 10
myPriority <= 10
myPriority > 10
myPriority < 100
myPriority != 10
myInstant = instant('2014-02-26T14:52:30.00Z')
myInstant <= instant('2014-02-26T14:52:30.00Z')
myInstant <= dateTime('2014-02-26T14:52:30.00+02:00')
myTime = time('09:00')
myDate = date('2015-02-26')
myLocalDateTime = localDateTime('2015-02-26T15:00')
myLocation = '59.9127300,10.7460900'
myLocation IN ('59.9127300,10.7460900','59.2181000,10.9298000')
```

> **Note:** `instant`, `dateTime`, `localDateTime`, `date` functions will force search in `datetime` index, meanwhile for `time` function usual `text` index will be used. Using expressions without functions perform a search in `text` index for any time-related field. See more about indexing [there](docs/code/stable/storage/indexing.md).

#### logicalExpr

Grammar

```ebnf
logicalExpr = constraintExpr operator constraintExpr ;
operator    = 'AND' | 'OR' ;
```

Examples

```sql
myCategory = "articles" AND myPriority > 10
myCategory IN ("articles", "documents") OR myPriority <= 10
```

#### notExpr

Grammar

```ebnf
notExpr = 'NOT' constraintExpr ;
```

Examples

```sql
NOT myCategory = 'article'
```

#### functionExpr

Grammar

```ebnf
functionExpr = functionName '(' arguments ')' ;
```

**Examples**

Fulltext analyzed property contains 'fish' and 'spot'

```sql
fulltext('_allText', 'fish spot', 'AND')
```

Sub properties of 'data.' contains 'fish' and 'spot'

```sql
fulltext('data.*', 'fish spot', 'AND')
```

Property 'myCategory' is either 'article' or 'document' and title starts with 'fish'.

```sql
myCategory IN ('article', 'document') AND ngram('title', 'fish', 'AND')
```

#### propertyPath

Grammar

```ebnf
propertyPath = pathElement ( '.' pathElement )* ;
pathElement  = ( [ validJavaIdentifier - '.' ] )* ;
```

Examples

```sql
myProperty
data.myProperty
data.myCategory.myProperty
```

> **Note:** Wildcards in propertyPaths are only supported in `fulltext` and `ngram` functions at the moment. When using these functions, expressions like these are valid:

`myProp*
*Property
data.*
*.myProperty
data.*.myProperty`

### Query functions

Here’s a description of all functions that can be used in a query.

#### fulltext()

The fulltext function is searching for words in a field, and calculates relevance scores based on a set of rules (e.g number of occurences, field-length, etc).

> **Note:** Only analyzed properties are considered when applying the fulltext function.

Function definition

```sql
fulltext(<fields>, <search-string>, <operator>)
```

fields

Comma-separated list of [propertyPaths](#propertyPath) to include in the search.

Example fields

```sql
'displayName' // Search in single field
'displayName,data.description,my.title' // Search in multiple fields
'data.*' // Wildcard usage
```

You can boost - thus increasing or decreasing hit-score per field basis. By providing more than one field to the query by appending a weight-factor: `^N`

Boosting example

```sql
fulltext('displayName^5,data.description', 'my search string', 'AND')
```

search-string

The search-string supports a set of operators

- `+` signifies AND operation.

- `|` signifies OR operation.

- `-` negates a single token.

- `*` at the end of a term signifies a prefix query.

- `(` and `)` signify precedence.

- `“` and `”` wraps a number of tokens to signify a phrase for searching

- `~N` after a word signifies edit distance (fuzziness) with a number representing [Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance).

- `~N` after a phrase signifies slop amount (how far apart terms in phrase are allowed)

operator

Allowed operators are:

- `OR` Any of the words in the search-string matches.

- `AND` All words in search-string matches.

**Examples**

Match if "myField" contains any of the given words.

```sql
fulltext("myField", "cheese fish cake onion", "OR")
```

Match if any field with path starting with "myData.myProperties" contains any of the given words.

```sql
fulltext("myData.myProperties.*", "cheese fish cake onion", "OR")
```

Match if "myField" contains any of the given words and "myCategory" = "soup".

```sql
myCategory = '"soup" AND fulltext("myField", "cheese fish cake onion", "OR")'
```

Match if "myField" contains all the given words.

```sql
fulltext("myField", "cheese fish cake onion", "AND")
```

Match if "myField" contains "Levenshtein" with a fuzziness distance of 2.

```sql
fulltext("myField", "Levenshtein~2", "AND")
```

Match if "myField" contains "fish" and not "boat".

```sql
fulltext("myField", "fish -boat", "AND")
```

Match if any field under data-set data contains "fish" and not "boat".

```sql
fulltext("data.*", "fish -boat", "AND")
```

Match exact phrase.

```sql
fulltext('data.*', '"gone fishing today"', "AND")
```

Match phrase where maximum distance between words are 2.

```sql
fulltext('data.*', '"gone fishing today"~2', "AND")
```

#### stemmed()

The stemmed function is similar to [fulltext()](#fulltext) except that it searches language optimized tokens instead of a source text. E.g. source text `The monkey loved bananas` will be transformed to `the`, `monkey`, `love`, `banana` tokens and they will be used for search.

> **Note:** Stemming is language-dependent, so [language](docs/code/stable/storage/indexing.md#languages) must be set either on the content or directly in the node indices via indexConfig.

Function definition

```sql
stemmed(<fields>, <search-string>, <operator>, <language>)
```

fields

Comma-separated list of [propertyPaths](#propertyPath) to include in the search.

> **Note:** Only `_alltext` field is currently indexed for stemming

search-string

The search-string supports a set of operators

- `+` signifies AND operation.

- `|` signifies OR operation.

- `-` negates a single token.

- `*` at the end of a term signifies a prefix query.

- `(` and `)` signify precedence.

- `“` and `”` wraps a number of tokens to signify a phrase for searching

- `~N` after a word signifies edit distance (fuzziness) with a number representing [Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance).

- `~N` after a phrase signifies slop amount (how far apart terms in phrase are allowed)

operator

Allowed operators are:

- `OR` Any of the words in the search-string matches.

- `AND` All words in search-string matches.

language

Content language that was used for stemming. List of [supported languages](docs/code/stable/storage/indexing.md#languages)

**Examples**

Match if any field contains any of the given words or their derivatives in english ("fishing", "cakes"…​)

```sql
stemmed("_alltext", "fish cake", "OR", "en")
```

#### nGram()

An n-gram is a sequence of n letters from a term. During ngram indexing, the term "foxy" is also indexed as: "f", "fo", and "fox".

When using the nGram search function, we are able get matches, even if the search only contains parts of a term. This is for instance useful when createing autocomplete functionality. The max limit of the ngram tokenizer is 25 characters, meaning that search strings over 25 characters will not match. As such, ngram queries may successfully be combined with the fulltext search function or other query expressions, to both match fragments of words as well as full phrases.

> **Note:** Only properties analyzed as text are considered when applying the ngram-function. This includes, by default, all text-based fields in the content domain.

Function definition

```sql
ngram(<field>, <search-string>, <operator>)
```

fields

Comma-separated list of [propertyPaths](#propertyPath) to include in the search.

operator

Allowed operators are:

- `OR` Any of the words in the search-string matches (default)

- `AND` All words in search-string matches.

**Examples**

Property "myProp" contains any word beginning with "lev", e.g "Levenshteins Algorithm".

```sql
ngram("myProp", "lev")
```

Property "myProp" contains words beginning with "lev" and "alg", e.g "Levenshteins Algorithm".

```sql
ngram("myProp", "lev alg", "AND")
```

Properties within "myProp" contains words beginning with "fish" or "boat", e.g "fishpond" or "boatman".

```sql
ngram("myProp.*", "fish boat", "OR")
```

#### range()

The range functions test each value in the given property for a given range.

Function definition

```sql
range(<field>, <from>, <to>, [<includeFrom>], [<includeTo>])
```

The `from` and `to` values must be of the same value type.

`includeFrom` and `includeTo` are optional with default value 'false', meaning that the actual values for the `from` and `to` are not included as matches.

Unbounded ranges can be queried by providing an empty string as argument.

**Examples**

Property version in the range, including '6.3.0'

```sql
range('version', '6.3.0', '6.4.0', 'true', 'false')
```

Property publishFrom is between two points in time

```sql
range('publishFrom', instant('2015-08-01T09:00:00Z'), instant('2015-08-01T11:00:00Z') )
```

Property myValue between 2.0 and 3.0, including 2.0

```sql
range('myValue', 2.0, 3.0, 'true', 'false' )
```

Property publishFrom newer that the given date.

```sql
range('publishFrom', instant('2015-08-01T09:00:00Z'), '')
```

Property publishTo older that the given date.

```sql
range('publishTo', '', instant('2015-08-01T09:00:00Z'))
```

#### pathMatch()

The path-match matches a path in a same branch, scoring the paths closest to the given query path first. Also, a number of minimum matching elements that must match could be set.

Function definition

```sql
pathMatch(<field>, <path>, [<minimum_elements_must_match>])
```

If not given, the default minimum-must-match value will be 1.

**Example**

Given the following nodes

```sql
/content/mySite
/content/mySite/fish
/content/mySite/fish/onion
/content/mySite/cheese
/content/mySite/cheese/jam
/content/myOtherSite
```

Property _path matching minimum 2 path elements

```sql
pathMatch('_path', '/content/mySite/fish/onion/mayonnaise', 2)
```

This will return (orded by _score):

- `/content/mySite/fish/onion`

- `/content/mySite/fish`

- `/content/mySite/cheese/jam`

- `/content/mySite/cheese`

- `/content/mySite`

## Sort

Similar to traditional SQL databases, XP lets you sort the result by property in ascending or descending order. A basic sort statement is simply defined by property and sorting direction i.e.:

```
myproperty DESC
```

Additionally, similar to Google, text-based query results may be sorted by ranking. Ranking is done through an internal algorithm that scores each individual item based on how it matches with your search. To sort by ranking, use the following statement:

```
_score DESC
```

A sorting statement can consist of one or more comma separate expressions:

If sort specified for a query, results will contain a meta system property `_sort`. It exposes field values used for sorting.

To use DSL sort check [documentation](docs/code/stable/storage/querying.md#sort).

### Syntax

#### sortExpr

Grammar

```ebnf
sortExpr = (  | dynamicSortExpr ) ( ',' ( fieldSortExpr | dynamicSortExpr ) )* ;
```

#### fieldSortExpr

Grammar

```ebnf
fieldSortExpr = propertyPath [ direction ] ;
direction     = 'ASC' | 'DESC' ;
```

Examples

```sql
_name ASC
_timestamp DESC
title DESC
data.myProperty
```

#### dynamicSortExpr

Grammar

```ebnf
dynamicSortExpr = functionExpr [ direction ] ;
direction        = 'ASC' | 'DESC' ;
```

Example sorting by distance from a geoPoint

```sql
geoDistance('locationProperty', '59.9127300,10.746090')
```

### Sort functions

Here’s a description of all functions that can be used in order-by clause.

#### geoDistance()

The geoDistance-function enables you to order the results according to distance to a given geo-point.

> **Tip:** Documents with no geo-point property with the given path will be ordered last if matching the query.

geoDistance syntax

```sql
geoDistance(<field>, <location>, [<unit>])
```

field

Any geoPoint property

location

The location is a geoPoint from which the distance factor should be calculated, formatted as "latitude,longitude".

unit

The string representation of distance unit to use. Defaults to "m" or "meters", the list of available values below:

- `"m" or "meters"`

- `"in" or "inch"`

- `"yd" or "yards"`

- `"ft" or "feet"`

- `"km" or "kilometers"`

- `"NM" or "nmi" or "nauticalmiles"`

- `"mm" or "millimeters"`

- `"cm" or "centimeters"`

- `"mi" or "miles"`

geoDistance example

```sql
geoDistance("shopLocation", "59.9127300,10.7460900", "km")
```

### Relevance sorting

All properties with values automatically get a sort index entry. This means that any property can be used for sorting, either (default) DESC (descending) or ASC (ascending).

_score

The dynamic system property **_score** is the default sort property

The score value of a node is dynamically calculated based on a number of factors: For instance, number of matching clauses in boolean expressions, how often the term appears in the documents when searching for text etc.

For more details, check out the Elasticsearch documentation.

### Sort DSL

Sort DSL is an AST (Abstract Syntax Tree) expressed in JSON to define sort expressions. See [documentation](docs/code/stable/storage/querying.md#sort) for further explanation and examples.

## More examples

### Querying paths

All nodes have three system-properties concerning the node placement in a branch, all of type `String`:

- `_name`: The node name without path.

- `_parentPath`: The parent node path.

- `_path`: The full path of the node.

See the [pathMatch()](#pathMatch) query function for advanced path matching

> **Note:** When working with the content API, all items are placed a special root node: `/content`. While this mostly is explicit when working in the content-domain, this has to be dealt with when using paths in query-expressions and functions since you are actually querying nodes.

**Examples**

Finds node with path /content/mySite/myCategory/myContent.

```sql
_path = '/content/mySite/myCategory/myContent'
```

Find all nodes with name myContent in a folder named myCategory

```sql
_name = 'myContent' AND _parentPath LIKE '*myCategory'
```

Find all nodes under the path /content/mySite/myCategory including children of children.

```sql
_path LIKE '/content/mySite/myCategory/*'
```

Find only first level children under the path /content/mySite/myCategory.

```sql
_parentPath = '/content/mySite/myCategory'
```

### Querying missing values

From time to time, it is also interesting to search for nodes with or without a value:

Sample query where property myValue "exists"

```
myValue LIKE "*"
```

Sample query where "publish.first" does NOT exists

```
publish.first NOT LIKE "*"
```

> **Note:** Using `exists` and `notExists` filters is considered the most efficient way searching for nodes with missing values

### Querying references

An aggregation of all outbound references in a node are stored in the system property `_references`. This property can then effectively be used also to find incoming references to a node.

Find all nodes referring to the node with id = 'abc':

```sql
_references = 'abc'
```

### Date and time

Querying against date and time-fields may require some knowledge on how data is stored and indexed.

#### LocalDate

LocalDate represents a date without time-zone in the ISO-8601 calendar, e.g `2015-03-19`. LocalDate-properties are stored as a ISO LocalDate-formatted string in the index, thus all searches are done against string-values.

LocalDate string-format:

```
yyyy-MM-dd
```

Given a node with a property named 'myLocalDate' of type `localDate` and value `2015-03-19`, all of the following queries will match:

```
myLocalDate = '2015-03-19'
myLocalDate > '2015-03-18'
myLocalDate <= '2015-03-19'
```

#### LocalTime

LocalTime represents a time without time-zone in the ISO-8601 calendar, e.g `11:39:49`. LocalTime-properties are stored as a ISO LocalTime-formatted string in the index, thus all searches are done against string-values.

LocalTime string-format:

```
HH:mm[:ss[.SSS]]
```

LocalTime string value examples:

```
09:30
10:00
10:00:30
10:00:30.142
```

Since the queries are matching string-values, the input time in query must either adhere the same string-format restrictions, or be wrapped in a function `time` which accepts a time-formatted string as input.

Given a node with a property named 'myLocalTime' of type `localTime` and value = `09:36:00`, all the following queries will match:

```
myLocalTime > '09:00'
myLocalTime = '09:36'
myLocalTime = '09:36:00'
myLocalTime LIKE '09:*'
myLocalTime < '09:36:01'
myLocalTime < '09:36:00.1'
```

This must be wrapped in time-function since its not padded with a leading 0:

```
myLocalTime > time('9:00')
```

If optional fractions of seconds are given, the string format will also contain this even if 0, and expression will not match unless wrapped in time-function::

```
myLocalTime = time('09:36:00.0')
```

Even if the string-matching will do the job 99% of the time, the safest bet is to always go with the time-function when applicable.

#### LocalDateTime

LocalDateTime represents a date-time without time-zone in the ISO-8601 calendar, e.g `2015-03-19T11:39:49`. LocalDateTime-properties are stored as a ISO LocalDateTime-formatted string in the index, thus all searches are done against string-values.

LocalDateTime string-format:

```
yyyy-MM-ddTHH:mm[:ss[.SSS]]
```

Since the queries are matching string-values, the input dateTime in query must either adhere the same string-format restrictions, or be wrapped in a function `dateTime` which accepts a dateTime-formatted string as input.

Given a node with a property named 'myLocalDateTime' of type localDateTime and value 2015-03-19T10:30:00, all of the following queries will match

myLocalDateTime = '2015-03-19T10:30:00' myLocalDateTime = dateTime('2015-03-19T10:30') myLocalDateTime

#### DateTime / Instant

DateTime represents a date-time with time-zone in the ISO-8601 calendar, e.g `2015-03-19T11:39:49+02:00`. Its possible to query properties of with value-type `DateTime` both as an ISO instant and as ISO dateTime, using the provided built-in functions `instant` and `dateTime`.

Instant string-format (instant always given in UTC-time):

```
yyyy-MM-ddTHH:mm[:ss[.SSS]Z
```

Instant string value examples:

```
2015-03-19T16:30:20Z
2015-03-19T16:30:20.123Z
```

DateTime string-format (`Z` for UTC, else offset in hours and minutes):

```
yyyy-MM-ddTHH:mm[:ss[.SSS](Z|+hh:mm|-hh:mm)
```

DateTime string value examples:

```
2015-03-19T16:30:20Z
2015-03-19T16:30:20+01:00
2015-03-19T16:30:20-01:30
2015-03-19T16:30:20.123-01:30
```

Given a node with a property named 'myDateTime' of type `dateTime` and value `2015-03-19T10:25:00+02:00`, all of the following queries will match:

```
myDateTime = instant('2015-03-19T08:25:00Z')
myDateTime = dateTime('2015-03-19T08:25:00Z')
myDateTime = dateTime('2015-03-19T10:25:00+02:00')
myDateTime = dateTime('2015-03-19T11:25:00+03:00')
```
