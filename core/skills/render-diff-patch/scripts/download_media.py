#!/usr/bin/env python3
"""Download diff2html-ui.min.js from the official diff2html npm package.

The built UI bundle is published with the npm package of
https://github.com/rtfpessoa/diff2html (not stored as a source blob in git).
Call this script only when the file is required and missing (lazy ensure).
`prepare_render.py` invokes the same ensure path automatically.

Usage:
    python3 scripts/download_media.py
    python3 scripts/download_media.py --force
    python3 scripts/download_media.py --check
"""

from __future__ import annotations

import argparse
import io
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TARGET = SKILL_DIR / "diff2html-ui.min.js"

# Pin matches the previously vendored bundle size/content generation line.
DIFF2HTML_VERSION = "3.4.56"
NPM_TGZ_URL = (
    f"https://registry.npmjs.org/diff2html/-/diff2html-{DIFF2HTML_VERSION}.tgz"
)
MEMBER = "package/bundles/js/diff2html-ui.min.js"
MIN_BYTES = 100_000


def is_present() -> bool:
    return TARGET.is_file() and TARGET.stat().st_size >= MIN_BYTES


def download(*, force: bool = False) -> str:
    if is_present() and not force:
        return f"skip diff2html-ui.min.js (present): {TARGET}"

    request = urllib.request.Request(
        NPM_TGZ_URL,
        headers={"User-Agent": "render-diff-patch-download-media/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        archive = response.read()

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        try:
            member = tar.getmember(MEMBER)
        except KeyError as exc:
            raise FileNotFoundError(
                f"{MEMBER} not found in {NPM_TGZ_URL}"
            ) from exc
        extracted = tar.extractfile(member)
        if extracted is None:
            raise FileNotFoundError(f"Could not read {MEMBER} from tarball")
        data = extracted.read()

    if len(data) < MIN_BYTES:
        raise ValueError(
            f"Downloaded {MEMBER} is unexpectedly small ({len(data)} bytes)"
        )

    TARGET.write_bytes(data)
    return f"installed diff2html-ui.min.js ({len(data)} bytes): {TARGET}"


def ensure(*, force: bool = False) -> str:
    return download(force=force)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even when the local file already exists.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 only when diff2html-ui.min.js is present; do not download.",
    )
    args = parser.parse_args(argv)

    if args.check:
        status = "ok" if is_present() else "missing"
        print(f"{status} diff2html-ui.min.js: {TARGET}")
        return 0 if is_present() else 1

    try:
        print(ensure(force=args.force))
    except (OSError, ValueError, tarfile.TarError, urllib.error.URLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
