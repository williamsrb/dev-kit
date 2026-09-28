"""Evidence inspect/manifest and image primitives for agentctl."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from agentctl_common import agents_home, argsafe_limit, emit, run, run_skill_script


def cmd_evidence_inspect(args: argparse.Namespace) -> int:
    image = args.image.resolve()
    checks: dict[str, Any] = {"exists": image.is_file()}
    if not image.is_file():
        emit({"valid": False, "image": str(image), "checks": checks})
        return 2
    identify = shutil.which("identify")
    if identify:
        result = run([identify, "-format", "%w %h %m", str(image)])
        if result.returncode == 0:
            width, height, image_format = result.stdout.split(maxsplit=2)
            checks["image"] = {"width": int(width), "height": int(height), "format": image_format}
            if args.min_width or args.min_height:
                checks["dimensions"] = {
                    "min_width": args.min_width,
                    "min_height": args.min_height,
                    "matches": int(width) >= args.min_width and int(height) >= args.min_height,
                }
    sidecar = args.sidecar or image.with_suffix(image.suffix + ".json")
    manifest: dict[str, Any] = {}
    if sidecar.is_file():
        try:
            manifest = json.loads(sidecar.read_text(encoding="utf-8"))
            checks["sidecar"] = "valid"
        except (OSError, json.JSONDecodeError) as exc:
            checks["sidecar"] = f"invalid: {exc}"
    else:
        checks["sidecar"] = "missing"
    if args.expected_url:
        actual_url = manifest.get("url")
        checks["url"] = {"expected": args.expected_url, "actual": actual_url,
                         "matches": actual_url == args.expected_url}
    if args.expected_selector:
        actual_selector = manifest.get("selector")
        checks["selector"] = {"expected": args.expected_selector, "actual": actual_selector,
                              "matches": actual_selector == args.expected_selector}
    ocr_payload = None
    if args.ocr or args.expected_text:
        tesseract = shutil.which("tesseract")
        if not tesseract:
            checks["ocr"] = "tesseract-missing"
        else:
            shared_tessdata = agents_home() / "share" / "tessdata"
            tessdata_args = []
            if shared_tessdata.is_dir() and all(
                (shared_tessdata / f"{language}.traineddata").is_file()
                for language in args.lang.split("+")
            ):
                tessdata_args = ["--tessdata-dir", str(shared_tessdata)]
            result = run([tesseract, str(image), "stdout", *tessdata_args, "-l", args.lang])
            ocr_payload = result.stdout[: argsafe_limit(args.max_ocr_chars)]
            checks["ocr"] = {"exit_code": result.returncode, "chars": len(result.stdout),
                             "truncated": len(result.stdout) > args.max_ocr_chars}
            if args.expected_text:
                checks["text"] = {
                    "expected": args.expected_text,
                    "matches": args.expected_text.casefold() in result.stdout.casefold(),
                }
    valid = checks["exists"] and not str(checks.get("sidecar", "")).startswith("invalid")
    if args.expected_url:
        valid = valid and checks.get("url", {}).get("matches", False)
    if args.expected_selector:
        valid = valid and checks.get("selector", {}).get("matches", False)
    if args.expected_text:
        valid = valid and checks.get("text", {}).get("matches", False)
    if args.min_width or args.min_height:
        valid = valid and checks.get("dimensions", {}).get("matches", False)
    emit({"valid": bool(valid), "image": str(image), "sidecar": str(sidecar),
          "checks": checks, "ocr_text": ocr_payload})
    return 0 if valid else 2


def cmd_evidence_manifest(args: argparse.Namespace) -> int:
    image = args.image.expanduser().resolve()
    if not image.is_file():
        emit({"status": "error", "error": f"image not found: {image}"})
        return 2
    output = (args.output or image.with_suffix(image.suffix + ".json")).expanduser().resolve()
    payload: dict[str, Any] = {
        "image": str(image),
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "bytes": image.stat().st_size,
        "url": args.url,
        "selector": args.selector,
        "title": args.title,
        "captured_at": dt.datetime.now().astimezone().isoformat(),
    }
    identify = shutil.which("identify")
    if identify:
        result = run([identify, "-format", "%w %h %m", str(image)])
        if result.returncode == 0:
            width, height, image_format = result.stdout.split(maxsplit=2)
            payload.update({"width": int(width), "height": int(height), "format": image_format})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                      encoding="utf-8")
    emit({"status": "written", "output": str(output), "manifest": payload})
    return 0


def cmd_image_stamp(args: argparse.Namespace) -> int:
    script = (
        Path.home()
        / ".agents"
        / "skills"
        / "plan-task-evidence"
        / "scripts"
        / "annotate-evidence-resolution.py"
    )
    script_args = ["--json"]
    if args.check:
        script_args.append("--check")
    if args.no_flatten:
        script_args.append("--no-flatten")
    script_args.extend(str(path.expanduser()) for path in args.paths)
    return run_skill_script(script, script_args, timeout=60)


def cmd_image_whitespace(args: argparse.Namespace) -> int:
    script = agents_home() / "skills" / "blank-space" / "scripts" / "blank_space.py"
    script_args = [str(args.image.expanduser().resolve()), "--background", args.background,
                   "--tolerance", str(args.tolerance)]
    if args.grid:
        script_args += ["--grid", str(args.grid)]
    return run_skill_script(script, script_args, timeout=30)


def cmd_image_describe(args: argparse.Namespace) -> int:
    script = agents_home() / "skills" / "describe-image" / "scripts" / "describe.py"
    script_args = [str(args.image.expanduser().resolve()), "--model", args.model,
                   "--timeout", str(args.timeout), "--max-chars", str(args.max_chars)]
    if args.prompt:
        script_args += ["--prompt", args.prompt]
    return run_skill_script(script, script_args, timeout=args.timeout + 30)


def cmd_image_diff(args: argparse.Namespace) -> int:
    script = agents_home() / "skills" / "diff-image" / "scripts" / "compare.py"
    first = args.first.expanduser().resolve()
    second = args.second.expanduser().resolve()
    output = (args.output or second.with_name(f"{second.stem}.diff.png")).expanduser().resolve()
    script_args = [str(first), str(second), "--output", str(output)]
    if args.mask_output:
        script_args += ["--mask-output", str(args.mask_output.expanduser().resolve())]
    if args.max_diff_pixels is not None:
        script_args += ["--max-diff-pixels", str(args.max_diff_pixels)]
    if args.max_diff_ratio is not None:
        script_args += ["--max-diff-ratio", str(args.max_diff_ratio)]
    return run_skill_script(script, script_args, timeout=60)


def cmd_image_palette_create(args: argparse.Namespace) -> int:
    script = agents_home() / "skills" / "color-palette" / "scripts" / "palette_create.py"
    script_args = [str(args.image.expanduser().resolve()), "--colors", str(args.colors),
                   "--method", args.method]
    if args.out:
        script_args += ["--out", str(args.out.expanduser().resolve())]
    if args.swatch:
        script_args += ["--swatch", str(args.swatch.expanduser().resolve())]
    if args.swatch_size:
        script_args += ["--swatch-size", args.swatch_size]
    return run_skill_script(script, script_args, timeout=120)


def cmd_image_palette_distance(args: argparse.Namespace) -> int:
    script = agents_home() / "skills" / "color-palette" / "scripts" / "palette_distance.py"
    palette = Path(args.palette).expanduser()
    script_args = [
        str(args.image.expanduser().resolve()),
        str(palette.resolve()) if palette.is_file() else args.palette,
        "--space", args.space,
        "--tolerance", str(args.tolerance),
        "--percentiles", args.percentiles,
        "--top-offenders", str(args.top_offenders),
        "--palette-max-colors", str(args.palette_max_colors),
    ]
    return run_skill_script(script, script_args, timeout=120)


def add_evidence_parsers(group) -> None:
    inspect = group.add_parser(
        "inspect",
        help="Verify screenshot dimensions, metadata, and optional OCR text.",
        description=(
            "Run deterministic screenshot assertions before visual review or Jira upload. "
            "Checks metadata sidecars, dimensions, and optional local Tesseract OCR."
        ),
    )
    inspect.add_argument("image", type=Path, help="Screenshot image.")
    inspect.add_argument("--sidecar", type=Path, help="Manifest JSON; defaults beside the image.")
    inspect.add_argument("--expected-url", help="Required captured page URL.")
    inspect.add_argument("--expected-selector", help="Required captured selector.")
    inspect.add_argument("--expected-text", help="Text that local OCR must find.")
    inspect.add_argument("--min-width", type=int, default=0, help="Minimum image width.")
    inspect.add_argument("--min-height", type=int, default=0, help="Minimum image height.")
    inspect.add_argument("--ocr", action="store_true", help="Run local OCR.")
    inspect.add_argument("--lang", default="eng", help="Tesseract language code.")
    inspect.add_argument("--max-ocr-chars", type=int, default=12000, help="Bound OCR output.")
    inspect.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    inspect.set_defaults(func=cmd_evidence_inspect)
    manifest = group.add_parser(
        "manifest",
        help="Write a screenshot metadata sidecar.",
        description="Record capture URL, selector, title, dimensions, and checksum as JSON.",
    )
    manifest.add_argument("image", type=Path, help="Screenshot image.")
    manifest.add_argument("--url", required=True, help="Captured page URL.")
    manifest.add_argument("--selector", help="Captured selector or target element.")
    manifest.add_argument("--title", help="Human-readable evidence title.")
    manifest.add_argument("--output", type=Path, help="Sidecar path; defaults beside the image.")
    manifest.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    manifest.set_defaults(func=cmd_evidence_manifest)



def add_image_parsers(group) -> None:
    stamp = group.add_parser(
        "stamp",
        help="Flatten a screenshot and stamp WIDTH x HEIGHT at bottom-left.",
        description=(
            "Delegate to annotate-evidence-resolution.py: flatten alpha, add a 2px "
            "#dddedd border, overlay WIDTH x HEIGHT at bottom-left, and record "
            "a resolution-stamp comment. Idempotent. Required before any Jira upload. "
            "Pass file paths (a directory only auto-stamps NN-*.png). --check exits 1 "
            "when the matching stamp is missing."
        ),
    )
    stamp.add_argument("paths", nargs="+", type=Path, help="PNG files, or an evidence directory.")
    stamp.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if any PNG is missing the matching stamp.",
    )
    stamp.add_argument(
        "--no-flatten",
        action="store_true",
        help="Stamp only; skip alpha flatten and 2px border.",
    )
    stamp.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    stamp.set_defaults(func=cmd_image_stamp)
    whitespace = group.add_parser(
        "whitespace",
        help="Measure blank/background pixel ratio in a screenshot.",
        description=(
            "Delegate to the blank-space skill (Pillow + numpy): overall blank ratio, "
            "border-trim ratio, and optional NxN grid. Deterministic, no model involved."
        ),
    )
    whitespace.add_argument("image", type=Path, help="Screenshot image.")
    whitespace.add_argument(
        "--background", default="auto",
        help="'auto' (corner sample), 'mode' (full-image mode color), or #RRGGBB.",
    )
    whitespace.add_argument("--tolerance", type=int, default=12, help="Per-channel blank tolerance (0-255).")
    whitespace.add_argument("--grid", type=int, default=0, help="Optional NxN per-cell blank-ratio grid.")
    whitespace.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    whitespace.set_defaults(func=cmd_image_whitespace)
    describe = group.add_parser(
        "describe",
        help="Describe a screenshot with a local vision-capable Ollama model.",
        description=(
            "Delegate to the describe-image skill: sends the image to a local Ollama "
            "vision model (default gemma4:e4b) over its HTTP API. Not deterministic; "
            "CPU-only inference measured ~140s per screenshot on this host."
        ),
    )
    describe.add_argument("image", type=Path, help="Screenshot image.")
    describe.add_argument("--prompt", help="Override the default layout/text/UI/issues prompt.")
    describe.add_argument("--model", default="gemma4:e4b", help="Vision-capable local Ollama model.")
    describe.add_argument("--timeout", type=float, default=300.0, help="Seconds to wait for inference.")
    describe.add_argument("--max-chars", type=int, default=4000, help="Bound the returned description.")
    describe.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    describe.set_defaults(func=cmd_image_describe)
    diff = group.add_parser(
        "diff",
        help="Compare two same-size images with exact pixel-diff metrics.",
        description=(
            "Delegate to the diff-image skill (image-diff CLI): exact changed-pixel "
            "count, ratio, a visible difference PNG, and optional threshold gating. "
            "Deterministic; images must already be aligned to the same dimensions."
        ),
    )
    diff.add_argument("first", type=Path, help="Baseline, expected, backend, or prototype image.")
    diff.add_argument("second", type=Path, help="Candidate, actual, frontend, or final image.")
    diff.add_argument(
        "--output", type=Path,
        help="Visible magnitude-difference PNG. Defaults beside the second image.",
    )
    diff.add_argument("--mask-output", type=Path, help="Optional black/white changed-pixel mask PNG.")
    diff.add_argument("--max-diff-pixels", type=int, help="Maximum allowed changed pixels.")
    diff.add_argument("--max-diff-ratio", type=float, help="Maximum allowed changed-pixel ratio (0-1).")
    diff.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    diff.set_defaults(func=cmd_image_diff)
    palette_create = group.add_parser(
        "palette-create",
        help="Extract a deterministic N-color palette from an image.",
        description=(
            "Delegate to the color-palette skill: quantize an image to N colors and "
            "report each entry with its hex, Lab, and pixel share. Optionally write a "
            "reusable palette JSON and a PNG swatch strip. Deterministic."
        ),
    )
    palette_create.add_argument("image", type=Path, help="Source image.")
    palette_create.add_argument("--colors", type=int, default=8, help="Palette size (2-256).")
    palette_create.add_argument(
        "--method", default="mediancut", choices=("mediancut", "maxcoverage", "fastoctree"),
        help="Quantizer; 'mediancut' balances the color cube, 'maxcoverage' favors dominant colors.",
    )
    palette_create.add_argument("--out", type=Path, help="Write the palette JSON here.")
    palette_create.add_argument("--swatch", type=Path, help="Write a PNG swatch strip here.")
    palette_create.add_argument("--swatch-size", default="400x50", help="Swatch strip WIDTHxHEIGHT.")
    palette_create.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    palette_create.set_defaults(func=cmd_image_palette_create)
    palette_distance = group.add_parser(
        "palette-distance",
        help="Score an image against a palette as a 0-1 deviation number.",
        description=(
            "Delegate to the color-palette skill: for every pixel take the distance to "
            "the nearest palette color, average over the image, and normalize to 0-1. "
            "Reports percentiles, on-palette coverage, palette usage, and the worst "
            "off-palette colors. Deterministic; no sampling."
        ),
    )
    palette_distance.add_argument("image", type=Path, help="Candidate image to score.")
    palette_distance.add_argument(
        "palette",
        help="Palette JSON, a swatch image, or a hex list like '#1a2b3c,#ffffff'.",
    )
    palette_distance.add_argument(
        "--space", default="lab", choices=("lab", "rgb"),
        help="Primary distance space; 'lab' is perceptual (CIE76 dE) and is the one to threshold on.",
    )
    palette_distance.add_argument(
        "--tolerance", type=float, default=10.0,
        help="Raw distance still counted as on-palette (Lab: ~2.3 is one JND).",
    )
    palette_distance.add_argument(
        "--percentiles", default="50,90,95,99", help="Per-pixel distance percentiles to report.",
    )
    palette_distance.add_argument(
        "--top-offenders", type=int, default=5, help="How many worst off-palette colors to list.",
    )
    palette_distance.add_argument(
        "--palette-max-colors", type=int, default=256,
        help="Reject a palette image with more distinct colors than this.",
    )
    palette_distance.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    palette_distance.set_defaults(func=cmd_image_palette_distance)
