#!/usr/bin/env python3
"""Extract a deterministic N-color palette from a local image."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from palette_lib import (
    load_rgb_and_alpha,
    opaque_pixels,
    srgb_to_lab,
    to_hex,
)

METHODS = {
    "mediancut": Image.Quantize.MEDIANCUT,
    "maxcoverage": Image.Quantize.MAXCOVERAGE,
    "fastoctree": Image.Quantize.FASTOCTREE,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract an N-color palette from an image. Deterministic: the same "
            "image, color count, and method always yield the same palette."
        ),
        epilog=(
            "Example:\n"
            "  palette_create.py brand.png --colors 8 "
            "--out palette.json --swatch palette.png"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("--colors", type=int, default=8, help="Palette size (2-256).")
    parser.add_argument(
        "--method",
        default="mediancut",
        choices=sorted(METHODS),
        help="Quantizer. 'mediancut' balances the color cube; 'maxcoverage' favors "
        "spatially dominant colors; 'fastoctree' is coarser but fastest.",
    )
    parser.add_argument("--out", type=Path, help="Write the palette JSON here.")
    parser.add_argument("--swatch", type=Path, help="Write a PNG swatch strip here.")
    parser.add_argument(
        "--swatch-size",
        default="400x50",
        help="Swatch strip dimensions as WIDTHxHEIGHT (default 400x50).",
    )
    return parser


def write_swatch(colors: np.ndarray, path: Path, size: str) -> None:
    try:
        width_text, height_text = size.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except ValueError as exc:
        raise ValueError(f"invalid --swatch-size {size!r}, expected WIDTHxHEIGHT") from exc
    if width < colors.shape[0] or height < 1:
        raise ValueError(f"--swatch-size {size!r} too small for {colors.shape[0]} colors")
    count = colors.shape[0]
    # Nearest-neighbour band fill keeps every swatch pixel an exact palette color,
    # so the strip can be read back losslessly as a palette.
    columns = (np.arange(width) * count // width).clip(0, count - 1)
    strip = np.repeat(colors[columns][None, :, :], height, axis=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(strip.astype(np.uint8), mode="RGB").save(path)


def main() -> int:
    args = build_parser().parse_args()

    source = args.image.expanduser().resolve()
    if not source.is_file():
        print(json.dumps({"status": "error", "error": f"image not found: {source}"}))
        return 2
    if not 2 <= args.colors <= 256:
        print(json.dumps({"status": "error", "error": "--colors must be between 2 and 256"}))
        return 2

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

    # Quantize the opaque pixels only, reshaped into a column. Median cut works on
    # the color histogram, so dropping the 2D layout does not change the palette
    # while it does keep transparent regions from inventing a black entry.
    column = Image.fromarray(pixels.reshape(-1, 1, 3), mode="RGB")
    try:
        quantized = column.quantize(colors=args.colors, method=METHODS[args.method])
    except Exception as exc:  # noqa: BLE001 - Pillow raises for odd mode/size combos
        print(json.dumps({"status": "error", "error": f"quantization failed: {exc}"}))
        return 2

    raw_palette = np.array(quantized.getpalette(), dtype=np.uint8).reshape(-1, 3)
    assignments = np.array(quantized, dtype=np.int64).reshape(-1)
    counts = np.bincount(assignments, minlength=raw_palette.shape[0])

    used = np.nonzero(counts)[0]
    order = used[np.argsort(-counts[used], kind="stable")]
    colors = raw_palette[order]
    color_counts = counts[order]
    total = int(color_counts.sum())
    lab = srgb_to_lab(colors)

    entries = [
        {
            "index": position,
            "hex": to_hex(colors[position]),
            "rgb": [int(channel) for channel in colors[position]],
            "lab": [round(float(value), 3) for value in lab[position]],
            "pixels": int(color_counts[position]),
            "pixel_share": round(float(color_counts[position]) / total, 6),
        }
        for position in range(colors.shape[0])
    ]

    payload: dict[str, object] = {
        "status": "ok",
        "source": {
            "path": str(source),
            "width": width,
            "height": height,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "opaque_pixels": total,
        },
        "method": args.method,
        "requested_colors": args.colors,
        "colors": entries,
        "hex": [entry["hex"] for entry in entries],
    }

    if args.out:
        out = args.out.expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["palette_file"] = str(out)

    if args.swatch:
        swatch = args.swatch.expanduser().resolve()
        try:
            write_swatch(colors, swatch, args.swatch_size)
        except ValueError as exc:
            print(json.dumps({"status": "error", "error": str(exc)}))
            return 2
        payload["swatch"] = str(swatch)

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
