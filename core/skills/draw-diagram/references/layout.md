# Default Multi-Diagram Layout

When the user asks for multiple diagrams, many charts, a visual explainer, or a set of graphics, default to one large editable Excalidraw canvas laid out as a clean grid of contained diagram panels.

Use this pattern unless the user explicitly asks for something different:

- One `.excalidraw` file as the source of truth.
- Multiple charts must be presented together in one combined canvas by default.
- A large grid canvas, typically 3 columns when there are many panels.
- Each diagram sits inside an outer light neutral container rectangle.
- Each container has a short title at the top left, optional one-line subtitle, and a thin divider line below the header.
- Keep generous padding inside each panel.
- Use consistent panel dimensions across the grid when possible.
- Put each mini-diagram, chart, flow, comparison, or decision tree inside its own container.
- Use the same color palette across all panels so the full canvas feels like one system.
- Prefer useful teaching diagrams over decorative diagrams: capability maps, comparison matrices, workflows, decision trees, stacks, loops, ladders, demo maps, and prompt anatomy charts.
- Keep labels short and readable. Split dense ideas into more nodes instead of forcing long text into one shape.
- If the user asks for "a ton of graphics" or similar, make many useful panels on one canvas rather than many disconnected files.

Good default panel structure:

```json
[
  {
    "type": "rectangle",
    "id": "panel_1",
    "x": 80,
    "y": 80,
    "width": 1450,
    "height": 900,
    "backgroundColor": "#f8f9fa",
    "strokeColor": "#dee2e6",
    "fillStyle": "solid",
    "strokeWidth": 2,
    "roughness": 1,
    "roundness": { "type": 3 }
  },
  {
    "type": "text",
    "id": "panel_1_title",
    "x": 114,
    "y": 106,
    "text": "Diagram Title",
    "fontSize": 30,
    "strokeColor": "#1e1e1e"
  },
  {
    "type": "text",
    "id": "panel_1_subtitle",
    "x": 116,
    "y": 150,
    "text": "One short sentence explaining what this panel teaches.",
    "fontSize": 17,
    "strokeColor": "#5f6368"
  },
  {
    "type": "arrow",
    "id": "panel_1_divider",
    "x": 114,
    "y": 192,
    "width": 1382,
    "height": 0,
    "points": [[0, 0], [1382, 0]],
    "endArrowhead": null,
    "strokeColor": "#ced4da",
    "strokeWidth": 2,
    "roughness": 1
  }
]
```

For grid placement, use a predictable coordinate system such as:

- Panel width: 1450
- Panel height: 900
- Gap: 120
- Start x/y: 80, 80
- Column x: `80 + column * (1450 + 120)`
- Row y: `80 + row * (900 + 120)`
