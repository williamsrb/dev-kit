---
id: manual-schemes-6-special-cases
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

## 6. Special cases

### 6.1 `application.xml`

The original `<description>` is preserved verbatim. Three fields are imported from `gradle.properties`:

- `title:` ← `appDisplayName`
- `vendorName:` ← `vendorName`
- `vendorUrl:` ← `vendorUrl`

```yaml
kind: "Application"
title: "Headless Movie DB"           # from gradle.properties appDisplayName
description: "Sample application demonstrating XP's headless API"
vendorName: "Enonic"                 # from gradle.properties vendorName
vendorUrl: "https://enonic.com"      # from gradle.properties vendorUrl
```

`enonic.yaml` does NOT receive a `title` derived from the XML's `<display-name>` — instead, the `title:` always comes from
`appDisplayName` in `gradle.properties`.

### 6.2 `site.xml` is split between `cms/site.yaml` and `cms/cms.yaml`

The single `site/site.xml` becomes two YAML files:

- **`cms/site.yaml`** receives only the `<mappings>`:

  ```xml
  <mappings>
    <mapping controller="/controllers/info.js" order="50">
      <match>type:'portal:site'</match>
    </mapping>
  </mappings>
  ```
  ↓
  ```yaml
  kind: "Site"
  mappings:
    - controller: "/controllers/info.js"
      order: 50
      match: "type:'portal:site'"
  ```

  `<mapping controller=... order=...>` and `<match>` collapse into a single object. Order is parsed as an integer.

- **`cms/cms.yaml`** receives the `<x-data>` references (renamed to `mixins`) and the top-level `<form>`:

  ```xml
  <site>
    <x-data name="SoMe" allowContentTypes=".*:person|.*:movie"/>
    <x-data name="spotlight" allowContentTypes="media:image"/>
    <form/>
  </site>
  ```
  ↓
  ```yaml
  kind: "CMS"
  mixins:
    - name: "com.enonic.app.hmdb:SoMe"     # qualified with applicationKey
      allowContentTypes: ".*:person|.*:movie"
      optional: false
    - name: "com.enonic.app.hmdb:spotlight"
      allowContentTypes: "media:image"
      optional: false
  form: []
  ```

  Notes:
    - The `<x-data name="X">` reference is qualified to `<applicationKey>:X`.
    - `optional:` is added with default `false` when the XML didn't specify it.
    - The XML attribute `allowContentTypes` (plural) is preserved as-is (it's a regex string here, not a list).

### 6.3 `site/styles.xml`

```xml

<styles>
  <image name="editor-image-widescreen">
    <display-name i18n="imageStyles.widescreen">Widescreen (16:9)</display-name>
    <aspect-ratio>16:9</aspect-ratio>
  </image>
  <image name="editor-image-portrait">
    <display-name i18n="imageStyles.portrait">Portrait</display-name>
    <aspect-ratio>1:1</aspect-ratio>
    <filter>rounded(1000)</filter>
  </image>
</styles>
```

↓ `cms/style/style.yaml`:

```yaml
kind: "Style"
styles:
  - name: "editor-image-widescreen"
    type: "Image"
    label:
      text: "Widescreen (16:9)"
      i18n: "imageStyles.widescreen"
    aspectRatio: "16:9"
  - name: "editor-image-portrait"
    type: "Image"
    label:
      text: "Portrait"
      i18n: "imageStyles.portrait"
    aspectRatio: "1:1"
    filter: "rounded(1000)"
```

Notes on the migrator output (verified against `app-superhero-blog`):

- The XP 8 path is **`cms/style/style.yaml`** (singular folder + filename), not `cms/styles/image.yaml`. Older docs/examples (including some
  hand-crafted XP 8 apps like `tutorial-intro`) use the plural `cms/styles/image.yaml` shape — those are an older form. The migrator's
  current output is the unified `cms/style/style.yaml`.
- The repeated `<image>` elements collapse into a single `styles:` array with each entry carrying a `type:` discriminator (`"Image"`,
  etc.) — this lets the unified file hold multiple style kinds, not just images.
- `<display-name i18n="...">...</display-name>` becomes a `label: { text, i18n }` object (not a flat `displayName:` string the way other
  Style-related fields are kept). If the XML omitted `i18n=`, only `text:` is present.
- Other fields (`<aspect-ratio>`, `<filter>`, `editor.css`, etc.) are preserved as camelCase keys at the entry level.
- The migrator emits `editor.css: "Please migrate your styles from \"styles/styles.css\" manually"` as a placeholder — the actual CSS isn't
  lifted automatically.

### 6.4 Content type extra fields

For files in `cms/content-types/<name>/<name>.yaml`, three properties are moved out of `<config>` to the top level and one is renamed:

- `displayNamePlaceholder` — top level (was inside `<config>`)
- `displayNameExpression` — top level (was inside `<config>`)
- `listTitleExpression` — top level **and renamed to** `displayNameListExpression`

```xml

<content-type>
  <display-name>Article</display-name>
  <super-type>base:structured</super-type>
  <config>
    <displayNamePlaceholder>Type a title</displayNamePlaceholder>
    <listTitleExpression>title</listTitleExpression>
  </config>
</content-type>
```

↓

```yaml
kind: "ContentType"
title: "Article"
superType: "base:structured"
displayNamePlaceholder: "Type a title"
displayNameListExpression: "title"
```

### 6.5 OptionSet field renames

For any descriptor that contains an input of type `"OptionSet"`, two fields are renamed inside its options:

- `selected:` → `selection:`
- `defaultOption:` → `selected:`

(Yes, the rename chain shifts both fields one position. Apply in this order.)
