---
name: diff-image
description: "Pixel-diff two local images: changed-pixel count/ratio, visible diff, optional mask. Crop localized before/after sidecars and optional labeled compose. Same dimensions required; not a semantic pass/fail gate. | recommendedRole: deterministic."
metadata:
  recommendedRole: deterministic
  cliDependencies:
    required:
      - python3
      - image-diff
      - identify
      - convert
    optional:
      - agentctl
---

# Diff Image

Run exact image comparison locally. Keep both source images on disk and expose only bounded metrics plus the generated diff artifacts to the model.

## Workflow

1. Establish the comparison meaning:

   - **Before vs after:** changed pixels prove change, not improvement.
   - **Expected vs actual:** use a threshold only when the plan or user defined it before capture.
   - **Frontend vs backend evidence:** compare the same rendered content/state. Do not pixel-compare a UI screenshot with JSON, logs, or a differently composed admin view.
   - **Prototype vs final:** use the diff to locate implementation drift; judge intentional responsive or dynamic differences separately.

2. Make the inputs comparable. Match viewport, pixel dimensions, device scale, crop, zoom, theme, locale, font state, animation state, and dynamic content. Preserve the originals. A dimension mismatch is a failed precondition; do not resize automatically because resampling creates false differences.

3. Run the bundled wrapper with absolute paths. Prefer `agentctl` — the shared entry point for local image primitives:

   ```bash
   agentctl image diff \
     /absolute/path/expected.png \
     /absolute/path/actual.png \
     --output /absolute/path/difference.png \
     --mask-output /absolute/path/difference-mask.png
   ```

   Equivalent direct call (same script, use if `agentctl` is unavailable):

   ```bash
   python3 <skill-dir>/scripts/compare.py \
     /absolute/path/expected.png \
     /absolute/path/actual.png \
     --output /absolute/path/difference.png \
     --mask-output /absolute/path/difference-mask.png
   ```

   Either form runs `image-diff count` and `image-diff diff`, makes the upstream RGBA diff visible for ordinary opaque screenshots, and returns bounded JSON containing dimensions, hashes, changed pixels, ratio, percentage, and artifact paths. `agentctl image diff` defaults `--output` to `<second-image-stem>.diff.png` beside the second image when omitted; the direct script requires `--output` explicitly.

4. Add mechanical thresholds only when already defined:

   ```bash
   agentctl image diff expected.png actual.png \
     --output difference.png \
     --max-diff-pixels 100 \
     --max-diff-ratio 0.001
   ```

   Exit `0` means comparison completed within all supplied thresholds. Exit `3` means a supplied threshold was exceeded. With no thresholds, any successfully completed comparison exits `0`, even when pixels differ.

5. Inspect the generated difference image and optional mask when pixels differ. The difference image encodes channel-distance magnitude; the mask is black for unchanged pixels and white for changed pixels. Use visual judgment only after the deterministic metrics identify the scope.

## Interpretation rules

- `different_pixels: 0` means exact pixel identity for the decoded images.
- A non-zero result does not explain whether the change is correct.
- Large ratios can come from viewport, font, antialiasing, animation, or capture-timing drift. Fix capture comparability before judging implementation.
- Transparent inputs produce an exact count, but the visible RGB diff can underrepresent alpha-only changes; heed the wrapper warning and inspect alpha-sensitive cases separately.
- Never use the local result alone to approve Jira evidence, security-sensitive output, or a destructive action. Apply the evidence plan and human/vendor-model judgment after deterministic comparison.

## Crop changed regions (before/after callout)

Use when the change is a localized blob and a crop (or labeled strip) is
cheaper than sending full pages to vendor vision. The command runs
`compare.py` itself; do not run `image diff` first unless you also need the
full-page diff PNG. Capture-time Playwright clip remains the default way to
isolate a part.

```bash
agentctl image crop-changed \
  /absolute/path/before.png \
  /absolute/path/after.png
agentctl image crop-changed \
  /absolute/path/before.png \
  /absolute/path/after.png \
  --compose
```

Equivalent direct call:

```bash
python3 <skill-dir>/scripts/crop_changed.py \
  /absolute/path/before.png \
  /absolute/path/after.png \
  --compose
```

The command reuses `compare.py` (temp diff + mask, then deleted), closes the
mask with `Square:2`, and keeps connected components whose area is at least
`max(256 px², 0.1% of canvas)`. On success it writes
`<after-stem>.before-crop.png` and `<after-stem>.after-crop.png` beside the
after image (`--output-dir` redirects). `--compose` also writes
`<after-stem>.before-after.png`: labeled `Before` | `After`, 8 px black
divider, 4 px red rectangle on the before half and green on the after half.
Inputs are never overwritten.

**Localization abort** (`status: not-localized`, exit `3`): remaining blob
count is 0 (including an identical pair), remaining blob count is greater
than 3, or the padded union bbox covers more than 50% of the canvas. No
crops and no compose in that case. Dimension mismatch is exit `2`.

OCR the **unannotated after** shot (`agentctl evidence inspect --ocr`). If
the composite goes to Jira, stamp it separately with `agentctl image stamp`.
`crop-changed` does not stamp, flatten, or send pixels to vendor vision. The
composite is a callout, not the live-UI proof and not a semantic pass/fail
gate.

## Direct CLI fallback

If the wrapper is unavailable, use the upstream CLI directly:

```bash
image-diff count first.png second.png
image-diff diff first.png second.png -o raw-difference.png
```

Prefer the wrapper because it checks dimensions, records provenance, bounds output, and makes ordinary screenshot diffs visible.
