---
id: how-to-capture-schema-labels-in-another-locale
when_skills: [plan-task-evidence, run-plan]
inputs: [part/layout/page descriptor key, target locale]
outputs: [schema label per locale as JSON + rendered Inspect screenshot]
read: whole
prose: caveman-lite
---

# How to capture Content Studio schema labels in another locale (Enonic XP 8)

Prove that a part/layout field label resolves from `phrases_<locale>.properties`. Needed for i18n
acceptance criteria where one label must be shown in several languages.

**Scope:** `_shared`
**Applies to:** XP 8 / Content Studio 6 (verified on acme-group review, PROJ-341)
**Related:** [How-to-use-content-studio-xp8.md](./How-to-use-content-studio-xp8.md)

## Prerequisites

- Logged-in `/admin` session (see the Content Studio How-To for the `idprovider` login)
- The component's descriptor key, e.g. `com.example.app:content-block`

## The XHR that carries the label

Content Studio fetches the component form schema from:

```
GET /admin/rest-v2/cs/content/page/part/descriptor?key=<app>:<part>
```

(no project segment; `…/page/layout/descriptor` and `…/page/descriptor` for the other kinds).
XP resolves labels from the request's `Accept-Language`, then `phrases.properties`, then the
schema's own `label`. The header must reach **this call**, not only the HTML document.

## Procedure

### 1. Deterministic first — assert every locale without a browser

One authenticated request per locale gives the exact resolved string, the option list, and the
default. Do this before any capture: it proves or disproves the AC in seconds and tells you what
the screenshot must show.

```python
url = base + "/admin/rest-v2/cs/content/page/part/descriptor?key=" + quote(descriptor)
for loc in ["en", "no", "se", "sv-SE"]:
    j = get(url, headers={"Cookie": ck, "Accept-Language": loc})
    # walk j for {"name": "<fieldName>"} → its "label" and config.options / config.default
```

Also probe the **real** browser tags (`sv-SE`, `nb-NO`, `da-DK`), not only the bundle suffix —
that is how you catch a bundle nobody will ever receive (see Pitfalls).

### 2. Rendered screenshot (still mandatory for Jira)

A JSON body is a supporting artifact; the evidence comment needs the label as an editor sees it.

1. Install the header route **before** navigating, and keep exactly one route alive:
   `browser_route` pattern `**/admin/**`, headers `["Accept-Language: <loc>"]`.
   Routes **stack** — `browser_unroute` (no pattern) before adding the next locale, or the first
   one keeps winning.
2. Navigate to the content edit URL, wait ~10s for CS to boot.
3. Context Panel → widget combobox → **Page** → click the component inside the draft iframe.
4. Read the label from the DOM, then clip-screenshot around it (see Pitfalls for why element
   screenshots misfire).

## Pitfalls

- **Stacked routes.** Adding a second `browser_route` with the same pattern does not replace the
  first. `browser_unroute` with no pattern, then add the one you want.
- **Never click blindly inside the Inspect form.** On a filled ComboBox the first `<button>` in the
  field wrapper is the **remove (X)**, not the dropdown toggle — clicking it clears the value.
  Resolve the toggle from the accessibility snapshot (`button "Toggle"` next to `combobox "Search"`)
  instead of `wrapper.querySelector('button')`.
- **Resolving the Toggle from the snapshot is not enough to click it.** Playwright MCP
  `browser_click` / `browser_type` take `target` as a **CSS selector**; a `ref_N` from
  `browser_snapshot` fails with "does not match any elements". Tag the node first via
  `evaluate` (`el.id = 'ev-toggle'`), then act on `#ev-toggle`. `browser_take_screenshot`
  does accept `element` + `ref`.
- **A filled ComboBox has no Toggle.** When a valid option is selected, the field shows the
  label plus **Remove occurrence** only. Clicking the selected text does not open the list.
  To photograph the option list: click Remove (form-local, not saved), then the Toggle that
  appears on the empty required field. Discard with `beforeunload` accept and confirm
  `modifiedTime` unchanged. An **invalid** stored value (no longer in `options`) is the same
  shape — raw value + Remove + "Value is not one of the allowed options", still no Toggle.
- **A dirtied form blocks navigation.** Any focus/clear in Inspect arms a `beforeunload` dialog;
  the next `browser_navigate` times out until you `browser_handle_dialog accept:true` (discard).
  The change is form-local — confirm the server is untouched via
  `GET /admin/rest-v2/cs/cms/<project>/content/content?id=<uuid>` and check `modifiedTime`.
  There is no autosave.
- **Element screenshots of the Inspect panel clip wrong.** The tabpanel role matches the *content
  form* first, and its box does not cover the right-hand context panel. Compute the field's
  `getBoundingClientRect()` and pass an explicit `clip` to `page.screenshot`, then upscale ~200%
  (the panel is ~320 CSS px wide and renders at DPR 1, so raw crops are hard to read).
- **The open dropdown hides the current value** — it swaps in a "Type to search…" box. To show both
  the selected value and the option list, take two clips and `+append` them into one image.
- **A bundle suffix is not a browser language tag.** Probe the tags a real editor sends
  (`sv-SE`, `nb-NO`), not only `se` / `no`. After `phrases_se.properties` was renamed to
  `phrases_sv.properties` (`f18e4da`, 2026-09), `sv-SE` and `sv` resolve Swedish **field**
  labels (`Bakgrund`). `se` falls back to English. `nb-NO` still catches `phrases_no.properties`
  (`Bakgrunn`).
- **ComboBox option labels can stay English after the field label translates.** On acme-group
  review (PROJ-341, 2026-09-03) the Content Block `background` field labelled Bakgrunn/Bakgrund
  under `nb-NO`/`sv-SE`, but the five options stayed Purple/Green/Red/Beige/White in the
  descriptor JSON **and** in the open Inspect list. Check `config.options[].value` (display
  string) per locale, not only `label`. CS chrome (search placeholder, toolbar) does localise.
- **Content Studio's own chrome and the app's schema phrases localize independently.** Under
  `Accept-Language: nb-NO` the CS toolbar turns Norwegian (`Vis kontekstpanelen`). After the
  workspace panel is open the same control becomes `Skjul arbeidsområdepanelet`. The Page widget
  is **Komponenter**; the Inspect tab is **Inspiser**. Under `sv-SE` chrome is Swedish
  (`Visa kontextpanelen`, `Landningssida`, `Sida`). Verify against the field, never the toolbar.
  Locale-proof selectors: `/Utvid alle|Expand all|Visa kontextpanelen|Vis kontekstpanelen|Skjul arbeidsområdepanelet|Show Context Panel/`
  and `/Page|Side|Sida|Komponenter/`.
- **Declare the tag you actually used in the Jira comment.** Capturing SE with `se` is honest for a
  leftover `phrases_se` bundle; presenting `se` as what a Swedish editor sees is not. `sv-SE` is
  the tag to use for Swedish editors. Say which tag produced the shot.
- **Option labels resolve separately** from the field label. A translated field name can sit above
  untranslated options if the bundle only carries the `…input.<field>` key and not the
  `…input.<field>.option.*` keys. The JSON from step 1 shows both — check them together.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| Schema XHR | `/admin/rest-v2/cs/content/page/part/descriptor?key=com.example.app:content-block` |
| Locales probed | `en` → Background / Purple…White; `nb-NO` → Bakgrunn / options still English; `sv-SE` → Bakgrund / options still English; `se` → Background (English fallback) |
| Route | `browser_route` `**/admin/**`, `["Accept-Language: no"]` |
