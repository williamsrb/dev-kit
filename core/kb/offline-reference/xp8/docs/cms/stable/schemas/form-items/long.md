<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/long generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/long.md

# Long - form item

A simple input for storing integer numbers.

## Appearance

Figure 1. Single occurence with validation error

Figure 2. Multiple occurrences

## Usage

```yaml
- type: "Long"
  name: "my_long"
  label: "My Long"
  default: 42  (1)

- type: "Long"
  name: "degrees"
  label: "Degrees"
  min: 0  (2)
  max: 360  (3)
```

| ****1** | **default** can be any Integer number |
| --- | --- |
| ****2** | **min** optionally specifies the minimum allowed value |
| ****3** | **max** optionally specifies the maximum allowed value |

## Output

**Value type:** `Long` — not included in `_alltext`

```JSON
{
  "my_long": 42
}
```

Multiple occurrences

```JSON
{
  "my_long": [
    42,
    99
  ]
}
```
