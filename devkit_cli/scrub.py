"""Keep names the kit must not track out of core/.

`devkit export` copies the maintainer's harness into core/. The harness keeps
whatever names its owner works with; this module drops, renames or rewrites them
on the way out. The rules are data in `<source>/config/export-scrub.json`, never
in this repository, because rules that name a trademark would themselves track
it. With no rules file the export copies as before.

Rules file (JSON, every key optional, regexes are Python regexes):

    drop_paths        matched against the export-relative path; a match is not exported
    path_rewrites     [regex, replacement] pairs applied to the exported path
    rewrites          [regex, replacement, optional path regex], applied in order,
                      multiline, to the text of every file that decodes as UTF-8
    no_rewrite_paths  paths whose text is copied untouched (vendored code)
    forbidden         [{"pattern": regex, "exempt": optional path regex}], case
                      insensitive; whatever survives the rewrites fails the export

Patterns that must also match a repository path start with `(?:core/)?`, so one
file serves both the export and a history rewrite.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .errors import DevkitError

RULES_PATH = "config/export-scrub.json"


class Rules:
    def __init__(self, data: dict):
        self._drop = [re.compile(p) for p in data.get("drop_paths", [])]
        self._path_rewrites = [(re.compile(a), b) for a, b in data.get("path_rewrites", [])]
        self._rewrites = [
            (re.compile(rule[0], re.MULTILINE), rule[1], re.compile(rule[2]) if len(rule) > 2 else None)
            for rule in data.get("rewrites", [])
        ]
        self._no_rewrite = [re.compile(p) for p in data.get("no_rewrite_paths", [])]
        self._forbidden = [
            (re.compile(f["pattern"], re.IGNORECASE), re.compile(f["exempt"]) if f.get("exempt") else None)
            for f in data.get("forbidden", [])
        ]

    def dropped(self, rel: str) -> bool:
        return any(p.search(rel) for p in self._drop)

    def rename(self, rel: str) -> str:
        for pattern, replacement in self._path_rewrites:
            rel = pattern.sub(replacement, rel)
        return rel

    def text(self, text: str, rel: str) -> str:
        if any(p.search(rel) for p in self._no_rewrite):
            return text
        for pattern, replacement, only in self._rewrites:
            if only is None or only.search(rel):
                text = pattern.sub(replacement, text)
        return text

    def leaks(self, text: str, rel: str) -> list[tuple[int, str]]:
        """(line, excerpt) for each forbidden match left in `text`; line 0 is the path."""
        found: list[tuple[int, str]] = []
        for pattern, exempt in self._forbidden:
            if exempt is not None and exempt.search(rel):
                continue
            if pattern.search(rel):
                found.append((0, rel))
            for match in pattern.finditer(text):
                start = max(0, match.start() - 30)
                found.append((text.count("\n", 0, match.start()) + 1,
                              text[start:match.end() + 30].replace("\n", " ")))
        return found


def load(source: Path) -> Rules | None:
    path = source / RULES_PATH
    if not path.is_file():
        return None
    try:
        return Rules(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, KeyError, TypeError, re.error) as error:
        raise DevkitError(f"{path} is not a valid scrub rules file: {error}",
                          "fix the file; the export will not run without valid rules")
