# Element Conventions

- Put a `cameraUpdate` element first and keep it 4:3, for example `1200x900`.
- Prefer the CLI's `label` shorthand on `rectangle`, `ellipse`, `diamond`, and straight two-point `arrow` elements instead of manually constructing bound text elements.
- Do not put `label` on a bent (3+ point) arrow. Excalidraw centers it on the middle point, which is the corner, and the label mask cuts the bend. Place a standalone `text` element beside one straight segment instead, at least 8px from any box.
- Keep at least 120px between columns when a straight arrow in the gap carries a label; a 90px gap cannot fit a 12-character label at fontSize 14.
- Use stable IDs so arrows can bind cleanly to shapes.
- Bind arrows with `startBinding` and `endBinding`.
- Fixed-point helpers:
  - Right edge: `[1, 0.5]`
  - Left edge: `[0, 0.5]`
  - Top edge: `[0.5, 0]`
  - Bottom edge: `[0.5, 1]`
- Use top-to-bottom layouts for flows and left-to-right layouts for architecture unless the user signals otherwise.

## Minimal JSON Pattern

Use this as a starting point and expand it to match the request:

```json
[
  { "type": "cameraUpdate", "width": 1200, "height": 900, "x": 0, "y": 0 },
  {
    "type": "ellipse",
    "id": "start",
    "x": 460,
    "y": 60,
    "width": 180,
    "height": 90,
    "backgroundColor": "#a5d8ff",
    "fillStyle": "solid",
    "label": { "text": "Start" },
    "boundElements": [{ "id": "a1", "type": "arrow" }]
  },
  {
    "type": "arrow",
    "id": "a1",
    "x": 550,
    "y": 150,
    "width": 0,
    "height": 120,
    "points": [[0, 0], [0, 120]],
    "endArrowhead": "arrow",
    "startBinding": { "elementId": "start", "fixedPoint": [0.5, 1] },
    "endBinding": { "elementId": "step", "fixedPoint": [0.5, 0] },
    "label": { "text": "continue" }
  },
  {
    "type": "rectangle",
    "id": "step",
    "x": 430,
    "y": 290,
    "width": 240,
    "height": 90,
    "backgroundColor": "#b2f2bb",
    "fillStyle": "hachure",
    "label": { "text": "Process step" },
    "boundElements": [{ "id": "a1", "type": "arrow" }]
  }
]
```
