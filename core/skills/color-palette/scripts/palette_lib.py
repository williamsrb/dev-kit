#!/usr/bin/env python3
"""Shared deterministic color math for palette extraction and palette distance.

sRGB -> CIELAB (D65) conversion, palette loading from JSON/image/hex-list, and
weighted nearest-color statistics. Same input always produces the same numbers.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

HEX_RE = re.compile(r"^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# Largest possible Euclidean sRGB distance: black to white across all channels.
MAX_RGB_DISTANCE = float(np.sqrt(3.0) * 255.0)

# sRGB D65 -> XYZ matrix (IEC 61966-2-1).
_RGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)
_D65_WHITE = np.array([0.95047, 1.00000, 1.08883], dtype=np.float64)
_LAB_EPS = (6.0 / 29.0) ** 3
_LAB_KAPPA = (1.0 / 3.0) * (29.0 / 6.0) ** 2


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert an (N, 3) uint8/int sRGB array to (N, 3) float CIELAB (D65)."""
    values = np.asarray(rgb, dtype=np.float64).reshape(-1, 3) / 255.0
    linear = np.where(
        values <= 0.04045,
        values / 12.92,
        ((values + 0.055) / 1.055) ** 2.4,
    )
    xyz = linear @ _RGB_TO_XYZ.T / _D65_WHITE
    f = np.where(xyz > _LAB_EPS, np.cbrt(xyz), _LAB_KAPPA * xyz + 4.0 / 29.0)
    lab = np.empty_like(f)
    lab[:, 0] = 116.0 * f[:, 1] - 16.0
    lab[:, 1] = 500.0 * (f[:, 0] - f[:, 1])
    lab[:, 2] = 200.0 * (f[:, 1] - f[:, 2])
    return lab


def _max_lab_distance() -> float:
    """Largest CIE76 dE between any two sRGB cube corners — the gamut extremes."""
    corners = np.array(
        [[r, g, b] for r in (0, 255) for g in (0, 255) for b in (0, 255)],
        dtype=np.uint8,
    )
    lab = srgb_to_lab(corners)
    deltas = np.sqrt(((lab[:, None, :] - lab[None, :, :]) ** 2).sum(axis=2))
    return float(deltas.max())


# ~258.68 — normalizing by this keeps the reported score inside 0..1.
MAX_LAB_DISTANCE = _max_lab_distance()

SPACE_MAX = {"rgb": MAX_RGB_DISTANCE, "lab": MAX_LAB_DISTANCE}
SPACE_UNIT = {"rgb": "sRGB Euclidean", "lab": "CIE76 dE"}


