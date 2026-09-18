---
name: diff-image
description: "Pixel-diff two local images: changed-pixel count/ratio, visible diff, optional mask. Use for screenshot regression or before/after evidence. Same dimensions required; not a semantic pass/fail gate. | recommendedRole: deterministic."
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

## Direct CLI fallback

If the wrapper is unavailable, use the upstream CLI directly:

```bash
image-diff count first.png second.png
image-diff diff first.png second.png -o raw-difference.png
```

Prefer the wrapper because it checks dimensions, records provenance, bounds output, and makes ordinary screenshot diffs visible.
