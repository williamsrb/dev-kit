<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/instant generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/instant.md

# Instant - form item

Dates with time and timezone. An instant represents a specific point in time. Use [DateTime](docs/cms/stable/schemas/form-items/datetime.md) for dates with time but without timezone.

## Appearance

Calendar, time and timezone selector allows easy editing, similar to [DateTime](docs/cms/stable/schemas/form-items/datetime.md)

## Usage

```yaml
- type: "Instant"
  name: "my_instant"
  label: "My Instant"
  default: "2025-06-15T12:00:00"  (1)
```

| ****1** | **default** value to be used. The format for the default value can be: |
| --- | --- |

- Combined date and time in ISO 8601 format with timezone: `yyyy-MM-ddThh:mm±hh:mm` (e.g. "2016-12-31T23:59+01:00")

- Relative datetime expression (e.g. "+1year -12hours")

Note that the ISO8601 format consists of concatenating a complete date expression, the letter `T` as a delimiter, and a valid time expression.

The timezone offset is a plus or minus sign, followed by an hour offset, followed by a colon, followed by a minute offset. A timezone offset of zero can also be represented as 'Z', meaning UTC or Zulu time. It is equivalent to offset `+00:00`.

A relative date expression is a sequence of one or more datetime offsets. An offset consists of: a plus or minus sign, followed by an integer, followed by a date/time unit string (e.g. "+3 days")

| Singular | Plural | initial letter |
| --- | --- | --- |
| "year" | "years" | "y" |
| "month" | "months" | "M" |
| "week" | "weeks" | "w" |
| "day" | "days" | "d" |
| "hour" | "hours" | "h" |
| "minute" | "minutes" | "m" |

An offset can also be the string `now`, which means current time.

If `default` value is set for an input, the UI Date/Time picker will display btn:[Set default] button for resetting to the default value with one click.

Examples:

```yaml
- type: "Instant"
  name: "published_at"
  label: "Published at"
  default: "now"

- type: "Instant"
  name: "expires_at"
  label: "Expires at"
  default: "+1year"
```

## Output

**Value type:** `Instant` — not included in `_alltext`

Z (UTC time) is same as +00:00

```JSON
{
  "my_instant": "2025-06-15T12:00:00Z"
}
```

Multiple occurrences

```JSON
{
  "my_instant": [
    "2025-06-15T12:00:00+01:00",
    "2025-07-01T09:30:00+01:00"
  ]
}
```
