---
name: tesseract-cli
description: "OCR local images with the Tesseract CLI. Use for screenshot text, error messages in PNG/JPEG, or any OCR request. Run locally; do not upload the image to vision APIs or MCPs. | recommendedRole: deterministic | aliases: ocr, tesseract, screenshot-ocr, read-image-text."
metadata:
  recommendedRole: deterministic
  aliases: ocr, tesseract, screenshot-ocr, read-image-text
  cliDependencies:
    required: [python3, tesseract, convert, identify]
    optional: [qpdf, ocrmypdf, pdftoppm]
---

## Local deterministic first

Run `scripts/ocr.py <image> --json` first. It preprocesses locally, reports confidence, bounds output, and never sends the image to a model.

Norwegian is installed user-locally; use `--lang nor` or `--lang eng+nor`. The wrapper selects `~/.agents/share/tessdata` automatically.

# Tesseract CLI (local OCR)

Read text from a local image file with the installed `tesseract` binary. Do **not** send the image to a vision model, the Read-image tool, browser MCP screenshot-to-model, or any other MCP.

Official CLI: https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html

## When to use

- Screenshot or PNG/JPEG that contains an error message, log line, label, or other readable text
- Quick check of “what does this image say?”
- Any request for OCR / extract text from an image on disk

## When not to use

Skip OCR and inspect the image visually (or tell the user OCR cannot answer) when the task needs:

- Color, spacing, alignment, or pixel-perfect design QA
- Layout judgment that is not recoverable from the words
- Charts/icons/UI state with little or no text

OCR returns **text**, not a visual verdict.

## Default command

Prefer stdout so you can parse immediately. Default language is English. `--psm 6` (single uniform block) is the usual fit for screenshots and error dialogs.

```bash
tesseract "IMAGE" stdout -l eng --psm 6 quiet
```

`quiet` is a Tesseract config file; it suppresses “Estimating resolution” noise. Quote `IMAGE`. Output base `stdout` prints UTF-8 text to stdout (no `.txt` file).

This machine: `tesseract` 5.3.4 at `/usr/bin/tesseract`. Installed traineddata: `eng`, `osd` (`osd` is orientation/script detection, not a reading language). Confirm with `tesseract --version` and `tesseract --list-langs`.

## Options

| Need | Flag |
|------|------|
| Known language | `-l LANG` (ISO 639-3, e.g. `eng`). Combine with `+`: `-l eng+nor`. Only use langs from `--list-langs`. |
| Full page / mixed blocks | `--psm 3` (Tesseract default) |
| Single text line | `--psm 7` |
| Sparse scattered text | `--psm 11` |
| LSTM engine only | `--oem 1` |
| Write a file | `tesseract "IMAGE" /tmp/out -l eng --psm 6 quiet` → `/tmp/out.txt` |

`--oem 0` (legacy) needs tessdata models that are **not** installed here. Leave OEM at default unless LSTM-only is required.

Do not install extra language packs unless the needed lang is missing and the user wants it.

## Failures

| Situation | Action |
|-----------|--------|
| Missing / unreadable file | Report the CLI error (`cannot read input file`). Do not invent text. |
| Empty stdout | Retry once with `--psm 11`, then `--psm 7`. If still empty, say OCR found no text. |
| Garbled / low-confidence | Retry once with a different `--psm` (6 ↔ 3 or 7). Treat remaining junk as unreliable; quote it, do not “fix” it into a confident answer. |
| Wrong language | Re-run with `-l` from `--list-langs`. If the lang is not installed, tell the user — do not fall back to vision. |

Never fall back to uploading the image to the LLM or an MCP after OCR fails.

## Examples

Error screenshot:

```bash
tesseract "/tmp/build-error.png" stdout -l eng --psm 6 quiet
```

Single status line:

```bash
tesseract "./status.png" stdout -l eng --psm 7 quiet
```
