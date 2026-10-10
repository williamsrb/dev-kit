#!/usr/bin/env python3
"""Download optional Archify media sets from the official GitHub repo.

`examples/` is needed for ordinary authorship; `test/` only when running the
package test suite. Call this script only when a set is required and missing
locally (lazy ensure).

Usage:
    python3 scripts/download_media.py
    python3 scripts/download_media.py examples
    python3 scripts/download_media.py --force test
    python3 scripts/download_media.py --check
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/tt-a1i/archify.git"
REPO_REF = "main"

# repo-relative path -> destination under SKILL_DIR
MEDIA_SETS: dict[str, tuple[str, Path]] = {
    "examples": ("archify/examples", SKILL_DIR / "examples"),
    "test": ("archify/test", SKILL_DIR / "test"),
}


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _has_files(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_file():
        return path.stat().st_size > 0
    return any(p.is_file() for p in path.rglob("*"))


def set_present(name: str) -> bool:
    return _has_files(MEDIA_SETS[name][1])


def sparse_fetch(repo_paths: list[str], work_dir: Path) -> Path:
    clone_dir = work_dir / "archify"
    _run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            "--branch",
            REPO_REF,
            REPO_URL,
            str(clone_dir),
        ]
    )
    _run(
        ["git", "-C", str(clone_dir), "sparse-checkout", "set", "--cone", *repo_paths]
    )
    return clone_dir


def install_set(name: str, clone_dir: Path, *, force: bool) -> str:
    repo_path, dest = MEDIA_SETS[name]
    src = clone_dir / repo_path
    if not src.is_dir():
        raise FileNotFoundError(
            f"Upstream path missing after sparse checkout: {repo_path}"
        )
    if set_present(name) and not force:
        return f"skip {name} (present): {dest}"
    if dest.exists():
        if dest.is_dir():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    return f"installed {name}: {dest}"


def ensure(names: list[str], *, force: bool) -> list[str]:
    needed = [n for n in names if force or not set_present(n)]
    if not needed:
        return [f"skip {n} (present): {MEDIA_SETS[n][1]}" for n in names]
    actions: list[str] = []
    with tempfile.TemporaryDirectory(prefix="archify-media-") as tmp:
        clone_dir = sparse_fetch([MEDIA_SETS[n][0] for n in needed], Path(tmp))
        for name in names:
            if name in needed:
                actions.append(install_set(name, clone_dir, force=True))
            else:
                actions.append(f"skip {name} (present): {MEDIA_SETS[name][1]}")
    return actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "sets",
        nargs="*",
        metavar="SET",
        help=f"Media sets to ensure (default: all). Choices: {', '.join(MEDIA_SETS)}",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even when the local set already exists.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 only when every requested set is present; do not download.",
    )
    args = parser.parse_args(argv)
    names = list(args.sets) if args.sets else list(MEDIA_SETS.keys())
    unknown = [n for n in names if n not in MEDIA_SETS]
    if unknown:
        print(f"error: unknown media set(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"known: {', '.join(MEDIA_SETS)}", file=sys.stderr)
        return 2

    if args.check:
        missing = [n for n in names if not set_present(n)]
        for name in names:
            status = "ok" if name not in missing else "missing"
            print(f"{status} {name}: {MEDIA_SETS[name][1]}")
        return 1 if missing else 0

    try:
        for line in ensure(names, force=args.force):
            print(line)
    except (OSError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
