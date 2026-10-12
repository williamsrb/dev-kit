# How to detect a third-party script load or failure

## Scope

Inline JS that shows a fallback when an external `<script>` fails or times out, and hides it when the script loads (seen in RFD-687 `sorting-guide.html`).

## Procedure

1. Prefer `onload` / `onerror` attributes on the script element itself. `addEventListener` cannot attach before the element is parsed.
2. If you must delegate, use a capture listener on `document`, not `window`:
   `document.addEventListener('load', fn, true)` and `document.addEventListener('error', fn, true)`.
3. Clear the timeout in the load handler and set `hidden = true`.

## Pitfalls

1. `window.addEventListener('load', fn, true)` never sees element `load` events. The HTML spec removes Window from the event path when the event type is `load`, so only the document's own load reaches window. `error` events do reach window, which hides the bug: the error path works, the load path silently does nothing, and the timeout shows the fallback on every normal page load.
2. Verify with an init script that logs `document` capture vs `window` capture `load` targets, plus a MutationObserver on the fallback's `hidden` attribute. Observed on review 2026-10-09: script load at 362 ms on document capture, nothing on window capture, fallback visible at 10017 ms.
