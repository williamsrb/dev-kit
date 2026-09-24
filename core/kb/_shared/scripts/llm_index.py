#!/usr/bin/env python3
"""Build llm-index.md files for owned KB buckets and offline-reference catalogs.

v2 rows: path<TAB>tokens<TAB>topic<TAB>skills<TAB>keywords

A bucket or catalog with two or more child folders becomes a thin chooser
(folder rows point at nested llm-index.md) plus leftover root files. Agents
open the chooser, then only the matching folder index, then matching How-tos.

when_skills from frontmatter is documentation. The skills column keeps only
canonical skill directory names (aliases resolved). Globs, URLs, and paths
are dropped.
"""

from __future__ import annotations

import re
from pathlib import Path

KB = Path("${HOME}/.agents/kb")
SKILLS = Path("${HOME}/.agents/skills")

SKIP_NAMES = {"llm-index.md", "index.md"}
SKIP_DIRS = {"scripts", "__pycache__", ".git"}
WRAPPER_DIRS = {"docs", "from-html", "learn"}

HEADER = (
    "# LLM_INDEX|machine|v2|path<TAB>tokens<TAB>topic<TAB>skills<TAB>keywords\n"
    "# Chooser rows end in llm-index.md — open that folder index, not sibling files.\n\n"
)

WORD_STOP = {
    "the", "and", "for", "how", "to", "a", "an", "of", "on", "in", "or",
    "with", "from", "via", "when", "without", "not", "do", "is", "are",
    "this", "that", "your", "into", "vs", "as",
}

LEADING_VERBS = {
    "use", "test", "verify", "capture", "check", "post", "prove", "run",
    "list", "search", "gate", "read", "edit", "add", "fix", "author",
    "write", "choose", "compact", "handle", "resolve", "enable",
}

CATALOG_HINTS = {
    "content-studio-stable": "xp8 cs6",
    "content-studio-5.x": "xp7 cs5",
    "react4xp-stable": "xp8",
    "react4xp-6.x": "xp7",
    "react4xp-5.x": "xp7",
    "xp8": "xp8",
    "xp7": "xp7",
    "godot-2d": "godot-2d",
    "godot-3d": "godot-3d",
}

FOLDER_NOT_TOPIC = {
    "_shared", "scripts", "docs", "from-html", "learn", "stable", "5.x", "6.x",
}


def catalog_hints(rel_root: Path) -> str:
    parts = rel_root.parts
    if "offline-reference" not in parts:
        return ""
    idx = parts.index("offline-reference")
    if idx + 1 >= len(parts):
        return ""
    return CATALOG_HINTS.get(parts[idx + 1], "")

_SKILL_MAP: dict[str, str] | None = None


