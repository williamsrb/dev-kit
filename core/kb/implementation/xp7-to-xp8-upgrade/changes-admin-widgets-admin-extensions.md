---
id: xp7-to-xp8-changes-admin-widgets-admin-extensions
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

### Admin widgets → admin extensions

`admin:widget` is renamed to `admin:extension` in XP 8. Update any reference to `admin:widget` (e.g. in the `apis:` list of an admin tool)
to `admin:extension`. The on-disk descriptor file location may also change — consult `develop-xp7-backend` and the upstream XP 8 docs for current
widget/extension layout.
