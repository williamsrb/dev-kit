---
id: xp7-to-xp8-changes-application-descriptor
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

### Application descriptor

`src/main/resources/application.xml` → `enonic.yaml` (handled by `xp8migrator`; XML is no longer recognized in XP 8).
`kind: "Application"` is mandatory — missing it fails deployment with `Invalid kind "null". Expected "Application"`. See
`references/manual-schemes-migration.md` §6.1 for the exact field map and
<https://raw.githubusercontent.com/enonic/doc-code/refs/heads/master/docs/upgrade.adoc> for an XP 7 → XP 8 example.

**Metadata flow.** The migrator pulls `appDisplayName` / `vendorName` / `vendorUrl` from `gradle.properties` and writes them into
`enonic.yaml` (as `title` / `vendorName` / `vendorUrl`). Two pre-migrator fixups in real XP 7 apps:

1. **Unprefixed `displayName`** in `gradle.properties` — rename to `appDisplayName` (the migrator only matches the `app`-prefixed form,
   otherwise `title:` ends up empty).
2. **Vendor info hard-coded in the `app{ }` block** of `build.gradle` — lift the literals into `gradle.properties` (or write them straight
   into `enonic.yaml` post-migration; both end states are valid).

If realized after running the migrator: fix the keys and re-run `./migrator -e overwrite`, or hand-edit `enonic.yaml`. (Don't use `-x`
on the re-run — see the "Descriptor pass" note.)
