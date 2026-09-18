#!/usr/bin/env python3
"""Mechanical caveman-lite pass on ~/.agents/skills.

Guardrails:
- Never change YAML `name:`.
- Never touch templates (templates.md, *template*, template/ trees).
- Never touch scripts, agents yaml, binary/vendor assets.
- Skip playwright-cli (external package symlink, not an alias directory).
- Do not rewrite `description:` (URL-safe provenance strip is disabled).

Future agents: kb/_shared/How-to-compact-kb-skills-and-offline-reference.md
"""

from __future__ import annotations

import re
from pathlib import Path

SKILLS = Path("${HOME}/.agents/skills")
VENDOR_NAMES = {"playwright-cli"}

TEMPLATE_DIR_PARTS = {"template", "templates"}
TEMPLATE_NAME_RE = re.compile(r"template", re.I)

SKIP_SUFFIX = {
    ".py",
    ".pyc",
    ".js",
    ".css",
    ".json",
    ".xml",
    ".yml",
    ".yaml",
    ".png",
    ".jpg",
    ".lock",
    ".gitignore",
    ".gitkeep",
    ".sh",
    ".tsx",
    ".ts",
    ".scss",
    ".mjs",
    ".html",
    ".patch",
}
SKIP_DIR_PARTS = {"scripts", "agents", "__pycache__", ".git"}

FENCE_SPLIT = re.compile(r"(^```[^\n]*\n.*?^```[ \t]*\n?)", re.M | re.S)
BLANK3 = re.compile(r"\n{3,}")
PROVENANCE_DESC = re.compile(
    r"\s*Installed for Cursor IDE from \S+\.?",
    re.I,
)
ADAPTED_LINE = re.compile(
    r"^Adapted from \[[^\]]+\]\([^)]+\)(?: v[\d.]+)?\.\s*$",
    re.M,
)


def tokens(text: str) -> int:
    return max(1, len(text) // 4)


def is_template(path: Path, root: Path) -> bool:
    rel_parts = path.relative_to(root).parts
    if any(p.lower() in TEMPLATE_DIR_PARTS for p in rel_parts):
        return True
    if TEMPLATE_NAME_RE.search(path.name):
        return True
    return False


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
    s = ADAPTED_LINE.sub("", prose)
    s = BLANK3.sub("\n\n", s)
    return s


def split_frontmatter(text: str) -> tuple[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    return text[: end + 5], text[end + 5 :]


def compact_description_block(fm: str) -> str:
    """Strip install provenance from description only. Leave name and the rest."""
    # Folded description: description: >- ... until next top-level key
    m = re.search(
        r"^(description:\s*>-?\n)((?:^[ \t].+\n)+)",
        fm,
        re.M,
    )
    if m:
        prefix, body = m.group(1), m.group(2)
        raw = re.sub(r"^[ \t]+", "", body, flags=re.M).replace("\n", " ").strip()
        stripped = PROVENANCE_DESC.sub("", raw).strip()
        if len(stripped) < 80 or stripped == raw:
            return fm
        # keep folded form, wrap ~88 cols
        indent = "  "
        lines = []
        words = stripped.split()
        cur = indent
        for w in words:
            if len(cur) + 1 + len(w) > 88 and cur != indent:
                lines.append(cur.rstrip())
                cur = indent + w
            else:
                cur = w if cur == indent else cur + " " + w
        if cur.strip():
            lines.append(cur.rstrip())
        new_body = "\n".join(lines) + "\n"
        return fm[: m.start()] + prefix + new_body + fm[m.end() :]

    m = re.search(r'^description:\s*"([^"]*)"', fm, re.M)
    if m:
        raw = m.group(1)
        stripped = PROVENANCE_DESC.sub("", raw).strip()
        if len(stripped) < 80 or stripped == raw:
            return fm
        return fm[: m.start()] + f'description: "{stripped}"' + fm[m.end() :]

    m = re.search(r"^description:\s*(.+)$", fm, re.M)
    if m and not m.group(1).startswith(">") and not m.group(1).startswith("|"):
        raw = m.group(1).strip().strip('"').strip("'")
        stripped = PROVENANCE_DESC.sub("", raw).strip()
        if len(stripped) < 80 or stripped == raw:
            return fm
        return fm[: m.start()] + f"description: {stripped}" + fm[m.end() :]
    return fm


def compact_skill_md(text: str) -> str:
    split = split_frontmatter(text)
    if not split:
        return compact_file_body(text)
    fm, body = split
    # Do not rewrite description or name. Provenance-only description
    # stripping is opt-in and easy to mangle URLs (git.example.com).
    body2 = compact_file_body(body)
    return fm + body2


def compact_file_body(text: str) -> str:
    text = map_prose(text, compact_prose)
    text = BLANK3.sub("\n\n", text)
    return text.rstrip() + "\n" if text.strip() else text


def unique_skill_roots() -> list[Path]:
    by_ino: dict[int, Path] = {}
    for p in SKILLS.glob("*/SKILL.md"):
        ino = p.stat().st_ino
        if ino not in by_ino:
            by_ino[ino] = p.parent
    return sorted(by_ino.values(), key=lambda p: p.name)


def extra_md_files(root: Path) -> list[Path]:
    out = []
    for f in root.rglob("*.md"):
        if f.name == "SKILL.md":
            continue
        if any(part in SKIP_DIR_PARTS for part in f.relative_to(root).parts):
            continue
        if is_template(f, root):
            continue
        out.append(f)
    return out


def main() -> None:
    skill_before = skill_after = extra_before = extra_after = 0
    skill_changed = extra_changed = 0
    skipped = []
    for root in unique_skill_roots():
        if root.name in VENDOR_NAMES or root.resolve().as_posix().find("/node_modules/") >= 0:
            skipped.append(root.name)
            continue
        skill = root / "SKILL.md"
        original = skill.read_text(encoding="utf-8")
        compact = compact_skill_md(original)
        skill_before += tokens(original)
        skill_after += tokens(compact)
        if compact != original:
            skill.write_text(compact, encoding="utf-8")
            skill_changed += 1
        for f in extra_md_files(root):
            original = f.read_text(encoding="utf-8")
            compact = compact_file_body(original)
            extra_before += tokens(original)
            extra_after += tokens(compact)
            if compact != original:
                f.write_text(compact, encoding="utf-8")
                extra_changed += 1
    print(
        f"SKILL.md {skill_before} -> {skill_after} changed={skill_changed} "
        f"extras {extra_before} -> {extra_after} changed={extra_changed} "
        f"skipped={skipped}"
    )


if __name__ == "__main__":
    main()
