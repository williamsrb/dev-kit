---
id: xp7-to-xp8-changes-apis
when_skills: [upgrade-xp-app, run-plan]
read: section
prose: caveman-lite
---

### APIs

> Also handled by `xp8migrator`.

`src/main/resources/apis/<name>/<name>.xml` → `<name>.yaml`.

```yaml
kind: "API"
title: "Content API"
allow:
  - "role:system.authenticated"
mount: true
```

`kind: "API"` is mandatory. Note `title:` is a **plain string** for APIs (not the object form admin tools use).

If the app uses `services/` and you want to migrate to the new API model, move each service to `apis/<name>/`, convert the descriptor to
YAML, and update callers from `serviceUrl({ service })` to `apiUrl({ api })`. Services still work in XP 8 — migration is recommended but not
required for the upgrade itself.
