---
name: export-canvas-html
description: "Export a Cursor `.canvas.tsx` file to a self-contained HTML page using Cursor's official canvas-runtime.esm.js and the live canvas host stylesheet. Use when the user wants to export, share, publish, or dump a Cursor canvas as HTML. | recommendedRole: deterministic | aliases: canvas-html, export-canvas, canvas-to-html."
metadata:
  recommendedRole: deterministic
  aliases: canvas-html, export-canvas, canvas-to-html
  cliDependencies:
    required: [python3, node, npm]
---

# Export Canvas HTML

Cursor canvases (`.canvas.tsx`) import only from `cursor/canvas`, which exists solely inside the IDE. This skill does **not** rewrite the canvas. It esbuild-transforms the file the same way Cursor does, then mounts the default export with the IDE's `canvas-runtime.esm.js` and the live canvas host CSS.

Cursor-only. Other harnesses do not load this skill.

## Workflow

1. Resolve the canvas path.

   Managed location: `~/.cursor/projects/<workspace>/canvases/<name>.canvas.tsx`. Accept an absolute path, or a slug.

   ```bash
   python3 ~/.agents/skills-vendor/cursor/export-canvas-html/scripts/export_canvas.py --list
   ```

2. Run the exporter. Do not recreate the host or substitute a third-party UI kit.

   Example canvas: `~/.cursor/projects/home-leanon-Workspace-Projects-date-fns-cdn/canvases/date-fns-upgrade-consistency.canvas.tsx`

   ```bash
   python3 ~/.agents/skills-vendor/cursor/export-canvas-html/scripts/export_canvas.py \
     ~/.cursor/projects/home-leanon-Workspace-Projects-date-fns-cdn/canvases/date-fns-upgrade-consistency.canvas.tsx \
     --theme light --output /tmp/date-fns-upgrade-consistency.html
   python3 ~/.agents/skills-vendor/cursor/export-canvas-html/scripts/export_canvas.py date-fns-upgrade-consistency --theme light --output /tmp/name.html
   ```

   PATH wrapper: `export-canvas-html` (same argv).

   First run installs `esbuild` into `~/.agents/.cache/export-canvas-html/` (needs network). Later runs reuse that cache. `--force-install` rebuilds it.

   The official runtime is copied from the local Cursor install (`cursor-agent-exec` / `cursor-agent-host` `canvas-runtime.esm.js`).

3. Read the JSON on stdout. On success, return the `html` path and `file://` `url` as clickable links. Keep the file long enough for the user to open it.

   Use `--output` only when the user names a destination. Default is a new temp directory.

   The HTML is a single file (runtime + transformed canvas inlined). A normal browser can open the `file://` URL. Playwright CLI blocks `file:`; if you need a screenshot, serve the parent directory on loopback and open `http://127.0.0.1:<port>/<file>.html`.

## Flags

| Flag | Effect |
|------|--------|
| `--list` | JSON list of `*.canvas.tsx` under `~/.cursor/projects/*/canvases/` |
| `--output PATH` | `.html` file, or a directory (`index.html`) |
| `--theme auto\|light\|dark` | Seeded into `__cursorCanvas.state` as `{kind}` (default `auto`) |
| `--title TEXT` | Document title (default: canvas stem) |
| `--keep-dist` | Also write `canvas-runtime.esm.js` and `app.js` next to the HTML |
| `--force-install` | Re-run `npm install` in the cache |

## Limits

- Component styles are the IDE canvas-runtime. IDE chrome (tabs) is not exported.
- `--theme light` seeds the Cursor Light Modern host tokens (`#ffffff` / `#3b3b3b` / `#005fb8`) that the live canvas server applies. `--theme dark` seeds Cursor dark editor tokens. `--theme auto` follows `prefers-color-scheme` with the runtime defaults.
- `useCanvasAction` is a no-op on the web.
- Canvas must `export default` and import only from `cursor/canvas` (no relative modules, no `fetch()`).

Do not edit the canvas to make the export work unless the user asked for a source change. If esbuild fails, report the exporter error and stop.
