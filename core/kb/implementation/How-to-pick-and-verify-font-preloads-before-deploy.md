# How to pick and verify font preloads before deploy

## Scope

Choosing the 2-4 woff2 faces worth `<link rel="preload">` on a site whose fonts are
declared inside one compiled stylesheet, and proving the tag works **without** deploying.
Written from JOT-284 (Enonic XP 7 / React4XP 5, `www.jotron.com`), but nothing here is XP-specific.

## Prerequisites

- `playwright-cli` (headless is the default; `open --mobile` emulates Pixel 10).
- The **served** stylesheet, not the SCSS source. Fetch it from the live host — the
  compiled file is what ships, and build steps rewrite font paths.

## Procedure

1. **List the declared faces.** `curl` the stylesheet URL out of the served HTML, then
   regex `@font-face` blocks for family / weight / style / `font-display` / `url(...)`.
   Record `font-display` — it decides whether preload can move FCP at all (see Pitfalls).

2. **Ask the page which faces the first screen actually uses.** Walk text nodes,
   skip invisible/zero-box elements, and key on
   `getComputedStyle(el).fontFamily.split(',')[0] + weight + style`, recording each
   key's **minimum** `getBoundingClientRect().top + scrollY`. A key whose minimum top
   is below `innerHeight` is above the fold. This beats eyeballing a screenshot and
   gives a number you can defend in review.

3. **Repeat across viewports and templates.** Mobile (360x732) and desktop (1440x900)
   disagree: a collapsed hamburger hides the nav face on mobile while desktop shows it
   at top ~40px. Sample one page per page-template, not just the front page — a badge
   or eyebrow label can pull an extra weight above the fold on one template only.
   Preload per template, not one union list.

4. **Confirm against the real waterfall.** `playwright-cli --raw requests --static`
   (fonts are "static" and hidden from the default listing). Every face fetched at
   the same millisecond is the symptom being fixed: discovery is serialised behind
   CSS parse. A face that is *never* fetched must not be preloaded.

5. **A/B the tag before deploying** by injecting it into the live HTML with
   `page.route(...)` + `route.fulfill({ response, body })`, under CDP throttling
   (`Network.emulateNetworkConditions`, `Emulation.setCPUThrottlingRate`) and
   `Network.clearBrowserCache` per run. Then assert from `performance.getEntriesByType('resource')`:
   - each preloaded face appears **exactly once**, with `initiatorType: "link"` — a
     second entry with `initiatorType: "css"` means `crossorigin` is missing or mismatched;
   - non-preloaded faces still show `initiatorType: "css"`, later — that is the control;
   - `transferSize` totals unchanged.
   Watch the console for "preloaded using link preload but not used within a few seconds".

## Pitfalls

- **`font-display: swap` means preload will not move FCP.** First paint never waited on
  the font; it painted fallback text. Preload removes the FOUT window (branded faces
  arriving ~4s earlier in a Slow-4G lab), which is real but is *not* the FCP number a
  PageSpeed ticket usually promises. Check `font-display` in step 1 and say so up front
  rather than reporting a non-improvement as a failure.
- **`crossorigin` is mandatory even same-origin.** Without it the preload is discarded
  and the font is fetched twice. `crossorigin="anonymous"` is the safe spelling in a
  Thymeleaf/HTML template (minimised boolean attributes survive, but explicit is cheaper
  than arguing about the parser).
- **Use the same URL helper as the stylesheet link.** In XP that is inline
  `portal.assetUrl({'_path=fonts/X.woff2'})`, matching the `css/build.min.css` link, so the
  preload URL is byte-identical to what `@font-face url(../fonts/X.woff2)` resolves to under
  `/_/asset/<app>:<hash>/`. A service-backed helper (XP: `myAssetURL` →
  `_/service/<app>/get-assets-url/...`) is a different URL space with no build hash and
  guarantees a double fetch.
- **Keep `<meta charset>` first.** "Preloads first in `<head>`" is about being before the
  stylesheet link, not about displacing the charset declaration.
- **Case-sensitivity between CSS and shipped file.** A compiled `@font-face` pointing at
  `Matter-SemiboldItalic.woff2` when the file ships as `Matter-SemiBoldItalic.woff2` 404s
  silently on a case-sensitive host. Step 1 plus a `curl -o /dev/null -w "%{http_code}"`
  loop over every declared URL catches it in seconds.
- **No Lighthouse binary?** CDP throttling plus `PerformanceObserver` with
  `{type:'largest-contentful-paint', buffered:true}` gives comparable FCP/LCP for a
  before/after A/B. Label it as a lab A/B, not a Lighthouse score — it is not comparable
  to a PSI number.

## Sample data

Above-the-fold audit output (mobile 360x732, front page):

```json
{"Proxima Nova|700|normal":{"minTop":144,"tag":"H1.frontpage-hero__title"},
 "Matter|400|normal":{"minTop":462,"tag":"P.frontpage-hero__intro"},
 "Matter|500|normal":{"minTop":1241},"Matter|700|normal":{"minTop":4257}}
```

→ preload two faces; the 500 and 700 weights are below the fold.
