<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/datetime generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/datetime.md

# DateTime - form item

For dates with time - without timezone.

> **Tip:** For dates with timezone, use the [Instant](docs/cms/stable/schemas/form-items/instant.md) form item.

## Appearance

The user format is `yyyy-MM-dd hh:mm` for example, `2015-02-09 09:00`. The timezone is always included.

## Usage

```yaml
- type: "DateTime"
  name: "my_datetime"
  label: "My DateTime"
  default: "2011-09-12T12:00+01:00"  (1)
```

| ****1** | **default** date value to be used. The format for the default date value can be: |
| --- | --- |

- Combined date and time in ISO 8601 format without timezone: `yyyy-MM-ddThh:mm` (e.g. "2016-12-31T23:59")

- Relative datetime expression (e.g. "+1year -12hours")

Note that the ISO8601 format consists of concatenating a complete date expression, the letter `T` as a delimiter, and a valid time expression.

A relative date expression is a sequence of one or more datetime offsets. An offset consists of: a plus or minus sign, followed by an integer, followed by a date/time unit string (e.g. "+3 days")

| Singular | Plural | initial letter |
| --- | --- | --- |
| "year" | "years" | "y" |
| "month" | "months" | "M" |
| "week" | "weeks" | "w" |
| "day" | "days" | "d" |
| "hour" | "hours" | "h" |
| "minute" | "minutes" | "m" |

An offset can also be the string `now`, which means current date and time.

If `default` value is set for an input, the UI Date/Time picker will display **Set default** button for resetting to the default value with one click.

Examples:

```yaml
- type: "DateTime"
  name: "datetime_default"
  label: "DateTime (with default value)"
  default: "2000-01-01T12:30+01:00"

- type: "DateTime"
  name: "datetime_relative"
  label: "DateTime (relative default value)"
  default: "+1year -12hours"

- type: "DateTime"
  name: "datetime_now"
  label: "DateTime (current time as default value)"
  default: "now"
```

## Output

**Value type:** `LocalDateTime` — not included in `_alltext`

```JSON
{
  "my_datetime": "2016-12-31T23:59:00"
}
```

Multiple occurrences

```JSON
{
  "my_datetime": [
    "2016-12-31T23:59:00",
    "2017-01-15T09:30:00"
  ]
}
```
