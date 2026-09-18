#!/usr/bin/env python3
"""Compare two aligned images with image-diff and emit bounded JSON metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:2000]
        raise RuntimeError(f"{' '.join(command[:2])} failed: {detail}")
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path: Path) -> dict[str, object]:
    output = run(["identify", "-ping", "-format", "%w %h %[opaque]\\n", str(path)])
    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) != 1:
        raise ValueError(f"expected one static image frame, found {len(lines)}: {path}")
    width_text, height_text, opaque_text = lines[0].split()
    return {
        "path": str(path),
        "width": int(width_text),
        "height": int(height_text),
        "opaque": opaque_text.lower() == "true",
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def output_path(value: str, inputs: set[Path]) -> Path:
    path = Path(value).expanduser().resolve()
    if path.suffix.lower() != ".png":
        raise ValueError(f"output must be a lossless .png file: {path}")
    if path in inputs:
        raise ValueError(f"output must not overwrite an input image: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Compare two same-size static images with image-diff. Generates a visible "
            "difference PNG and emits exact changed-pixel metrics as JSON."
        ),
        epilog=(
            "Example:\n"
            "  compare.py before.png after.png --output diff.png "
            "--mask-output diff-mask.png --max-diff-ratio 0.001"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def main() -> int:
    parser = build_parser()
    parser.add_argument("first", help="Baseline, expected, backend, or prototype image.")
    parser.add_argument("second", help="Candidate, actual, frontend, or final image.")
    parser.add_argument("--output", required=True, help="Visible magnitude-difference PNG.")
    parser.add_argument("--mask-output", help="Optional black/white changed-pixel mask PNG.")
    parser.add_argument("--max-diff-pixels", type=int, help="Maximum allowed changed pixels.")
    parser.add_argument(
        "--max-diff-ratio", type=float, help="Maximum allowed changed-pixel ratio from 0 to 1."
    )
    args = parser.parse_args()

    try:
        first = Path(args.first).expanduser().resolve(strict=True)
        second = Path(args.second).expanduser().resolve(strict=True)
        if not first.is_file() or not second.is_file():
            raise ValueError("both inputs must be regular files")
        inputs = {first, second}
        output = output_path(args.output, inputs)
        mask_output = output_path(args.mask_output, inputs) if args.mask_output else None
        if mask_output == output:
            raise ValueError("--output and --mask-output must be different files")
        if args.max_diff_pixels is not None and args.max_diff_pixels < 0:
            raise ValueError("--max-diff-pixels must be non-negative")
        if args.max_diff_ratio is not None and not 0 <= args.max_diff_ratio <= 1:
            raise ValueError("--max-diff-ratio must be between 0 and 1")

        first_info = inspect_image(first)
        second_info = inspect_image(second)
        first_size = (first_info["width"], first_info["height"])
        second_size = (second_info["width"], second_info["height"])
        if first_size != second_size:
            emit(
                {
                    "status": "dimension-mismatch",
                    "first": first_info,
                    "second": second_info,
                    "message": "Align capture dimensions without resampling, then compare again.",
                }
            )
            return 2

        different_pixels = int(run(["image-diff", "count", str(first), str(second)]))
        total_pixels = int(first_info["width"]) * int(first_info["height"])
        ratio = different_pixels / total_pixels if total_pixels else 0.0

        with tempfile.TemporaryDirectory(prefix=".image-diff-", dir=output.parent) as temp:
            raw_diff = Path(temp) / "raw-difference.png"
            run(["image-diff", "diff", str(first), str(second), "-o", str(raw_diff)])
            run(["convert", str(raw_diff), "-alpha", "off", str(output)])
            if mask_output:
                run(
                    [
                        "convert",
                        str(raw_diff),
                        "-alpha",
                        "off",
                        "-colorspace",
                        "gray",
                        "-threshold",
                        "0",
                        str(mask_output),
                    ]
                )

        thresholds: dict[str, object] = {}
        checks: list[bool] = []
        if args.max_diff_pixels is not None:
            thresholds["max_diff_pixels"] = args.max_diff_pixels
            checks.append(different_pixels <= args.max_diff_pixels)
        if args.max_diff_ratio is not None:
            thresholds["max_diff_ratio"] = args.max_diff_ratio
            checks.append(ratio <= args.max_diff_ratio)
        within_threshold = all(checks) if checks else None
        warnings = []
        if not bool(first_info["opaque"]) or not bool(second_info["opaque"]):
            warnings.append(
                "Transparent input detected; the visible RGB diff may underrepresent alpha-only changes."
            )
        status = "threshold-exceeded" if within_threshold is False else "ok"
        payload: dict[str, object] = {
            "status": status,
            "tool": run(["image-diff", "--version"]),
            "first": first_info,
            "second": second_info,
            "identical": different_pixels == 0,
            "different_pixels": different_pixels,
            "total_pixels": total_pixels,
            "difference_ratio": round(ratio, 12),
            "difference_percent": round(ratio * 100, 9),
            "difference_image": {
                "path": str(output),
                "sha256": sha256(output),
            },
            "mask_image": (
                {"path": str(mask_output), "sha256": sha256(mask_output)}
                if mask_output
                else None
            ),
            "thresholds": thresholds,
            "within_threshold": within_threshold,
            "warnings": warnings,
        }
        emit(payload)
        return 3 if within_threshold is False else 0
    except (OSError, RuntimeError, ValueError) as exc:
        emit({"status": "error", "error": str(exc), "type": type(exc).__name__})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
