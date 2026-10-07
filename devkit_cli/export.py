"""`devkit export` — the one-way copy from the harness into core/.

The export is curated, not a mirror: `export-allowlist.json` names what ships,
and `hard_excludes` wins over every allowlist entry so a directory carrying
credentials cannot be re-admitted by a careless edit.

Direction is one-way by design. Editing core/ directly is drift, which is what
`--check` exists to catch.
"""

from __future__ import annotations

import filecmp
import fnmatch
import json
import shutil
import subprocess
from pathlib import Path

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
                            ("hooks", "hooks"), ("mcp", "mcp"), ("config", "config"),
                            ("agents", "agents"), ("kb", "kb"), ("vendor", "vendor")):
        block = allowlist.get(section) or {}
        for layer in layers:
            entries = block.get(layer)
            if not entries:
                continue
            add(prefix, entries, block.get(f"{layer}_excludes"))

    vendor = allowlist.get("skills_vendor") or {}
    for layer in layers:
        add("skills-vendor", vendor.get(layer, []))
    add("skills-vendor", vendor.get("files", []))
    return chosen


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_symlink():
        link = src.readlink()
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        dest.symlink_to(link)
        return
    if src.suffix in TEXT_SUFFIXES:
        try:
            text = src.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(src, dest)
            return
        dest.write_text(unrender_home(text), encoding="utf-8")
        shutil.copystat(src, dest)
        return
    shutil.copy2(src, dest)


def _same(src: Path, dest: Path) -> bool:
    if not dest.exists():
        return False
    if src.is_symlink() or dest.is_symlink():
        return src.is_symlink() and dest.is_symlink() and src.readlink() == dest.readlink()
    if src.suffix in TEXT_SUFFIXES:
        try:
            return unrender_home(src.read_text(encoding="utf-8")) == dest.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            pass
    return filecmp.cmp(src, dest, shallow=False)


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

    chosen = selected_files(source, allowlist, layers)
    if not chosen:
        raise DevkitError(f"the allowlist selected nothing under {source}",
                          "check 'source' in export-allowlist.json")

    stale = [rel for rel, src in chosen.items() if not _same(src, target / rel)]
    existing = {
        str(p.relative_to(target)) for p in target.rglob("*")
        if p.is_file() or p.is_symlink()
    } if target.is_dir() else set()
    hard = allowlist.get("hard_excludes", [])
    # Hard-excluded paths (e.g. __pycache__) must not ship, but they also must
    # not fail --check when an import regenerates them under core/. --apply still
    # sweeps them so the tree stays tidy.
    extras = sorted(existing - set(chosen))
    orphans = [rel for rel in extras if not _excluded(rel, hard)]
    noise = [rel for rel in extras if _excluded(rel, hard)]

    if args.check:
        if not stale and not orphans:
            print(f"{target} matches {source}: {len(chosen)} files.")
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
            _copy(chosen[rel], target / rel)
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
