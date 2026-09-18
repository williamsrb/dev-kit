#!/usr/bin/env python3
"""Prepare a self-contained local HTML rendering directory for a unified diff."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import download_media

MARKER = "<DIFF STRING GOES HERE>"
ASSET_NAMES = (
    "github.min.css",
    "diff2html.min.css",
    "diff2html-ui.min.js",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Insert a unified diff into the bundled diff2html template."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Patch file to render, or '-' to read UTF-8 text from stdin.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory. Defaults to a newly created temporary directory.",
    )
    return parser.parse_args()


def read_diff(input_name: str) -> tuple[str, str]:
    if input_name == "-":
        return sys.stdin.read(), "stdin"

    input_path = Path(input_name).expanduser().resolve(strict=True)
    return input_path.read_bytes().decode("utf-8"), str(input_path)


def escape_template_literal(value: str) -> str:
    """Preserve the runtime string while making insertion into HTML/JS safe."""
    return (
        value.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
        .replace("<", "\\x3c")
    )


def prepare_render(diff_text: str, output_dir: Path | None) -> tuple[Path, Path]:
    skill_dir = Path(__file__).resolve().parent.parent
    download_media.ensure()
    template_path = skill_dir / "template.html"
    template = template_path.read_bytes().decode("utf-8")

    marker_count = template.count(MARKER)
    if marker_count != 1:
        raise ValueError(
            f"Expected exactly one {MARKER!r} marker in {template_path}; "
            f"found {marker_count}."
        )

    if output_dir is None:
        render_dir = Path(tempfile.mkdtemp(prefix="render-diff-patch-"))
    else:
        render_dir = output_dir.expanduser().resolve()
        render_dir.mkdir(parents=True, exist_ok=True)

    for asset_name in ASSET_NAMES:
        source = skill_dir / asset_name
        if not source.is_file():
            raise FileNotFoundError(f"Missing bundled asset: {source}")
        shutil.copy2(source, render_dir / asset_name)

    html = template.replace(MARKER, escape_template_literal(diff_text), 1)
    html_path = render_dir / "render.html"
    html_path.write_bytes(html.encode("utf-8"))
    return render_dir, html_path


def main() -> int:
    args = parse_args()
    try:
        diff_text, source = read_diff(args.input)
        if not diff_text.strip():
            raise ValueError("The diff input is empty.")
        render_dir, html_path = prepare_render(diff_text, args.output_dir)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "source": source,
                "render_dir": str(render_dir),
                "html": str(html_path),
                "url": html_path.as_uri(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
