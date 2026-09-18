<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/double generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/double.md

# Double - form item

Support high precision decimal numbers

## Appearance

## Usage

```yaml
- type: "Double"
  name: "my_double"
  label: "My Double"
  default: 3.89  (1)

- type: "Double"
  name: "angle"
  label: "Angle (rad)"
  min: 0  (2)
  max: 3.14159  (3)
```

| ****1** | **default** can be any double-precision floating-point number, with the dot character as decimal separator |
| --- | --- |
| ****2** | **min** optionally specifies the minimum allowed value |
| ****3** | **max** optionally specifies the maximum allowed value |

## Output

**Value type:** `Double` — not included in `_alltext`

```JSON
{
  "my_double": 3.89
}
```

Multiple occurrences

```JSON
{
  "my_double": [
    3.89,
    2
  ]
}
```

> **Note:** Double is also capable of storing integer values, which are valid double-precision floating-point numbers.
