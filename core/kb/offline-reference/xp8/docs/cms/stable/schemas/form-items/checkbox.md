<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/checkbox generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/checkbox.md

# CheckBox - form item

A checkbox field has a value if it is checked, or no value if it is not checked. Therefore, the only values for occurrences that makes sense is a minimum of zero and a maximum of one, which is default and may be skipped.

## Appearance

The below screenshot shows four variants of how a checkbox can be presented, based on use of alignment.

## Usage

Sample definition with a default checked, right aligned checkbox.

```yaml
- type: "CheckBox"
  name: "my_checkbox"
  label: "My Checkbox"
  default: "checked"  (1)
  alignment: "right"  (2)
```

| ****1** | **default** - Use `checked` to check it, default is unchecked. |
| --- | --- |
| ****2** | **alignment** defines placement of checkbox relative to label text. Supported values are: "left", "right", "top", "bottom", default is "left". |

## Output

**Value type:** `Boolean` — not included in `_alltext`

Checked

```JSON
{
  "my_checkbox": true
}
```

> **Note:** When the checkbox is unchecked, the property is omitted from the output entirely.
