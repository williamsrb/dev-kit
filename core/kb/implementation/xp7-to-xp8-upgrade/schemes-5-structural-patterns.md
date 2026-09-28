---
id: manual-schemes-5-structural-patterns
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

## 5. Structural patterns

### Forms

`<form/>` (empty self-closing) becomes `form: []`.

```xml

<form/>
```

↓

```yaml
form: [ ]
```

`<form>` with children becomes a list of input objects:

```xml

<form>
  <input type="TextLine" name="heading">
    <label>Override heading</label>
  </input>
</form>
```

↓

```yaml
form:
  - type: "TextLine"
    name: "heading"
    label: "Override heading"
    occurrences:
      min: 0
      max: 1
```

The `name` and `type` attributes become keys on the same object. `<label>` becomes `label:`. Note that `occurrences` is always emitted
explicitly — defaults are written out (`min: 0, max: 1`) rather than relying on implicit XP defaults.

### Occurrences

```xml

<occurrences minimum="0" maximum="1"/>
```

↓

```yaml
occurrences:
  min: 0
  max: 1
```

### `<config>` flattening

The `<config>` wrapper is removed; its children are flattened to keys on the input itself:

```xml

<input type="TextLine" name="trailer">
  <label>Youtube Trailer</label>
  <config>
    <regexp>^http(?:s?)://.*$</regexp>
  </config>
</input>
```

↓

```yaml
- type: "TextLine"
  name: "trailer"
  label: "Youtube Trailer"
  regexp: "^http(?:s?)://.*$"
```

`<config>` children that move to the input level include `regexp`, `exclude`, `include`, `allowContentType`, and ComboBox `<option>`
entries.

### `<item-set>`

The `<item-set>` element becomes an input with `type: "ItemSet"` and an `items:` array:

```xml

<item-set name="cast">
  <label>Cast</label>
  <occurrences minimum="0" maximum="0"/>
  <items>
    <input type="ContentSelector" name="actor">...</input>
  </items>
</item-set>
```

↓

```yaml
- type: "ItemSet"
  name: "cast"
  label: "Cast"
  occurrences:
    min: 0
    max: 0
  items:
    - type: "ContentSelector"
      name: "actor"
      ...
```

### Regions

```xml

<regions>
  <region name="left"/>
  <region name="right"/>
</regions>
```

↓

```yaml
regions:
  - "left"
  - "right"
```

**This string form is correct — verified at runtime; the official XP 8 doc example is wrong.**
`docs/cms/stable/pages/page.md` and `pages/parts.md` both show `regions:` as a list of objects
(`- name: "main"`). On XP 8.0.4 that object form parses into a region whose **name is empty**, and
the failure surfaces far from the descriptor — the app deploys fine, the page renders, but the first
`portal.getContent()` inside a response processor throws:

```
IllegalArgumentException: key can not be empty
  at ...ScriptObjectMirror.checkKey
  at ...RegionMapper.serialize(RegionMapper.java:28)
  at ...PageMapper.serializeRegions(PageMapper.java:91)
```

Switching the descriptor to the string form fixes it with no other change. Measured on cookiebot-app
+ a scratch host app, 2026-08-25. If you see `key can not be empty` from `RegionMapper`, check the
page/layout descriptor's `regions:` shape before suspecting your page data.

Regions become a flat array of strings (just the names).

### ComboBox / RadioButton options

Options inside `<config>` become an `options:` array on the input:

```xml

<input type="ComboBox" name="sorting">
  <config>
    <option value="displayName ASC">Ascending</option>
    <option value="displayName DESC">Descending</option>
  </config>
  <default>displayName ASC</default>
</input>
```

↓

```yaml
- type: "ComboBox"
  name: "sorting"
  options:
    - value: "displayName ASC"
      label: "Ascending"
    - value: "displayName DESC"
      label: "Descending"
  default: "displayName ASC"
```
