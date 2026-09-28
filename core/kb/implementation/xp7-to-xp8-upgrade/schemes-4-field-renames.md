---
id: manual-schemes-4-field-renames
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

## 4. Field renames

XML elements and attributes become camelCase YAML keys:

| XP 7 (XML)                 | XP 8 (YAML)                                                           |
|----------------------------|-----------------------------------------------------------------------|
| `<display-name>`           | `title:` (most descriptors — see below for exceptions)                |
| `<description>`            | `description:`                                                        |
| `<help-text>`              | `help-text:` (YAML descriptors keep the hyphen — see note)             |
| `<super-type>`             | `superType:`                                                          |
| `<aspect-ratio>`           | `aspectRatio:`                                                        |
| `<allowContentType>`       | `allowContentType:` (always emitted as an array, even with one entry) |
| `<list-title-expression>`  | `displayNameListExpression:` (and moved out of `<config>` — see §6.4) |
| `<displayNamePlaceholder>` | `displayNamePlaceholder:` (moved out of `<config>` — see §6.4)        |
| `<displayNameExpression>`  | `displayNameExpression:` (moved out of `<config>` — see §6.4)         |

> **`help-text`, not `helpText`.** In **YAML descriptors** the key is hyphenated: every example under
> `docs/cms/stable/schemas/` (`form-items.md`, `option-set.md`, `i18n.md`) uses `help-text:`.
> `helpText` appears only in the **JS/TS runtime APIs** (`lib-content`, `lib-schema`,
> `fundamentals/types.md`) — a different surface. An earlier version of this table mapped
> `<help-text>` to `helpText:`; that is wrong for descriptors. Corrected 2026-08-25 (docs-based;
> a `help-text:` form was accepted by the XP 8.0.4 parser, but the rendered label was not
> visually confirmed — Content Studio was unavailable).

### `displayName` → `title` rename, with exceptions

For most descriptors, the top-level `<display-name>` is renamed to `title:`. **If the XML had no `<display-name>`, add one with the file's
base name** (e.g. `title: "movie"` for a content type whose file is `movie.yaml`).

**Exceptions** — these descriptors do NOT get a `title` field at the top level (and any `displayName`/`<display-name>` present is preserved
as-is):

- `enonic.yaml`
- `cms/cms.yaml`
- `cms/site.yaml`
- `idprovider/idprovider.yaml`
- `cms/style/style.yaml` (per-style `displayName:` is preserved as-is)
- `tasks/<name>/<name>.yaml`
- `webapp/webapp.yaml`
