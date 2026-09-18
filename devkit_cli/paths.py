"""`devkit lint-paths` — the path contract gate.

The finding this enforces: `~` is a shell construct, not a path. It expands only
in a shell, unquoted, at word start. A renderer handed `[x](~/.agents/foo)` reads
the relative path `./~/.agents/foo`, which is the broken link the visual apps
show. So `${HOME}` is the only home-anchored token in kit source, and it is
rendered per context at install time.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from .common import REPO_ROOT, load_json, repo_file
from .errors import DevkitError

SKIP_DIR_NAMES = {".git", "__pycache__", "node_modules", ".venv"}

# `[x](~/foo)` inside backticks is a code sample of a broken link, not a broken
# link. Stripping inline code before matching keeps a document that explains a
# rule from tripping it.
INLINE_CODE = re.compile(r"`[^`]*`")
PROSE_CATEGORIES = {"prose"}


class Violation:
    def __init__(self, path: Path, line_no: int, rule: dict, line: str) -> None:
        self.path, self.line_no, self.rule, self.line = path, line_no, rule, line

    def __str__(self) -> str:
        rel = self.path.relative_to(REPO_ROOT) if self.path.is_relative_to(REPO_ROOT) else self.path
        return (f"{rel}:{self.line_no}: {self.rule['id']}: {self.rule['message']}\n"
                f"    {self.line.strip()[:120]}\n"
                f"    fix: {self.rule['fix']}")


def _category(path: Path, contract: dict) -> str | None:
    for name in ("machine_consumed", "prose", "shell", "scripts"):
        block = contract.get(name) or {}
        if path.suffix in set(block.get("suffixes", [])):
            return name
        if path.name in set(block.get("names", [])):
            return name
    return None


# A .sh file is both "shell" and "scripts"; the narrower category wins for
# _category(), so scripts-scoped rules must still reach shell files.
CATEGORY_PARENTS = {"shell": {"scripts"}}


def _applies(rule: dict, category: str | None) -> bool:
    scope = rule.get("applies_to", "all")
    if scope == "all" or scope == category:
        return True
    return scope in CATEGORY_PARENTS.get(category or "", set())


def _iter_files(roots: list[Path], contract: dict):
    ignore = contract.get("ignore", [])
    for root in roots:
        candidates = [root] if root.is_file() else [
            p for p in root.rglob("*")
            if p.is_file() and not SKIP_DIR_NAMES & set(p.parts)
        ]
        for path in candidates:
            rel = str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)
            if any(fnmatch.fnmatch(rel, pattern) for pattern in ignore):
                continue
            yield path, rel


def scan(roots: list[Path], contract: dict) -> list[Violation]:
    compiled = [(rule, re.compile(rule["pattern"])) for rule in contract["rules"]]
    allow = contract.get("allow", {})
    violations: list[Violation] = []

    for path, rel in _iter_files(roots, contract):
        category = _category(path, contract)
        if category is None:
            continue
        exempt = set(allow.get(rel, []))
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(lines, 1):
            haystack = INLINE_CODE.sub("", line) if category in PROSE_CATEGORIES else line
            for rule, pattern in compiled:
                if rule["id"] in exempt or not _applies(rule, category):
                    continue
                if pattern.search(haystack):
                    violations.append(Violation(path, line_no, rule, line))
    return violations


def cmd_lint_paths(args) -> int:
    contract_path = Path(args.contract) if args.contract else repo_file("path-contract.json")
    contract = load_json(contract_path, "path contract")

    roots = [Path(p).resolve() for p in args.paths] if args.paths else [REPO_ROOT]
    for root in roots:
        if not root.exists():
            raise DevkitError(f"{root} does not exist")

    violations = scan(roots, contract)
    if not violations:
        where = ", ".join(str(r.name) for r in roots)
        print(f"lint-paths: clean ({where}).")
        return 0

    for violation in violations:
        print(violation)
        print()
    by_rule: dict[str, int] = {}
    for violation in violations:
        by_rule[violation.rule["id"]] = by_rule.get(violation.rule["id"], 0) + 1
    summary = ", ".join(f"{count} {rule}" for rule, count in sorted(by_rule.items()))
    print(f"lint-paths: {len(violations)} violation(s) — {summary}")
    return 1
