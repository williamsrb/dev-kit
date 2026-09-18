#!/usr/bin/env python3
"""Bounded local measurement of blank/whitespace pixel ratio in a screenshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def parse_color(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) != 6:
        raise ValueError(f"invalid hex color: {value!r}")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def detect_background(rgb: np.ndarray) -> tuple[int, int, int]:
    h, w = rgb.shape[:2]
    corners = np.array([rgb[0, 0], rgb[0, w - 1], rgb[h - 1, 0], rgb[h - 1, w - 1]])
    colors, counts = np.unique(corners, axis=0, return_counts=True)
    return tuple(int(c) for c in colors[np.argmax(counts)])  # type: ignore[return-value]


def mode_color(rgb: np.ndarray) -> tuple[int, int, int]:
    flat = rgb.reshape(-1, 3)
    colors, counts = np.unique(flat, axis=0, return_counts=True)
    return tuple(int(c) for c in colors[np.argmax(counts)])  # type: ignore[return-value]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the fraction of a screenshot that is blank/background. Reports an "
            "overall blank-pixel ratio and a border-trim ratio (content bounding box vs "
            "full canvas), plus an optional NxN grid breakdown."
        ),
        epilog=(
            "Example:\n"
            "  blank_space.py screenshot.png --background auto --tolerance 12 --grid 4"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--background",
        default="auto",
        help="'auto' (sample the four corners), 'mode' (most frequent color in the "
        "whole image), or an explicit #RRGGBB / RRGGBB hex color.",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=12,
        help="Max per-channel distance (0-255) from the background color still counted as blank.",
    )
    parser.add_argument(
        "--grid",
        type=int,
        default=0,
        help="Optional NxN grid; reports blank ratio per cell to localize whitespace.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    source = args.image.expanduser().resolve()
    if not source.is_file():
        print(json.dumps({"status": "error", "error": f"image not found: {source}"}))
        return 2
    if not 0 <= args.tolerance <= 255:
        print(json.dumps({"status": "error", "error": "--tolerance must be between 0 and 255"}))
        return 2
    if args.grid < 0:
        print(json.dumps({"status": "error", "error": "--grid must be non-negative"}))
        return 2

    try:
        image = Image.open(source)
        image.load()
    except Exception as exc:  # noqa: BLE001 - surface any decode failure as bounded JSON
        print(json.dumps({"status": "error", "error": f"cannot decode image: {exc}"}))
        return 2

    rgba = image.convert("RGBA")
    rgb = np.array(rgba.convert("RGB"))
    alpha = np.array(rgba.getchannel("A"))
    h, w = rgb.shape[:2]
    total_pixels = h * w

    try:
        if args.background == "auto":
            bg, bg_source = detect_background(rgb), "corner-sample"
        elif args.background == "mode":
            bg, bg_source = mode_color(rgb), "full-image-mode"
        else:
            bg, bg_source = parse_color(args.background), "explicit"
    except ValueError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2

    diff = np.abs(rgb.astype(np.int16) - np.array(bg, dtype=np.int16))
    within_tolerance = np.all(diff <= args.tolerance, axis=-1)
    blank_mask = within_tolerance | (alpha == 0)
    blank_pixels = int(blank_mask.sum())
    blank_ratio = blank_pixels / total_pixels if total_pixels else 0.0

    non_blank_rows = np.where(~blank_mask.all(axis=1))[0]
    non_blank_cols = np.where(~blank_mask.all(axis=0))[0]
    if non_blank_rows.size and non_blank_cols.size:
        top, bottom = int(non_blank_rows[0]), int(non_blank_rows[-1])
        left, right = int(non_blank_cols[0]), int(non_blank_cols[-1])
        content_bbox = {"left": left, "top": top, "right": right + 1, "bottom": bottom + 1}
        content_area = (right + 1 - left) * (bottom + 1 - top)
        border_blank_ratio = 1 - (content_area / total_pixels) if total_pixels else 0.0
    else:
        content_bbox = None
        border_blank_ratio = 1.0

    payload: dict[str, object] = {
        "status": "ok",
        "image": {"path": str(source), "width": w, "height": h},
        "background": {"rgb": list(bg), "source": bg_source, "tolerance": args.tolerance},
        "total_pixels": total_pixels,
        "blank_pixels": blank_pixels,
        "blank_ratio": round(blank_ratio, 6),
        "blank_percent": round(blank_ratio * 100, 3),
        "content_bbox": content_bbox,
        "border_blank_ratio": round(border_blank_ratio, 6),
        "border_blank_percent": round(border_blank_ratio * 100, 3),
    }

    if args.grid:
        n = args.grid
        grid_rows = []
        for gy in range(n):
            y0 = int(gy * h / n)
            y1 = int((gy + 1) * h / n) if gy < n - 1 else h
            row = []
            for gx in range(n):
                x0 = int(gx * w / n)
                x1 = int((gx + 1) * w / n) if gx < n - 1 else w
                cell = blank_mask[y0:y1, x0:x1]
                row.append(round(float(cell.mean()), 4) if cell.size else None)
            grid_rows.append(row)
        payload["grid"] = {"size": n, "blank_ratio_per_cell": grid_rows}

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
