#!/usr/bin/env python3
"""Bounded local image description via a vision-capable Ollama model (no remote LLM call)."""

from __future__ import annotations

import argparse
import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_MODEL = "gemma4:e4b"
DEFAULT_HOST = "http://localhost:11434"
DEFAULT_PROMPT = (
    "Describe this screenshot factually: overall layout, visible text, UI elements, "
    "colors, and any obvious visual issues (misalignment, overlap, clipping, unexpected "
    "blank areas). Be concise and stick to what is actually visible."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Send a local image to a local Ollama vision model for a text description. "
            "Runs entirely on-machine via the Ollama HTTP API; nothing leaves the host."
        ),
        epilog=(
            "Example:\n"
            "  describe.py screenshot.png --prompt \"List every visible button label\""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Must be a vision-capable local Ollama model.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="CPU inference on this machine took ~140s warm, longer cold on first load; raise for large images.",
    )
    parser.add_argument("--max-chars", type=int, default=4000)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    source = args.image.expanduser().resolve()
    if not source.is_file():
        print(json.dumps({"status": "error", "error": f"image not found: {source}"}))
        return 2
    if args.max_chars <= 0:
        print(json.dumps({"status": "error", "error": "--max-chars must be positive"}))
        return 2

    try:
        image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    except OSError as exc:
        print(json.dumps({"status": "error", "error": f"cannot read image: {exc}"}))
        return 2

    request_payload = {
        "model": args.model,
        "prompt": args.prompt,
        "images": [image_b64],
        "stream": False,
    }
    request = urllib.request.Request(
        f"{args.host.rstrip('/')}/api/generate",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"ollama HTTP {exc.code}: {detail}",
                    "hint": f"is model '{args.model}' pulled? try: ollama pull {args.model}",
                }
            )
        )
        return 2
    except urllib.error.URLError as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"cannot reach ollama at {args.host}: {exc.reason}",
                    "hint": "is the ollama service running? try: systemctl status ollama",
                }
            )
        )
        return 2

    text = (body.get("response") or "").strip()
    truncated = len(text) > args.max_chars
    if truncated:
        text = text[: args.max_chars]

    total_duration_ns = body.get("total_duration")
    payload = {
        "status": "ok",
        "model": args.model,
        "image": str(source),
        "description": text,
        "truncated": truncated,
        "eval_count": body.get("eval_count"),
        "total_duration_ms": round(total_duration_ns / 1e6, 1) if total_duration_ns else None,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
