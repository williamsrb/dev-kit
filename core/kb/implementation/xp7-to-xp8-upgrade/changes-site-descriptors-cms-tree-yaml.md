---
id: xp7-to-xp8-changes-site-descriptors-cms-tree-yaml
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

### Site descriptors → `cms/` tree (YAML)

The entire `site/` tree relocates to `cms/`, every descriptor becomes YAML with a kind-specific `kind:`, `site.xml` splits into
`cms/site.yaml` + `cms/cms.yaml`, and `x-data/` is renamed to `mixins/`. **Handled by `xp8migrator`.** See
`references/manual-schemes-migration.md` for the systematic transformations: the path/`kind:` map, field renames (including
`<display-name>` → `title:` and its exceptions), structural patterns (`<form/>` → `form: []`, `<occurrences>`, `<config>` flattening,
`<regions>`), and special cases for `application.xml`, `site.xml` split, `styles.xml`, content-type field moves, and `OptionSet` renames.

Two real-world gotchas worth flagging up front (not in the systematic reference):

- **`title:` and `description:` accept either a plain string or a `{ text, i18n }` object.** Use the object form whenever the XP 7 XML had
  an `i18n="…"` attribute on `<display-name>`/`<description>` — it's the form the migrator emits, and it preserves localization keys. Plain
  strings are fine when there's no i18n key. (Admin tools are special — see "Admin tools" above; their `title:` *must* be the object form
  regardless.)
- **Site mappings can use either `match:` or `pattern:`/`invertPattern:`** — both forms are valid in `cms/site.yaml`. The XP 7
  `<match>type:'…'</match>` becomes `match: "type:'…'"`; XP 7 `<pattern>` becomes `pattern: ".*\\/rss"` with an explicit
  `invertPattern: false/true`.

#### `cms/site.yaml` `apis:` list — gotcha

Like admin tools (see above), a site must explicitly mount any **mounted-API** library it uses — most commonly `lib-asset` (which exposes an
`asset` API). Without the declaration, `assetUrl()`/asset-resolution calls fail at runtime. The migrator does NOT infer this — the
declaration must be added by hand:

```yaml
kind: "Site"
mappings:
  - controller: "/lib/rss/rss.js"
    order: 50
    pattern: ".*\\/rss"
    invertPattern: false
apis:
  - "asset"        # required when the site uses lib-asset
```

App-key qualification follows the same rules as admin tool `apis:` lists — a bare name (`"asset"`) refers to the current app's API
namespace; a fully-qualified key (`"<other-app>:<api>"`) targets a *separately-deployed* app's API.

**Important: a lib bundled into your app is not a "separate app".** When the app `include`s a library that publishes a mounted API
(e.g. `com.enonic.lib:lib-asset` providing the `asset` API), the lib's `apis/<name>/` directory is merged into your app's JAR at
build time, and the API is mounted under **your** app's key — not the lib's. So the reference must be the bare name (`"asset"`),
**never** `"com.enonic.lib.asset:asset"` and **never** `"com.enonic.app.<your-app>:asset"` either (the fully-qualified form is
only for cross-app calls). Verify the mount by inspecting the built JAR: `unzip -l build/libs/<app-name>.jar | grep apis/` should
show `apis/asset/...` regardless of which lib contributed the descriptor.
