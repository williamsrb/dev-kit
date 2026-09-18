#!/usr/bin/env python3
"""Measure how far a local image sits from a reference palette, as a 0..1 score."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from palette_lib import (
    SPACE_MAX,
    SPACE_UNIT,
    load_palette,
    load_rgb_and_alpha,
    nearest,
    opaque_pixels,
    srgb_to_lab,
    to_hex,
    unique_colors,
    weighted_percentiles,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Score an image against a palette: for every pixel take the distance to "
            "the nearest palette color, average over the image, and normalize to "
            "0..1. Deterministic — no sampling, no model."
        ),
        epilog=(
            "Example:\n"
            "  palette_distance.py photo.png palette.json --space lab --tolerance 10"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "palette",
        help="Palette JSON from palette_create.py, a swatch image, or a hex list "
        "like '#1a2b3c,#ffffff'.",
    )
    parser.add_argument(
        "--space",
        default="lab",
        choices=("lab", "rgb"),
        help="Distance space for the primary score. 'lab' is perceptual (CIE76 dE) "
        "and is what you should threshold on; 'rgb' is plain sRGB Euclidean.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Raw distance in the selected space still counted as on-palette "
        "(default 10; in Lab ~2.3 is one just-noticeable difference).",
    )
    parser.add_argument(
        "--percentiles",
        default="50,90,95,99",
        help="Comma-separated per-pixel distance percentiles to report.",
    )
    parser.add_argument(
        "--top-offenders",
        type=int,
        default=5,
        help="How many worst off-palette colors to list (0 disables).",
    )
    parser.add_argument(
        "--palette-max-colors",
        type=int,
        default=256,
        help="Reject a palette image with more distinct colors than this.",
    )
    return parser


def score(sample: np.ndarray, counts: np.ndarray, palette: np.ndarray, space: str):
    """Nearest-palette distances for unique colors, in the requested space."""
    if space == "lab":
        sample_points, palette_points = srgb_to_lab(sample), srgb_to_lab(palette)
    else:
        sample_points = sample.astype(np.float64)
        palette_points = palette.astype(np.float64)
    distances, indices = nearest(sample_points, palette_points)
    total = float(counts.sum())
    mean_raw = float((distances * counts).sum() / total) if total else 0.0
    return distances, indices, mean_raw


def main() -> int:
    args = build_parser().parse_args()

    source = args.image.expanduser().resolve()
    if not source.is_file():
        print(json.dumps({"status": "error", "error": f"image not found: {source}"}))
        return 2
    if args.tolerance < 0:
        print(json.dumps({"status": "error", "error": "--tolerance must be non-negative"}))
        return 2
    try:
        percentiles = [float(part) for part in args.percentiles.split(",") if part.strip()]
    except ValueError:
        print(json.dumps({"status": "error", "error": "--percentiles must be comma-separated numbers"}))
        return 2
    if any(not 0 <= value <= 100 for value in percentiles):
        print(json.dumps({"status": "error", "error": "--percentiles must be between 0 and 100"}))
        return 2

    try:
        palette_info = load_palette(args.palette, max_colors=args.palette_max_colors)
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": f"cannot load palette: {exc}"}))
        return 2
    palette = palette_info["colors"]

    try:
        rgb, alpha = load_rgb_and_alpha(source)
    except Exception as exc:  # noqa: BLE001 - surface any decode failure as bounded JSON
        print(json.dumps({"status": "error", "error": f"cannot decode image: {exc}"}))
        return 2

    height, width = rgb.shape[:2]
    pixels = opaque_pixels(rgb, alpha)
    if pixels.size == 0:
        print(json.dumps({"status": "error", "error": "image is fully transparent"}))
        return 2

    sample, counts = unique_colors(pixels)
    total = int(counts.sum())

    distances, indices, mean_raw = score(sample, counts, palette, args.space)
    normalizer = SPACE_MAX[args.space]

    # The other space is reported too, so a batch sweep can be thresholded either
    # way without re-running every image.
    other = "rgb" if args.space == "lab" else "lab"
    _, _, other_mean_raw = score(sample, counts, palette, other)

    raw_percentiles = weighted_percentiles(distances, counts, percentiles)
    raw_percentiles["max"] = float(distances.max())

    within = float(counts[distances <= args.tolerance].sum()) / total if total else 0.0

    usage = np.bincount(indices, weights=counts.astype(np.float64), minlength=palette.shape[0])
    palette_usage = [
        {
            "index": position,
            "hex": to_hex(palette[position]),
            "pixel_share": round(float(usage[position]) / total, 6) if total else 0.0,
        }
        for position in range(palette.shape[0])
    ]

    offenders = []
    if args.top_offenders > 0:
        # Rank by total deviation contributed, not by distance alone — a single
        # extreme stray pixel matters far less than a large mildly-off region.
        contribution = distances * counts
        ranked = np.argsort(-contribution, kind="stable")[: args.top_offenders]
        offenders = [
            {
                "hex": to_hex(sample[position]),
                "rgb": [int(channel) for channel in sample[position]],
                "pixels": int(counts[position]),
                "pixel_share": round(float(counts[position]) / total, 6),
                "distance_raw": round(float(distances[position]), 4),
                "distance": round(float(distances[position]) / normalizer, 6),
                "nearest_palette_hex": to_hex(palette[int(indices[position])]),
            }
            for position in ranked
            if contribution[position] > 0
        ]

    payload = {
        "status": "ok",
        "image": {
            "path": str(source),
            "width": width,
            "height": height,
            "counted_pixels": total,
            "unique_colors": int(sample.shape[0]),
        },
        "palette": {
            "source": palette_info["source"],
            "path": palette_info["path"],
            "size": int(palette.shape[0]),
            "hex": [to_hex(color) for color in palette],
        },
        "space": args.space,
        "unit": SPACE_UNIT[args.space],
        "normalizer": round(normalizer, 4),
        "distance": round(mean_raw / normalizer, 6),
        "distance_raw": round(mean_raw, 4),
        f"distance_{other}": round(other_mean_raw / SPACE_MAX[other], 6),
        "percentiles": {
            key: round(value / normalizer, 6) for key, value in raw_percentiles.items()
        },
        "percentiles_raw": {key: round(value, 4) for key, value in raw_percentiles.items()},
        "coverage": {
            "tolerance_raw": args.tolerance,
            "within_tolerance_ratio": round(within, 6),
            "within_tolerance_percent": round(within * 100, 3),
        },
        "palette_usage": palette_usage,
        "unused_palette_colors": [
            entry["hex"] for entry in palette_usage if entry["pixel_share"] == 0.0
        ],
        "top_offenders": offenders,
    }

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
