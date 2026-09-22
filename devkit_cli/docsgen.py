"""`devkit docs generate` — the generated parts of the docs tree.

Only the mechanical sections are generated: the CLI reference and the profile
table. Prose is written by hand, because generated prose is how a docs tree ends
up saying nothing. `--check` exits 1 on any diff, which is the gate that catches
a CLI change nobody documented.
"""

from __future__ import annotations

import argparse
import difflib
import re

from . import manifest
from .common import repo_file
from .errors import DevkitError

MARKER_START = "<!-- devkit:generated:{name} -->"
MARKER_END = "<!-- /devkit:generated:{name} -->"

# Option help wraps at 80. Usage is rendered unwrapped: argparse 3.12 (CI) and
# 3.14 (a local install) split the same usage line at different columns.
_HELP_WIDTH = 80
_USAGE_WIDTH = 10_000


class _StableHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, prog: str, **kwargs) -> None:
        kwargs["width"] = _HELP_WIDTH
        super().__init__(prog, **kwargs)

    def _format_usage(self, usage, actions, groups, prefix):
        saved = self._width
        self._width = _USAGE_WIDTH
        try:
            return super()._format_usage(usage, actions, groups, prefix)
        finally:
            self._width = saved


def _pin_help_formatter(parser: argparse.ArgumentParser) -> None:
    parser.formatter_class = _StableHelpFormatter
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            for sub in choices.values():
                _pin_help_formatter(sub)


def _cli_reference() -> str:
    from .cli import build_parser
    parser = build_parser()
    _pin_help_formatter(parser)
    lines = ["```", parser.format_help().rstrip(), "```", ""]

    # Only a subparser action maps names to parsers. A flag with a choices
    # *list* is an ordinary option, not a group to recurse into.
    actions = [a for a in parser._actions if isinstance(getattr(a, "choices", None), dict)]
    for action in actions:
        for name, sub in action.choices.items():
            lines += [f"### `devkit {name}`", "", "```",
                      sub.format_help().rstrip(), "```", ""]
            nested = [a for a in sub._actions
                      if isinstance(getattr(a, "choices", None), dict)]
            for inner in nested:
                for sub_name, sub_parser in inner.choices.items():
                    lines += [f"#### `devkit {name} {sub_name}`", "", "```",
                              sub_parser.format_help().rstrip(), "```", ""]
    return "\n".join(lines)


def _profile_table() -> str:
    rows = ["| Profile | Extends | Skills | Rules | Vendors | Required tools |",
            "|---------|---------|--------|-------|---------|----------------|"]
    for name in manifest.available():
        profile = manifest.load(name)
        lineage = profile.get("lineage", [name])
        parent = lineage[-2] if len(lineage) > 1 else "—"
        vendors = ", ".join(i["vendor"] for i in profile.get("instances", []))
        required = len(manifest.provided_binaries(profile, include_optional=False))
        rows.append(f"| `{name}` | `{parent}` | {len(profile.get('skills', []))} | "
                    f"{len(profile.get('rules', []))} | {vendors} | {required} |")
    return "\n".join(rows)


GENERATORS = {
    "cli-reference": _cli_reference,
    "profile-table": _profile_table,
}


def _apply_blocks(text: str, name: str, body: str) -> str:
    start, end = MARKER_START.format(name=name), MARKER_END.format(name=name)
    if start not in text or end not in text:
        return text
    head = text.split(start)[0]
    tail = text.split(end, 1)[1]
    return f"{head}{start}\n\n{body.rstrip()}\n\n{end}{tail}"


def cmd_generate(args) -> int:
    docs_root = repo_file("docs")
    targets = sorted(docs_root.rglob("*.md")) if docs_root.is_dir() else []
    targets += [repo_file("README.md")] if repo_file("README.md").is_file() else []
    if not targets:
        raise DevkitError("no documentation files found",
                          "create docs/ and README.md first")

    bodies = {name: generator() for name, generator in GENERATORS.items()}

    stale: list[str] = []
    for path in targets:
        original = path.read_text(encoding="utf-8")
        updated = original
        for name, body in bodies.items():
            updated = _apply_blocks(updated, name, body)
        if updated == original:
            continue
        stale.append(str(path.relative_to(repo_file(""))))
        if not args.check:
            path.write_text(updated, encoding="utf-8")
        else:
            diff = list(difflib.unified_diff(
                original.splitlines(), updated.splitlines(),
                f"{path.name} (committed)", f"{path.name} (generated)", lineterm="", n=1))
            print("\n".join(diff[:40]))

    orphans = unreachable_docs()
    if orphans and args.check:
        for orphan in orphans:
            print(f"  unreachable from README.md: {orphan}")

    if args.check:
        if orphans:
            print(f"\n{len(orphans)} doc(s) unreachable from README.md")
            print("fix:   link them from README.md, or delete them")
            return 1
        if stale:
            print(f"\ndocs are stale: {', '.join(stale)}")
            print("fix:   devkit docs generate")
            return 1
        print(f"docs: up to date ({len(targets)} file(s) checked).")
        return 0

    if stale:
        print(f"regenerated: {', '.join(stale)}")
    else:
        print(f"docs: already up to date ({len(targets)} file(s) checked).")
    return 0


def unreachable_docs() -> list[str]:
    """Every file under docs/ must be reachable from README.md."""
    readme = repo_file("README.md")
    docs_root = repo_file("docs")
    if not readme.is_file() or not docs_root.is_dir():
        return []
    linked, frontier = set(), [readme]
    while frontier:
        current = frontier.pop()
        try:
            text = current.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in re.finditer(r"\]\(([^)#\s]+)", text):
            target = (current.parent / match.group(1)).resolve()
            if target.is_file() and target.suffix == ".md" and target not in linked:
                linked.add(target)
                frontier.append(target)
    return sorted(str(p.relative_to(repo_file("")))
                  for p in docs_root.rglob("*.md") if p.resolve() not in linked)
