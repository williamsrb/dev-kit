<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/field-set generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/field-set.md

# FieldSet - form item

Visually group other form items under a common label

## Appearance

FieldSet as seen in Content Studio.

## Usage

Sample field-set definition containing a single input-type

```yaml
- type: "FieldSet"  (1)
  label:
    text: "Metadata"
    i18n: "metadata.label"
  items:  (2)
    - type: "Tag"
      name: "tags"
      label: "Tags for tag cloud"
      occurrences:
        min: 0
        max: 5
```

| ****1** | **FieldSet** does not need a name since it is only visual, and does not affect the data model |
| --- | --- |
| ****2** | **items** is a container for form items that should be listed within the FieldSet. |

## Output

None - FieldSets do not produce any output, and are purely decorative. Form items contained within the FieldSet will produce output as normal and will not affect the data structure in any way.
