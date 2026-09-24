---
id: how-to-use-content-studio-xp8
when_skills: [plan-task-evidence, run-plan]
read: section
prose: caveman-lite
---

# How to use Content Studio on XP 8 / CS 6

Open only the matching `###` heading. Do not read the REST fallback unless UI drag failed.

## Prerequisites

- Logged-in XP admin session
- Content Studio admin tool URL (XP 8 — note **no** `/tool/` segment):

```
<base>/admin/com.enonic.app.contentstudio/main
```

Legacy `/admin/tool/com.enonic.app.contentstudio/main` returns 404 on XP 8.

### Agent login when no browser session (XP 8 idprovider)

Anonymous `/admin` is HTTP 401. Cold automation (e.g. Playwright without cookies) can obtain a session with:

```
POST <base>/admin/_/idprovider/system
Content-Type: application/json

{"action":"login","user":"<login>","password":"<password>"}
```

Default **dev/review** credentials (Enonic stock `su`, widely known — use these unless the env documents otherwise):

```
login: su
password: password
```

or

```
login: su
password: mofser8
```

Success returns `{"authenticated":true,…}` and sets `JSESSIONID` (often also `INGRESSCOOKIE` behind ingress). Reuse those cookies for CS REST and authenticated browser navigation.

## Procedure

### Select project / layer

1. Open Content Studio. If prompted **Select project**, pick the CMS project that matches the site vhost (e.g. **English (en)** / `english`).
2. Browse URL shape: `#/<project>/browse` (e.g. `#/english/browse`).

### Create content

1. In the tree, select the **parent** (site or folder). New items are created under the current selection (`Create content in location: /…`).
2. Toolbar **New** (or `Alt+N`) → dialog with tabs **All / Suggested / Media**.
3. Type in the dialog **Search** field to filter types (e.g. `Landing`).
4. Click the type (e.g. **Landing page**). Content Studio opens the editor (often a **new browser tab**).

### Open existing content in the editor

Prefer direct navigation (avoids popup-blocker issues with toolbar **Edit**):

```
<base>/admin/com.enonic.app.contentstudio/main/<project>/edit/<content-id>
```

Example: `…/main/english/edit/54af2a2e-6240-4f32-a21c-aad9640d8227`

### Page editor + insert a Part

1. In the content editor, ensure the item is **renderable** (has a page controller or template). Collapse the content form if needed (**Collapse content form**) so the live page iframe is visible.
2. **Show Context Panel** → widget combobox (often shows **Details**) → **Toggle** → choose **Page** (“Draggable components and page controller”).
3. **Inspect** tab: set/select the page controller (e.g. app **Default**). Template **Automatic** locks editing — **Insert** stays disabled until the page is customized / uses a direct controller.
4. **Insert** tab: drag **Part** placeholder into a region (e.g. `main`), then pick the part from the dropdown (titles from YAML, e.g. Client Logo Bar).
5. Configure fields on **Inspect**; save.

**Preferred under automation — Components-tree context menu (no drag, no REST).** In the left
form's **Page** tab, the Components tree rows are `div[role=button]`, not `<button>`, so query
by role/text rather than tag. **Right-click** a component row → menu with *Select parent /
Insert / Inspect / Reset / Remove / Duplicate / Save as Fragment* → **Insert** → **Part**.
An unconfigured `Part` placeholder is appended after that component and Inspect switches to it;
type the part title into the Inspect **Search** combobox and pick the option to bind the
descriptor. Verified on CS 6 review (PROJ-353). This works even when the page reports
`page.customized: false`, and avoids both the flaky HTML5 drag and the `page/update` REST call.

ContentSelector fields in Inspect need two clicks per item: pick the row in the dropdown, then
press the dropdown's own **Apply**. The combobox does **not** clear between items — send
`Control+a` before typing the next name or the queries concatenate (`EgilSteinar`) and return
nothing.

**Remove** from the same context menu updates the tree immediately but leaves the change
**unsaved** — the toolbar `Save` becomes enabled and a REST read still returns the old
component list until you click it.

