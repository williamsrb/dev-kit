---
id: manual-schemes-migration
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

# Manual schemes migration (XP 7 → XP 8)

Open only the matching step. Do not read every step unless the upgrade needs it.

| Step | File |
|------|------|
| 1. File extensions | `schemes-1-file-extensions.md` |
| 2. Directory tree: `site/` → `cms/` | `schemes-2-directory-tree-site-cms.md` |
| 3. `kind:` field | `schemes-3-kind-field.md` |
| 4. Field renames | `schemes-4-field-renames.md` |
| 5. Structural patterns | `schemes-5-structural-patterns.md` |
| 6. Special cases | `schemes-6-special-cases.md` |
| 7. Sibling files and cleanup | `schemes-7-sibling-files-and-cleanup.md` |

## What is NOT touched

The migrator never modifies:

- `controllers/` — all controllers, HTML templates
- `i18n/` — `.properties` files
- `import/` — content data
- `assets/` — static files
- `main.js` — app lifecycle script
- `application.svg` — app icon (stays at root). **This is a migrator gap, not a no-op.** XP 8
  resolves the app icon from `src/main/resources/enonic.svg` by filename convention
  (`xp8/docs/code/stable/tooling/starters.md:94`), exactly as XP 7 resolved `application.svg`
  (`xp7/development/code.md:100`). Neither descriptor declares it — there is no `icon:` key in
  `enonic.yaml`. The migrator leaves `application.svg` in place and never creates `enonic.svg`,
  so a migrator-only run ships an app with **no icon** and no error. Always
  `cp application.svg enonic.svg` by hand, then delete `application.svg` with the rest of the
  XP 7 originals. Same square-SVG requirement in both versions.

  Related trap: an `<icon>path/to.svg</icon>` element inside an XP 7 `application.xml` or
  admin-tool `<tool>` descriptor is **undocumented** — no hit anywhere under
  `offline-reference/xp7/`. Do not treat it as the icon XP 7 actually rendered when deciding
  what to carry over; the convention file wins. Admin tools have their own convention,
  `admin/tools/<name>/<name>.svg`, independent of the app icon.
- `build.gradle`, `gradle.properties`, `gradle/wrapper/*` — build files (handled separately, see SKILL.md)
- `tsconfig.json`, `tsup.config.ts`, etc. — TypeScript / bundler config (handled separately)
- `logback.xml` — logging config (handled separately, see
  <https://raw.githubusercontent.com/enonic/doc-xp/refs/heads/8.0/docs/release/upgrade.adoc>)
## Summary checklist

When migrating by hand, work through each file in this order:

1. Inventory all `.xml` (and `.yml`) descriptors under `src/main/resources/`.
2. For each one, determine the new path (§2) and `kind:` (§3).
3. Convert XML to YAML, applying the field renames (§4) and structural patterns (§5).
4. Apply the special cases (§6) where they apply: `application.xml`, `site.xml`, `styles.xml`, content-type field moves, OptionSet renames.
5. Copy sibling `.js` / `.html` / `.svg` files into the new location.
6. After validating the output, delete the old `site/` tree (§7).
