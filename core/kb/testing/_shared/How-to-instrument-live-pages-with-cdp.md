---
id: how-to-instrument-live-pages-with-cdp
when_skills: []
read: section
prose: caveman-lite
---

# How to instrument live pages with CDP for evidence

`cursor-ide-browser` → `browser_cdp`; Playwright CDP session works the same. CS click paths: [How-to-use-content-studio-xp8.md](./How-to-use-content-studio-xp8.md).

## Hover states

Two different mechanisms — pick by what the component uses.

**CSS `:hover` only** (colour, underline, background): force the pseudo-state so it survives
a screenshot, since a real pointer cannot be parked while capturing.

```js
// CDP, in order
CSS.enable
DOM.getDocument            → root nodeId
DOM.querySelector          → nodeId of the element
CSS.forcePseudoState       { nodeId, forcedPseudoClasses: ['hover'] }
// capture, then clear with forcedPseudoClasses: []
```
Read the effect with `CSS.getComputedStyleForNode` (or `Runtime.evaluate` +
`getComputedStyle`) **before and after** so the report can state the actual values.

**React `onMouseEnter` / `onFocus`** (state change, e.g. swapping an image panel):
`forcePseudoState` does nothing — React needs a real event. Dispatch `mouseover` **with a
`relatedTarget` that is a sibling element**, not `document.body`:

```js
row.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, relatedTarget: otherRow }))
```
With `relatedTarget: document.body` React's synthetic `mouseenter` is often computed as
"already inside" and the handler never fires. Verify the state actually changed (class,
`src`, panel height) before capturing — do not assume the dispatch worked.

**Playwright MCP `browser_hover`** is a real pointer hover and is the simpler route when the
capture and the assertion can happen while the pointer stays put — it survives both
`browser_evaluate` and an *element* `browser_take_screenshot`. Re-read `el.matches(':hover')`
after the shot to prove the state was still live when the pixels were taken. To clear it,
hover a neutral sibling rather than moving to `body`; that also gives you the AC-negative
("hovering the card changes nothing") for free.

## Verifying a utility class actually shipped in the CSS bundle

Grepping deployed CSS for a Tailwind arbitrary-value class **as it appears in the HTML** is a
false-negative machine. Tailwind escapes the selector, so the class `decoration-[length:7%]`
is emitted as:

```
.decoration-\[length\:7\%\]{text-decoration-thickness:.0700001em}
```

A grep for `decoration-[length:7%]` finds nothing and reads as "the utility was never built",
which can send a whole diagnosis down the wrong path (this happened on PROJ-353). Grep for the
**declaration** instead of the selector, or escape the selector:

```bash
grep -o 'text-decoration-thickness:[^};]*' main.css | sort -u
grep -o 'decoration-\\\[[^{]*{[^}]*}' main.css
```

Cross-check by asserting the class is present in the live HTML *and* the computed style on the
element resolves to the expected value — that proves markup and bundle agree, which is what an
"assets rebuilt from current source" gate actually needs.

## Viewport / responsive

```js
Emulation.setDeviceMetricsOverride { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }
// capture
Emulation.clearDeviceMetricsOverride
```
Always clear it — a leftover override silently poisons every later desktop capture.

## Motion

- Reduced motion: `Emulation.setEmulatedMedia { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] }`,
  then assert the animation stopped (`getAnimations().length`, or `playState`).
- Auto-scrolling / marquee: sample the moving value twice with a delay and show it changed:
  ```js
  const t1 = getComputedStyle(el).transform; await new Promise(r => setTimeout(r, 600));
  [t1, getComputedStyle(el).transform]
  ```
  `element.getAnimations()` gives `animationName`, `duration`, `iterations`, `playState` —
  better proof than a still image.

## Making DOM facts capturable

A screenshot of a page cannot show an `href` or a `target`. Build a small overlay from the
**live DOM** and screenshot that, so the image is self-evidencing:

```js
const box = document.createElement('div')
box.setAttribute('style', 'position:fixed;inset:0;z-index:99999;background:#fff;padding:16px;overflow:auto')
box.innerHTML = '<p>Live DOM of ' + location.href + '</p>' + tableBuiltFromQuerySelectorAll
document.body.appendChild(box)
```
Same trick for navigation proof: after a click, inject a fixed banner containing
`location.href` and capture it, since the embedded browser screenshot has no address bar.
Keep the values **read from the page** — never hand-typed.

## Abort / fail a same-origin `fetch` (form POST)

When a UI success state must stay off on network failure (e.g. Contact CTA **Sent**), wrap
`window.fetch` before submit and throw for the target URL substring:

```js
const orig = window.fetch.bind(window)
window.fetch = async (input, init) => {
  if (String(input).includes('sendFormEmail')) throw new TypeError('Failed to fetch')
  return orig(input, init)
}
```

Do not clear Email Receiver to force failure — an unconfigured Contact CTA renders no form.
Capture the button label + console error via an injected overlay if needed.

## Reading React4XP SSR props off a live page

The server-side props ride in the page as a `script[type="application/json"]` sibling of the
`data-react4xp-ref` node. That is the only way to assert a *server* fact (a field the processor did
or did not emit) — no screenshot can show it.

```js
const j = [...document.querySelectorAll('script[type="application/json"]')]
  .map(s => s.textContent).find(t => t.includes('<a field name you expect>'));
JSON.stringify({ found: !!j, hits: (j.match(/fieldName/g) || []).length })
```

Two things this catches that nothing else does:

- a field leaking into the payload that the contract says belongs only on another path;
- a **server render error**. React4XP puts the failing component's error markup in the payload
  (`{"html":"<h1>Error</h1>…","type":"error"}`) and the client then renders an empty region, so the
  page merely *looks* empty. Grep the served HTML for `Error in processor` before concluding
  "renders nothing" is the intended empty state.

## ES5/Nashorn: never spread a possibly-boolean

XP-side code compiled for Nashorn (`tsconfig.*.nashorn.json`, `target: es5`) must not use
`...(cond && { … })`. swc lowers it to

```js
var source = arguments[i] != null ? arguments[i] : {};
var ownKeys = Object.keys(source);
```

`false != null` is true, so the helper calls `Object.keys(false)`. ES2015+ coerces and returns `[]`;
ES5/Nashorn throws **`TypeError: <value> is not an Object`**. The construct type-checks, lints
clean, and works in every browser bundle in the same repo — it fails only in the Nashorn runtime,
and only on the branch where the condition is false. Rewrite as two object literals
(`cond ? {...base, ...extra} : base`). Verified on acme-group PROJ-359, 2026-08-27.

## Pitfalls

- `Input.*` CDP methods are denied in the Cursor embedded browser; use the dedicated
  `browser_click` / `browser_type` tools or `Runtime.evaluate` + `dispatchEvent`.
- Screenshots taken via `browser_take_screenshot` with a path land under
  `/tmp/cursor/screenshots/<the path you asked for>` — copy them to the real evidence folder
  before flattening, or the folder stays empty.
- Content Studio's page-editor surface is an iframe; snapshots do not see inside it. Use
  `Runtime.evaluate` against `iframe.contentDocument` (same origin) or drive the outer panel.
- Overlays and injected banners must be removed (or the tab reloaded) before the next capture.


## Sample data (minimal)

| Thing | Example |
|-------|---------|
| Mobile viewport | 390 × 844, `deviceScaleFactor: 2` |
| Hover-transition sample delay | 600 ms |
