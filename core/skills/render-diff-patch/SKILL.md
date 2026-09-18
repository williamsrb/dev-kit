---
name: render-diff-patch
description: "Render a unified diff or patch as side-by-side HTML and a screenshot (diff2html). Use to visualize a git diff, patch file, or code-review diff. | recommendedRole: deterministic."
metadata:
  recommendedRole: deterministic
  cliDependencies:
    required:
      - python3
      - playwright-cli
    optional:
      - git
---

# Render Diff/Patch

Turn unified-diff text into a browser-rendered visual artifact. Use the bundled `template.html` as the rendering base.

## Lazy media

`diff2html-ui.min.js` may be absent from a thin checkout. Do not download it until a render is required. `scripts/prepare_render.py` ensures it automatically; manual ensure:

```bash
python3 scripts/download_media.py
```

`--check` reports presence; `--force` replaces the local file. Source: official `diff2html` npm package (`rtfpessoa/diff2html`, pinned `3.4.56`), member `bundles/js/diff2html-ui.min.js`.

## Workflow

1. Resolve the exact diff input.

   - Read the requested patch file, use the diff supplied by the user, or obtain repository changes with a read-only command such as `git diff` or `git diff --cached`.
   - Do not summarize, normalize, or rewrite the patch.
   - If the input is empty, report that and stop.

2. Run the bundled preparation script. Pass a patch path, or pass `-` and provide the diff on standard input:

   ```bash
   python3 scripts/prepare_render.py /absolute/path/to/change.patch
   git diff | python3 scripts/prepare_render.py -
   ```

   Resolve `scripts/prepare_render.py` relative to this skill directory when the current working directory differs. Use `--output-dir /absolute/path` only when the user requests a specific destination. Read the JSON result for the generated `html` path and `file://` `url`.

   The script performs the fragile work deterministically: it lazily ensures `diff2html-ui.min.js` when missing, copies the bundled assets, uses `template.html` unchanged as the base, replaces its single `<DIFF STRING GOES HERE>` marker, and safely escapes the diff for the JavaScript template literal and surrounding HTML. Do not recreate this logic manually unless the script is unavailable.

3. Open the generated URL with Playwright CLI in a named headless session. Set local-file access only on the launch command:

   ```bash
   PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS=true playwright-cli -s=render-diff-patch open file:///absolute/path/to/render.html
   playwright-cli -s=render-diff-patch resize 1600 1000
   ```

   Use a distinct session name if `render-diff-patch` is already active. Enable unrestricted local-file access only for this trusted generated render and its bundled sibling assets. Do not browse other content in that session.

   If local-file loading fails, serve the generated directory from a loopback-only static HTTP server and open `http://127.0.0.1:<port>/render.html`.

4. Verify the render before capture.

   - Confirm there are no page or console errors. Ignore only an automatic `/favicon.ico` 404.
   - Confirm `#myDiffElement .d2h-wrapper` and at least one `.d2h-file-wrapper` exist.
   - Confirm the rendered filenames and changed lines match the source patch.
   - Capture a readable screenshot after the checks pass, then close the browser session.

## Output

Return clickable links to the screenshot and generated HTML, and identify the diff source. Keep temporary artifacts long enough for the user to open them. Do not modify the bundled template or assets during rendering.
