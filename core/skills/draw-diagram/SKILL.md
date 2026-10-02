---
name: draw-diagram
description: >-
  Create polished Excalidraw diagrams from text descriptions: a .excalidraw file,
  a PNG preview, and an optional excalidraw.com URL. Use when the user wants a
  static editable drawing, flowchart, architecture diagram, decision tree,
  process or data flow, or says draw this, diagram this, or make a chart. Not
  for README, git docs, or a static diagram in Markdown (write Mermaid in the
  doc). Not for an interactive HTML viewer, pan/zoom page, or presentation
  deck (use archify). User naming this skill wins.
metadata:
  recommendedRole: follow
  aliases: excalidraw, excalidraw-diagrams, flowchart-diagram, architecture-diagram
  source: rbrown101010/codex-marketing-skills@excalidraw-diagrams
  cliDependencies:
    required: [excalidraw-cli]
    optional: [playwright-cli, qlmanage]
---

# Excalidraw Diagrams

Use `excalidraw-cli` to turn structured diagram plans into `.excalidraw` files. The published CLI accepts Excalidraw JSON elements, not a custom DSL, so any shorthand notation is only for planning. The executable artifact is always a JSON elements file plus the generated `.excalidraw`.

## Wrong artifact?

Decide the sink before writing elements. User naming this skill
wins; do not bounce a second time.

- README, docs, PR, or "add diagrams to the docs" → stop. Write
  Mermaid in the Markdown. Do not emit Excalidraw.
- Interactive HTML viewer, pan/zoom page, or presentation deck →
  stop. Read and follow `archify`.
- Static editable Excalidraw/PNG the operator will keep editing →
  continue below.

Load this file first, then only the matching references. Do not preload later files.

| When | Read |
|------|------|
| Colors, fills, dashed error paths | [references/styling.md](references/styling.md) |
| More than one diagram, chart, or panel on one canvas | [references/layout.md](references/layout.md) |
| JSON elements, bindings, `cameraUpdate`, `label` shorthand | [references/elements.md](references/elements.md) |
| Flowchart vs architecture vs decision tree vs data flow; sequence/Gantt/pie/bar | [references/guidance.md](references/guidance.md) |
| Typical single diagram | styling.md and elements.md |
| Several charts in one file | styling.md, elements.md, and layout.md |

## Prerequisites

- `excalidraw-cli` must be on `PATH` (`npm install -g excalidraw-cli`).
- Preview PNG: `qlmanage` on macOS, otherwise `playwright-cli` (headless) for `scripts/render_preview.py`.
- When you need exact field names or supported element properties, run `excalidraw-cli reference` or `excalidraw-cli ref --raw`.

## Triggering

Use this skill when the user wants a polished Excalidraw artifact
they can keep editing (flowchart, architecture, decision tree, data
or process map). See Wrong artifact? before generating.

## Working Model

1. Reduce the request into nodes, arrows, labels, and layout direction.
2. If helpful, sketch the structure in shorthand first:
   - `(Start)` = ellipse
   - `[Step]` = rectangle
   - `{Decision?}` = diamond
   - `[[Store]]` = storage/data node
   - `->`, `-->`, `-> "label" ->` = connectors
3. Translate that plan into Excalidraw JSON elements in an
   `elements.json` file. Read
   [references/elements.md](references/elements.md) for the JSON
   pattern and bindings. Read
   [references/styling.md](references/styling.md) for the palette.
   Put `"fontFamily": 5` (Excalifont) on every `text` and `label`;
   the CLI otherwise writes `1` (Virgil).
4. For multiple diagrams, charts, or visual explanations, read [references/layout.md](references/layout.md) and use that container-grid canvas unless the user specifies a different layout.
   - Present multiple charts in one combined editable Excalidraw canvas unless the user asks for separate files.
   - If separate chart files are useful or already created, also create a single combined `.excalidraw` canvas that contains all charts.
5. Generate the diagram with `excalidraw-cli create elements.json -o output.excalidraw`.
6. Generate a local preview image for the `.excalidraw` file:
   - macOS: `qlmanage -t -s 1600 -o <preview_dir> output.excalidraw` (typically produces `output.excalidraw.png`).
   - Linux or no Quick Look: `python3 scripts/render_preview.py output.excalidraw output.png`. It renders with Excalidraw's own exporter in headless Playwright CLI (needs network for esm.sh). Exit 2 means `playwright-cli` is missing.
   - Look at the preview before returning it. A render straight from the CLI output can hide solid arrows and stack multi-line labels; `render_preview.py` repairs that with `restoreElements`, the same step excalidraw.com runs on load.
7. Export a browser-openable share link with `excalidraw-cli export output.excalidraw`.
8. Return the `.excalidraw` path, the preview image path, and the shareable URL.

## CLI Workflow

Core commands:

```bash
# Build a diagram from a JSON file
excalidraw-cli create elements.json -o diagram.excalidraw

# Generate a local preview PNG with macOS Quick Look
qlmanage -t -s 1600 -o previews diagram.excalidraw

# Or on Linux (headless Playwright CLI; --scale defaults to 2)
python3 scripts/render_preview.py diagram.excalidraw previews/diagram.png

# Or from inline JSON for tiny examples
excalidraw-cli create --json '[...]' -o diagram.excalidraw

# Export to a shareable excalidraw.com URL
excalidraw-cli export diagram.excalidraw

# Inspect the supported element format
excalidraw-cli reference
```

Important constraints:
- `create` expects Excalidraw JSON elements, not Mermaid and not the shorthand DSL above.
- The published CLI does not render local PNG files itself. On macOS, prefer Quick Look via `qlmanage`; elsewhere use `scripts/render_preview.py`.
- `create` writes sparse elements (no `strokeColor`, `lineHeight`, `seed`). excalidraw.com fills them on load; other renderers must run `restoreElements` first.
- If neither preview path works, still return the `.excalidraw` file and the share URL, and say that a local preview image could not be generated in this environment.
- Do not delete generated files unless the user asks or you are working in a temporary scratch location.

## Output Expectations

- The `.excalidraw` file is the source of truth.
- By default, also generate a preview image from the `.excalidraw` file when the environment supports it.
- By default, also export a URL with `excalidraw-cli export` so the user can open the diagram in Excalidraw quickly.
- When multiple diagrams or charts are created, always create and present one combined editable `.excalidraw` canvas containing all charts, with a preview image and share URL.
- If individual diagram files are also created, provide links to every individual artifact, but make the combined canvas the primary deliverable.
- When more than one diagram file is created, also create a simple Markdown index file that links to the combined canvas, all individual diagram files, preview images, and share URLs, then include that index link in the final response.
- In the final response, include:
  - a rendered image preview using Markdown image syntax when a preview file exists
  - a clickable file path to the `.excalidraw` file
  - a clickable file path to the preview image
  - the excalidraw.com share/open URL
- If the user asks for a sequence diagram, Gantt chart, pie chart, or bar chart, read [references/guidance.md](references/guidance.md) and suggest Mermaid instead.