> Agent note: the live page surface is an **iframe** (`…/admin/com.enonic.app.contentstudio/site/edit/<project>/draft/<site-path>`). Accessibility snapshots do not see inside it; use CDP `iframe.contentDocument` on same-origin or drive Insert from the outer **Page** widget.

### Fallback — insert / configure Part via CS REST (when UI drag fails)

Authenticated browser `fetch` (session cookies). Verified on XP 8 / CS 6 review (PROJ-341):

```
POST /admin/rest-v2/cs/cms/<project>/content/content/page/update
Content-Type: application/json
```

Body shape (`CreatePageJson` known fields: `contentId`, `controller`, `template`, `config`, `fragment`, `regions`):

- `regions` must be an **array** (not a map): `{ name: 'main', components: […] }`
- Each component is a **typed wrapper**, e.g. `{ PartComponent: { descriptor, name?, config } }` (ids: `PartComponent`, `LayoutComponent`, `TextComponent`, `ImageComponent`, `FragmentComponent`)
- `config` is PropertyArray JSON: `{ name, type, values: [{ v }] }` — `Reference` uses `{ v: '<content-uuid>' }`
- **ItemSet** fields use `type: 'PropertySet'` with each occurrence as `{ set: [ /* nested PropertyArray entries */ ] }` (verified PROJ-343 Expandable Link List `links`)

Rename / displayName (same session): `POST …/content/content/update` with `{ contentId, contentName, displayName, data, meta: [], requireValid: false }` (`contentName` renames the path segment).

Reload `/edit/<id>` (or draft site URL) after update. Draft preview without wizard:

```
<base>/admin/com.enonic.app.contentstudio/site/edit/<project>/draft/<site-path>/<page-name>
```

The `/site/preview/…` variant renders the same draft page **without** the editor chrome or iframe, so accessibility snapshots and DOM queries reach the page directly — prefer it for draft evidence (verified PROJ-388):

```
<base>/admin/com.enonic.app.contentstudio/site/preview/<project>/draft/<site-path>/<page-name>
```

#### `page/update` pitfalls (verified on acme review, PROJ-398, 2026-08-28)

- **`CreatePageJson` accepts exactly six fields**: `contentId`, `controller`, `template`,
  `config`, `fragment`, `regions`. Sending `meta` or `requireValid` is a hard
  `500 Unrecognized field` — there is no validation escape hatch on this endpoint.
- **It revalidates the whole stored content**, so orphaned x-data blocks the save:

  ```
  500 Not allowed mixinName: com.example.app:macros
  ```

  That x-data existed in no branch of the app — it is meta left on review content by an older
  version. Any content still carrying it cannot be page-updated over REST until the x-data is
  stripped (`content/update` with `meta: []`, which mutates shared content — get sign-off first).
  Diagnose with: fetch the content and compare `meta[].name` against the app's `cms/x-data/`
  (acme has none at all today).

#### XP does not store a region that has no components

Proven by experiment on acme review, 2026-08-28 (PROJ-398): `page/update` with a
`LayoutComponent` whose region holds **one** component persists as
`regions: [{name:'main', components:[…]}]`; the identical call with `components: []` returns
**200** and reads back as `regions: []`. A region only appears in the stored page tree once it
holds at least one component — you cannot pre-materialise an empty dropzone.

So `regions: []` on a template's layout is **not a defect and not fixable as such**. If a
template's layout shows `regions: ['main']` it is because something was placed inside it.

> **Retracted:** an earlier version of this section claimed the templates *without* the
> orphaned x-data were the ones with materialised regions, and inferred that a Content Studio
> re-save fixes both. That correlation was coincidence. On acme the clean template (`article`)
> is clean **in the `base` project** that `english` inherits from — nothing stripped anything.
> Always check `originProject` and `inherit` before reading anything into per-project state.

#### Layer inheritance: any write localises the content

`cms/<project>` writes hit that project's **layer**. A `content/update` on an item whose
`inherit` is `['CONTENT','PARENT','NAME','SORT']` drops it to `['PARENT','SORT']` — the item is
now localised and stops following the parent project. It also flips `workflow.state` to
`IN_PROGRESS` and clears `publish.time`, so the change sits as an unpublished draft (the
published site keeps serving the previous version).

