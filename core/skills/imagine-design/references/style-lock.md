# design.json and style-lock.json

Two files, two owners. The lock executes the direction; it never changes it.

| File | Owner | Holds |
|---|---|---|
| `<lake>/design.json` | `imagine` (or the operator, standalone) | Art direction: the values every asset must agree on, plus the asset list. |
| `<lake>/assets/style-lock.json` | `imagine-design` | `"extends": "../design.json"` plus how to execute it: provider, model, seed, prompt parts, anchors. |

**Agreement rule.** The lock may add keys the design left open. It may never change a design value. `assets.py resolve` and `check` exit 2 and name the path when it tries. When the design has an `image` block, it must set `medium`, `projection`, `palette.mode`, `direction.drawing_style`, `direction.proportions` and `direction.lighting`; a missing one stops the run with a proposal, because choosing it would be deciding for the parent.

## `design.json`

```json
{
  "title": "Dry Season",
  "medium": "pixel-art",
  "projection": "isometric 2:1 (26.565°), camera from the south-east",
  "image": {
    "format": "png",
    "grid": [32, 16],
    "pixel_scale": 1,
    "background": "transparent",
    "max_colors": 24,
    "sizes": [[32, 16], [32, 32], [64, 64]]
  },
  "palette": {
    "mode": "exact",
    "colors": ["#1a1c2c", "#5d275d", "#b13e53", "#ef7d57", "#ffcd75", "#a7f070", "#38b764", "#257179"],
    "notes": "warm sand ramp, two cold shadow tones"
  },
  "direction": {
    "drawing_style": "clean pixel clusters, no dithering except the sky",
    "proportions": "characters 2.5 heads tall, 24 px high on the 32x16 grid",
    "lighting": "sun from the top-left, hard shadows to the bottom-right",
    "outline": "1 px dark outline, dropped on the lit side",
    "shading": "3 tones per material",
    "mood": "warm, cozy, dusty",
    "forbidden": ["gradients", "photo textures", "text", "lakes or jungles (canon: desert)"]
  },
  "audio": {
    "format": ["wav"], "sample_rate": 44100, "channels": 1, "max_seconds": 3,
    "loudness_lufs": -16, "loudness_tolerance": 2,
    "direction": "dry, wooden, soft attacks"
  },
  "model3d": {"format": ["glb"], "max_bytes": 20000000, "direction": "low-poly, flat shaded"},
  "video": {"format": ["mp4"], "sizes": [[1920, 1080]], "fps": 24, "max_seconds": 10,
            "direction": "slow pans over the anchors' world, no camera shake"},
  "assets": [
    {"id": "palm-well-tile", "entity": "palm-well", "kind": "tile", "size": [32, 16], "notes": "oasis water ring"},
    {"id": "asha-idle", "entity": "well-keeper-asha", "kind": "sprite", "size": [32, 32], "frames": 4}
  ]
}
```

Leave out `audio`, `model3d` or `video` when the run has none. `entity` is a registry id; the asset depicts that entity and nothing the canon forbids.

### Palette modes

| Mode | For | Check |
|---|---|---|
| `exact` | pixel art, flat vector, UI icons | every opaque pixel is a palette color; `normalize` remaps to it |
| `perceptual` | painted, rendered, photographic | `agentctl image palette-distance` thresholds: `max_distance` (default 0.05), `min_coverage` (0.9), `tolerance` in dE (10) |
| `none` | grayscale studies, audio-only runs | none |

### What checks what

| Field | Checked by |
|---|---|
| `image.format`, `sizes`, `grid`, `pixel_scale`, `background`, `max_colors`, `palette` | `assets.py check` |
| `audio.format`, `sample_rate`, `channels`, `max_seconds`, `loudness_lufs` | `assets.py check` (ffprobe, ffmpeg ebur128) |
| `model3d.format`, `max_bytes` | `assets.py check` |
| `video.format`, `sizes`, `fps`, `max_seconds` | `assets.py check` (ffprobe) |
| `projection`, every `direction` field, `forbidden` | contact-sheet review (`references/consistency.md`) |

`pixel_scale` > 1 means the delivered file is the native art enlarged N times with point sampling; `check` fails any image whose pixels do not sit on that N-px grid (a blurred or sub-pixel render). `grid` sizes are native sizes; `check` multiplies them by `pixel_scale`.

## `style-lock.json`

```json
{
  "extends": "../design.json",
  "provider": {"id": "pixellab", "access": "rest", "model": "<current id from the provider docs>", "seed": 4242,
               "settings": {"no_background": true, "style_image": "anchors/style.png", "target_palette": "design palette"}},
  "prompt": {
    "prefix": "isometric pixel art, 2:1, warm desert palette, sun from top-left,",
    "suffix": "transparent background, crisp pixels, no text",
    "negative": "blur, gradient, photo, text, watermark, lake, jungle"
  },
  "anchors": [
    {"id": "style", "file": "anchors/style.png", "use": "style reference on every call"},
    {"id": "asha-ref", "file": "anchors/asha.png", "subject": "well-keeper-asha", "use": "character reference for every Asha asset"}
  ],
  "direction": {"dithering": "none"}
}
```

- `provider` and `prompt` are fixed for the whole batch. Changing provider or model mid-batch restarts the anchors.
- `prompt.prefix` and `suffix` restate the design in the provider's vocabulary; they add words, never new direction.
- A `direction` key the design left open (here `dithering`) is an addition: allowed, logged in `design-log.md`, and returned to the parent in `additions` so it can adopt it.
