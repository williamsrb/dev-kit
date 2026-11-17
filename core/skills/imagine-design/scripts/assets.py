#!/usr/bin/env python3
"""Asset consistency for the imagine-design skill: check, normalize, resolve, sheet.

Checks generated assets against style-lock.json with ImageMagick (images) and
ffprobe/ffmpeg (audio, video). Exit codes: 0 clean, 1 check findings, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE_EXT = {".png", ".webp", ".jpg", ".jpeg", ".gif"}
AUDIO_EXT = {".wav", ".mp3", ".ogg", ".flac"}
MODEL_EXT = {".glb", ".gltf", ".obj", ".fbx"}
VIDEO_EXT = {".mp4", ".webm", ".mov"}
UNIQUE_COLOR_LIMIT = 4096
IMAGE_DIRECTION = ("medium", "projection", "palette.mode", "direction.drawing_style", "direction.proportions", "direction.lighting")
HEX_RE = re.compile(r"#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?")
PALETTE_DISTANCE = Path(__file__).resolve().parents[2] / "color-palette" / "scripts" / "palette_distance.py"


class BadInput(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except BadInput as exc:
        print(f"assets: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="assets.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(required=False)

    check = sub.add_parser("check", help="Check assets against a style lock.")
    check.add_argument("--lock", required=True, type=Path, help="style-lock.json")
    check.add_argument("--json", action="store_true", help="print the JSON report")
    check.add_argument("files", nargs="+", type=Path)
    check.set_defaults(func=cmd_check)

    normalize = sub.add_parser("normalize", help="Snap images to the lock: native size, palette, binary alpha, pixel scale.")
    normalize.add_argument("--lock", required=True, type=Path, help="style-lock.json")
    normalize.add_argument("--out", required=True, type=Path, help="output folder")
    normalize.add_argument("--size", help="native size WxH before pixel_scale (pixel art downsampled from a large render)")
    normalize.add_argument("files", nargs="+", type=Path)
    normalize.set_defaults(func=cmd_normalize)

    resolve = sub.add_parser("resolve", help="Print the effective lock (parent design + lock); exit 2 if the lock overrides the parent.")
    resolve.add_argument("--lock", required=True, type=Path, help="style-lock.json")
    resolve.set_defaults(func=cmd_resolve)

    sheet = sub.add_parser("sheet", help="Contact sheet of images for one side-by-side vision review, long edge capped.")
    sheet.add_argument("--out", required=True, type=Path, help="sheet PNG")
    sheet.add_argument("--max-edge", type=int, default=1280)
    sheet.add_argument("--columns", type=int, default=4)
    sheet.add_argument("files", nargs="+", type=Path)
    sheet.set_defaults(func=cmd_sheet)
    return parser


# --- commands ---------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    lock = load_lock(args.lock)
    reports = [check_file(lock, path) for path in args.files]
    failed = [r for r in reports if not r["ok"]]
    if args.json:
        print(json.dumps({"ok": not failed, "checked": len(reports), "failed": len(failed), "assets": reports}, indent=2))
    else:
        for report in reports:
            for item in report["checks"]:
                if not item["ok"]:
                    print(f"FAIL\t{report['file']}\t{item['name']}\t{item['detail']}")
        print(f"{len(reports) - len(failed)}/{len(reports)} assets pass")
    return 1 if failed else 0


def cmd_normalize(args: argparse.Namespace) -> int:
    lock = load_lock(args.lock)
    image = lock.get("image", {})
    palette = lock.get("palette", {})
    scale = int(image.get("pixel_scale", 1))
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        palette_png = None
        if palette.get("mode") == "exact":
            palette_png = Path(tmp) / "palette.png"
            magick(*[f"xc:{c}" for c in palette["colors"]], "+append", str(palette_png))
        written = []
        for path in args.files:
            require_file(path, IMAGE_EXT)
            target = args.out / f"{path.stem}.png"
            cmd = [str(path)]
            if args.size:
                cmd += ["-sample", f"{parse_size(args.size)}!"]
            if lock.get("medium") == "pixel-art" or palette_png:
                rgb = ["-alpha", "off"] + (["-dither", "None", "-remap", str(palette_png)] if palette_png else [])
                cmd += ["(", "+clone", "-alpha", "extract", "-threshold", "50%", ")",
                        "(", "-clone", "0", *rgb, ")", "-delete", "0", "+swap",
                        "-alpha", "off", "-compose", "CopyOpacity", "-composite"]
            if scale > 1:
                cmd += ["-sample", f"{scale * 100}%"]
            magick(*cmd, str(target))
            written.append(str(target))
    print(json.dumps({"written": written}, indent=2))
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    print(json.dumps(load_lock(args.lock), indent=2))
    return 0


def cmd_sheet(args: argparse.Namespace) -> int:
    for path in args.files:
        require_file(path, IMAGE_EXT)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    run(["magick", "montage", "-label", "%t", *map(str, args.files), "-tile", f"{args.columns}x", "-geometry", "+6+6",
         "-background", "#808080", str(args.out)])
    edge = args.max_edge
    magick(str(args.out), "-filter", "point", "-resize", f"{edge}x{edge}>", str(args.out))
    print(str(args.out))
    return 0


# --- checks -----------------------------------------------------------------


def check_file(lock: dict, path: Path) -> dict:
    suffix = path.suffix.lower()
    if not path.is_file():
        checks = [result("exists", False, "file not found")]
    elif suffix in IMAGE_EXT:
        checks = check_image(lock, path)
    elif suffix in AUDIO_EXT:
        checks = check_audio(lock.get("audio", {}), path)
    elif suffix in VIDEO_EXT:
        checks = check_video(lock.get("video", {}), path)
    elif suffix in MODEL_EXT:
        checks = check_model(lock.get("model3d", {}), path)
    else:
        checks = [result("type", False, f"unsupported extension {suffix}")]
    return {"file": str(path), "ok": all(c["ok"] for c in checks), "checks": checks}


def check_image(lock: dict, path: Path) -> list[dict]:
    image = lock.get("image", {})
    palette = lock.get("palette", {})
    fmt, width, height, alpha, count = magick("identify", "-format", "%m %w %h %A %k", f"{path}[0]").split()
    width, height, count = int(width), int(height), int(count)
    checks = []

    if image.get("format"):
        checks.append(result("format", fmt.lower() == image["format"].lower(), f"{fmt.lower()} vs {image['format']}"))
    if image.get("sizes"):
        sizes = [tuple(s) for s in image["sizes"]]
        checks.append(result("size", (width, height) in sizes, f"{width}x{height} not in {sizes}"))
    scale = int(image.get("pixel_scale", 1))
    if image.get("grid"):
        gw, gh = (g * scale for g in image["grid"])
        checks.append(result("grid", width % gw == 0 and height % gh == 0, f"{width}x{height} is not a multiple of {gw}x{gh}"))
    if scale > 1:
        checks.append(check_pixel_scale(path, width, height, scale))

    background = image.get("background", "any")
    if background != "any":
        has_alpha = alpha.lower() not in ("undefined", "false")
        transparent = has_alpha and float(magick(f"{path}[0]", "-alpha", "extract", "-format", "%[fx:minima]", "info:")) == 0
        wanted = background == "transparent"
        checks.append(result("background", transparent == wanted,
                             f"has transparent pixels: {transparent}, lock wants {background}"))

    if image.get("max_colors") or palette.get("mode") == "exact":
        colors = opaque_colors(path, count)
        if image.get("max_colors"):
            n = len(colors) if colors is not None else count
            checks.append(result("max-colors", n <= image["max_colors"], f"{n} opaque colors, max {image['max_colors']}"))
        if palette.get("mode") == "exact":
            allowed = {c.lower() for c in palette["colors"]}
            off = sorted(colors - allowed) if colors is not None else None
            detail = f"{count} colors, too many to list" if off is None else f"{len(off)} off-palette: {', '.join(off[:8])}"
            checks.append(result("palette", off == [], detail))
    elif palette.get("mode") == "perceptual":
        checks.append(check_palette_distance(path, palette))
    return checks


def check_pixel_scale(path: Path, width: int, height: int, scale: int) -> dict:
    if width % scale or height % scale:
        return result("pixel-scale", False, f"{width}x{height} is not divisible by pixel_scale {scale}")
    with tempfile.TemporaryDirectory() as tmp:
        snapped = Path(tmp) / "snapped.png"
        magick(f"{path}[0]", "-sample", f"{width // scale}x{height // scale}!", "-sample", f"{width}x{height}!", str(snapped))
        proc = subprocess.run(["magick", "compare", "-metric", "AE", f"{path}[0]", str(snapped), "null:"],
                              capture_output=True, text=True, check=False)
    differing = proc.stderr.split()[0] if proc.stderr else "?"
    return result("pixel-scale", proc.returncode == 0, f"{differing} pixels break the {scale}px grid (blur or sub-pixel detail)")


def check_palette_distance(path: Path, palette: dict) -> dict:
    cmd = [sys.executable, str(PALETTE_DISTANCE), str(path), ",".join(palette["colors"]),
           "--tolerance", str(palette.get("tolerance", 10))]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return result("palette-distance", False, f"not run: {proc.stderr.strip()[:200]}")
    report = json.loads(proc.stdout)
    distance = report["distance"]
    coverage = report["coverage"]["within_tolerance_ratio"]
    ok = distance <= palette.get("max_distance", 0.05) and coverage >= palette.get("min_coverage", 0.9)
    return result("palette-distance", ok, f"distance {distance:.3f}, on-palette {coverage:.1%}")


def check_audio(spec: dict, path: Path) -> list[dict]:
    probe = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channels:format=duration",
                            "-of", "json", str(path)]))
    stream = probe["streams"][0]
    duration = float(probe["format"]["duration"])
    checks = []
    if spec.get("format"):
        checks.append(result("format", path.suffix.lower().lstrip(".") in spec["format"], f"{path.suffix} vs {spec['format']}"))
    if spec.get("sample_rate"):
        checks.append(result("sample-rate", int(stream["sample_rate"]) == spec["sample_rate"], f"{stream['sample_rate']} Hz"))
    if spec.get("channels"):
        checks.append(result("channels", stream["channels"] == spec["channels"], f"{stream['channels']} channels"))
    if spec.get("max_seconds"):
        checks.append(result("duration", duration <= spec["max_seconds"], f"{duration:.2f}s, max {spec['max_seconds']}s"))
    if spec.get("loudness_lufs") is not None:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                             capture_output=True, text=True, check=False).stderr
        found = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
        tolerance = spec.get("loudness_tolerance", 2)
        if found:
            lufs = float(found[-1])
            checks.append(result("loudness", abs(lufs - spec["loudness_lufs"]) <= tolerance,
                                 f"{lufs} LUFS, target {spec['loudness_lufs']} ±{tolerance}"))
        else:
            checks.append(result("loudness", False, "not measured"))
    return checks


def check_video(spec: dict, path: Path) -> list[dict]:
    probe = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)]))
    stream = probe["streams"][0]
    duration = float(probe["format"]["duration"])
    num, den = stream["r_frame_rate"].split("/")
    fps = int(num) / int(den)
    checks = []
    if spec.get("format"):
        checks.append(result("format", path.suffix.lower().lstrip(".") in spec["format"], f"{path.suffix} vs {spec['format']}"))
    if spec.get("sizes"):
        size = (stream["width"], stream["height"])
        sizes = [tuple(s) for s in spec["sizes"]]
        checks.append(result("size", size in sizes, f"{size[0]}x{size[1]} not in {sizes}"))
    if spec.get("fps"):
        checks.append(result("fps", abs(fps - spec["fps"]) < 0.01, f"{fps:.3f} fps, lock wants {spec['fps']}"))
    if spec.get("max_seconds"):
        checks.append(result("duration", duration <= spec["max_seconds"], f"{duration:.2f}s, max {spec['max_seconds']}s"))
    return checks


def check_model(spec: dict, path: Path) -> list[dict]:
    checks = []
    if spec.get("format"):
        checks.append(result("format", path.suffix.lower().lstrip(".") in spec["format"], f"{path.suffix} vs {spec['format']}"))
    if spec.get("max_bytes"):
        size = path.stat().st_size
        checks.append(result("file-size", size <= spec["max_bytes"], f"{size} bytes, max {spec['max_bytes']}"))
    return checks


# --- helpers ----------------------------------------------------------------


def opaque_colors(path: Path, count: int) -> set[str] | None:
    if count > UNIQUE_COLOR_LIMIT:
        return None
    colors = set()
    for line in magick(f"{path}[0]", "-depth", "8", "-unique-colors", "txt:-").splitlines()[1:]:
        match = HEX_RE.search(line)
        if match and match.group(2) != "00":
            colors.add(f"#{match.group(1).lower()}")
    return colors


def load_lock(path: Path) -> dict:
    lock = read_object(path)
    parent_name = lock.pop("extends", None)
    if parent_name:
        parent = read_object(path.parent / parent_name)
        if "image" in parent:
            missing = [key for key in IMAGE_DIRECTION if lookup(parent, key) in (None, "", [])]
            if missing:
                raise BadInput(f"{parent_name} misses {', '.join(missing)}; propose values to imagine instead of choosing them")
        conflicts = overrides(parent, lock)
        if conflicts:
            raise BadInput(f"{path}: overrides the parent design at {', '.join(conflicts)}; propose the change to imagine instead")
        lock = merged(parent, lock)
    palette = lock.get("palette", {})
    if palette.get("mode") in ("exact", "perceptual"):
        colors = palette.get("colors")
        if not isinstance(colors, list) or not colors or not all(isinstance(c, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", c) for c in colors):
            raise BadInput(f"{path}: palette.colors must be a non-empty list of #rrggbb")
    for tool in ("magick",) + (("ffprobe", "ffmpeg") if "audio" in lock or "video" in lock else ()):
        if shutil.which(tool) is None:
            raise BadInput(f"{tool} is not on PATH")
    return lock


def read_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BadInput(f"{path}: not found") from None
    except json.JSONDecodeError as exc:
        raise BadInput(f"{path}: invalid JSON ({exc})") from None
    if not isinstance(data, dict):
        raise BadInput(f"{path}: must be a JSON object")
    return data


def lookup(data: dict, dotted: str) -> object:
    for part in dotted.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def overrides(parent: dict, child: dict, prefix: str = "") -> list[str]:
    conflicts = []
    for key, value in child.items():
        if key not in parent:
            continue
        if isinstance(value, dict) and isinstance(parent[key], dict):
            conflicts += overrides(parent[key], value, f"{prefix}{key}.")
        elif value != parent[key]:
            conflicts.append(f"{prefix}{key}")
    return conflicts


def merged(parent: dict, child: dict) -> dict:
    out = dict(parent)
    for key, value in child.items():
        out[key] = merged(parent[key], value) if isinstance(value, dict) and isinstance(parent.get(key), dict) else value
    return out


def require_file(path: Path, extensions: set[str]) -> None:
    if not path.is_file():
        raise BadInput(f"{path}: not found")
    if path.suffix.lower() not in extensions:
        raise BadInput(f"{path}: unsupported extension {path.suffix}")


def parse_size(text: str) -> str:
    if not re.fullmatch(r"\d+x\d+", text):
        raise BadInput(f"--size must be WxH, got {text!r}")
    return text


def magick(*args: str) -> str:
    return run(["magick", *args])


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise BadInput(f"{cmd[0]} {cmd[1] if len(cmd) > 1 else ''} failed: {proc.stderr.strip()[:300]}")
    return proc.stdout.strip()


def result(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": "" if ok else detail}


if __name__ == "__main__":
    sys.exit(main())
