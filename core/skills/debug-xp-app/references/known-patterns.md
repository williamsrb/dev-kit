# Known Debug Patterns

Concise heuristics from past debug sessions. Max ~5 lines per entry. Prune when file exceeds ~30 entries.

---

## Serializer NPE on modify

**Symptom**: `ScriptValueTranslator.handleValue` throws NPE after `node.modify()`
**Cause**: Any null property in the returned object graph triggers it, not just the edited field. The serializer iterates the entire object.
**Fix**: Sanitize the entire returned object — strip nulls before returning from the editor function. Don't assume you know which property
is null.
**Applies to**: XP 8+ (stricter null handling than XP 7)

---

## API not found — wrong descriptor format (XP 8)

**Symptom**: Browser gets `API [com.example.app:my-api] not found` (404). JAR contains `apis/<name>/<name>.xml` and `apis/<name>/<name>.js`
correctly.
**Cause**: XP 8 uses `YmlApiDescriptorParser` — it only looks for `.yml` descriptors. XML descriptors are silently ignored, so the API is
never registered.
**Fix**: Rename `<name>.xml` → `<name>.yml` and convert to YAML format: `allow:\n  - "role:system.admin"`.
**Applies to**: XP 8+ (XP 7 uses XML). Same applies to admin tool and webapp descriptors.

---

## Silent app — no log entries at all

**Symptom**: User reports "app doesn't load" or "I can't see it in logs". Grepping `server.log` for the app name returns zero results.
**Cause**: The app JAR was never deployed to the directory XP reads from. The deploy target path doesn't match `$XP_HOME/deploy/`.
**Fix**: Verify where the build tool places the JAR vs. where XP actually reads from. Check project deploy configuration and `$XP_HOME`.
**Key insight**: Actual app errors (bad code, version mismatch) always produce log entries. Complete absence means XP never saw the JAR.

---

## Nashorn TypeError: X is not a function (ES2015+ API in server bundle)

**Symptom**: `TypeError: Object.values is not a function` (or similar ES2015+ API) at module scope in a `_chunks/*.js` file.
**Cause**: A dependency ships untranspiled ES2015+ API calls; esbuild/tsup `target: es5` only transpiles syntax, NOT APIs. Module-scope calls crash at chunk load, before any polyfill can run.
**Fix**: Rewrite with ES5 APIs at the source (e.g. `Object.keys(o).map(k=>o[k])` instead of `Object.values(o)`), or ensure a core-js polyfill loads first. Check `git log -L` — such fixes get regressed by dep-update commits.
**Applies to**: All XP versions running Nashorn server-side.

---

## Fragment preview 404 — logless, from a site mapping

**Symptom**: A `portal:fragment` won't preview in Content Studio — "No preview available", or a 404 in the panel. Nothing in `server.log`.
**Cause**: A site controller mapping (`match: "type:'portal:fragment'"`) routes the fragment to a controller path left stale by the
`site/` → `cms/` migration, e.g. `/site/pages/default/default.js` when the controller now lives at `/cms/pages/default/default.js`.
**Fix**: Correct the controller path in `cms/site.yaml`. The real reason is only in the admin-site response body (`Controller [...] not found`),
not the log — see `runtime-http-probing.md`.
**Applies to**: XP 8 apps migrated from the `site/` to the `cms/` resource layout.
