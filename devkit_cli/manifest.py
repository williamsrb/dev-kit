"""Profile manifest loading and composition.

`extends` composes, so a PHP profile gets core's kb without inheriting 3.4M of
XP reference. Lists concatenate parent-first; scalars and dicts are overridden
by the child.

`skills`, `rules` and `kb` accept an `@allowlist:<section>.<layer>` reference
instead of a literal list, so the export boundary and the profile manifest
cannot disagree about what a layer contains — there is one list, in
export-allowlist.json, and the profile names it. The layer's `<layer>_excludes`
land in the composed profile as `<key>_excludes` (e.g. `kb_excludes`); a child
entry that covers an inherited exclude adds that path back.
"""

from __future__ import annotations

from pathlib import Path

from .common import REPO_ROOT, load_json
from .errors import DevkitError

ALLOWLIST_PREFIX = "@allowlist:"
LAYER_KEYS = ("skills", "rules", "kb")

# Keys a child REPLACES rather than extends. `instances` is the important one: a
# PHP profile that declares claude and codex means exactly those two, not those
# two plus whatever core happened to declare.
OVERRIDE_KEYS = ("instances", "color", "settings", "client_overlay", "todo")


def layer_leaf(entry: str) -> str:
    """The top-level name a skills/rules/kb entry projects as (`x/**` -> `x`)."""
    return entry.split("/")[0].replace("**", "").rstrip("/")


def entry_parts(entry: str) -> tuple[str, ...]:
    """The path an entry names, as parts (`a/b/**` -> `("a", "b")`).

    Excludes are read as path prefixes, not globs: the allowlist only uses
    `dir/**` and exact files.
    """
    path = entry.replace("**", "")
    return tuple(part for part in path.split("/") if part)


def profile_path(name: str, kit_root: Path | None = None) -> Path:
    return (kit_root or REPO_ROOT) / "profiles" / f"{name}.json"


def _resolve_allowlist_ref(ref: str, allowlist: dict) -> tuple[list[str], list[str]]:
    spec = ref[len(ALLOWLIST_PREFIX):]
    try:
        section, layer = spec.split(".", 1)
    except ValueError:
        raise DevkitError(f"malformed allowlist reference {ref!r}",
                          "use @allowlist:<section>.<layer>, e.g. @allowlist:skills.core") from None
    block = allowlist.get(section)
    if not isinstance(block, dict) or layer not in block:
        raise DevkitError(f"{ref} does not exist in export-allowlist.json",
                          f"add a {layer!r} key under {section!r}, or fix the reference")
    value = block[layer]
    excludes = block.get(f"{layer}_excludes")
    return (list(value) if isinstance(value, list) else [],
            list(excludes) if isinstance(excludes, list) else [])


def _compose_excludes(composed: dict, key: str, entries: list[str],
                      excludes: list[str]) -> None:
    """Drop inherited excludes a child entry covers, then add the child's own."""
    added = [entry_parts(e) for e in entries]
    kept = [ex for ex in composed.get(key, [])
            if not any(entry_parts(ex)[:len(parts)] == parts for parts in added)]
    kept += [ex for ex in excludes if ex not in kept]
    if kept:
        composed[key] = kept
    else:
        composed.pop(key, None)


def load(name: str, _seen: set[str] | None = None,
         kit_root: Path | None = None) -> dict:
    """Load a profile with its ancestors composed in.

    `kit_root` points the lookup at another checkout of the kit — `update apply`
    reads the staged payload's profiles, not the local ones.
    """
    root = kit_root or REPO_ROOT
    seen = _seen or set()
    if name in seen:
        chain = " -> ".join([*sorted(seen), name])
        raise DevkitError(f"profile inheritance loops: {chain}",
                          "break the cycle by setting one profile's 'extends' to null")
    seen = seen | {name}

    path = profile_path(name, root)
    if not path.is_file():
        available = sorted(p.stem for p in (root / "profiles").glob("*.json"))
        raise DevkitError(f"no profile named {name!r}",
                          f"available: {', '.join(available) or 'none'}")
    profile = load_json(path, f"profile {name}")

    parent_name = profile.get("extends")
    composed: dict = load(parent_name, seen, root) if parent_name else {}

    # Read lazily: most profiles carry literal layer lists and never touch it.
    allowlist: dict | None = None
    for key, value in profile.items():
        if key in ("_comment", "extends"):
            continue
        excludes: list[str] = []
        if key in LAYER_KEYS and isinstance(value, str) and value.startswith(ALLOWLIST_PREFIX):
            if allowlist is None:
                allowlist = load_json(root / "export-allowlist.json", "export allowlist")
            value, excludes = _resolve_allowlist_ref(value, allowlist)
        if key in LAYER_KEYS and isinstance(value, list):
            _compose_excludes(composed, f"{key}_excludes", value, excludes)
        if key in OVERRIDE_KEYS:
            composed[key] = value
        elif isinstance(value, list) and isinstance(composed.get(key), list):
            merged = list(composed[key])
            merged += [item for item in value if item not in merged]
            composed[key] = merged
        elif isinstance(value, dict) and isinstance(composed.get(key), dict):
            composed[key] = {**composed[key], **value}
        else:
            composed[key] = value

    composed["name"] = profile["name"]
    composed["lineage"] = [*composed.get("lineage", []), profile["name"]]
    return composed


def available() -> list[str]:
    directory = REPO_ROOT / "profiles"
    return sorted(p.stem for p in directory.glob("*.json")) if directory.is_dir() else []


def dependencies(profile: dict, include_optional: bool = True) -> list[dict]:
    deps = profile.get("deps", [])
    return deps if include_optional else [d for d in deps if not d.get("optional")]


def provided_binaries(profile: dict, include_optional: bool = True) -> list[str]:
    """Every binary the profile expects on PATH. `provides` is authoritative."""
    names: list[str] = []
    for dep in dependencies(profile, include_optional):
        for binary in dep.get("provides", []):
            if binary not in names:
                names.append(binary)
    return names
