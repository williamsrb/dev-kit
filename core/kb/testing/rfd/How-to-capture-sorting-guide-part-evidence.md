# How to capture sorting-guide part evidence

**Scope:** `rfd`
**Applies to:** review (`https://review.rfd.k8s.example.com`), XP 7, Content Studio 5.x, project `default`
**Related:** [How to create persistent part evidence content on review](./How-to-create-persistent-part-evidence-content-on-review.md), `_shared/How-to-capture-a-gitlab-commit-diff-as-evidence.md`

## Prerequisites

- Spawned `playwright-<TASK-ID>` with `~/.agents/.auth/rfd-review.json`.
- `set_storage_state` only reads files under the MCP allowed roots (`~/.agents/.playwright-mcp/<TASK-ID>/`, the repo). `install -m 600` a copy there; delete it after the run. It also clears every other cookie, so switch states per realm (CS ↔ GitLab) and back.
- `kubectl` context with `enonic-review` access. `kubectl logs rfd-0 -c xp-app -n enonic-review` carries app `log.info` lines (no `server.log` exec needed).

## Procedure

1. Ids: `fetch('/admin/rest-v2/cs/cms/default/content/content/bypath?path=/rfd/sorteringsguide')` from any CS page. `/rfd` = `134b7a9e-a8cc-4dbe-875b-4e73d0ada6d8`, sorteringsguide = `dd41a653-21b1-4c03-a7b0-e77b88ad091e` (own page, no template).
2. Third-party script states: register `page.context().route('**://sortere.no/**', …)` **before** `goto`. Abort = error state. Hang = `r => setTimeout(() => r.continue(), 20000)` on `**://sortere.no/sokeminiprivat/**`, `goto(url, { waitUntil: 'commit' })`, shoot at 12 s, then wait for `#sortere-fallback[hidden]` + `#mini-sortere-private-search input`.
3. Normal state: poll `#sortere-fallback.hidden` for 13 s (past the 10 s timer). One `false` sample = fail.
4. Clip: scroll to top, `page.screenshot({ clip })` from `.sorting-guide` bounding box ±20 px. Element screenshots after scroll get covered by the sticky header.
5. CS editor: open `…/contentstudio/main/default/edit/<id>` by **path**, not `#/default/edit/<id>` (hash nav from browse does nothing). Part is in frame `/admin/site/edit/default/draft/<id>`; click `[data-portal-component-type="part"]:has(#sortere-fallback)` once (a second click deselects). Field: `input[name="fallback_message-0"]` in `.context-window`; Apply, then toolbar Save.
6. Draft preview: `/admin/site/preview/default/draft/rfd/<name>` in a new page of the same context, so the route applies.
7. Site config receiver: edit `/rfd`, cog on the RFD app row, `input[name="sortingAlertReceiver-0"]`, Apply. Apply already saves (Save stays disabled). Verify via `content?id=` REST.
8. Restore: `POST …/content/content/revert` `{contentKey, versionId}` after checking `getVersions` shows no newer foreign version.
9. Alert jars: patched jars (`patch_jar.py`) run `checkSortere` every minute against a 404 URL. Sequence down → reinstall down → up → down → original. Expected log: `check failed` (min 1), `alert sent` (min 2), silence, `recovered (down since <first>)`, then a new `alert sent`.

## Pitfalls

- Script `load` does not reach a `window` capture listener (spec). The fallback then shows on every normal load. Shipped bug in 1.0.2966, fixed in 1.0.2967 (`document` listeners).
- CS edit mode never loads Sortere: the editor always shows the fallback. Not a fail.
- Review mail wrapper prefixes `[TEST]` and adds `Original Receivers`; `emailSettings.overrideReceiver` on `/rfd` was already the tester's mailbox in the published version.
- OCR with Norwegian tokens needs `--lang nor+eng`; plain `eng` drops ø/å and fails the match.
- A repeat failure logs nothing; dedupe is proved by silence plus the later `recovered (down since <first>)` line.
- Site config shot (alert fields): CS edit of `/rfd` (`134b7a9e-a8cc-4dbe-875b-4e73d0ada6d8`, project `default`), hover
  `.application-configurator .selected-option` (RFD row) → `a.edit`, screenshot
  `.application-configurator-dialog .field-set-view:has-text("Sorteringssøk alarm")`, then **Cancel**. Cancel creates
  no version (checked with `getVersions`). This proves the recipient/subject override for AC-6; plan it, it was missed once.
