<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/radiobutton generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/radiobutton.md

# RadioButton - form item

An input type for selecting *one* of the available options defined in the `config` element.

## Appearance

The interface is a standard radio buttons group, with one button per option. Only one button can be selected at a time.

Figure 1. Example with three options, where one is selected

## Usage

```yaml
- type: "RadioButton"
  name: "my_radiobutton"
  label: "My RadioButton"
  occurrences:
    min: 1
    max: 1  (1)
  options:  (2)
    - value: "one"
      label:
        text: "Option One"
        i18n: "option_one.label"
    - value: "two"
      label:
        text: "Option Two"
        i18n: "option_two.label"
  default: "one"  (3)
```

| ****1** | **occurrences** only make supports minimum=1 or 0 - maximum will always be 1. |
| --- | --- |
| ****2** | **options** define the available choices. The `value` is stored when the option is selected. Multiple options are allowed and ordered. Option labels support [localization](docs/cms/stable/schemas/i18n.md) via the `text`/`i18n` object pattern. |
| ****3** | **default** is optional, and may be equal to one of the option values. |

## Output

**Value type:** `String` — not included in `_alltext`

The stored value is the `value` attribute of the selected option. Only one value can be selected.

```JSON
{
  "my_radiobutton": "one"
}
```

> **Note:** The stored value corresponds to the `value` attribute, not the `label` which is for display purposes only.