There is **no REST endpoint to undo this**: `resetInherit`, `resetInherited`, `reset`,
`unlocalize`, `inherit/reset` are all 404 (`localize` exists, one-way). Reverting means the
**Reset** action in the Content Studio UI. Check `originProject` / `inherit` **before** writing,
and fix shared templates in the parent project rather than the layer.

> **Do not probe mutating routes with an empty body to test whether they exist.**
> `POST /content/content/publish {}` returns **200 with a taskId** — it enqueues a real publish
> task (it failed on null ids that time, but that is luck, not a guarantee). Probe with GETs, or
> read the endpoint list from a known-good call.

List content: `POST …/content/content/query` with `{ queryExpr, contentTypeNames: ['media:image'|'portal:site'|…], from, size }` → `{ contents: [{ id }] }`. Get one: `GET …/content/content?id=<uuid>` (only `id` works — `?path=` / `?contentPath=` return 500).

**Finding content you just created (draft-only):** the `queryExpr` form does **not** return
unpublished items, so a freshly created draft looks like it failed even when `create` returned 200.
Use the shape Content Studio's own search sends (verified PROJ-388):

```json
POST …/content/content/query
{"from":0,"size":5,"contentTypeNames":[],"expand":"summary","aggregationQueries":[],"queryFilters":[],
 "query":{"boolean":{"should":[{"fulltext":{"fields":["displayName^5","_name^3","_allText"],
 "query":"vacancies","operator":"AND"}}]}}}
```

Create: `POST …/content/content/create` with `{ contentType, parent, name, displayName, data, meta: [], requireValid: false }` — `parent` is a **content path** (`/site/Insights/blog`), `displayName` is mandatory (500 `displayName cannot be null` otherwise), and re-posting an existing name returns a 500 that names the branch (`… in branch [draft] already exists`) — a useful existence check.

**Nested layout + parts in one `page/update`:** a `LayoutComponent` carries its own `regions`, so the whole page tree goes in a single call:

```json
{"contentId":"<uuid>","controller":"com.example.app:default","config":[],
 "regions":[{"name":"main","components":[
   {"LayoutComponent":{"descriptor":"<app>:article","name":"article","config":[],
     "regions":[{"name":"main","components":[{"PartComponent":{"descriptor":"<app>:list-people","config":[…]}}]}]}}]}]}
```

### Preview (draft)

- Toolbar **Preview** opens a full-tab draft render (subject to popup blocker).
- Prefer the draft site URL above or the in-editor iframe when Preview is blocked.

### Publish → live

1. Toolbar **Mark as ready** and/or **Publish** / **Publish tree** → Publishing wizard → **Publish Now**.
2. Only **master** is visible on public vhosts. After edits, status becomes **Modified** until re-published.

**REST fallback** (same auth session) when the wizard is awkward under automation:

1. `POST …/content/content/markAsReady` body `{ contentIds: ['<uuid>'] }` → 204  
2. Optional: `POST …/content/content/updateWorkflow` body `{ contentId, workflow: { state: 'READY', checks: {} } }`  
3. `POST …/content/content/publish` body `{ ids: ['<page-uuid>', '<dep-uuid>…'], excludedIds: [], excludeChildrenIds: [] }` → `{ taskId }`  
4. Poll `GET /admin/rest-v2/cs/tasks/<taskId>` until `progress.info` has `"state":"SUCCESS"`.

### Deterministic `publish.from` ordering without a schedule field

When evidence needs several items to sort a specific way on `publish.from` (e.g. proving a "3 latest" query), there is **no confirmed `schedule`/`online-from` field** on the `content/publish` REST body — passing one would be an unverified assumption. Instead rely on the *confirmed* default from `lib-content` §Schedule: `from` "defaults to the time of publishing" when omitted.

