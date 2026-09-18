<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-items/contenttypefilter generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-items/contenttypefilter.md

# ContentTypeFilter - form item

Select one or more of the available content types.

## Appearance

## Usage

```yaml
- type: "ContentTypeFilter"
  name: "my_cty_filter"
  label: "My CTYFilter"
  occurrences:
    min: 0
    max: 0
  context: true  (1)
```

| ****1** | **context** `true` limits the list of content types to the applications configured for the current site. Default is `false`. |
| --- | --- |

## Output

**Value type:** `String` — not included in `_alltext`

The stored value is the fully qualified content type name.

```JSON
{
  "my_cty_filter": "com.example.myapp:article"
}
```

Multiple selections

```JSON
{
  "my_cty_filter": [
    "com.example.myapp:article",
    "base:folder"
  ]
}
```
