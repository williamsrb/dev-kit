---
name: blank-space
description: "Measure blank/background fraction of a local screenshot (overall ratio, border-trim, optional grid). Use for empty evidence shots, collapsed layout QA, or whitespace questions — not whether whitespace is correct. | recommendedRole: deterministic | aliases: whitespace-ratio, whitespace-check, image-whitespace."
metadata:
  recommendedRole: deterministic
  aliases: whitespace-ratio, whitespace-check, image-whitespace
  cliDependencies:
    required: [python3]
    optional: [agentctl]
    pythonDependencies:
      required: [Pillow, numpy]
---

# Blank Space

Measure blank/whitespace pixel ratio in a local image without spending remote LLM tokens. Fully deterministic — same image and flags always produce the same numbers.

## When to use

- An evidence screenshot looks mostly empty and you need a number, not a guess.
- Checking whether a layout change introduced an oversized gap, collapsed a section, or clipped content.
- Comparing "how blank" a before/after pair is (run once per image, then diff the ratios).

## When not to use

- Judging whether the whitespace is *correct* per design/plan — that requires the plan, Figma spec, or human/vendor-model judgment. This tool only measures pixels.
- Semantic description of what's on the page — use [describe-image](../describe-image/SKILL.md) or [ocr](../tesseract-cli/SKILL.md) for that.

## Command

Prefer `agentctl` — it's the shared entry point that keeps bounded JSON conventions consistent across skills, and its `tools audit` reports whether `Pillow`/`numpy` are actually importable before you run this:

```bash
agentctl image whitespace /absolute/path/screenshot.png
```

Equivalent direct call (same script, use if `agentctl` is unavailable):

```bash
python3 ~/.agents/skills/blank-space/scripts/blank_space.py /absolute/path/screenshot.png
```

Options (identical flags on both forms):

| Flag | Default | Purpose |
|------|---------|---------|
| `--background` | `auto` | `auto` samples the four corner pixels (typical for page/card backgrounds); `mode` uses the single most frequent color in the whole image; or pass an explicit `#RRGGBB` when you know the background (e.g. pure white forms). |
| `--tolerance` | `12` | Max per-channel distance from the background color still counted as blank. Raise it for JPEG artifacts or subtle gradients; lower it for exact-color synthetic UI captures. |
| `--grid N` | `0` (off) | Splits the image into an NxN grid and reports blank ratio per cell — use this to localize *where* the blank space is (e.g. "bottom third is empty"). |

## Output

Bounded JSON on stdout:

- `blank_ratio` / `blank_percent` — fraction of all pixels within `--tolerance` of the detected background color (or fully transparent).
- `border_blank_ratio` / `border_blank_percent` — like ImageMagick `-trim`: fraction of the canvas *outside* the tight bounding box of non-blank content. Use this for "is there a big empty margin" questions.
- `content_bbox` — pixel bounding box of detected non-blank content, or `null` if the whole image is blank.
- `grid.blank_ratio_per_cell` — present only with `--grid`; a row-major NxN array of per-cell blank ratios.

## Interpretation rules

- A high `blank_ratio` with `background: "auto"` on a mostly-white app screenshot is expected — sanity-check against `border_blank_ratio` and the grid before calling something a bug.
- `--background auto` samples only the four corners; a screenshot with a header/sidebar in a different color at the corners will misdetect the background. Fall back to `mode` or an explicit hex color when the corner color is not representative of the page background.
- This tool cannot tell you *why* an area is blank (collapsed section vs. correctly empty state vs. capture timing). Pair it with the plan/AC and, if still ambiguous, [describe-image](../describe-image/SKILL.md).
- Never use a blank-ratio threshold alone as an authoritative Jira evidence pass/fail gate unless the evidence plan already defined that threshold before capture.

## Example

Evidence screenshot that should show a filled article form, but might have a rendering gap at the bottom:

```bash
agentctl image whitespace \
  ${HOME}/.agents/prds/PROJ-388/evidence/01-article-content-form.png \
  --grid 3
```

`grid.blank_ratio_per_cell` bottom row spiking relative to the rest flags exactly which third of the page is empty, without opening the image.
