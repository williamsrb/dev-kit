#!/usr/bin/env python3
"""Translate text with Cloud Translation API Basic (v2) using an API key."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_ROOT = "https://translation.googleapis.com/language/translate/v2"
ENV_KEYS = ("GOOGLE_TRANSLATE_API_KEY", "GOOGLE_API_KEY")
ENV_FILE = Path.home() / ".google-cloud.env"


def load_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def api_key() -> str:
    file_values = load_env_file(ENV_FILE)
    for name in ENV_KEYS:
        value = os.environ.get(name, "").strip() or file_values.get(name, "").strip()
        if value:
            return value
    names = " or ".join(ENV_KEYS)
    raise SystemExit(
        f"Missing API key. Set {names} in {ENV_FILE} "
        f"(or export it in the environment)."
    )


def post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"key": api_key()})
    url = f"{API_ROOT}{path}?{query}"
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Translate API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Translate API request failed: {exc.reason}") from exc


def get(path: str, params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode({"key": api_key(), **params})
    url = f"{API_ROOT}{path}?{query}"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Translate API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Translate API request failed: {exc.reason}") from exc


def read_text(args: argparse.Namespace) -> list[str]:
    if args.file is not None:
        return [args.file.read_text(encoding="utf-8")]
    if args.text:
        return list(args.text)
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data:
            return [data]
    raise SystemExit("Provide text as arguments, --file, or stdin.")


def cmd_translate(args: argparse.Namespace) -> int:
    texts = read_text(args)
    body: dict[str, Any] = {
        "q": texts,
        "target": args.target,
        "format": args.format,
    }
    if args.source:
        body["source"] = args.source
    if args.model:
        body["model"] = args.model

    result = post("", body)
    translations = result.get("data", {}).get("translations", [])
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    for item in translations:
        print(item.get("translatedText", ""))
    return 0


def cmd_detect(args: argparse.Namespace) -> int:
    texts = read_text(args)
    result = post("/detect", {"q": texts})
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    detections = result.get("data", {}).get("detections", [])
    for group in detections:
        top = group[0] if group else {}
        lang = top.get("language", "?")
        confidence = top.get("confidence")
        if confidence is None:
            print(lang)
        else:
            print(f"{lang}\t{confidence}")
    return 0


def cmd_languages(args: argparse.Namespace) -> int:
    params: dict[str, str] = {}
    if args.target:
        params["target"] = args.target
    result = get("/languages", params)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    languages = result.get("data", {}).get("languages", [])
    for item in languages:
        code = item.get("language", "")
        name = item.get("name")
        if name:
            print(f"{code}\t{name}")
        else:
            print(code)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Cloud Translation API Basic (v2). "
            f"API key from {ENV_FILE} ({' / '.join(ENV_KEYS)}; "
            "process env overrides)."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full API JSON response",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    translate = sub.add_parser("translate", help="Translate text")
    translate.add_argument(
        "text",
        nargs="*",
        help="Text to translate (repeatable). Omit to use --file or stdin.",
    )
    translate.add_argument(
        "-t",
        "--target",
        required=True,
        help="Target language code (e.g. en, nb, pt)",
    )
    translate.add_argument(
        "-s",
        "--source",
        help="Source language code (auto-detect if omitted)",
    )
    translate.add_argument(
        "--format",
        choices=("text", "html"),
        default="text",
        help="Input format (default: text)",
    )
    translate.add_argument(
        "--model",
        help="Optional model id (nmt or full Translation LLM resource name)",
    )
    translate.add_argument(
        "-f",
        "--file",
        type=Path,
        help="Read source text from a UTF-8 file",
    )
    translate.set_defaults(func=cmd_translate)

    detect = sub.add_parser("detect", help="Detect language of text")
    detect.add_argument("text", nargs="*", help="Text to inspect")
    detect.add_argument(
        "-f",
        "--file",
        type=Path,
        help="Read source text from a UTF-8 file",
    )
    detect.set_defaults(func=cmd_detect)

    languages = sub.add_parser("languages", help="List supported languages")
    languages.add_argument(
        "-t",
        "--target",
        help="Return language names localized in this language",
    )
    languages.set_defaults(func=cmd_languages)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
