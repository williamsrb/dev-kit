#!/usr/bin/env python3
"""Bounded local OCR with optional preprocessing and confidence reporting."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def tessdata_options(language: str) -> list[str]:
    shared = Path.home() / ".agents" / "share" / "tessdata"
    requested = language.split("+")
    if shared.is_dir() and all((shared / f"{item}.traineddata").is_file() for item in requested):
        return ["--tessdata-dir", str(shared)]
    return []


def preprocess(source: Path, destination: Path) -> tuple[Path, list[str]]:
    convert = shutil.which("convert")
    if not convert:
        return source, ["convert unavailable; used original image"]
    command = [
        convert,
        str(source),
        "-colorspace", "Gray",
        "-auto-level",
        "-sharpen", "0x1",
        str(destination),
    ]
    result = run(command)
    if result.returncode != 0:
        return source, [f"preprocessing failed; used original image: {result.stderr[:300]}"]
    return destination, ["grayscale", "auto-level", "sharpen 0x1"]


def parse_tsv(tsv: str) -> tuple[str, float | None, int]:
    words: list[str] = []
    confidences: list[float] = []
    rows = csv.DictReader(tsv.splitlines(), delimiter="\t")
    last_line: tuple[str, str, str] | None = None
    chunks: list[str] = []
    for row in rows:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        line_key = (row.get("block_num", ""), row.get("par_num", ""), row.get("line_num", ""))
        if last_line is not None and line_key != last_line:
            chunks.append("\n")
        elif chunks and chunks[-1] != "\n":
            chunks.append(" ")
        chunks.append(text)
        words.append(text)
        last_line = line_key
        try:
            confidence = float(row.get("conf", "-1"))
        except ValueError:
            confidence = -1
        if confidence >= 0:
            confidences.append(confidence)
    mean = round(sum(confidences) / len(confidences), 2) if confidences else None
    return "".join(chunks).strip(), mean, len(words)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--lang", default="eng")
    parser.add_argument("--psm", type=int, default=6)
    parser.add_argument("--preprocess", choices=("auto", "none"), default="auto")
    parser.add_argument("--max-chars", type=int, default=16000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source = args.image.expanduser().resolve()
    if not source.is_file():
        print(json.dumps({"status": "error", "error": f"image not found: {source}"}))
        return 2
    tesseract = shutil.which("tesseract")
    if not tesseract:
        print(json.dumps({"status": "error", "error": "tesseract is not installed"}))
        return 2

    with tempfile.TemporaryDirectory(prefix="agent-ocr-") as temp:
        prepared = Path(temp) / "prepared.png"
        if args.preprocess == "auto":
            target, operations = preprocess(source, prepared)
        else:
            target, operations = source, ["none"]
        result = run([tesseract, str(target), "stdout", *tessdata_options(args.lang),
                      "-l", args.lang, "--psm", str(args.psm), "tsv"])
    text, confidence, words = parse_tsv(result.stdout)
    maximum = max(1, min(args.max_chars, 100_000))
    payload = {
        "status": "ok" if result.returncode == 0 else "error",
        "image": str(source),
        "language": args.lang,
        "psm": args.psm,
        "preprocess": operations,
        "confidence_mean": confidence,
        "words": words,
        "text": text[:maximum],
        "truncated": len(text) > maximum,
        "exit_code": result.returncode,
        "stderr": result.stderr[:1000],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(payload["text"])
        print(f"\n[confidence={confidence} words={words}]", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
