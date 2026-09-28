---
id: manual-schemes-2-directory-tree-site-cms
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

## 2. Directory tree: `site/` → `cms/`

The XP 7 `site/` tree is renamed to `cms/`, and `x-data` is renamed to `mixins`. The relocations are:

| XP 7 path                               | XP 8 path                                                   |
|-----------------------------------------|-------------------------------------------------------------|
| `site/site.xml`                         | `cms/site.yaml` (mappings only) + `cms/cms.yaml` (the rest) |
| `site/styles.xml`                       | `cms/style/style.yaml`                                      |
| `site/content-types/<name>/<name>.xml`  | `cms/content-types/<name>/<name>.yaml`                      |
| `site/pages/<name>/<name>.xml`          | `cms/pages/<name>/<name>.yaml`                              |
| `site/parts/<name>/<name>.xml`          | `cms/parts/<name>/<name>.yaml`                              |
| `site/layouts/<name>/<name>.xml`        | `cms/layouts/<name>/<name>.yaml`                            |
| `site/mixins/<name>/<name>.xml`         | `cms/mixins/<name>/<name>.yaml`                             |
| `site/macros/<name>/<name>.xml`         | `cms/macros/<name>/<name>.yaml`                             |
| `site/x-data/<name>/<name>.xml`         | `cms/mixins/<name>/<name>.yaml`                             |
| `site/form-fragments/<name>/<name>.xml` | `cms/form-fragments/<name>/<name>.yaml`                     |

Files that stay in their original location: `application.xml`, `apis/`, `services/`, `webapp/`, `admin/`, `tasks/`, `idprovider/`. They keep
their relative path; only the extension and content change.
