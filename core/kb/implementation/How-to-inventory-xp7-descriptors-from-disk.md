---
id: how-to-inventory-xp7-descriptors-from-disk
when_skills: [run-plan, plan-implementation, develop-xp7-backend]
inputs: [an XP7 checkout with src/main/resources]
outputs: [static inventory covering FR-10 kinds]
stop_if: [starting the XP runtime for static inventory]
read: whole
prose: caveman-lite
---

# Inventory XP7 descriptors from disk

Walk each `**/src/main/resources/` and parse XML with stdlib
`xml.etree.ElementTree`. Do not start the XP runtime.

## Coverage kinds (v1)

Under `site/`: `site.xml`, `content-types/`, `mixins/`, `x-data/`, `pages/`,
`layouts/`, `parts/`, `macros/`.

**Sibling** folders next to `site/`, not under it: `services/`, `tasks/`.

Out of coverage in v1: `admin/`, `site/filters/`, `site/processors/`,
`site/error/`.

Offline layout: `~/.agents/kb/offline-reference/xp7/development/code.md`.

## Procedure

1. Find every `src/main/resources` directory.
2. Read `site/site.xml` as kind `site`.
3. For each kind folder, take `name/name.xml` (XP convention) or any `*.xml`
   in that folder.
4. App key from the nearest `gradle.properties` (`appName`, or `group` +
   `projectName`). Stop walking at the source root.
5. Paths in the inventory are source-relative. `check` coverage uses those
   paths against `map/*.json` or `hygiene/dead-code.md`.

## Pitfalls

- Treating `services/` and `tasks/` as `site/services` misses every XP7 app
  that follows the documented layout (`as` included).
- Copying descriptor XML from a live project into the kit. Tests use
  `tests/fixtures/enonic-mini/` with one file per kind.