def tokens(text: str) -> int:
    return max(1, len(text) // 4)


def catalog_skill_names(skills_root: Path = SKILLS) -> dict[str, str]:
    """Map canonical directory name and aliases → canonical directory name."""
    mapping: dict[str, str] = {}
    for skill in sorted(skills_root.glob("*/SKILL.md")):
        canonical = skill.parent.name
        mapping[canonical] = canonical
        head = skill.read_text(encoding="utf-8", errors="replace")[:2500]
        match = re.search(r"^  aliases:\s*(.+)$", head, re.M)
        if not match:
            match = re.search(r"^aliases:\s*(.+)$", head, re.M)
        if match:
            for alias in match.group(1).split(","):
                alias = alias.strip().strip("\"'").rstrip(".")
                if alias:
                    mapping[alias] = canonical
    return mapping


def skill_map() -> dict[str, str]:
    global _SKILL_MAP
    if _SKILL_MAP is None:
        _SKILL_MAP = catalog_skill_names()
    return _SKILL_MAP


def parse_when_skills(text: str) -> list[str]:
    if not text.startswith("---\n"):
        return []
    end = text.find("\n---\n", 4)
    if end < 0:
        return []
    match = re.search(r"^when_skills:\s*\[([^\]]*)\]", text[4:end], re.M)
    if not match:
        return []
    return [item.strip().strip("'\"") for item in match.group(1).split(",") if item.strip()]


def sanitize_skills(raw: list[str], mapping: dict[str, str] | None = None) -> str:
    mapping = mapping if mapping is not None else skill_map()
    seen: list[str] = []
    for item in raw:
        canonical = mapping.get(item)
        if canonical and canonical not in seen:
            seen.append(canonical)
    return " ".join(seen)


def filename_tokens(path: Path) -> list[str]:
    stem = re.sub(r"^how-to-", "", path.stem.lower())
    parts = [part for part in re.split(r"[-_]+", stem) if part and part not in WORD_STOP]
    compounds = [f"{left}-{right}" for left, right in zip(parts, parts[1:])]
    return parts + compounds


def h1_keywords(text: str) -> list[str]:
    match = re.search(r"^# +(.+)$", text, re.M)
    if not match:
        return []
    heading = match.group(1).lower()
    heading = heading.replace("\u00b6", "").replace("\uf0b6", "")
    words = []
    for word in re.findall(r"[a-z0-9]{3,}", heading):
        if word in WORD_STOP:
            continue
        words.append(word)
    compounds = [f"{left}-{right}" for left, right in zip(words, words[1:])]
    return words + compounds


def keywords(path: Path, text: str, limit: int = 24, extra: str = "") -> str:
    seen: list[str] = []
    extras = extra.split() if extra else []
    for word in extras + filename_tokens(path) + h1_keywords(text):
        if word in seen:
            continue
        seen.append(word)
        if len(seen) >= limit:
            break
    return " ".join(seen) if seen else path.stem.lower()


def topic_for(path: Path, root: Path) -> str:
    rel_dirs = path.relative_to(root).parts[:-1]
    for part in reversed(rel_dirs):
        if part in FOLDER_NOT_TOPIC:
            continue
        if re.fullmatch(r"\d+\.x", part):
            continue
        return part
    parts: list[str] = []
    stem = re.sub(r"^how-to-", "", path.stem.lower())
    for part in re.split(r"[-_]+", stem):
        if not part or part in WORD_STOP or part in LEADING_VERBS:
            continue
        parts.append(part)
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    if parts:
        return parts[0]
    return root.name


def skip_markdown(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return True
    if path.name == "README.md" and "offline-reference" in path.parts:
        return True
    return False


def has_markdown(folder: Path) -> bool:
    for item in folder.rglob("*.md"):
        if skip_markdown(item):
            continue
        if any(part in SKIP_DIRS for part in item.relative_to(folder).parts):
            continue
        return True
    return False


def iter_markdown(folder: Path):
    for item in sorted(folder.rglob("*.md")):
        if skip_markdown(item):
            continue
        if any(part in SKIP_DIRS for part in item.relative_to(folder).parts):
            continue
        yield item


def child_dirs(folder: Path) -> list[Path]:
    return sorted(
        child
        for child in folder.iterdir()
        if child.is_dir() and child.name not in SKIP_DIRS and has_markdown(child)
    )


def find_split(root: Path) -> tuple[list[Path], list[Path]]:
    """Return (folder units to index separately, leftover md files at root)."""
    cursor = root
    while True:
        dirs = child_dirs(cursor)
        files = [
            child
            for child in sorted(cursor.iterdir())
            if child.is_file() and child.suffix == ".md" and not skip_markdown(child)
        ]
        if len(dirs) == 1 and not files and dirs[0].name in WRAPPER_DIRS:
            cursor = dirs[0]
            continue
        break
    leftover = [
        child
        for child in sorted(root.iterdir())
        if child.is_file() and child.suffix == ".md" and not skip_markdown(child)
    ]
    if len(dirs) >= 2:
        return dirs, leftover
    return [], leftover if leftover and not dirs else leftover


def leaf_row(path: Path, rel_root: Path, mapping: dict[str, str]) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(rel_root).as_posix()
    skills = sanitize_skills(parse_when_skills(text), mapping)
    hints = catalog_hints(rel_root)
    return (
        f"{rel}\t{tokens(text)}\t{topic_for(path, rel_root)}\t{skills}\t"
        f"{keywords(path, text, extra=hints)}"
    )


def aggregate_chooser_row(folder: Path, parent: Path, file_rows: list[str]) -> str:
    rel = (folder / "llm-index.md").relative_to(parent).as_posix()
    topic = folder.name
    tok = 0
    skills: list[str] = []
    kws: list[str] = []
    for row in file_rows:
        parts = row.split("\t")
        if len(parts) < 5:
            continue
        tok += int(parts[1]) if parts[1].isdigit() else 0
        for skill in parts[3].split():
            if skill not in skills:
                skills.append(skill)
        if len(kws) < 24:
            for word in parts[4].split():
                if word not in kws:
                    kws.append(word)
                if len(kws) >= 24:
                    break
    return f"{rel}\t{max(tok, 1)}\t{topic}\t{' '.join(skills)}\t{' '.join(kws[:24])}"


def write_index(path: Path, rows: list[str]) -> None:
    path.write_text(HEADER + "\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def write_bucket_indexes(root: Path, mapping: dict[str, str] | None = None) -> None:
    mapping = mapping if mapping is not None else skill_map()
    split_units, leftover = find_split(root)
    if split_units:
        chooser: list[str] = []
        for unit in split_units:
            rows = [leaf_row(path, unit, mapping) for path in iter_markdown(unit)]
            write_index(unit / "llm-index.md", rows)
            chooser.append(aggregate_chooser_row(unit, root, rows))
        for path in leftover:
            chooser.append(leaf_row(path, root, mapping))
        chooser.sort()
        write_index(root / "llm-index.md", chooser)
        return
    rows = [leaf_row(path, root, mapping) for path in iter_markdown(root)]
    write_index(root / "llm-index.md", rows)


def write_owned_indexes() -> None:
    mapping = skill_map()
    for bucket in ["_shared", "calibration", "implementation", "testing", "validation", "worklog"]:
        write_bucket_indexes(KB / bucket, mapping)


def write_offline_indexes() -> None:
    mapping = skill_map()
    root = KB / "offline-reference"
    for catalog in sorted(path for path in root.iterdir() if path.is_dir() and path.name != "scripts"):
        write_bucket_indexes(catalog, mapping)


if __name__ == "__main__":
    write_owned_indexes()
    write_offline_indexes()
