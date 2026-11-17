#!/usr/bin/env python3
"""Flatten evidence PNGs and stamp WIDTH x HEIGHT at bottom-left (8pt).

Replaces the raw ImageMagick mogrify one-liner in plan-task-evidence Execution.
Idempotent: already-stamped files are skipped (PNG comment, or OCR of the
bottom-left label matching current pixels).

Usage:
    annotate-evidence-resolution.py PATH [PATH ...]
    annotate-evidence-resolution.py ~/.agents/prds/PROJ-345/evidence
    annotate-evidence-resolution.py --no-flatten 01-foo.png
    annotate-evidence-resolution.py --check 01-foo.png
    annotate-evidence-resolution.py --json --check 01-foo.png

A directory argument stamps ``NN-*.png`` in that folder (and in ``before/`` /
``after/`` if present). Sidecars such as ``*.viewport.png`` are skipped unless
named explicitly. Jira-bound shots that are not ``NN-*.png`` must be named as
files. Prefer ``agentctl image stamp`` from agent flows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

STEP_PNG = re.compile(r"^\d{2}-.+\.png$", re.IGNORECASE)
LABEL_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+)", re.IGNORECASE)
STAMP_COMMENT_RE = re.compile(r"resolution-stamp:(\d+)x(\d+)")
FONT = "DejaVu-Sans"
POINTSIZE = "8"
OFFSET = "+6+4"
FILL = "#222222"
UNDERCOLOR = "#ffffffee"
BORDER = "#dddedd"
CROP = "240x32+0+0"


def require_tools() -> None:
    missing = [name for name in ("mogrify", "identify", "convert") if shutil.which(name) is None]
    if missing:
        raise SystemExit(f"error: missing ImageMagick tool(s): {', '.join(missing)}")


def collect_pngs(raw: list[str]) -> list[Path]:
    found: list[Path] = []
    for item in raw:
        path = Path(item).expanduser().resolve()
        if path.is_dir():
            found.extend(sorted(p for p in path.glob("*.png") if STEP_PNG.match(p.name)))
            for sub in ("before", "after"):
                child = path / sub
                if child.is_dir():
                    found.extend(
                        sorted(p for p in child.glob("*.png") if STEP_PNG.match(p.name))
                    )
        elif path.is_file() and path.suffix.lower() == ".png":
            found.append(path)
        else:
            raise SystemExit(f"error: not a PNG or evidence directory: {item}")
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in found:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    if not unique:
        raise SystemExit("error: no evidence PNGs to stamp")
    return unique


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise SystemExit(f"error: {' '.join(cmd[:3])} … failed: {err}")
    return proc.stdout


def flatten(path: Path) -> None:
    run(
        [
            "mogrify",
            "-background",
            "white",
            "-alpha",
            "remove",
            "-bordercolor",
            BORDER,
            "-border",
            "2x2",
            str(path),
        ]
    )


def dimensions(path: Path) -> tuple[int, int]:
    raw = run(["identify", "-format", "%w %h", str(path)]).strip()
    parts = raw.split()
    if len(parts) != 2:
        raise SystemExit(f"error: identify failed on {path}: {raw!r}")
    return int(parts[0]), int(parts[1])


def stamp_comment(width: int, height: int) -> str:
    return f"resolution-stamp:{width}x{height}"


def read_comment(path: Path) -> str:
    return run(["identify", "-format", "%c", str(path)]).strip()


def write_comment(path: Path, width: int, height: int) -> None:
    run(["mogrify", "-set", "comment", stamp_comment(width, height), str(path)])


def comment_matches(path: Path, width: int, height: int) -> bool:
    match = STAMP_COMMENT_RE.search(read_comment(path))
    return bool(match) and int(match.group(1)) == width and int(match.group(2)) == height


def ocr_label(path: Path) -> tuple[int, int] | None:
    tesseract = shutil.which("tesseract")
    if tesseract is None:
        return None
    fd, crop = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    crop_path = Path(crop)
    try:
        run(
            [
                "convert",
                str(path),
                "-gravity",
                "southwest",
                "-crop",
                CROP,
                "+repage",
                "-resize",
                "400%",
                str(crop_path),
            ]
        )
        proc = subprocess.run(
            [tesseract, str(crop_path), "stdout", "--psm", "7"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None
        match = LABEL_RE.search(proc.stdout or "")
        if not match:
            return None
        return int(match.group(1)), int(match.group(2))
    finally:
        crop_path.unlink(missing_ok=True)


def already_stamped(path: Path, width: int, height: int) -> bool:
    if comment_matches(path, width, height):
        return True
    label = ocr_label(path)
    return label == (width, height)


def stamp(path: Path, width: int, height: int, font: str | None) -> None:
    label = f"{width} x {height}"
    cmd = [
        "mogrify",
        "-gravity",
        "southwest",
        "-pointsize",
        POINTSIZE,
        "-fill",
        FILL,
        "-undercolor",
        UNDERCOLOR,
        "-annotate",
        OFFSET,
        label,
        str(path),
    ]
    if font:
        cmd[1:1] = ["-font", font]
    run(cmd)
    write_comment(path, width, height)


def pick_font() -> str | None:
    listing = run(["convert", "-list", "font"])
    return FONT if FONT in listing else None


def emit(rows: list[dict[str, object]], *, as_json: bool, check: bool) -> None:
    if as_json:
        missing = [row["path"] for row in rows if row.get("action") == "missing"]
        print(
            json.dumps(
                {"files": rows, "ok": [row["path"] for row in rows if row.get("action") != "missing"], "missing": missing},
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    for row in rows:
        action = str(row["action"])
        name = str(row["name"])
        size = f"{row['width']} x {row['height']}"
        if check:
            print(f"{action}\t{name}\t{size}")
        elif action == "skipped":
            print(f"{name}\t{size}\tskipped")
        else:
            print(f"{name}\t{size}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        help="PNG files, or an evidence directory (stamps NN-*.png)",
    )
    parser.add_argument(
        "--no-flatten",
        action="store_true",
        help="stamp only; skip alpha flatten and 2px border",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if any PNG is missing the matching WIDTH x HEIGHT stamp",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print a JSON object instead of TSV lines",
    )
    args = parser.parse_args(argv)
    require_tools()
    pngs = collect_pngs(args.paths)
    font = None if args.check else pick_font()
    rows: list[dict[str, object]] = []
    missing = 0
    for path in pngs:
        width, height = dimensions(path)
        if already_stamped(path, width, height):
            if not args.check and not comment_matches(path, width, height):
                write_comment(path, width, height)
            rows.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "width": width,
                    "height": height,
                    "action": "ok" if args.check else "skipped",
                }
            )
            continue
        if args.check:
            missing += 1
            rows.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "width": width,
                    "height": height,
                    "action": "missing",
                }
            )
            continue
        if not args.no_flatten:
            flatten(path)
        width, height = dimensions(path)
        stamp(path, width, height, font)
        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "width": width,
                "height": height,
                "action": "stamped",
            }
        )
    emit(rows, as_json=args.json, check=args.check)
    if args.check and missing:
        print(
            f"error: {missing}/{len(pngs)} PNG(s) missing WIDTH x HEIGHT stamp",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
