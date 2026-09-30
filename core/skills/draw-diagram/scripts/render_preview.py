#!/usr/bin/env python3
"""Render an .excalidraw file to PNG without macOS Quick Look.

Loads @excalidraw/excalidraw from esm.sh inside headless Playwright CLI, runs
restoreElements (fills the defaults `excalidraw-cli create` omits: stroke color,
line height, seed values), exports SVG, and screenshots it.

Exit codes: 0 PNG written, 1 render failed, 2 playwright-cli missing.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

EXCALIDRAW = "https://esm.sh/@excalidraw/excalidraw@0.17.6"

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><style>body{margin:0;background:#fff}#out svg{display:block}</style></head>
<body><div id="out"></div>
<script type="module">
const scene = __SCENE__;
try {
  window.EXCALIDRAW_ASSET_PATH = "__EXCALIDRAW__/dist/";
  const mod = await import("__EXCALIDRAW__");
  const { exportToSvg, restoreElements } = mod.default || mod;
  const elements = restoreElements(scene.elements, null, { refreshDimensions: true, repairBindings: true });
  const svg = await exportToSvg({
    elements,
    appState: { ...scene.appState, exportBackground: true, viewBackgroundColor: "#ffffff", exportWithDarkMode: false },
    files: scene.files || {},
    exportPadding: __PADDING__,
  });
  for (const dim of ["width", "height"]) svg.setAttribute(dim, String(parseFloat(svg.getAttribute(dim)) * __SCALE__));
  document.getElementById("out").appendChild(svg);
  await document.fonts.ready;
  window.__done = "ok";
} catch (e) {
  window.__done = "error: " + e;
}
</script></body></html>
"""

# page.goto("file://...") is blocked by playwright-cli, so the page is injected with setContent.
# Placeholders must not use %-formatting: scene JSON often contains "%".
SCRIPT = """async page => {
  await page.setContent(__HTML__);
  await page.waitForFunction(() => window.__done, null, { timeout: 60000 });
  const status = await page.evaluate(() => window.__done);
  if (status !== "ok") return status;
  const [w, h] = await page.evaluate(() => {
    const s = document.querySelector("#out svg");
    return [Math.ceil(s.width.baseVal.value), Math.ceil(s.height.baseVal.value)];
  });
  await page.setViewportSize({ width: w, height: h });
  await page.waitForTimeout(1000);
  await page.locator("#out svg").screenshot({ path: __PNG__ });
  return "ok";
}"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scene", type=Path, help=".excalidraw file")
    parser.add_argument("png", type=Path, nargs="?", help="output PNG (default: <scene>.png)")
    parser.add_argument("--scale", type=float, default=2, help="pixel scale (default 2)")
    parser.add_argument("--padding", type=int, default=32, help="export padding in px (default 32)")
    args = parser.parse_args()

    if not shutil.which("playwright-cli"):
        print("playwright-cli not on PATH; install @playwright/cli or return the .excalidraw + share URL only")
        return 2

    scene = args.scene.expanduser().resolve()
    png = (args.png or scene.with_suffix(".png")).expanduser().resolve()
    page_html = (PAGE.replace("__SCENE__", scene.read_text(encoding="utf-8"))
                 .replace("__EXCALIDRAW__", EXCALIDRAW)
                 .replace("__PADDING__", str(args.padding))
                 .replace("__SCALE__", str(args.scale)))
    session = f"-s=excalidraw-render-{os.getpid()}"

    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "render.js"
        script.write_text(
            SCRIPT.replace("__HTML__", json.dumps(page_html)).replace("__PNG__", json.dumps(str(png))),
            encoding="utf-8",
        )
        png.unlink(missing_ok=True)
        opened = subprocess.run(
            ["playwright-cli", session, "open"],
            capture_output=True,
            text=True,
            cwd=tmp,
            check=False,
        )
        if opened.returncode != 0:
            print(opened.stdout[-600:], opened.stderr[-600:])
            return 1
        try:
            result = subprocess.run(
                ["playwright-cli", session, "run-code", f"--filename={script}"],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
            )
        finally:
            subprocess.run(
                ["playwright-cli", session, "close"],
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
            )

    lines = result.stdout.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(("### Result", "### Error")):
            print("\n".join(lines[i:i + 2])[:600])
    if not png.exists():
        return 1
    print(png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
