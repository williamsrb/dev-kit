#!/usr/bin/env python3
"""Localize pixel changes on an aligned before/after pair and write crop sidecars."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

COMPARE_SCRIPT = Path(__file__).resolve().parent / "compare.py"
CLOSE_KERNEL = "Square:2"
CONNECTIVITY = "4"
PAD_PX = 16
DIVIDER_PX = 8
STROKE_PX = 4
MAX_BLOBS = 3
MIN_AREA_PX = 256
MIN_AREA_RATIO = 0.001
MAX_COVERAGE = 0.5
LABEL_POINTSIZE = 12
BEFORE_STROKE = "#cc0000"
AFTER_STROKE = "#2e7d32"
OBJECT_RE = re.compile(
    r"^\s*(\d+):\s+(\d+)x(\d+)\+(\d+)\+(\d+)\s+\S+\s+(\d+)\s+(.+)$"
)


@dataclass(frozen=True)
class BBox:
    x: int
    y: int
    width: int
    height: int

    def area(self) -> int:
        return self.width * self.height

    def as_json(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    def geometry(self) -> str:
        return f"{self.width}x{self.height}+{self.x}+{self.y}"

    def draw_spec(self) -> str:
        x1 = self.x + self.width - 1
        y1 = self.y + self.height - 1
        return f"rectangle {self.x},{self.y} {x1},{y1}"


def emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[:2000]
        raise RuntimeError(f"{' '.join(command[:2])} failed: {detail}")
    return f"{result.stdout}\n{result.stderr}".strip()


def empty_sidecars() -> dict[str, None]:
    return {"before_crop": None, "after_crop": None, "compose": None}


def is_foreground(mean_color: str) -> bool:
    nums = [int(value) for value in re.findall(r"\d+", mean_color)]
    if not nums:
        return False
    peak = 65535 if any(value > 255 for value in nums) else 255
    sample = nums[:3]
    return (sum(sample) / len(sample)) > (peak / 2)


@dataclass(frozen=True)
class Blob:
    bbox: BBox
    area: int


def parse_components(verbose: str) -> list[Blob]:
    blobs: list[Blob] = []
    for line in verbose.splitlines():
        match = OBJECT_RE.match(line.strip())
        if match is None:
            continue
        _oid, width, height, x, y, area, mean_color = match.groups()
        if not is_foreground(mean_color):
            continue
        blobs.append(
            Blob(
                BBox(int(x), int(y), int(width), int(height)),
                int(area),
            )
        )
    return blobs


def union_bboxes(boxes: list[BBox]) -> BBox:
    x0 = min(box.x for box in boxes)
    y0 = min(box.y for box in boxes)
    x1 = max(box.x + box.width for box in boxes)
    y1 = max(box.y + box.height for box in boxes)
    return BBox(x0, y0, x1 - x0, y1 - y0)


def pad_bbox(box: BBox, canvas_w: int, canvas_h: int) -> BBox:
    x0 = max(0, box.x - PAD_PX)
    y0 = max(0, box.y - PAD_PX)
    x1 = min(canvas_w, box.x + box.width + PAD_PX)
    y1 = min(canvas_h, box.y + box.height + PAD_PX)
    return BBox(x0, y0, max(0, x1 - x0), max(0, y1 - y0))


def map_into(inner: BBox, crop: BBox) -> BBox:
    return BBox(inner.x - crop.x, inner.y - crop.y, inner.width, inner.height)


def sidecar_path(output_dir: Path, after_stem: str, suffix: str, inputs: set[Path]) -> Path:
    path = (output_dir / f"{after_stem}{suffix}").expanduser().resolve()
    if path.suffix.lower() != ".png":
        raise ValueError(f"sidecar must be a lossless .png file: {path}")
    if path in inputs:
        raise ValueError(f"output must not overwrite an input image: {path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return path


def crop_to(source: Path, dest: Path, box: BBox) -> None:
    run(["convert", str(source), "-crop", box.geometry(), "+repage", str(dest)])


def image_size(path: Path) -> tuple[int, int]:
    output = run(["identify", "-ping", "-format", "%w %h", str(path)])
    width_text, height_text = output.split()[:2]
    return int(width_text), int(height_text)


def stroke_and_label(
    source: Path, dest: Path, *, label: str, stroke: str, rect: BBox
) -> None:
    command = [
        "convert",
        str(source),
        "-strokewidth",
        str(STROKE_PX),
        "-stroke",
        stroke,
        "-fill",
        "none",
        "-draw",
        rect.draw_spec(),
        "-stroke",
        "none",
        "-strokewidth",
        "0",
        "-gravity",
        "North",
        "-pointsize",
        str(LABEL_POINTSIZE),
        "-fill",
        "white",
        "-undercolor",
        "#000000",
        "-annotate",
        "+0+8",
        label,
        str(dest),
    ]
    run(command)


def compose_strip(before_crop: Path, after_crop: Path, dest: Path, rect: BBox) -> None:
    _width, height = image_size(before_crop)
    with tempfile.TemporaryDirectory(prefix=".crop-changed-compose-") as temp:
        temp_dir = Path(temp)
        labeled_before = temp_dir / "before.png"
        labeled_after = temp_dir / "after.png"
        stroke_and_label(
            before_crop, labeled_before, label="Before", stroke=BEFORE_STROKE, rect=rect
        )
        stroke_and_label(
            after_crop, labeled_after, label="After", stroke=AFTER_STROKE, rect=rect
        )
        run(
            [
                "convert",
                str(labeled_before),
                "(",
                "-size",
                f"{DIVIDER_PX}x{height}",
                "xc:black",
                ")",
                str(labeled_after),
                "+append",
                str(dest),
            ]
        )


def run_compare(before: Path, after: Path, temp_dir: Path) -> tuple[dict[str, object], Path]:
    diff_png = temp_dir / "diff.png"
    mask_png = temp_dir / "mask.png"
    result = subprocess.run(
        [
            sys.executable,
            str(COMPARE_SCRIPT),
            str(before),
            str(after),
            "--output",
            str(diff_png),
            "--mask-output",
            str(mask_png),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        detail = (result.stderr or result.stdout).strip()[:2000]
        raise RuntimeError(f"compare.py returned non-JSON: {detail}") from exc
    if not isinstance(payload, dict):
        raise TypeError("compare.py JSON must be an object")
    payload["exit_code"] = result.returncode
    return payload, mask_png


def not_localized_payload(
    *,
    blob_count: int,
    union: BBox | None,
    different_pixels: object,
    difference_ratio: object,
    message: str,
) -> dict[str, object]:
    return {
        "status": "not-localized",
        "blob_count": blob_count,
        "union_bbox": None if union is None else union.as_json(),
        "sidecars": empty_sidecars(),
        "different_pixels": different_pixels,
        "difference_ratio": difference_ratio,
        "message": message,
    }


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Localize changed pixels on two same-size screenshots, write crop sidecars, "
            "and optionally compose a labeled Before|After strip. No vendor vision. "
            "Does not stamp. Does not overwrite inputs. Not a semantic pass/fail gate."
        ),
        epilog=(
            "Example:\n"
            "  crop_changed.py before.png after.png\n"
            "  crop_changed.py before.png after.png --compose --output-dir /tmp/sidecars"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


def main() -> int:
    parser = build_parser()
    parser.add_argument("before", help="Baseline screenshot (before).")
    parser.add_argument("after", help="Candidate screenshot (after).")
    parser.add_argument(
        "--compose",
        action="store_true",
        help="Also write a labeled Before|After PNG with red/green rectangles.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for sidecars. Defaults beside the after image.",
    )
    args = parser.parse_args()

    try:
        before = Path(args.before).expanduser().resolve(strict=True)
        after = Path(args.after).expanduser().resolve(strict=True)
        if not before.is_file() or not after.is_file():
            raise ValueError("both inputs must be regular files")
        inputs = {before, after}
        output_dir = (
            Path(args.output_dir).expanduser().resolve()
            if args.output_dir
            else after.parent
        )

        with tempfile.TemporaryDirectory(prefix=".crop-changed-") as temp:
            temp_dir = Path(temp)
            compare_payload, mask_png = run_compare(before, after, temp_dir)
            status = compare_payload.get("status")
            if status == "dimension-mismatch":
                compare_payload.setdefault("blob_count", 0)
                compare_payload.setdefault("union_bbox", None)
                compare_payload.setdefault("sidecars", empty_sidecars())
                compare_payload.pop("exit_code", None)
                emit(compare_payload)
                return 2
            if status == "error":
                compare_payload.pop("exit_code", None)
                emit(compare_payload)
                return 2
            if status != "ok":
                raise RuntimeError(f"unexpected compare.py status: {status}")

            different_pixels = compare_payload["different_pixels"]
            difference_ratio = compare_payload["difference_ratio"]
            first_info = compare_payload["first"]
            canvas_w = int(first_info["width"])
            canvas_h = int(first_info["height"])
            canvas_pixels = canvas_w * canvas_h
            area_floor = max(MIN_AREA_PX, int(MIN_AREA_RATIO * canvas_pixels))

            if not mask_png.is_file():
                raise RuntimeError("compare.py did not write a mask")

            closed = temp_dir / "closed.png"
            run(
                [
                    "convert",
                    str(mask_png),
                    "-morphology",
                    "Close",
                    CLOSE_KERNEL,
                    str(closed),
                ]
            )
            verbose = run(
                [
                    "convert",
                    str(closed),
                    "-define",
                    "connected-components:verbose=true",
                    "-define",
                    "connected-components:mean-color=true",
                    "-connected-components",
                    CONNECTIVITY,
                    "null:",
                ]
            )
            all_blobs = parse_components(verbose)
            blobs = [blob for blob in all_blobs if blob.area >= area_floor]
            blob_count = len(blobs)
            blob_boxes = [blob.bbox for blob in blobs]

            if blob_count == 0:
                emit(
                    not_localized_payload(
                        blob_count=0,
                        union=None,
                        different_pixels=different_pixels,
                        difference_ratio=difference_ratio,
                        message="Change is not localized: no blobs remain after area filter.",
                    )
                )
                return 3
            if blob_count > MAX_BLOBS:
                emit(
                    not_localized_payload(
                        blob_count=blob_count,
                        union=union_bboxes(blob_boxes),
                        different_pixels=different_pixels,
                        difference_ratio=difference_ratio,
                        message=(
                            f"Change is not localized: {blob_count} blobs remain "
                            f"(max {MAX_BLOBS})."
                        ),
                    )
                )
                return 3

            union = union_bboxes(blob_boxes)
            padded = pad_bbox(union, canvas_w, canvas_h)
            coverage = padded.area() / canvas_pixels if canvas_pixels else 1.0
            if coverage > MAX_COVERAGE:
                emit(
                    not_localized_payload(
                        blob_count=blob_count,
                        union=union,
                        different_pixels=different_pixels,
                        difference_ratio=difference_ratio,
                        message=(
                            "Change is not localized: padded union bbox covers "
                            f"{coverage:.1%} of the canvas (max {MAX_COVERAGE:.0%})."
                        ),
                    )
                )
                return 3

            before_crop = sidecar_path(
                output_dir, after.stem, ".before-crop.png", inputs
            )
            after_crop = sidecar_path(
                output_dir, after.stem, ".after-crop.png", inputs
            )
            crop_to(before, before_crop, padded)
            crop_to(after, after_crop, padded)
            compose_path = None
            if args.compose:
                compose_path = sidecar_path(
                    output_dir, after.stem, ".before-after.png", inputs
                )
                compose_strip(
                    before_crop, after_crop, compose_path, map_into(union, padded)
                )

            emit(
                {
                    "status": "ok",
                    "blob_count": blob_count,
                    "union_bbox": union.as_json(),
                    "sidecars": {
                        "before_crop": str(before_crop),
                        "after_crop": str(after_crop),
                        "compose": None if compose_path is None else str(compose_path),
                    },
                    "different_pixels": different_pixels,
                    "difference_ratio": difference_ratio,
                }
            )
            return 0
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        emit({"status": "error", "error": str(exc), "type": type(exc).__name__})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
