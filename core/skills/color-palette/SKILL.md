---
name: color-palette
description: "Extract an N-color palette from a local image and score another image against it (CIELAB distance, coverage). Use for brand/style conformance or palette deviation — not aesthetic judgment. | recommendedRole: deterministic | aliases: palette-distance, image-palette, extract-palette."
metadata:
  recommendedRole: deterministic
  aliases: palette-distance, image-palette, extract-palette
  cliDependencies:
    required: [python3]
    optional: [agentctl]
    pythonDependencies:
      required: [Pillow, numpy]
---

# Color Palette

Two deterministic primitives: build a palette from a reference image, then measure how far other images sit from it. Same inputs always produce the same numbers — no sampling, no model.

## When to use

- Validating a batch of images against a brand/style palette and discarding outliers.
- Choosing an accept/reject cutoff by looking at the score distribution across a sample first.
- Explaining *why* an image scored badly (which colors are off-palette, which palette entries went unused).

## When not to use

- Judging whether a palette is the *right* palette — that is design/brand judgment, not pixel math.
- Comparing two images to each other pixel-for-pixel — use [diff-image](../diff-image/SKILL.md).
- Measuring emptiness rather than color — use [blank-space](../blank-space/SKILL.md).

## Commands

Prefer `agentctl` — it keeps the bounded-JSON conventions consistent, and its `tools audit` reports whether `Pillow`/`numpy` are importable before you run.

```bash
agentctl image palette-create reference.png --colors 8 --out palette.json --swatch palette.png
```

```bash
agentctl image palette-distance candidate.png palette.json
```

Equivalent direct calls (same scripts, use if `agentctl` is unavailable):

```bash
python3 ~/.agents/skills/color-palette/scripts/palette_create.py reference.png --colors 8
```

```bash
python3 ~/.agents/skills/color-palette/scripts/palette_distance.py candidate.png palette.json
```

### `palette-create` flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--colors` | `8` | Palette size, 2-256. |
| `--method` | `mediancut` | `mediancut` balances the color cube (closest to ImageMagick `-colors`); `maxcoverage` favors spatially dominant colors; `fastoctree` is coarser but fastest. |
| `--out` | — | Write the palette JSON for reuse by `palette-distance`. |
| `--swatch` | — | Write a PNG swatch strip. Bands are nearest-neighbour filled, so the strip reads back losslessly as a palette. |
| `--swatch-size` | `400x50` | Swatch strip `WIDTHxHEIGHT`. |

Fully transparent pixels are excluded, so an image on a transparent canvas does not spend a palette slot on black.

### `palette-distance` flags

The `palette` argument accepts three forms: a palette JSON from `palette-create`, **any swatch image** (including one produced by `convert ... -unique-colors`), or an inline hex list like `'#1a2b3c,#ffffff'`.

| Flag | Default | Purpose |
|------|---------|---------|
| `--space` | `lab` | Space for the primary score. `lab` is perceptual (CIE76 dE) and is the one to threshold on; `rgb` is plain sRGB Euclidean, which over-penalizes bright colors and under-penalizes dark ones. |
| `--tolerance` | `10` | Raw distance still counted as on-palette, in the selected space's units. In Lab, ~2.3 dE is one just-noticeable difference and ~10 dE is "clearly a different color". |
| `--percentiles` | `50,90,95,99` | Per-pixel distance percentiles to report. |
| `--top-offenders` | `5` | How many worst off-palette colors to list. |
| `--palette-max-colors` | `256` | Reject a palette image with more distinct colors than this — catches passing a photo where a swatch was meant. |

## Output

`palette-distance` emits bounded JSON:

- `distance` — **the 0-1 number**: mean over all pixels of the distance to the nearest palette color, divided by the maximum possible distance in that space (`441.67` for sRGB, `258.68` for Lab). `0` means every pixel is exactly a palette color.
- `distance_rgb` / `distance_lab` — the same score in the *other* space, always present, so a batch sweep can be thresholded either way without re-running.
- `distance_raw` — the un-normalized mean, in dE or sRGB units. Easier to reason about than the normalized score once you know the scale.
- `percentiles` / `percentiles_raw` — per-pixel distance distribution including `max`. An image can have a low mean and still carry one badly off-palette region; `p99` catches that, the mean does not.
- `coverage.within_tolerance_ratio` — fraction of pixels within `--tolerance`. Often a more intuitive gate than the mean: "97% of pixels are on-palette".
- `palette_usage` / `unused_palette_colors` — pixel share per palette entry. An image using only 1 of 8 brand colors scores near-zero distance while still being off-brand; this is what catches it.
- `top_offenders` — worst colors ranked by *total* deviation contributed (distance x pixel count), each with its nearest palette entry. This is the "why did it fail" field.

## Interpretation rules

- Typical normalized scores are small. On real photos against an 8-color palette, `distance` in Lab lands roughly in the 0.01-0.06 band; a cutoff of "0.5" would never fire. Always derive the cutoff from an observed distribution, never from the fact that the scale is 0-1.
- **Score a sample batch before setting a cutoff.** Sort by `distance`, eyeball the images either side of the candidate threshold, then fix the number. Doing it the other way round produces a threshold that rejects the wrong images.
- A low mean does not mean on-brand. Check `unused_palette_colors` and `p99` alongside it — those catch monochrome crops and localized off-palette regions that the mean averages away.
- Palette size drives the score mechanically: more colors always means lower distance. Only compare scores computed against the *same* palette at the *same* size.
- Distance is color-only. It is blind to composition, layout, and subject matter, so never use it alone as an authoritative evidence pass/fail gate unless the plan defined that threshold before capture.

## Batch sweep

Score a directory and sort, to pick a cutoff from real data:

```bash
for f in images/*.png; do
  printf '%s\t%s\n' \
    "$(agentctl image palette-distance "$f" palette.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["distance"])')" \
    "$f"
done | sort -n
```

The bottom of that list is your reject candidate set. Open a few, then set the threshold where the visual judgment actually flips.
