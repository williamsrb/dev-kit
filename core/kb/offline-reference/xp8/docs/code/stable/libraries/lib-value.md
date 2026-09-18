<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-value generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-value.md

# Value library

Helper functions for creating typed Java values from JavaScript — used when storing geo-points, instants, references, and similar typed fields in nodes and content.

## Usage

```groovy
dependencies {
  include xplibs.value
}
```

```typescript
import valueLib from '/lib/xp/value';
```

## Functions

### binary

Creates a `BinaryAttachment` value from a name and a binary stream.

Parameters

`binary()` takes two positional arguments: `name` (string — the binary name) and `stream` ([ByteSource](docs/code/stable/fundamentals/types.md#byte-source) — the binary stream).

Returns

**object** : ([`BinaryAttachment`](#binary-attachment))

### geoPoint

Creates a `GeoPoint` value from numeric coordinates.

Parameters

`geoPoint()` takes two positional arguments: `lat` (number — latitude) and `lon` (number — longitude).

Returns

**object** : ([`GeoPoint`](#geo-point))

### geoPointString

Creates a `GeoPoint` value from a comma-separated latitude and longitude string.

Parameters

`geoPointString()` takes one positional argument: `value` (string — comma-separated latitude and longitude, e.g. `'59.9139,10.7522'`).

Returns

**object** : ([`GeoPoint`](#geo-point))

### instant

Creates an `Instant` value from an ISO-8601 string or a `Date` object.

Parameters

`instant()` takes one positional argument: `value` (`string | Date` — an ISO-8601-formatted instant such as `'2011-12-03T10:15:30Z'`, or a JavaScript `Date`).

Returns

**object** : ([`Instant`](#instant-type))

### localDate

Creates a `LocalDate` value from an ISO local date string or a `Date` object.

Parameters

`localDate()` takes one positional argument: `value` (`string | Date` — an ISO local date such as `'2011-12-03'`, or a JavaScript `Date`).

Returns

**object** : ([`LocalDate`](#local-date))

### localDateTime

Creates a `LocalDateTime` value from a local date-time string or a `Date` object.

Parameters

`localDateTime()` takes one positional argument: `value` (`string | Date` — a local date-time string such as `'2007-12-03T10:15:30'`, or a JavaScript `Date`).

Returns

**object** : ([`LocalDateTime`](#local-date-time))

### localTime

Creates a `LocalTime` value from an ISO local time string or a `Date` object.

Parameters

`localTime()` takes one positional argument: `value` (`string | Date` — an ISO local time such as `'10:15:30'`, or a JavaScript `Date`).

Returns

**object** : ([`LocalTime`](#local-time))

### reference

Creates a `Reference` value from a node ID string.

Parameters

`reference()` takes one positional argument: `value` (string — a node ID, e.g. `'1234-5678-91011'`).

Returns

**object** : ([`Reference`](#reference-type))

## Type Definitions

### GeoPoint

A typed geo-point value. Returned by `geoPoint()` and `geoPointString()`.

Methods

| Name | Type | Description |
| --- | --- | --- |
| `getLatitude()` | number | The latitude component. |
| `getLongitude()` | number | The longitude component. |
| `toString()` | string | Serialized form — `'<lat>,<lon>'`. |

### Instant

A typed instant (point in time) value. Returned by `instant()`.

Methods

| Name | Type | Description |
| --- | --- | --- |
| `getEpochSecond()` | number | Seconds since the Unix epoch. |
| `getNano()` | number | Nanoseconds adjustment within the current second. |
| `toEpochMilli()` | number | Milliseconds since the Unix epoch. |

### Reference

A typed node reference value. Returned by `reference()`.

Methods

| Name | Type | Description |
| --- | --- | --- |
| `getNodeId()` | string | The referenced node ID. |
| `toString()` | string | String form of the node ID. |

### LocalDateTime

A typed local date-time value (no time-zone). Returned by `localDateTime()`.

Methods

| Name | Type | Description |
| --- | --- | --- |
| `getYear()` | number | The year. |
| `getMonthValue()` | number | Month as a number (1–12). |
| `getMonth()` | string | Month as a string constant (e.g. `'JANUARY'`). |
| `getDayOfMonth()` | number | Day of the month (1–31). |
| `getDayOfWeek()` | string | Day of the week as a string constant (e.g. `'MONDAY'`). |
| `getHour()` | number | Hour of day (0–23). |
| `getMinute()` | number | Minute of hour (0–59). |
| `getSecond()` | number | Second of minute (0–59). |
| `getNano()` | number | Nanosecond of second. |

### LocalDate

A typed local date value (no time, no time-zone). Returned by `localDate()`.

Methods

| Name | Type | Description |
| --- | --- | --- |
| `getYear()` | number | The year. |
| `getMonthValue()` | number | Month as a number (1–12). |
| `getMonth()` | string | Month as a string constant (e.g. `'JANUARY'`). |
| `getDayOfMonth()` | number | Day of the month (1–31). |
| `getDayOfYear()` | number | Day of the year (1–366). |
| `getDayOfWeek()` | string | Day of the week as a string constant (e.g. `'MONDAY'`). |
| `isLeapYear()` | boolean | Whether the year is a leap year. |

### LocalTime

A typed local time value (no date, no time-zone). Returned by `localTime()`.

Methods

| Name | Type | Description |
| --- | --- | --- |
| `getHour()` | number | Hour of day (0–23). |
| `getMinute()` | number | Minute of hour (0–59). |
| `getSecond()` | number | Second of minute (0–59). |
| `getNano()` | number | Nanosecond of second. |

### BinaryAttachment

A typed binary attachment value wrapping a name reference and a stream. Returned by `binary()`.

Methods

| Name | Type | Description |
| --- | --- | --- |
| `getReference()` | object | A `BinaryReference` — call `.toString()` on it to get the binary name string. |
| `getByteSource()` | [ByteSource](docs/code/stable/fundamentals/types.md#byte-source) | The underlying binary stream. |