def parse_hex(value: str) -> tuple[int, int, int]:
    """Parse '#rgb', '#rrggbb', or the same without '#' into an (r, g, b) tuple."""
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(char * 2 for char in text)
    if len(text) != 6 or not HEX_RE.match(text):
        raise ValueError(f"invalid hex color: {value!r}")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def to_hex(rgb: Iterable[int]) -> str:
    r, g, b = (int(channel) for channel in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def load_rgb_and_alpha(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load an image as an (H, W, 3) uint8 RGB array plus an (H, W) alpha array."""
    image = Image.open(path)
    image.load()
    rgba = image.convert("RGBA")
    return np.array(rgba.convert("RGB")), np.array(rgba.getchannel("A"))


def opaque_pixels(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Flatten to (N, 3), dropping fully transparent pixels."""
    flat = rgb.reshape(-1, 3)
    mask = alpha.reshape(-1) > 0
    return flat[mask]


def unique_colors(pixels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (unique (M, 3) uint8 colors, (M,) int64 counts).

    Packs RGB into one int32 before np.unique — far cheaper than a row-wise
    unique on multi-megapixel images, and exact rather than sampled.
    """
    flat = pixels.reshape(-1, 3).astype(np.uint32)
    packed = (flat[:, 0] << 16) | (flat[:, 1] << 8) | flat[:, 2]
    values, counts = np.unique(packed, return_counts=True)
    colors = np.stack(
        [(values >> 16) & 0xFF, (values >> 8) & 0xFF, values & 0xFF], axis=1
    ).astype(np.uint8)
    return colors, counts


def nearest(sample: np.ndarray, palette: np.ndarray, chunk: int = 262144) -> tuple[np.ndarray, np.ndarray]:
    """Nearest palette entry per sample row. Returns (distances, palette indices).

    Chunked so a photo with millions of unique colors cannot blow up memory.
    """
    total = sample.shape[0]
    distances = np.empty(total, dtype=np.float64)
    indices = np.empty(total, dtype=np.int32)
    for start in range(0, total, chunk):
        block = sample[start : start + chunk]
        deltas = np.sqrt(((block[:, None, :] - palette[None, :, :]) ** 2).sum(axis=2))
        distances[start : start + chunk] = deltas.min(axis=1)
        indices[start : start + chunk] = deltas.argmin(axis=1)
    return distances, indices


def weighted_percentiles(
    values: np.ndarray, weights: np.ndarray, percentiles: Iterable[float]
) -> dict[str, float]:
    """Percentiles over per-pixel values represented as (unique value, count) pairs."""
    order = np.argsort(values, kind="stable")
    ordered_values = values[order]
    cumulative = np.cumsum(weights[order].astype(np.float64))
    total = float(cumulative[-1]) if cumulative.size else 0.0
    result: dict[str, float] = {}
    for percentile in percentiles:
        if total <= 0:
            result[f"p{percentile:g}"] = 0.0
            continue
        index = int(np.searchsorted(cumulative, percentile / 100.0 * total, side="left"))
        result[f"p{percentile:g}"] = float(ordered_values[min(index, ordered_values.size - 1)])
    return result


def load_palette(spec: str, *, max_colors: int = 256) -> dict[str, Any]:
    """Load a palette from a JSON file, a swatch image, or a hex-color list.

    Accepts the JSON written by palette_create.py, any image whose distinct
    colors *are* the palette (including an ImageMagick `-unique-colors` strip),
    or a literal string like '#1a2b3c,#ffffff'.
    """
    candidate = Path(spec).expanduser()
    if candidate.is_file():
        if candidate.suffix.lower() == ".json":
            return _palette_from_json(candidate)
        return _palette_from_image(candidate, max_colors=max_colors)

    entries = [part for part in re.split(r"[,\s]+", spec.strip()) if part]
    if not entries:
        raise ValueError("empty palette specification")
    for entry in entries:
        if not HEX_RE.match(entry):
            raise ValueError(
                f"palette not found as a file and not a hex color list: {spec!r}"
            )
    colors = np.array([parse_hex(entry) for entry in entries], dtype=np.uint8)
    return {"colors": colors, "source": "hex-list", "path": None, "weights": None}


def _palette_from_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("colors")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"palette JSON has no 'colors' array: {path}")
    colors = []
    weights = []
    for entry in entries:
        if isinstance(entry, str):
            colors.append(parse_hex(entry))
            weights.append(None)
        elif isinstance(entry, dict):
            if "rgb" in entry:
                colors.append(tuple(int(channel) for channel in entry["rgb"]))
            elif "hex" in entry:
                colors.append(parse_hex(entry["hex"]))
            else:
                raise ValueError(f"palette entry lacks 'rgb' and 'hex': {entry!r}")
            weights.append(entry.get("pixel_share"))
        else:
            # ValueError, not TypeError: this is malformed file data reported back to
            # the caller as bounded JSON, not a programming type error.
            raise ValueError(f"unsupported palette entry: {entry!r}")  # noqa: TRY004
    return {
        "colors": np.array(colors, dtype=np.uint8),
        "source": "json",
        "path": str(path.resolve()),
        "weights": weights if all(weight is not None for weight in weights) else None,
    }


def _palette_from_image(path: Path, *, max_colors: int) -> dict[str, Any]:
    rgb, alpha = load_rgb_and_alpha(path)
    colors, counts = unique_colors(opaque_pixels(rgb, alpha))
    if colors.shape[0] > max_colors:
        raise ValueError(
            f"palette image has {colors.shape[0]} distinct colors (limit {max_colors}); "
            "it looks like a photo rather than a swatch — quantize it first with "
            "'agentctl image palette-create', or raise --palette-max-colors"
        )
    order = np.argsort(-counts, kind="stable")
    return {
        "colors": colors[order],
        "source": "image",
        "path": str(path.resolve()),
        "weights": None,
    }