1. Create all the items first (still unpublished).
2. Publish them **oldest-intended-first**, as **separate** `markAsReady` + `publish` + poll-to-`SUCCESS` calls per item, a few seconds apart (each is that item's *first-ever* publish, so `publish.from` = that call's timestamp).
3. Do **not** batch multiple items into one `publish` call if their relative order matters — a batched call gives them (approximately) the same `publish.from` and the ordering stops being deterministic.
4. Poll each item's task to `SUCCESS` before starting the next publish — publishing item N+1 while N's task is still running risks the same near-simultaneous-timestamp problem.

## Pitfalls

- **Popup blocker:** Edit / Preview / New often open a second tab. Prefer direct `/edit/<id>` URLs. Dismiss CS’s “Pop-up Blocker is enabled…” toast when it appears. Capture draft evidence from the in-editor iframe if Preview is blocked.
- **Insert disabled:** page still on automatic template without Customize / without choosing a controller. **Customize Page** (or pick controller **Default**) unlocks Insert.
- **Part drag under automation:** HTML5 / tool drag onto the region often does not stick; use the page/update REST fallback above, then reload the editor.
- **Inspect stuck on page Template after REST insert:** Components-tree clicks alone often leave Inspect on **Template / Default**. Click the part inside the draft iframe (`[data-portal-component-type=part]`), then **Expand content form** (or Collapse→Expand) so Inspect switches to the Part form (Overline / ItemSet fields).
- **`page/update` must use typed wrappers:** body needs `controller` + `regions[].components[]` as `{ PartComponent: { descriptor, config } }` (not a raw GET `page` echo). A wrong shape can return 200 but leave `page: { customized: false }` with regions wiped → live “Something went wrong” / teapot until restored.
- **Publish after REST edit:** `markAsReady` (`contentIds`) and/or `updateWorkflow` → `READY`, then `publish` `{ ids, excludedIds, excludeChildrenIds }`. Poll `/admin/rest-v2/cs/tasks/<taskId>` for `"state":"SUCCESS"`.
- **Wrong project:** English vs Norwegian layers; public vhost must match the project you published in. The project is a **path segment** (`/admin/rest-v2/cs/cms/<project>/…`) — passing `project` inside a request body 500s with `Unrecognized field "project"`.
- **`content/query` needs a `queryExpr`**, even an empty string. Omitting it 500s with `Cannot invoke "java.lang.CharSequence.length()" because "source" is null` — which reads like an auth or type problem and is not.
- **An invalid page blocks the publish of everything under it.** A component config missing a `min: 1` field (e.g. `content-block`'s required `background` ComboBox) makes the *page* invalid, and every `publish` — including publishes of unrelated children — returns `{"state":"ERROR","message":"Item \"<page-name>\" could not be published."}`. Diagnose before guessing: `POST …/content/content/resolvePublishContent` with `{ids, excludedIds: [], excludeChildrenIds: []}` returns `containsInvalid` and `invalidContents`, naming the offending content id.
- **Re-publishing an already-published item does not move `publish.from`** (only `publish.time`), so a later edit does not disturb evidence that depends on publish ordering.
- `GET …/content/content?id=<uuid>` returns `name`/`path`, **not** `_name`/`_path` — the underscore-prefixed keys only exist on query hits and on lib-content results.
- **Component form schema (labels, options, defaults) is its own XHR:** `GET /admin/rest-v2/cs/content/page/part/descriptor?key=<app>:<part>` (no project segment; `…/page/layout/descriptor`, `…/page/descriptor` for the other kinds). Authenticated GET returns the resolved labels — the fastest way to assert a field's label, option list, and default without driving the UI. Locale resolution and the header route: [How-to-capture-schema-labels-in-another-locale.md](./How-to-capture-schema-labels-in-another-locale.md).
- **Proving a field is optional does not need the UI.** `POST …/content/content/markAsReady`
  `{contentIds:[id]}` returning **204**, plus `POST …/content/content/resolvePublishContent`
  returning `containsInvalid: false`, is server-side proof that the current config satisfies every
  `occurrences.min`. A required-field violation shows up as `containsInvalid: true` with the content
  in `invalidContents`. Use this instead of screenshotting validation chrome.
- **Reading the Inspect form is not free of side effects.** The first `<button>` inside a filled ComboBox wrapper is the **remove (X)**, not the dropdown toggle — a blind `querySelector('button').click()` clears the value. Any such edit arms a `beforeunload` dialog that makes the next `browser_navigate` time out; handle the dialog with accept (discard). Nothing is autosaved: re-`GET …/content/content?id=<uuid>` and compare `modifiedTime` to confirm.
- **Open Context Panel by `aria-label`, not visible text.** `getByText('Show Context Panel')` resolves the sr-only tooltip, not the toolbar button; the click is intercepted and CS can navigate to `#/english/browse`. Use `button[aria-label="Show Context Panel"]` with `{ force: true }`. Confirm the edit URL still contains the content id after the click.
- **Draft iframe frames:** `frameLocator('iframe')` finds 0 components. Use `page.frames().find(f => f.url().includes('/site/edit/'))`, then `[data-portal-component-type="part"]`.
- Do not confuse emulator/preview-mode menus (**Automatic / Media / Standard / JSON**) with the **Page** context widget.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| CS URL | `http://localhost:8080/admin/com.enonic.app.contentstudio/main` |
| Project | `english` |
| Edit URL | `http://localhost:8080/admin/com.enonic.app.contentstudio/main/english/edit/<uuid>` |

### Edit-mode page URL renders the page directly (no CS iframe)

`<base>/admin/com.enonic.app.contentstudio/site/edit/<project>/draft/<site-path>` served on its
own — not inside the CS wizard — returns the **page itself** with `meta.mode === 'edit'` and no
iframe. Playwright can query and screenshot its DOM directly, which is far cheaper than driving
the wizard.

Always pair it with a **positive control** before reporting an absence: load a page you know has
an empty owned part and assert its placeholder node is present. On acme, `/site/test/evidence/card-grid`
renders `.card-grid--empty` at this URL form. Without that control, "no placeholder found" is
equally consistent with "this URL is not edit mode", and the evidence proves nothing.

### `content/query` needs `contentTypeNames`, and `_path` does not match

- Project segment is the **layer** name (`english` on acme), not `main` or `default`;
  `/admin/rest-v2/cs/cms/english/content/content?id=<uuid>` is the working read.
- `POST …/content/content/query` **500s** without `contentTypeNames`
  (`Cannot invoke "java.util.List.stream()" because "contentTypeNameString" is null`).
- `_path LIKE '/content/…'` and `_path LIKE '/…'` both return 0 hits. `_parentPath = '/content/<parent>'`
  and `_name = '<segment>'` work. Use those to resolve a path to an id.

### Duplicate, publish status and Reset across layers (verified acme review, PROJ-446, 2026-09-23)

- **Duplicate over REST** (the call CS's Duplicate button makes): `POST …/content/content/duplicate`
  `{"contents":[{"contentId":"<src>","includeChildren":false,"parent":"/site/test/…","name":"<slug>"}]}` → `{taskId}`.
  `parent` + `name` put the copy straight at the target path, so no separate move/rename. The source is untouched.
  Set the display name afterwards with `content/update` (in the project that owns the copy).
- **`page/update` accepts a descriptor the app does not ship** (e.g. an old-site part). Useful to reproduce legacy content.
- **`compare` `diff` is not a draft-vs-master signal.** It stayed `[]` while an inherited item's draft and master had different page trees; it only listed `inherit` after a Reset. Compare `modifiedTime` on `branch: draft` vs `branch: master` (`content/query` with `queryExpr: "_id = '<id>'"`, `expand: full`) instead.
- **"Online" hides inherited drift.** When a Base change reaches a layer's draft through inheritance, the layer item keeps the **Online** badge and "Unpublish" as the main action, although master is older. A layer `publish` still pushes it and keeps `inherit`.
- **Layer drafts follow only marked-ready Base versions** once the item is ready: a Base edit left `IN_PROGRESS` does not reach the layer draft.
- **Reset in the UI:** editor → "More actions" → **Reset** → dialog **Confirm**. Restores `inherit` to `[CONTENT, PARENT, NAME, SORT]` and the Base draft; master keeps the localized version until the layer is published.
