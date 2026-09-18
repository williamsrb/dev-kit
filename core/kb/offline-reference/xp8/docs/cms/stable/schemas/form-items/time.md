<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/time generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/time.md

# Time - form item

Stores time in the format hh:mm.

A time input field and selector for hours and minutes. The time is stored in 24h format, and timezone is not included.

## Appearance

## Usage

```yaml
- type: "Time"
  name: "my_time"
  label: "My Time"
  default: "13:22"  (1)
```

| ****1** | **default** date value to be used. The format for the default date value can be: |
| --- | --- |

- Time in 24h format: `hh:mm (e.g. "23:59")

- Relative time expression (e.g. "+1hour -12minutes")

A relative time expression is a sequence of one or more time offsets. An offset consists of: a plus or minus sign, followed by an integer, followed by a time unit string (e.g. "+3 minutes")

| Singular | Plural | initial letter |
| --- | --- | --- |
| "hour" | "hours" | "h" |
| "minute" | "minutes" | "m" |

An offset can also be the string `now`, which means current date and time.

If `` value is set for an input, the Time picker will display "**Set default**" button for setting the default value with one click.

## Output

**Value type:** `LocalTime` — not included in `_alltext`

```JSON
{
  "my_time": "13:22"
}
```

Multiple occurrences

```JSON
{
  "my_time": [
    "08:00",
    "13:22"
  ]
}
```
