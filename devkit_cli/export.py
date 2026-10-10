"""`devkit export` — the one-way copy from the harness into core/.

The export is curated, not a mirror: `export-allowlist.json` names what ships,
and `hard_excludes` wins over every allowlist entry so a directory carrying
credentials cannot be re-admitted by a careless edit.

Direction is one-way by design. Editing core/ directly is drift, which is what
`--check` exists to catch.
"""

from __future__ import annotations

import fnmatch
import json
import shutil
import subprocess
from pathlib import Path

from . import scrub
from .common import (
    Plan,
    load_json,
    repo_file,
    require_checkout,
    resolve_source,
    unrender_home,
)
from .errors import DevkitError

# Text files get ${HOME} substitution on the way out; everything else is
# copied byte for byte.
TEXT_SUFFIXES = {".md", ".mdc", ".json", ".toml", ".sh", ".py", ".cjs", ".js",
                 ".yaml", ".yml", ".txt", ".desktop", ".cfg", ".ini"}


def _excluded(rel: str, hard_excludes: list[str]) -> bool:
    """Is this export-relative path hard-excluded?

    Patterns are anchored at the export root unless they start with `**/`. That
    distinction is load-bearing: an unanchored `graft/` also matches
    `skills/graft/`, which silently dropped a real skill from the export. Write
    `**/name/` when you mean "a directory called this, anywhere".
    """
    parts = rel.split("/")
    for pattern in hard_excludes:
        anywhere = pattern.startswith("**/")
        body = pattern[3:] if anywhere else pattern
        if body.endswith("/"):
            name = body.rstrip("/")
            if anywhere:
                if name in parts[:-1]:
                    return True
            elif rel == name or rel.startswith(name + "/"):
                return True
        elif anywhere:
            if fnmatch.fnmatch(parts[-1], body) or fnmatch.fnmatch(rel, body):
                return True
        elif fnmatch.fnmatch(rel, body):
            return True
    return False


def _iter_entry(source: Path, entry: str) -> list[Path]:
    """Expand one allowlist entry into concrete files under source."""
    if entry.endswith("/**"):
        base = source / entry[:-3]
        return sorted(p for p in base.rglob("*") if p.is_file()) if base.is_dir() else []
    if entry == "**":
        return sorted(p for p in source.rglob("*") if p.is_file())
    target = source / entry
    if target.is_dir():
        return sorted(p for p in target.rglob("*") if p.is_file())
    return [target] if target.is_file() else []


def selected_files(source: Path, allowlist: dict, layers: set[str]) -> dict[str, Path]:
    """Map of relative export path -> source file, for the requested layers."""
    hard = allowlist.get("hard_excludes", [])
    chosen: dict[str, Path] = {}

    def add(prefix: str, entries: list[str], excludes: list[str] | None = None) -> None:
        for entry in entries:
            for path in _iter_entry(source / prefix if prefix else source, entry):
                rel = str(path.relative_to(source))
                if _excluded(rel, hard):
                    continue
                if excludes and any(
                    fnmatch.fnmatch(str(path.relative_to(source / prefix)), ex)
                    for ex in excludes
                ):
                    continue
                chosen[rel] = path

    for section, prefix in (("skills", "skills"), ("rules", "rules"), ("bin", "bin"),
                            ("bin_vendor", "bin-vendor"), ("hooks", "hooks"),
                            ("benchmarks", "benchmarks"), ("mcp", "mcp"),
                            ("config", "config"), ("agents", "agents"), ("kb", "kb"),
                            ("vendor", "vendor")):
        block = allowlist.get(section) or {}
        for layer in layers:
            entries = block.get(layer)
            if not entries:
                continue
            add(prefix, entries, block.get(f"{layer}_excludes"))

    vendor = allowlist.get("skills_vendor") or {}
    for layer in layers:
        add("skills-vendor", vendor.get(layer, []), vendor.get(f"{layer}_excludes"))
    add("skills-vendor", vendor.get("files", []))
    return chosen


