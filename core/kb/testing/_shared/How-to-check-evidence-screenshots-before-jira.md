---
id: how-to-check-evidence-screenshots-before-jira
when_skills: [plan-task-evidence, run-plan]
inputs: [evidence PNG folder]
outputs: [pass/fail per file; retake list]
stop_if: [blank_percent >= 85 on a viewport-sized overlay, OCR missing planned tokens, agentctl image stamp --check exit 1, posting without verify-jira-comment-images.py]
read: whole
prose: caveman-lite
---

# How to check evidence screenshots before Jira

Local tools first. Do not flatten, upload, or post until every Jira-bound PNG passes. Do not use vendor vision for OCR.

Worked failure (PROJ-427/429, 2026-09-04): overlay shots were 1440×900 white pages with 3–8 lines of text (`blank_percent` 97–99). OCR still found the tokens. The shots were posted. They are trash. The same run also posted 429 twice and reused deleted-comment `fileId`s — that is [How to post Jira evidence comments](./How-to-post-jira-evidence-comments.md), not this file.

## Commands (every Jira-bound PNG, then stamp)

```bash
agentctl image whitespace /abs/path.png --background auto --tolerance 18 --grid 3
agentctl evidence inspect /abs/path.png --ocr --expected-text 'token from the step'
```

Equivalent if `agentctl` is missing: `python3 ~/.agents/skills/blank-space/scripts/blank_space.py` and `python3 ~/.claude/skills/tesseract-cli/scripts/ocr.py --json`.

**`agentctl image whitespace` is dead on this box** (re-confirmed 2026-09-17): it shells out to `blank-space/scripts/blank_space.py`, which fails on `ModuleNotFoundError: No module named 'numpy'`. The `agentctl evidence inspect --ocr` half still works. ImageMagick covers the gap with no install:

```bash
convert shot.png -colorspace Gray -threshold 90% -format '%[fx:mean]' info:   # -> 0.94 = ~94% blank
```

`--expected-text` matching is literal and Tesseract confuses `I`/`l` in UI headings — it read `AI crawler guide (llms.txt)` as `Al crawler guide (Ilms.txt)` and failed the check. Pick a token with no ambiguous glyphs (`crawler guide`, a field label) before concluding the shot is wrong.

Then **read the PNG** (vendor-vision-image-preview: cap long edge 1280). Confirm element, zoom, example page, and — on live/integration shots — the **product concept paint** (form fields, player, widget). A heading over an empty embed is a fail. Diagnose console/CSP before retake or post: [How to gate evidence on the product concept](./How-to-gate-evidence-on-the-product-concept.md).

After that gate passes, stamp pixel size, then refuse upload if the stamp is missing:

```bash
agentctl image stamp /abs/path.png
agentctl image stamp --check /abs/path.png
```

`--check` exit 1 = do not flatten-again/upload/post. Pass **file paths**. A directory only auto-stamps `NN-*.png`. Do not mention the stamp in the Jira comment.

## Fail (retake)

| Error | How it shows | Fix |
|-------|----------------|-----|
| Full-viewport overlay | `blank_percent` ≥ 85, longest edge ≥ 1200, 3×3 grid mostly ≥ 0.95 | Screenshot the overlay node (`#ev-overlay` clip), not the page |
| Wrong zoom | Subject is a strip in one corner; rest empty | Crop to the Inspect panel / dialog / overlay bbox |
| Wrong page / env | OCR or URL bar is a different path | Navigate again; do not keep the file |
| Missing labels | `--expected-text` fails | Retake; do not “explain around” the gap |
| Concept missing (empty form/player) | Heading/OCR pass; no fields/iframe in the pixels | Not an overlay fail. Diagnose CSP / network / fixture IDs. Do not pass. [Product concept](./How-to-gate-evidence-on-the-product-concept.md) |
| Missing pixel stamp | `agentctl image stamp --check` exit 1 | Run `agentctl image stamp` on the file path; re-check. Do not upload. |
| Stacked PNG with no merge flags | Two shots glued; empty band or no labels | Rebuild with a banner, a black bar between parts, and a short label on each. Do not post a silent stitch (PROJ-435 `08-featured-cards`). |
| Duplicate post / missing Jira images | Two comments, or empty boxes | Not a retake. Follow [How to post Jira evidence comments](./How-to-post-jira-evidence-comments.md) |

`border_blank_percent` near 0 on a 1440×900 white overlay does **not** pass — the stamp/border can pin content to the canvas. Use `blank_percent` + grid + longest edge.

## Pass examples

- Tight Inspect / dialog crop: high `blank_percent` is OK if the crop is the panel (longest edge often < 900) and OCR has the field labels.
- Live integration page: whitespace can pass while the form never painted. That is a **concept fail**, not an overlay pass. OCR the field labels (`First name`, `Submit`), not only the section heading.

## Overlay capture

```js
const box = await page.locator('#ev-overlay').boundingBox();
await page.screenshot({ path, clip: { x: box.x - 8, y: box.y - 8, width: box.width + 16, height: box.height + 16 } });
```

Do not `screenshot()` the full viewport after painting a corner overlay.

---

## `agentctl image whitespace` reads high on an unstamped shot — measure after stamping

`--background auto` picks the background by corner sample. On a raw capture of a white page the
corners are white, so the whole page counts as blank and a perfectly good text capture reads 90%+.
After `agentctl image stamp` adds its 2px `#dddedd` border, the corner sample becomes the border
colour and the same file reads 1-2%.

Worked example (JOT-290, 2026-09-17): `01-llms-txt-served.png`, a tight crop of a 5-section
`/llms.txt`, measured **92.4% blank** before stamping and **2.0%** after. Nothing about the image
changed but the border.

**Run the whitespace gate after stamping, not before.** If you must gate first, read the image
yourself before believing a high blank ratio on a light-background page — and never retake on that
number alone.

(`numpy` is installed again as of 2026-09-17, so this tool works; a `ModuleNotFoundError` for numpy
means the interpreter `agentctl` shells out to lost it, not that the gate is retired.)

## Tesseract renders capital I as lowercase l — pick OCR tokens that avoid it

`--expected-text 'AI policy'` fails on an image that plainly reads *AI policy*, because the OCR text
is `Al policy`. Same for `llms.txt` → `Ilms.txt` and `AI crawler guide` → `Al crawler guide`.
Choose a token with no capital-I/lowercase-l ambiguity (`policy page`, `policy -> /ai-policy`,
`Attribute the source`), or check the returned `ocr_text` before concluding the capture is wrong.
A "NO MATCH" on an I-bearing token is an OCR artifact, not evidence of a bad screenshot.

## Localized before/after strip

Clip at capture first (Playwright locator clip).
`agentctl image crop-changed --compose` is only for a localized mask (exit 0).
Exit 3 (`not-localized`) means do not invent a strip from the full
viewports.

The composite is a callout, not the live-UI proof. Run OCR on the
**unannotated after** shot. If the composite itself goes to Jira, stamp it
with `agentctl image stamp` after `crop-changed`. That command does not stamp.
