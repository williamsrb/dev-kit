---
id: manual-schemes-3-kind-field
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

## 3. `kind:` field

Every descriptor must declare a `kind:` at the top. The value is determined by the file's location relative to `src/main/resources/`:

| Path                                    | `kind:`            |
|-----------------------------------------|--------------------|
| `enonic.yaml`                           | `"Application"`    |
| `idprovider/idprovider.yaml`            | `"IdProvider"`     |
| `apis/<name>/<name>.yaml`               | `"API"`            |
| `services/<name>/<name>.yaml`           | `"Service"`        |
| `webapp/webapp.yaml`                    | `"WebApp"`         |
| `admin/tools/<name>/<name>.yaml`        | `"AdminTool"`      |
| `admin/extensions/<name>/<name>.yaml`   | `"AdminExtension"` |
| `tasks/<name>/<name>.yaml`              | `"Task"`           |
| `cms/cms.yaml`                          | `"CMS"`            |
| `cms/site.yaml`                         | `"Site"`           |
| `cms/style/style.yaml`                  | `"Style"`          |
| `cms/form-fragments/<name>/<name>.yaml` | `"FormFragment"`   |
| `cms/content-types/<name>/<name>.yaml`  | `"ContentType"`    |
| `cms/mixins/<name>/<name>.yaml`         | `"Mixin"`          |
| `cms/macros/<name>/<name>.yaml`         | `"Macro"`          |
| `cms/layouts/<name>/<name>.yaml`        | `"Layout"`         |
| `cms/pages/<name>/<name>.yaml`          | `"Page"`           |
| `cms/parts/<name>/<name>.yaml`          | `"Part"`           |

`kind:` is mandatory — missing it fails deployment with `Invalid kind "null". Expected "<expected>"`.
