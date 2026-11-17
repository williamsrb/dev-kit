"""Bare invocation and --help print the module doc and exit 0; only --apply lets a script write."""

from __future__ import annotations

import argparse
import sys


def gate(doc: str | None, argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="run and write files (without it, print this help)")
    args = parser.parse_args(argv)
    if not args.apply:
        parser.print_help()
        sys.exit(0)
