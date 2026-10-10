"""Flavors: skills-only layers for `devkit project`.

A flavor is one JSON file in the kit's `flavors/` or a repo's `harness/flavors/`.
It names skills, not behaviour: no colour, deps, MCP or instances, so it is never
a profile type. A flavor includes other flavors or profile types, and a repo
flavor of the same name overrides the kit's.

This module imports only `manifest`, `common` and `errors`, so `project` can
use it without a cycle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import manifest
from .common import load_json
from .errors import DevkitError

KIT_DIR = "flavors"
REPO_DIR = "harness/flavors"
TIER_KIT, TIER_REPO = "kit", "repo"

# Same rule as project layer names: a repo-controlled file must never reach a
# path outside core/skills.
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_KEYS = frozenset({"_comment", "name", "description", "includes", "skills", "exclude", "detect"})
_LIST_KEYS = ("includes", "skills", "exclude")


@dataclass(frozen=True)
class Flavor:
    name: str
    description: str
    includes: tuple[str, ...]
    skills: tuple[str, ...]
    exclude: tuple[str, ...]
    tier: str
    path: Path


@dataclass(frozen=True)
class Expanded:
    skills: tuple[str, ...]
    lineage: frozenset[str]     # profile types reached through includes


def _bad(flavor: str, path: Path, message: str, fix: str) -> DevkitError:
    return DevkitError(f"flavor {flavor!r} ({path}): {message}", fix)


def load_flavor(path: Path, tier: str, kit_root: Path) -> Flavor:
    stem = path.stem
    data = load_json(path, f"flavor {stem}")
    if not isinstance(data, dict):
        raise _bad(stem, path, "must be a JSON object", 'start from {"name": "<stem>", "skills": []}')
    unknown = sorted(set(data) - _KEYS)
    if unknown:
        raise _bad(stem, path, f"unknown key(s): {', '.join(unknown)}",
                   f"allowed keys: {', '.join(sorted(_KEYS))}")
    name = data.get("name")
    if name != stem:
        raise _bad(stem, path, f"\"name\" is {name!r} but the file is {path.name}",
                   f'set "name": "{stem}", or rename the file to match')
    if not _NAME.match(stem):
        raise _bad(stem, path, "name must match [A-Za-z0-9][A-Za-z0-9_.-]*",
                   "rename the file and its \"name\"")
    description = data.get("description", "")
    if not isinstance(description, str):
        raise _bad(stem, path, "\"description\" must be a string", "make it a string")
    if "detect" in data and not isinstance(data["detect"], dict):
        raise _bad(stem, path, "\"detect\" must be an object (it is ignored for now)",
                   "make it an object or remove it")

    lists: dict[str, tuple[str, ...]] = {}
    for key in _LIST_KEYS:
        value = data.get(key, [])
        if not (isinstance(value, list)
                and all(isinstance(x, str) and _NAME.match(x) for x in value)):
            raise _bad(stem, path, f"\"{key}\" must be a list of names ([A-Za-z0-9][A-Za-z0-9_.-]*)",
                       f'e.g. "{key}": ["core"]')
        lists[key] = tuple(dict.fromkeys(value))

    skills_dir = kit_root / "core" / "skills"
    for skill in lists["skills"]:
        if not (skills_dir / skill).exists():
            available = sorted(c.name for c in skills_dir.iterdir()) if skills_dir.is_dir() else []
            raise _bad(stem, path, f"skill {skill!r} is not in the kit's core/skills",
                       f"fix the name; available: {', '.join(available) or 'none'}")
    return Flavor(stem, description, lists["includes"], lists["skills"], lists["exclude"],
                  tier, path)


def _load_dir(directory: Path, tier: str, kit_root: Path) -> dict[str, Flavor]:
    if not directory.is_dir():
        return {}
    return {p.stem: load_flavor(p, tier, kit_root) for p in sorted(directory.glob("*.json"))}


def profile_types(kit_root: Path) -> list[str]:
    directory = kit_root / "profiles"
    return sorted(p.stem for p in directory.glob("*.json")) if directory.is_dir() else []


def catalog(kit_root: Path, repo: Path | None = None) -> tuple[dict[str, Flavor], list[str]]:
    """Flavors by name, kit first and repo overriding, plus one note per override."""
    found = _load_dir(kit_root / KIT_DIR, TIER_KIT, kit_root)
    notes: list[str] = []
    if repo is not None:
        types = set(profile_types(kit_root))
        for name, flavor in _load_dir(repo / REPO_DIR, TIER_REPO, kit_root).items():
            if name in types:
                raise _bad(name, flavor.path, "shares its name with a profile type",
                           f"rename the file and its \"name\" (profile types: {', '.join(sorted(types))})")
            if name in found:
                notes.append(f"repo flavor {name} ({flavor.path}) overrides the kit flavor")
            found[name] = flavor
    return found, notes


def unknown_name(name: str, cat: dict[str, Flavor], kit_root: Path) -> DevkitError:
    return DevkitError(
        f"no flavor or profile type named {name!r}",
        f"flavors: {', '.join(sorted(cat)) or 'none'}; "
        f"profile types: {', '.join(profile_types(kit_root)) or 'none'}")


def _profile_expanded(name: str, kit_root: Path) -> Expanded:
    # Lenient on purpose, as before: a profile entry that is not a core skill is dropped.
    profile = manifest.load(name, kit_root=kit_root)
    skills: list[str] = []
    for entry in profile.get("skills", []):
        leaf = manifest.layer_leaf(entry)
        if leaf and leaf not in skills and (kit_root / "core" / "skills" / leaf).exists():
            skills.append(leaf)
    return Expanded(tuple(skills), frozenset(profile.get("lineage", [])))


def expand(name: str, cat: dict[str, Flavor], kit_root: Path,
           _chain: tuple[str, ...] = ()) -> Expanded:
    """The ordered, de-duplicated skills of a flavor or profile type.

    A flavor is its includes in order, then its own skills, minus `exclude`.
    """
    if name not in cat:
        if name in profile_types(kit_root):
            return _profile_expanded(name, kit_root)
        raise unknown_name(name, cat, kit_root)
    flavor = cat[name]
    if name in _chain:
        raise _bad(name, flavor.path, f"includes loop: {' -> '.join([*_chain, name])}",
                   "remove one of the includes in the chain")
    chain = (*_chain, name)

    skills: list[str] = []
    lineage: set[str] = set()
    for include in flavor.includes:
        if include not in cat and include not in profile_types(kit_root):
            raise _bad(name, flavor.path, f"includes unknown {include!r}",
                       f"available: {', '.join(sorted({*cat, *profile_types(kit_root)})) or 'none'}")
        part = expand(include, cat, kit_root, chain)
        lineage |= part.lineage
        skills += [s for s in part.skills if s not in skills]
    skills += [s for s in flavor.skills if s not in skills]

    for gone in flavor.exclude:
        if gone not in skills:
            raise _bad(name, flavor.path, f"excludes {gone!r}, which it does not include",
                       f"remove it from \"exclude\"; the flavor holds: {', '.join(skills) or 'nothing'}")
    return Expanded(tuple(s for s in skills if s not in flavor.exclude), frozenset(lineage))
