---
id: how-to-port-xp8-admin-tool-app-to-xp7-13
when_skills: [run-plan]
read: section
prose: caveman-lite
---

# How to port an XP 8 admin-tool app down to XP 7.13.x

Reverse of the usual XP7→XP8 upgrade. Confirmed on `logviewer` → `7.13.3` / image tag `7.13.3-node20`.

## Scope

Small admin tools: Mustache/vanilla assets, Java `ScriptBean`, HTTP JSON endpoints. No React4XP, no CMS site tree.

## Procedure

1. **Gradle:** drop `com.enonic.xp.settings` 4.x / `xplibs` / `libs.versions.toml`. Use plugin `com.enonic.xp.app` **3.4.0**, `xpVersion = 7.13.3`, Java **11** `sourceCompatibility`, Gradle wrapper **7.6.x**, explicit `com.enonic.xp:lib-*` + `core-api` / `portal-api`.
2. **Descriptors:** `enonic.yaml` → `application.xml`; `enonic.svg` → `application.svg`; admin tool YAML → `admin/tools/<name>/<name>.xml` (`<tool>`, `<display-name>`, `<allow><principal>…`); Universal API `apis/<name>/` → `services/<name>/` + `<service>` XML (same principals). Do not keep `apis:` mounts.
3. **URLs:** `portal.apiUrl` / `lib-asset` → `portal.serviceUrl({service})` + `portal.assetUrl`. Keep Mustache key names (`apiUrl`, `cssUrl`, `jsUrl`) if the client only reads `data-api`.
4. **Controllers:** XP 7 resolves **lowercase** `exports.get` / `exports.post`. Uppercase `exports.GET` (accepted on some XP 8 setups) returns **405 Method Not Allowed** on 7.13.
5. **lib-mustache:** `3.0.0` declares Java **25** and fails resolve on a Java 11 consumer. Use **`2.1.1`** on 7.13.3.
6. **Docker/CI:** `leanon/enonic-xp:7.13.3-node20` and `leanon/enonic-ci:7.13.3-node20` (Node **20.13.1**). XP 7 `xp.suPassword` is plaintext (`password`), not sha512.
7. **Cold build:** image sets `JAVA_HOME=/opt/java/openjdk` but does **not** put it on `PATH`. Prefix: `export PATH=$JAVA_HOME/bin:$PATH && ./gradlew …`. Prefer `docker exec` without `-it` for non-interactive make targets.

## Smoke (admin session — frontend + backend together)

- Login POST JSON to **`/admin/tool/_/idprovider/system`** (idprovider **root**), not `/…/login`. Body: `{"action":"login","user":"su","password":"password"}`.
- Tool HTML `data-api` must contain `/_/service/…`, not `/api/`.
- Assets via `/_/asset/…` return 200.
- Restricted roles: service returns **403** JSON for download / other-day files (not only UI hide).

## Pitfalls

- Stale `build/libs/*.jar` from an earlier XP 8 build can sit beside the new `appName.jar` — `clean build` before inspecting the jar.
- Empty client `APP_REPO` on first `make up` fails repo wget; XP still boots with an empty repo and `su` still works via `xp.suPassword`.
- Do not raise `xpVersion` to 7.15 just to unlock `lib-asset` when the plan floor is 7.13.3.
