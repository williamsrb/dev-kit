# Consistency

The job is that no asset deviates from the others or from `design.json`. Text prompts alone drift; images anchor.

## Techniques, in the order they help

1. **Anchor first.** Before the batch, make a style anchor: one tile, one character, one prop, side by side, on the design's grid and palette. Iterate it until it passes `check` and the review below. Every later call passes the anchor as a style or image reference when the provider supports one.
2. **One reference per recurring subject.** Each character or landmark that appears in more than one asset gets a reference image from its first approved asset. Poses, angles and animation frames derive from that reference (edit or reference endpoint), never from text alone.
3. **Variants by editing.** Color, pose or damage variants edit the approved asset instead of generating a new one.
4. **Frozen recipe.** Same provider, model version, seed policy, size and prompt `prefix`/`suffix`/`negative` for the whole batch. The subject phrase comes from the registry entity's summary, in canon-safe words. `negative` holds `direction.forbidden` and the canon's forbidden features for the asset's region.
5. **Deterministic post-processing.** `assets.py normalize` point-samples to the native size, remaps to an `exact` palette, makes alpha binary for pixel art, and re-enlarges by `pixel_scale`. Raw provider output stays in `raw/` untouched.
6. **Check, then look.** `assets.py check` on every file, then a contact sheet with the anchor first for one side-by-side review per batch.
7. **Drift watch.** Every 8 accepted assets, put the newest ones next to the anchor. Outline weight, shadow side or head size creeping away means the recipe drifted: fix the lock's prompt parts, never `design.json`.

## Review checklist (contact sheet)

Build the sheet with `assets.py sheet` (long edge capped at 1280, point filter). Look at the sheet, not at each file. Fail an asset on any of:

- **Drawing style:** cluster shapes, line quality, dithering, level of detail match the anchor.
- **Palette:** ramps used the way the anchor uses them; no tone outside the palette mood even when `check` passed (perceptual mode).
- **Proportions:** head count and height in pixels match `direction.proportions`; props scale against characters as in the anchor.
- **Lighting:** light from the stated side on every asset; shadows fall the same way and length.
- **Projection:** same camera and angle; isometric edges keep the 2:1 slope; no asset in a different view.
- **Outline and shading:** same outline rule and tone count per material.
- **Grid and scale:** the asset sits on the grid the same way its neighbors do.
- **Canon:** nothing forbidden by `design.json` or the canon (a lake in a desert region, a modern prop in a medieval world).

Fix by regenerating with the same recipe and a sharper subject phrase, or by editing from the anchor. At most 3 attempts per asset; then mark it `failed` with the reason.

## Budget

Generation calls stop at 4 per anchor plus 3 per listed asset. Reaching the budget ends the batch; the rest is `failed: budget`. Log every call in `design-log.md`.

## References from the web

You may search the web for visual references and technique (how a genre handles isometric shadows, palette ramps of known pixel-art games). Record each in `assets/references.md`: URL, access date, what it informed. References inform words and proposals; they are never uploaded to a provider as reference images (third-party rights), and prompts never name living artists. Only anchors made in this run are uploaded.

## Video

Start every clip from approved anchors (image-to-video), never from text alone, so the world in motion is the world in the stills. `check` covers format, size, frame rate and length. For review, pull one frame per second (`ffmpeg -i <clip> -vf fps=1 <lake>/assets/sheets/<clip>-%02d.png`) and put the frames on a contact sheet next to the anchor with the same checklist; also watch for style drift between the first and last frame.

## Audio and 3D

Audio: `check` covers format, sample rate, channels, length and loudness, so a set of effects plays at one level. You cannot listen; keep one provider, one voice or preset, and one prompt prefix, and report timbre consistency as not reviewed.

3D: `check` covers format and size. Review the provider's preview renders on a contact sheet with the same checklist (proportions, palette mood, style, lighting of the preview).
