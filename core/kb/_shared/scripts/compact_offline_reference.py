#!/usr/bin/env python3
"""Mechanical caveman-lite pass on kb/offline-reference.

Keeps API signatures, tables, and fenced code exact. Strips conversion
artifacts, marketing, and wrapper sentences. Regenerates each catalog
llm-index.md (v2: path<TAB>tokens<TAB>topic<TAB>skills<TAB>keywords).

Future agents: kb/_shared/How-to-compact-kb-skills-and-offline-reference.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path("${HOME}/.agents/kb/offline-reference")
SKIP_NAMES = {"llm-index.md", "index.md", "README.md"}

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from llm_index import write_bucket_indexes  # noqa: E402

FENCE_SPLIT = re.compile(r"(^```[^\n]*\n.*?^```[ \t]*\n?)", re.M | re.S)

GODOT_ADMONITION = re.compile(
    r"^(Tip|Note|Warning|Caution|Important|Attention|See also|See Also)\s*$",
    re.M,
)
PILCROW_CHARS = "\uf0c1\uf0b6\u00b6\u1f517"
SPHINX_FOOTER = re.compile(
    r"\n(?:Previous\nNext\n)+\n*"
    r"(?:### User-contributed notes\n+"
    r"Please read the User-contributed notes policy before submitting a comment\.\n+"
    r"(?:Previous\nNext\n)+)?"
    r"(?:© Copyright[^\n]*\n)?"
    r"(?:Built with\nSphinx\nusing a\ntheme\nprovided by\nRead the Docs\n\.?\n*)?"
    r"\Z",
)
USER_NOTES = re.compile(
    r"\n### User-contributed notes\n+"
    r"Please read the User-contributed notes policy before submitting a comment\.\n"
    r"(?:Previous\nNext\n)*"
    r"(?:© Copyright[^\n]*\n)?"
    r"(?:Built with\nSphinx\nusing a\ntheme\nprovided by\nRead the Docs\n\.?\n*)?"
    r"\Z",
)
PREV_NEXT = re.compile(r"^(Previous|Next)\s*$", re.M)
LINK_EMOJI = "\U0001f517"
READY_API = re.compile(r"^You are now ready to use the API\.\s*\n?", re.M)
ADD_GRADLE = re.compile(
    r"^Add the following to your `build\.gradle` file:\s*\n+",
    re.M,
)
ADD_IMPORT = re.compile(r"^Add the `import` statement to your code:\s*\n+", re.M)
THIS_PAGE_WILL = re.compile(
    r"^This page will show you[^\n]*\n",
    re.M | re.I,
)
IF_YOU_WOULD_LIKE = re.compile(
    r"^If you would like to get an introduction to[^\n]*\n",
    re.M | re.I,
)
THIS_DOC_COVERS = re.compile(
    r"^This documentation covers[^\n]*\n+"
    r"(?:- \[[^\n]+\]\([^\n]+\)[^\n]*\n+)*",
    re.M,
)
MARKET_NOTE = re.compile(
    r"^> \*\*Note:\*\* \[Enonic Market\].*\n(?:^> .*\n)*",
    re.M,
)
DEVELOPERS_MAY_ADAPT = re.compile(
    r"^Developers may adapt the platform[^\n]+\n",
    re.M,
)
BLANK3 = re.compile(r"\n{3,}")


def tokens(text: str) -> int:
    return max(1, len(text) // 4)


def map_prose(text: str, fn) -> str:
    parts = FENCE_SPLIT.split(text)
    out = []
    for part in parts:
        if part.startswith("```"):
            out.append(part)
        else:
            out.append(fn(part))
    return "".join(out)


def compact_prose(prose: str) -> str:
    s = prose
    for ch in ("\uf0c1", "\uf0b6", "\u00b6", "\U0001f517"):
        s = s.replace(ch, "")
    s = GODOT_ADMONITION.sub("", s)
    s = READY_API.sub("", s)
    s = ADD_GRADLE.sub("", s)
    s = ADD_IMPORT.sub("", s)
    s = THIS_PAGE_WILL.sub("", s)
    s = IF_YOU_WOULD_LIKE.sub("", s)
    s = THIS_DOC_COVERS.sub("", s)
    s = MARKET_NOTE.sub("", s)
    s = DEVELOPERS_MAY_ADAPT.sub("", s)
    s = re.sub(r"^[^\n]*Demo available on the Asset Library\.\s*\n", "", s, flags=re.M)
    s = PREV_NEXT.sub("", s)
    s = BLANK3.sub("\n\n", s)
    return s


def compact_file(text: str) -> str:
    text = map_prose(text, compact_prose)
    text = USER_NOTES.sub("\n", text)
    text = SPHINX_FOOTER.sub("\n", text)
    text = BLANK3.sub("\n\n", text)
    return text.rstrip() + "\n"


def write_llm_index(catalog: Path) -> None:
    write_bucket_indexes(catalog)


def main() -> None:
    before = after = files = changed = 0
    for catalog in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name != "scripts"):
        cat_before = cat_after = 0
        for f in catalog.rglob("*.md"):
            if f.name in SKIP_NAMES:
                continue
            original = f.read_text(encoding="utf-8")
            compact = compact_file(original)
            b, a = tokens(original), tokens(compact)
            cat_before += b
            cat_after += a
            files += 1
            if compact != original:
                f.write_text(compact, encoding="utf-8")
                changed += 1
        write_llm_index(catalog)
        before += cat_before
        after += cat_after
        print(f"{catalog.name:22s} {cat_before:7d} -> {cat_after:7d}  delta={cat_after - cat_before}")
    print(f"{'TOTAL':22s} {before:7d} -> {after:7d}  files={files} changed={changed}")


if __name__ == "__main__":
    main()
