---
id: xp7-to-xp8-changes-server-side-configuration-files
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

### Server-side configuration files

If the project repo contains server-config files (most commonly a `logback.xml` — remove `<withJansi>true</withJansi>` to avoid a startup
error), apply the changes documented at
<https://raw.githubusercontent.com/enonic/doc-xp/refs/heads/8.0/docs/release/upgrade.adoc>. That guide also covers data migration
(`dump`/`load`), Management API breaking changes, security (`xp.suPassword`, password hashing), and the default
`com.enonic.cms.default` repo behavior change.
