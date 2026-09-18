<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-value generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-value.md

# Value API

Helper functions for various value types.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-value:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import valueLib from '/lib/xp/value';
```

## Functions

### binary

Creates a BinaryAttachment value.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| name | string | The binary name |
| stream |  | The binary stream |

Returns

**object** : BinaryAttachment

### geoPoint

Creates a GeoPoint value.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| lat | number | Latitude |
| lon | number | Longitude |

Returns

**object** : GeoPoint

### geoPointString

Creates a GeoPoint value as a string.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| value | string | Comma-separated latitude and longitude |

Returns

**object** : GeoPoint

### instant

Creates an Instant value.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| value | string \| Date | An ISO-8601-formatted instant (f.ex. `2011-12-03T10:15:30Z`) or a Date object |

Returns

**object** : Instant

### localDate

Creates a LocalDate value.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| value | string \| Date | A ISO local date-time string (e.g '2011-12-03') or a Date object |

Returns

**object** : LocalDate

### localDateTime

Creates a LocalDateTime value.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| value | string \| Date | A local date-time string (e.g '2007-12-03T10:15:30') or a Date object |

Returns

**object** : LocalDateTime

### localTime

Creates a LocalTime value.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| value | string \| Date | A ISO local date-time string (e.g '10:15:30') or a Date object |

Returns

**object** : LocalTime

### reference

Creates a Reference value.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| value | string | A nodeId as string (e.g '1234-5678-91011') |

Returns

**object** : Reference