def _render(src: Path, rel: str, rules: scrub.Rules | None) -> bytes | None:
    """The bytes core/ should hold for this file, or None for a symlink."""
    if src.is_symlink():
        return None
    if src.suffix in TEXT_SUFFIXES:
        try:
            text = unrender_home(src.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            return src.read_bytes()
    else:
        raw = src.read_bytes()
        if rules is None:
            return raw
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw
    if rules is not None:
        text = rules.text(text, rel)
    return text.encode("utf-8")


def _copy(src: Path, dest: Path, rendered: bytes | None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if rendered is None:
        link = src.readlink()
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        dest.symlink_to(link)
        return
    dest.write_bytes(rendered)
    shutil.copystat(src, dest)


def _same(src: Path, dest: Path, rendered: bytes | None) -> bool:
    if rendered is None or dest.is_symlink():
        return (rendered is None and dest.is_symlink()
                and src.readlink() == dest.readlink())
    return dest.is_file() and dest.read_bytes() == rendered


def scrubbed_paths(chosen: dict[str, Path],
                   rules: scrub.Rules | None) -> dict[str, tuple[str, Path]]:
    """Destination path -> (source path, file), after the scrub drops and renames."""
    files: dict[str, tuple[str, Path]] = {}
    for rel, path in chosen.items():
        if rules is not None and rules.dropped(rel):
            continue
        dest = rules.rename(rel) if rules is not None else rel
        if dest in files:
            raise DevkitError(f"{files[dest][0]} and {rel} both export to {dest}",
                              "adjust the scrub rules so the paths stay distinct")
        files[dest] = (rel, path)
    return files


def scrub_leaks(rules: scrub.Rules | None, rendered: dict[str, bytes | None]) -> list[str]:
    """`path:line: excerpt` for each forbidden name the rules left in the export."""
    if rules is None:
        return []
    found: list[str] = []
    for dest, data in sorted(rendered.items()):
        text = data.decode("utf-8", errors="ignore") if data is not None else ""
        found += [f"{dest}:{line}: {excerpt}" for line, excerpt in rules.leaks(text, dest)]
    return found


def gitleaks_scan(target: Path) -> tuple[bool, str]:
    """Run the export gate. Missing gitleaks is reported, never silently skipped."""
    if shutil.which("gitleaks") is None:
        return False, "gitleaks is not installed; the export secret gate did not run"
    command = ["gitleaks", "dir", str(target), "--no-banner",
               "--report-format", "json", "--report-path", "/dev/stdout"]
    # Verified false positives live in the kit's own config, not in a --no-verify
    # style bypass, so each exemption carries its reason and stays reviewable.
    config = repo_file(".gitleaks.toml")
    if config.is_file():
        command += ["--config", str(config)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    try:
        findings = json.loads(result.stdout or "[]")
    except ValueError:
        findings = []
    if findings:
        where = ", ".join(sorted({f.get("File", "?") for f in findings})[:5])
        return False, f"gitleaks found {len(findings)} finding(s) in the export: {where}"
    return True, "gitleaks: clean"


def cmd_export(args) -> int:
    require_checkout("export")
    allowlist = load_json(repo_file("export-allowlist.json"), "export allowlist")
    source = resolve_source(getattr(args, "source", None), allowlist)
    target = repo_file(allowlist.get("target", "core"))
    layers = {"core", "enonic", "client"}

    rules = scrub.load(source)
    chosen = selected_files(source, allowlist, layers)
    if not chosen:
        raise DevkitError(f"the allowlist selected nothing under {source}",
                          "check 'source' in export-allowlist.json")
    files = scrubbed_paths(chosen, rules)
    rendered = {dest: _render(path, rel, rules) for dest, (rel, path) in files.items()}
    leaks = scrub_leaks(rules, rendered)
    if leaks:
        print("\n".join(f"  leak: {line}" for line in leaks[:20]))
        raise DevkitError(f"the export would ship {len(leaks)} name(s) the scrub rules forbid",
                          f"extend {scrub.RULES_PATH} under {source} so they are rewritten or dropped")

    stale = [dest for dest, (_, src) in files.items()
             if not _same(src, target / dest, rendered[dest])]
    existing = {
        str(p.relative_to(target)) for p in target.rglob("*")
        if p.is_file() or p.is_symlink()
    } if target.is_dir() else set()
    hard = allowlist.get("hard_excludes", [])
    # Hard-excluded paths (e.g. __pycache__) must not ship, but they also must
    # not fail --check when an import regenerates them under core/. --apply still
    # sweeps them so the tree stays tidy.
    extras = sorted(existing - set(files))
    orphans = [rel for rel in extras if not _excluded(rel, hard)]
    noise = [rel for rel in extras if _excluded(rel, hard)]

    if args.check:
        if not stale and not orphans:
            print(f"{target} matches {source}: {len(files)} files.")
            return 0
        shown = 0
        for rel in stale[:20]:
            print(f"  behind: {rel}")
            shown += 1
        for rel in orphans[:20]:
            print(f"  orphan: {rel}")
            shown += 1
        extra = len(stale) + len(orphans) - shown
        if extra > 0:
            print(f"  ... and {extra} more")
        print(f"\n{target} is behind {source} "
              f"({len(stale)} changed, {len(orphans)} orphaned).")
        print("fix:   devkit export --apply")
        return 1

    plan = Plan(args.apply)
    for rel in stale:
        plan.record(f"export {rel}")
    for rel in orphans:
        plan.record(f"remove {rel} (no longer allowlisted)")
    for rel in noise:
        plan.record(f"remove {rel} (hard-excluded)")

    if args.apply:
        for rel in stale:
            _copy(files[rel][1], target / rel, rendered[rel])
        for rel in orphans + noise:
            (target / rel).unlink()
        for directory in sorted((p for p in target.rglob("*") if p.is_dir()),
                                key=lambda p: -len(p.parts)):
            if not any(directory.iterdir()):
                directory.rmdir()

    result = plan.report(f"export into {target}")
    if args.apply and not args.no_scan:
        ok, message = gitleaks_scan(target)
        print(message)
        if not ok:
            raise DevkitError("the export did not pass the secret gate",
                              "review the findings, then fix export-allowlist.json")
    return result
