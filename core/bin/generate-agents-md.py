#!/usr/bin/env python3
"""Generate rules/AGENTS.md from rules/manifest.json.

AGENTS.md is the single instruction file Claude Code and Codex ingest. It was
hand-maintained alongside the Cursor `.mdc` rules, so the two drifted silently
(plan devkit, A0/B2). This makes it generated, and gives a profile a rule
list it can filter by layer instead of a 668-line file it must edit by hand.

Each section names its body source:

  body.from == "mdc"   embed that rule file verbatim; frontmatter and the H1 are
                       stripped and headings are demoted one level. Editing the
                       .mdc is the only way to change the section.
  body.from == "file"  the AGENTS.md text is a translation of a rule, or a merge
                       of several. It lives in agents.d/ as its single source.

Usage:
    generate-agents-md.py                 # dry run: report what would change
    generate-agents-md.py --check         # exit 1 if AGENTS.md is out of date
    generate-agents-md.py --apply         # write AGENTS.md
    generate-agents-md.py --layer core    # only core sections (drop the client overlay)
    generate-agents-md.py --stdout        # print the render

Exit codes: 0 = up to date or written, 1 = drift (--check) or error, 2 = bad invocation.

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
MANIFEST = RULES_DIR / "manifest.json"
OUTPUT = RULES_DIR / "AGENTS.md"


class GenerateError(Exception):
    """A manifest or body file is missing or malformed."""


def read_body_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise GenerateError(f"cannot read {path}: {exc}") from exc


def mdc_body(path: Path) -> str:
    """Rule body with frontmatter and H1 stripped and headings demoted one level.

    Demotion is what lets a rule's own `## Do` sit under the `##` section heading
    AGENTS.md gives it. Fenced blocks are left alone so a `#` comment in a shell
    sample is not mistaken for a heading.
    """
    text = read_body_file(path)
    front = re.match(r"^---\n.*?\n---\n", text, re.S)
    if front:
        text = text[front.end():].strip()
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    out, in_fence = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"^#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out).strip()


def render(manifest: dict, layers: set[str] | None) -> str:
    parts = [read_body_file(RULES_DIR / manifest["intro"]), "", "---", ""]
    parts += [read_body_file(RULES_DIR / manifest["base"]["file"]), "---", "", "# Operational rules", ""]

    for section in manifest["sections"]:
        if layers is not None and section.get("layer", "core") not in layers:
            continue
        body = section["body"]
        if body["from"] == "mdc":
            text = mdc_body(RULES_DIR / body["file"])
        elif body["from"] == "file":
            text = read_body_file(RULES_DIR / "agents.d" / body["file"])
        else:
            raise GenerateError(f"{section['title']}: unknown body.from {body['from']!r}")
        parts += [f"## {section['title']}", "", f"Source: {section['source']}", "", text, ""]

    parts.append(read_body_file(RULES_DIR / manifest["trailer"]))
    return "\n".join(parts).rstrip("\n") + "\n"


def load_manifest() -> dict:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GenerateError(f"cannot read {MANIFEST}: {exc}") from exc
    except ValueError as exc:
        raise GenerateError(f"{MANIFEST} is not valid JSON: {exc}") from exc
    for key in ("base", "intro", "trailer", "sections"):
        if key not in manifest:
            raise GenerateError(f"{MANIFEST} is missing the {key!r} key")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="generate-agents-md.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Write AGENTS.md.")
    mode.add_argument("--check", action="store_true", help="Exit 1 if AGENTS.md is out of date.")
    mode.add_argument("--stdout", action="store_true", help="Print the render and write nothing.")
    parser.add_argument("--layer", action="append", metavar="LAYER",
                        help="Keep only sections in this layer (repeatable). Default: all.")
    args = parser.parse_args()

    layers = set(args.layer) if args.layer else None
    try:
        manifest = load_manifest()
        rendered = render(manifest, layers)
    except GenerateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.stdout:
        sys.stdout.write(rendered)
        return 0

    current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    if rendered == current:
        print(f"{OUTPUT} is up to date.")
        return 0

    diff = list(difflib.unified_diff(
        current.splitlines(), rendered.splitlines(),
        f"{OUTPUT.name} (on disk)", f"{OUTPUT.name} (generated)", lineterm="", n=2))

    if args.apply:
        OUTPUT.write_text(rendered, encoding="utf-8")
        print(f"Wrote {OUTPUT} ({len(diff)} diff lines against the previous file).")
        return 0

    print("\n".join(diff))
    verb = "is out of date" if args.check else "would change"
    print(f"\n{OUTPUT} {verb}. Run: {Path(__file__).name} --apply", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
