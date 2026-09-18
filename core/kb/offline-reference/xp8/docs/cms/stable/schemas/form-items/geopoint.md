<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/geopoint generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/geopoint.md

# GeoPoint - form item

Store Geographical coordinates for places on Earth.

## Appearance

- The first number must be between -90 and 90, where a negative number indicates a location south of equator and a positive is north of the equator.

- The second number must be between -180 and 180, where a negative number indicates a location in the western hemisphere and a positive number is a location in the eastern hemisphere.

## Usage

```yaml
- type: "GeoPoint"
  name: "my_geopoint"
  label: "My GeoPoint"
  occurrences:
    min: 0
    max: 1
  default: "51.5,-0.1"  (1)
```

| ****1** | **default** specifies a default string value for the GeoPoint, for example `51.5,-0.1`. |
| --- | --- |

## Output

**Value type:** `GeoPoint` — not included in `_alltext`

```JSON
{
  "my_geopoint": "29.97917,31.13417"
}
```

Multiple occurrences

```JSON
{
  "my_geopoint": [
    "51.5,-0.1",
    "40.7,-74.0"
  ]
}
```
