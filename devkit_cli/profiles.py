"""Profile commands: create, sync, adopt, list, show, doctor, fix-home-rules.

Every write goes through Plan so `--dry-run` is the default and `--apply` is the
exception (Definition of Done 7), and through `_write`, so an existing path the
kit did not author aborts and names itself unless `--force` backs it up first.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path

from . import (
    appfork,
    auth,
    cli_link,
    globalignore,
    instances,
    kithome,
    kitsource,
    manifest,
    mcp,
    migrations,
    privilege,
    uninstaller,
)
from .common import (
    EXEC_MODE,
    FILE_MODE,
    REPO_ROOT,
    Plan,
    back_up,
    ensure_dir,
    relative_to_home,
    write_json,
)
from .errors import DevkitError

# Claude Code and Codex walk up to $HOME collecting instruction
# files, so a populated ~/CLAUDE.md loads in addition to the config-dir one and
# leaks into every profile at once.
HOME_ROOT_RULES = {
    "CLAUDE.md": (".claude", "claude"),
    "AGENTS.md": (".codex", "codex"),
}
STUB_BYTES = b"\n"
STUB_MODE = 0o000
CLIENT_OVERLAY_NAME = "client-overlay.json"


# ---------------------------------------------------------------- materialize

def _instance_vendors(profile: dict, wanted: list[str] | None) -> list[dict]:
    declared = profile.get("instances", [])
    if not wanted:
        return declared
    chosen = [i for i in declared if i["vendor"] in wanted]
    unknown = set(wanted) - {i["vendor"] for i in declared}
    if unknown:
        raise DevkitError(
            f"profile {profile['name']!r} declares no instance for: {', '.join(sorted(unknown))}",
            f"declared vendors: {', '.join(i['vendor'] for i in declared)}")
    return chosen


def _write(plan: Plan, target: Path, content: str, force: bool,
           executable: bool = False, label: str | None = None) -> None:
    existing = target.read_text(encoding="utf-8") if target.is_file() else None
    if existing == content:
        return
    # Regenerating our own template output is not a collision; a file we did not
    # write is. Templates carry the generated marker.
    if (existing is not None and not force and "devkit" not in existing
            and target.name != instances.PROVENANCE_NAME):
        raise DevkitError(f"{target} exists and was not written by devkit",
                          "re-run with --force to back it up and proceed")
    plan.record(f"{'update' if existing is not None else 'write '} {label or target}")
    if not plan.apply:
        return
    ensure_dir(target.parent)
    if existing is not None and force:
        back_up(target)
    target.write_text(content, encoding="utf-8")
    target.chmod(EXEC_MODE if executable else FILE_MODE)


def _link_layer(plan: Plan, config_dir: Path, name: str, entries: list[str],
                core_root: Path, link_core: Path,
                excludes: list[str] | None = None,
                extra: dict[str, Path] | None = None) -> None:
    """Project one layer (skills/rules/kb) into the instance as symlinks.

    Symlinks, not copies: this is the contract sync-skill-projections.sh already
    uses, and it means an update to core/ reaches every profile without a re-copy.
    Existence is checked under `core_root` (the tree being read) while each link
    names `link_core` (the stable `current` tree), which dry run cannot read.

    A path is linked whole unless an entry names something below it (a deeper
    entry, or an exclude); then it becomes a real directory of finer links, so
    `offline-reference/scripts/**` does not expose the rest of offline-reference.
    """
    dest_root = config_dir / name
    source_root = link_core / name
    links, dirs = _projection(entries, excludes or [], core_root / name)
    for rel in sorted(dirs):
        _projection_dir(plan, dest_root.joinpath(*rel), "/".join((name, *rel)))
    wanted = {rel: source_root.joinpath(*rel) for rel in links}
    for entry, source in (extra or {}).items():
        wanted.setdefault((entry,), source)
    for rel, source in sorted(wanted.items()):
        link = dest_root.joinpath(*rel)
        if link.is_symlink() and link.readlink() == source:
            continue
        plan.record(f"link   {'/'.join((name, *rel))}")
        if plan.apply:
            ensure_dir(link.parent)
            if link.is_dir() and not link.is_symlink():
                if not _projection_owned(link, source_root):
                    raise DevkitError(f"{link} is a real directory, not a projection",
                                      "move it aside by hand, then re-run")
                shutil.rmtree(link)
            elif link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(source)
    _prune_layer(plan, dest_root, name, (), set(wanted), dirs, source_root)


VENDOR_SKILLS = ("orchestrate",)


def _vendor_skills(core_root: Path, link_core: Path, vendor: str) -> dict[str, Path]:
    """Skills that exist once per vendor, linked from skills-vendor/<vendor>/."""
    return {name: link_core / "skills-vendor" / vendor / name for name in VENDOR_SKILLS
            if (core_root / "skills-vendor" / vendor / name).is_dir()}


CLAUDE_RULES_MARKER = "<!-- devkit: rendered at profile sync; do not edit -->"


def _claude_rule_files(core_root: Path, layers: list[str]) -> dict[str, str] | None:
    """The per-section Claude rule files, from the kit's generator.

    None when the kit predates the folder render, which a profile pinned to an
    older ref still reads.

    The generator is loaded, not run: its CLI writes AGENTS.md and BASE.mdc
    into the tree it lives in, which here is the kit.
    """
    script = core_root / "bin" / "generate-agents-md.py"
    spec = importlib.util.spec_from_file_location("devkit_generate_agents_md", script)
    if not script.is_file() or spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # The script lives in an installed release, which must stay as installed.
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    if not hasattr(module, "render_claude_dir"):
        return None
    try:
        files = module.render_claude_dir(module.load_manifest(), set(layers))
    except module.GenerateError as exc:
        raise DevkitError(f"the rules generator failed: {exc}") from exc
    # The generator's notice names no devkit, and `_write` refuses a file without it.
    return {name: text.replace("\n", f"\n{CLAUDE_RULES_MARKER}\n", 1)
            for name, text in files.items()}


def _render_claude_rules(plan: Plan, config_dir: Path, profile: dict,
                         core_root: Path, link_core: Path, force: bool) -> bool:
    """Claude reads a rules folder of .md files, not the raw rules tree.

    Rendered at sync, per the policy that the generator ships and a snapshot
    does not. Layer links from earlier versions are pruned first, since `_write`
    would read through them.
    """
    files = _claude_rule_files(core_root, manifest.rules_layers(profile.get("lineage", [])))
    if files is None:
        return False
    dest = config_dir / "rules"
    label = "rules"
    if dest.is_symlink():
        plan.record(f"prune  {label}")
        if plan.apply:
            dest.unlink()
    else:
        _prune_layer(plan, dest, label, (), set(), set(), link_core / "rules")
    for name, text in sorted(files.items()):
        target = dest / name
        if target.is_symlink() or not target.exists():
            plan.record(f"write  {label}/{name}")
            if plan.apply:
                ensure_dir(dest)
                if target.is_symlink():
                    target.unlink()
                target.write_text(text, encoding="utf-8")
                target.chmod(FILE_MODE)
        else:
            _write(plan, target, text, force, label=f"{label}/{name}")
    if dest.is_dir() and not dest.is_symlink():
        for entry in sorted(dest.glob("*.md")):
            if (entry.name not in files and entry.is_file()
                    and CLAUDE_RULES_MARKER in entry.read_text(encoding="utf-8")):
                plan.record(f"prune  {label}/{entry.name}")
                if plan.apply:
                    entry.unlink()
    return True


def _projection(entries: list[str], excludes: list[str], layer_root: Path
                ) -> tuple[list[tuple[str, ...]], set[tuple[str, ...]]]:
    """The paths to link and the real directories that hold them.

    The most specific rule covering a path decides it; an exclude wins a tie.
    A rule naming nothing under `layer_root` (an exclude the export already
    dropped) splits nothing.
    """
    rules = [(parts, include)
             for group, include in ((entries, True), (excludes, False))
             for parts in map(manifest.entry_parts, group)
             if layer_root.joinpath(*parts).exists()]

    def included(rel: tuple[str, ...]) -> bool:
        best: tuple[int, bool] | None = None
        for parts, include in rules:
            if rel[:len(parts)] == parts and (best is None or len(parts) >= best[0]):
                best = (len(parts), include)
        return bool(best and best[1])

    def split(rel: tuple[str, ...]) -> bool:
        return any(len(parts) > len(rel) and parts[:len(rel)] == rel
                   for parts, _ in rules)

    links: list[tuple[str, ...]] = []

    def walk(rel: tuple[str, ...]) -> None:
        path = layer_root.joinpath(*rel)
        if rel and not split(rel):
            if included(rel) and path.exists():
                links.append(rel)
            return
        if path.is_dir():
            for child in sorted(path.iterdir()):
                walk((*rel, child.name))

    walk(())
    dirs = {rel[:depth] for rel in links for depth in range(1, len(rel))}
    return links, dirs


def _projection_dir(plan: Plan, path: Path, label: str) -> None:
    if path.is_dir() and not path.is_symlink():
        return
    if path.is_symlink():
        plan.record(f"unlink {label} (becomes a directory)")
        if plan.apply:
            path.unlink()
    elif path.exists():
        raise DevkitError(f"{path} is a real file, not a projection",
                          "move it aside by hand, then re-run")
    plan.record(f"mkdir  {label}")
    if plan.apply:
        ensure_dir(path)


def _projection_owned(directory: Path, source_root: Path) -> bool:
    """True when the directory holds only links into the layer, so devkit made it."""
    def links_below(path: Path) -> int | None:
        count = 0
        for entry in path.iterdir():
            if entry.is_symlink():
                if not Path(os.readlink(entry)).is_relative_to(source_root):
                    return None
                count += 1
            elif entry.is_dir() and (found := links_below(entry)) is not None:
                count += found
            else:
                return None
        return count
    return bool(links_below(directory))


def _prune_layer(plan: Plan, dest_root: Path, name: str, rel: tuple[str, ...],
                 wanted: set[tuple[str, ...]], dirs: set[tuple[str, ...]],
                 source_root: Path) -> None:
    """Prune projections the profile no longer names. Real files and directories
    devkit did not make stay."""
    directory = dest_root.joinpath(*rel)
    if not directory.is_dir() or directory.is_symlink():
        return
    for entry in sorted(directory.iterdir()):
        child = (*rel, entry.name)
        if child in wanted:
            continue
        if child in dirs:
            _prune_layer(plan, dest_root, name, child, wanted, dirs, source_root)
            continue
        label = "/".join((name, *child))
        if entry.is_symlink():
            plan.record(f"prune  {label}")
            if plan.apply:
                entry.unlink()
        elif entry.is_dir() and _projection_owned(entry, source_root):
            plan.record(f"prune  {label}/")
            if plan.apply:
                shutil.rmtree(entry)


def materialize(profile: dict, vendors: list[str] | None, home: Path,
                plan: Plan, force: bool, kit_root: Path | None = None,
                source_commit: str | None = None,
                content: tuple[Path, Path] | None = None,
                kit_ref: dict | None = None) -> None:
    """Write one profile's instances from the kit.

    The kit is first installed into the kit home (a no-op when `kit_root`, or
    the running tree, already is `current`). Everything is then read from and
    linked through `current`, so nothing devkit writes names the checkout. A
    dry run installs nothing: it reads the source tree and prints the `current`
    paths the links would have.

    `content` is `(ref link, tree to read)` for a profile on a kit ref: skills,
    rules, kb and the rest of `core/` come from that tree and every link names
    the ref link. A dry run has no ref link yet, so the tree read is then the
    checkout. Templates, wrappers, vendor config and auth stay on the running
    kit and `current`.
    """
    src = kit_root or REPO_ROOT
    root = kithome.ensure_installed(src, home, plan)
    kit = _kit_metadata(root)
    commit = source_commit or instances.kit_commit(root)
    if content:
        link_core, core_root = content[0] / "core", content[1] / "core"
    else:
        link_core, core_root = kithome.current_link(home) / "core", root / "core"
    if not core_root.is_dir():
        raise DevkitError(f"{core_root} has not been exported yet",
                          "run 'devkit export --apply' first")

    _bind_profile_runtime(plan, profile, home, core_root, link_core, force, root)

    wrote_desktop = False
    for instance in _instance_vendors(profile, vendors):
        vendor = instance["vendor"]
        layout = instances.paths_for(profile["name"], vendor, home)
        tokens = instances.render_tokens(profile, vendor, home)

        for key in ("harness_dir", "config_dir", "data_dir"):
            directory = layout[key]
            if not directory.is_dir():
                plan.record(f"mkdir  {relative_to_home(directory)}")
                if plan.apply:
                    ensure_dir(directory)

        for layer in ("skills", "rules", "kb"):
            if vendor == "claude" and layer == "rules":
                if _render_claude_rules(plan, layout["config_dir"], profile, core_root,
                                        link_core, force):
                    continue
                plan.record("note   this kit cannot render Claude rules; linking the raw rules layer")
            _link_layer(plan, layout["config_dir"], layer,
                        profile.get(layer, []), core_root, link_core,
                        profile.get(f"{layer}_excludes"),
                        _vendor_skills(core_root, link_core, vendor) if layer == "skills" else None)
        hooks_dir = layout["harness_dir"] / "hooks"
        if hooks_dir.is_dir():
            _symlink(plan, layout["config_dir"] / "hooks", hooks_dir,
                     f"{vendor}/hooks")

        _write_vendor_config(plan, vendor, profile, layout, tokens, force, root)
        _write_wrapper(plan, vendor, layout, tokens, force, root)
        if ("desktop" in instance.get("kind", "")
                and not profile.get("headless")
                and _write_desktop(plan, vendor, profile, layout, tokens,
                                 force, root)):
            wrote_desktop = True

        prov = instances.provenance(profile, vendor, home, kit, commit, kit_ref=kit_ref)
        existing = instances.read_provenance(layout["config_dir"])
        if existing:
            prov["history"] = existing.get("history", [])
            prov["installed_at"] = existing.get("installed_at", prov["installed_at"])
        target = layout["config_dir"] / instances.PROVENANCE_NAME
        if not existing or {k: v for k, v in existing.items() if k != "history"} != \
                {k: v for k, v in prov.items() if k != "history"}:
            plan.record(f"write  {vendor}/{instances.PROVENANCE_NAME}")
            if plan.apply:
                write_json(target, prov)

    if not profile.get("headless"):
        auth.install_dispatchers(plan, home, kit_root=root)
    if wrote_desktop:
        plan.record(f"icon-cache {relative_to_home(instances.hicolor_root(home))}")
        if plan.apply and not instances.refresh_hicolor_cache(home):
            print("  note: gtk-update-icon-cache failed or is missing; "
                  "GNOME may not show launcher icons until the cache is rebuilt")


def _write_vendor_config(plan: Plan, vendor: str, profile: dict, layout: dict,
                         tokens: dict, force: bool, root: Path) -> None:
    template_dir = root / "templates" / vendor
    if not template_dir.is_dir():
        return
    for template in sorted(template_dir.iterdir()):
        if not template.is_file():
            continue
        rendered = instances.render(template.read_text(encoding="utf-8"), tokens)
        target = layout["config_dir"] / template.name
        if template.name == "mcp.json" and vendor == "cursor":
            rendered = _fill_cursor_mcp(
                rendered, profile, root, Path(tokens["HOME"]), target, layout["agents_dir"])
        elif template.name == "config.toml" and vendor == "codex":
            rendered = _fill_codex_mcp(
                rendered, profile, root, Path(tokens["HOME"]), target, layout["agents_dir"])
        _write(plan, target, rendered, force, label=f"{vendor}/{template.name}")
    if vendor == "claude":
        _write_claude_mcp(plan, profile, layout, force, root, Path(tokens["HOME"]))


def _fill_cursor_mcp(rendered: str, profile: dict, root: Path, home: Path,
                     target: Path, agents_home: Path) -> str:
    catalog = mcp.load_catalog(root)
    data = json.loads(rendered)
    comment = data.get("_comment") or []
    existing = {}
    if target.is_file():
        try:
            existing = json.loads(target.read_text()).get("mcpServers") or {}
        except json.JSONDecodeError:
            existing = {}
    payload = mcp.cursor_payload(profile, catalog, home, comment, existing, agents_home)
    return json.dumps(payload, indent=2) + "\n"


def _fill_codex_mcp(rendered: str, profile: dict, root: Path, home: Path,
                    target: Path, agents_home: Path) -> str:
    catalog = mcp.load_catalog(root)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    extra = mcp.codex_toml_sections(profile, catalog, home, existing, agents_home)
    if not extra:
        return rendered
    body = rendered.rstrip() + "\n\n" + extra
    if not body.endswith("\n"):
        body += "\n"
    return body


def _write_claude_mcp(plan: Plan, profile: dict, layout: dict, force: bool,
                      root: Path, home: Path) -> None:
    catalog = mcp.load_catalog(root)
    target = layout["config_dir"] / ".claude.json"
    current = {}
    if target.is_file():
        try:
            loaded = json.loads(target.read_text())
        except json.JSONDecodeError:
            loaded = None
        current = loaded if isinstance(loaded, dict) else {}
    merged = {**current, **mcp.claude_payload(
        profile, catalog, home, existing=current.get("mcpServers") or {},
        agents_home=layout["agents_dir"])}
    if merged == current:
        return
    _write(plan, target, json.dumps(merged, indent=2) + "\n", force,
           label="claude/.claude.json")


def _write_wrapper(plan: Plan, vendor: str, layout: dict,
                   tokens: dict, force: bool, root: Path) -> None:
    template = root / "templates" / "shell" / f"{_wrapper_template(vendor)}.sh"
    if not template.is_file():
        return
    rendered = instances.render(template.read_text(encoding="utf-8"), tokens)
    _write(plan, layout["wrapper"], rendered, force, executable=True,
           label=relative_to_home(layout["wrapper"]))
    _link_profile_cli(plan, vendor, layout)


def _wrapper_template(vendor: str) -> str:
    return {"cursor": "cursor-agent"}.get(vendor, vendor)


def _bind_profile_runtime(plan: Plan, profile: dict, home: Path, core_root: Path,
                          link_core: Path, force: bool, root: Path) -> None:
    """Give this profile a ~/.agents-shaped tree and PATH wrappers for harness tools.

    PATH prepend is not enough: agentctl hardcodes its data root. Wrappers
    export AGENTS_HOME / DEVKIT_PROFILE so a tool sees this profile only.
    Do not symlink the kit's full core/ here: that tree contains every
    exported skill/kb and would leak Enonic into a PHP profile.
    """
    vendor = ((profile.get("instances") or [{}])[0].get("vendor") or "claude")
    tokens = instances.render_tokens(profile, vendor, home)
    layout = instances.paths_for(profile["name"], vendor, home)
    harness = layout["harness_dir"]
    if not harness.is_dir():
        plan.record(f"mkdir  {relative_to_home(harness)}")
        if plan.apply:
            ensure_dir(harness)
    _prune_core_symlink(plan, harness)
    agents_dir = layout["agents_dir"]
    if not agents_dir.is_dir():
        plan.record(f"mkdir  {relative_to_home(agents_dir)}")
        if plan.apply:
            ensure_dir(agents_dir)
    for layer in ("skills", "rules", "kb"):
        _link_layer(plan, agents_dir, layer, profile.get(layer, []), core_root,
                    link_core, profile.get(f"{layer}_excludes"))
    for name in ("bin", "bin-vendor", "benchmarks", "mcp", "share", "config", "docs", ".agentctl"):
        if name == "config" and profile.get("client_overlay"):
            _write_client_config(plan, agents_dir / name, profile["client_overlay"],
                                 core_root, link_core, force)
        elif (core_root / name).exists():
            _symlink(plan, agents_dir / name, link_core / name, f"agents/{name}")
    if (core_root / "skills-vendor" / "ROLES.md").is_file():
        # agentctl bench and agentctl factory read $AGENTS_HOME/skills-vendor/ROLES.md; link only that file
        # (the per-vendor skill folders beside it stay out of the profile).
        vendor_dir = agents_dir / "skills-vendor"
        if not vendor_dir.is_dir():
            plan.record(f"mkdir  {relative_to_home(vendor_dir)}")
            if plan.apply:
                ensure_dir(vendor_dir)
        _symlink(plan, vendor_dir / "ROLES.md", link_core / "skills-vendor" / "ROLES.md", "agents/skills-vendor/ROLES.md")
    _project_hooks(plan, harness / "hooks", core_root, link_core, tokens, force, root)
    _symlink(plan, agents_dir / "hooks", harness / "hooks", "agents/hooks")
    for name in ("prds", "plans", "history", ".cache", ".playwright-mcp"):
        dest = agents_dir / name
        if dest.is_dir() or dest.is_symlink():
            continue
        plan.record(f"mkdir  {relative_to_home(dest)}")
        if plan.apply:
            ensure_dir(dest)
    _isolate_auth(plan, agents_dir, home)
    _write_profile_tools(plan, layout, tokens, force, root, core_root)
    _sync_python_shim(plan, layout, tokens)


def _prune_core_symlink(plan: Plan, harness: Path) -> None:
    """A full core/ link exposes every exported skill to every profile."""
    core_link = harness / "core"
    if not core_link.is_symlink():
        return
    plan.record(f"prune  {relative_to_home(core_link)} (leaked the full core tree)")
    if plan.apply:
        core_link.unlink()


def _project_hooks(plan: Plan, dest: Path, core_root: Path, link_core: Path,
                   tokens: dict, force: bool, root: Path) -> None:
    source = core_root / "hooks"
    if not dest.is_dir():
        plan.record(f"mkdir  {relative_to_home(dest)}")
        if plan.apply:
            ensure_dir(dest)
    if source.is_dir():
        wanted = {item.name for item in source.iterdir()
                  if item.name != "__pycache__" and not item.name.startswith(".")}
        for item in sorted(source.iterdir()):
            if item.name not in wanted:
                continue
            _symlink(plan, dest / item.name, link_core / "hooks" / item.name,
                     f"hooks/{item.name}")
        if dest.is_dir():
            for link in sorted(dest.iterdir()):
                if link.is_symlink() and link.name not in wanted \
                        and link.name != "profile-statusline.sh":
                    plan.record(f"prune  hooks/{link.name}")
                    if plan.apply:
                        link.unlink()
    template = root / "templates" / "shell" / "profile-statusline.sh"
    if template.is_file():
        rendered = instances.render(template.read_text(encoding="utf-8"), tokens)
        _write(plan, dest / "profile-statusline.sh", rendered, force,
               executable=True, label=relative_to_home(dest / "profile-statusline.sh"))


def _isolate_auth(plan: Plan, agents_dir: Path, home: Path) -> None:
    """Profile-local .auth; share only named token files, never storage-state JSON."""
    dest = agents_dir / ".auth"
    if dest.is_symlink():
        plan.record(f"prune  {relative_to_home(dest)} (shared .auth leaked sessions)")
        if plan.apply:
            dest.unlink()
    if not dest.is_dir():
        plan.record(f"mkdir  {relative_to_home(dest)}")
        if plan.apply:
            ensure_dir(dest)
    host = home / ".agents" / ".auth"
    if not host.is_dir():
        return
    for name in instances.SHARED_AUTH_FILES:
        source = host / name
        if source.is_file():
            _symlink(plan, dest / name, source, f"agents/.auth/{name}")


def _write_client_config(plan: Plan, config_dir: Path, overlay: dict,
                         core_root: Path, link_core: Path, force: bool) -> None:
    """A real config/ holding the client overlay beside links into core/config.

    Skills read `$AGENTS_HOME/config/client-overlay.json`; `core/` ships only the
    example, and a link to the read-only release could not hold the real file.
    The profile only creates that file with placeholders: the real hosts are the
    operator's, so a later sync keeps an existing file unless --force.
    """
    if config_dir.is_symlink():
        plan.record(f"unlink {relative_to_home(config_dir)} (becomes a directory)")
        if plan.apply:
            config_dir.unlink()
    entries = sorted(p.name for p in (core_root / "config").iterdir()) \
        if (core_root / "config").is_dir() else []
    _link_layer(plan, config_dir.parent, config_dir.name, entries, core_root, link_core)
    target = config_dir / CLIENT_OVERLAY_NAME
    if target.is_file() and not force:
        return
    _write(plan, target, json.dumps(overlay, indent=2) + "\n", force=True,
           label=relative_to_home(target))


def _symlink(plan: Plan, dest: Path, target: Path, label: str) -> None:
    if dest.is_symlink() and dest.readlink() == target:
        return
    plan.record(f"link   {label} -> {relative_to_home(target)}")
    if not plan.apply:
        return
    ensure_dir(dest.parent)
    if dest.is_symlink() or dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            raise DevkitError(f"{dest} is a real directory, not a projection",
                              "move it aside by hand, then re-run")
        dest.unlink()
    dest.symlink_to(target)


def _write_profile_tools(plan: Plan, layout: dict, tokens: dict,
                         force: bool, root: Path, core_root: Path) -> None:
    template = root / "templates" / "shell" / "profile-tool.sh"
    if not template.is_file():
        return
    rendered = instances.render(template.read_text(encoding="utf-8"), tokens)
    for name in instances.PROFILE_PATH_TOOLS:
        if not (core_root / "bin" / name).is_file():
            continue
        _write(plan, layout["bin_dir"] / name, rendered, force, executable=True,
               label=relative_to_home(layout["bin_dir"] / name))


def _sync_python_shim(plan: Plan, layout: dict, tokens: dict) -> None:
    """`<profile>/bin/python3` -> a 3.12+ interpreter, only where `python3` is too old.

    The CLI wrappers and `bind_profile_env` put this bin/ first on PATH, so
    hooks and `env python3` scripts started from a profile get the floor
    without touching the system python3.
    """
    dest = layout["bin_dir"] / "python3"
    wanted = tokens["PROFILE_PYTHON"]
    if wanted == "python3":
        if dest.is_symlink():
            plan.record(f"unlink {relative_to_home(dest)} (system python3 meets the floor)")
            if plan.apply:
                dest.unlink()
        return
    target = Path(wanted)
    if dest.is_symlink() and dest.readlink() == target:
        return
    plan.record(f"link   {relative_to_home(dest)} -> {target}")
    if not plan.apply:
        return
    ensure_dir(dest.parent)
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(target)


def _link_profile_cli(plan: Plan, vendor: str, layout: dict) -> None:
    """Unprefixed name under the profile bin/ so the GUI finds this CLI on PATH."""
    names = instances.VENDOR_BINARIES.get(vendor) or []
    if not names:
        return
    dest = layout["bin_dir"] / names[0]
    target = layout["wrapper"]
    if dest.is_symlink() and dest.readlink() == target:
        return
    plan.record(f"link   {relative_to_home(dest)} -> {relative_to_home(target)}")
    if not plan.apply:
        return
    ensure_dir(dest.parent)
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(target)


def _write_desktop(plan: Plan, vendor: str, profile: dict, layout: dict,
                   tokens: dict, force: bool, root: Path) -> bool:
    if not instances.first_existing(instances.VENDOR_GUI_CANDIDATES.get(vendor, [])):
        plan.record(f"skip   desktop {vendor} (GUI not installed)")
        return False
    template = root / "templates" / "desktop" / f"{vendor}.desktop"
    if not template.is_file():
        return False
    light, _dark = instances.profile_colors(profile)
    source_icon = _find_vendor_icon(vendor)
    if source_icon:
        sizes = "/".join(str(s) for s in instances.ICON_THEME_SIZES)
        plan.record(f"icon   hicolor {sizes} {layout['icon'].name} (badge {light})")
        if plan.apply and not instances.install_launcher_icons(
                source_icon, layout["icon"], light):
            fallback = "keeps the previous badge"
            if not layout["icon"].is_file():
                # Icon= must name an icon that exists, or the launcher shows none.
                tokens = {**tokens, "PROFILE_ICON_NAME": source_icon.stem}
                fallback = f"uses the stock icon {source_icon.stem}"
            print(f"  note: could not badge {vendor} icon "
                  f"(ImageMagick or emblem missing?); the launcher {fallback}")
    else:
        print(f"  note: no stock {vendor} icon found; the launcher has no icon")

    rendered = instances.render(template.read_text(encoding="utf-8"), tokens)
    _write(plan, layout["desktop"], rendered, force,
           label=relative_to_home(layout["desktop"]))
    return source_icon is not None


def _find_vendor_icon(vendor: str) -> Path | None:
    roots = [Path("/usr/share/icons/hicolor/512x512/apps"),
             Path("/usr/share/icons/hicolor/256x256/apps"),
             Path("/usr/share/pixmaps")]
    stems = {"cursor": ["co.anysphere.cursor", "cursor"],
             "claude": ["claude-desktop", "claude"],
             "codex": ["chatgpt", "codex"]}.get(vendor, [vendor])
    for root in roots:
        for stem in stems:
            candidate = root / f"{stem}.png"
            if candidate.is_file():
                return candidate
    return None


def _kit_metadata(root: Path | None = None) -> dict:
    """Read devkit.yaml without a YAML parser.

    It is a flat file of `key: value` lines by design, so a line reader is
    honest here. Inline `#` comments are stripped: the file documents itself
    heavily.
    """
    path = (root or REPO_ROOT) / "devkit.yaml"
    data: dict = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, _, value = line.partition(":")
            value = value.split("#", 1)[0].strip().strip('"').strip("'")
            data[key.strip()] = None if value in ("null", "") else value
    return data


# ---------------------------------------------------------------- commands

def choose_first_profile(home: Path, default_type: str, *,
                         name: str | None = None, offer: bool = False,
                         input_fn=input, print_fn=print) -> tuple[str, str] | None:
    """Pick (instance name, type) for a first install.

    When `offer` is false, name defaults to the type (unattended / --profile given).
    When `offer` is true, ask on a TTY. Decline returns None.
    """
    if not offer:
        chosen_type = default_type
        chosen_name = name or chosen_type
        load_for_create(chosen_name, chosen_type)
        return chosen_name, chosen_type
    if instances.discover_instances(home):
        chosen_type = default_type
        chosen_name = name or chosen_type
        load_for_create(chosen_name, chosen_type)
        return chosen_name, chosen_type

    types = manifest.available()
    print_fn("No profile is installed yet.")
    print_fn("Available types: " + (", ".join(types) or "none"))
    reply = input_fn("Create a first profile? [Y/n] ").strip().lower()
    if reply in ("n", "no"):
        print_fn("Skipped. Later: devkit profile create NAME --type TYPE --apply")
        return None
    type_default = default_type if default_type in types else (types[0] if types else default_type)
    raw_type = input_fn(f"  Type [{type_default}]: ").strip() or type_default
    name_default = name or raw_type
    raw_name = input_fn(f"  Name [{name_default}]: ").strip() or name_default
    load_for_create(raw_name, raw_type)
    return raw_name, raw_type


def flag_given(flag: str, argv: list[str] | None = None) -> bool:
    """True when the user passed `flag` (not merely an argparse default)."""
    args = argv if argv is not None else sys.argv[1:]
    return flag in args or any(a.startswith(flag + "=") for a in args)


def load_for_create(name: str, type_name: str | None,
                    kit_root: Path | None = None) -> dict:
    """Bind a type JSON to a free-form instance name."""
    instances.validate_instance_name(name)
    chosen = type_name
    if not chosen:
        if manifest.profile_path(name, kit_root).is_file():
            chosen = name
        else:
            available = ", ".join(manifest.available()) or "none"
            raise DevkitError(
                f"no type named {name!r} and --type was not given",
                f"pass --type TYPE (available: {available})")
    if not manifest.profile_path(chosen, kit_root).is_file():
        available = ", ".join(manifest.available()) or "none"
        raise DevkitError(f"no profile type named {chosen!r}",
                          f"available: {available}")
    return instances.bind_instance(manifest.load(chosen, kit_root=kit_root),
                                   name, chosen)


def load_for_instance(name: str, home: Path, kit_root: Path | None = None,
                      headless: bool | None = None) -> dict:
    """Load the type manifest for a materialized instance on disk."""
    instances.validate_instance_name(name)
    matches = [row for row in instances.discover_instances(home) if row[0] == name]
    if not matches:
        raise DevkitError(
            f"no installed profile named {name!r}",
            f"run 'devkit profile create {name} --type TYPE --apply' first")
    type_name = instances.instance_type(matches[0][3], name)
    profile = instances.bind_instance(manifest.load(type_name, kit_root=kit_root),
                                      name, type_name)
    instances.apply_provenance_color(profile, matches[0][3])
    instances.apply_headless(profile, headless, home)
    return profile


def _refuse_duplicate(home: Path, name: str) -> None:
    existing = home / ".agents-profiles" / name
    if existing.exists():
        raise DevkitError(
            f"profile {name!r} already exists at {existing}",
            "pick a unique name, or run 'devkit profile sync "
            f"{name} --apply' to re-materialize")


def ref_spec(args) -> dict | None:
    """The kit ref the flags ask for, or None."""
    track, pin = getattr(args, "track", None), getattr(args, "pin", None)
    source = getattr(args, "from_source", None)
    if track and pin:
        raise DevkitError("--track and --pin are exclusive",
                          "follow a branch with --track, or fix a tag or commit with --pin")
    if not (track or pin):
        if source:
            raise DevkitError("--from names a kit to read a ref from, and no ref was given",
                              "add --track <branch> or --pin <tag|commit>")
        return None
    return {"kind": "track" if track else "pin", "ref": track or pin, "source": source}


@contextmanager
def ref_checkout(home: Path, spec: dict, name: str):
    """A checked clone of the ref: lineage, fork and release layout verified."""
    kit = _kit_metadata()
    source = kitsource.resolve_source(spec["source"], home)
    with kitsource.checkout(source, spec["ref"], spec["kind"], kit) as (tree, facts):
        kitsource.refuse_other_fork(facts, kit, name)
        kitsource.refuse_layout(tree)
        yield tree, facts


def install_ref(home: Path, plan: Plan, name: str, tree: Path, facts: dict,
                prior: dict | None) -> tuple[tuple[Path, Path], dict]:
    """Install the ref's tree as a release and point `refs/<name>` at it.

    Returns the `content` pair for `materialize` and the provenance `kit_ref`.
    A dry run installs and flips nothing and reads the checkout.
    """
    files = kithome.payload_files(tree)
    digest = kithome.payload_digest(tree, files)
    release = kithome.releases_dir(home) / digest[:12]
    previous = kithome.ref_release(home, name)
    held = previous.name if previous and previous != release.resolve() else (
        (prior or {}).get("previous_release"))
    kit_ref = {"kind": facts["kind"], "source": facts["source"], "ref": facts["ref"],
               "commit": facts["commit"], "release": digest[:12], "previous_release": held}
    link = kithome.ref_link(home, name)
    plan.record(f"ref    {name} -> {facts['kind']} {facts['ref']} @ {facts['commit'][:8]} "
                f"(release {digest[:12]})")
    if plan.apply:
        kithome.install_checked(tree, home, files, digest, {**facts, "dirty": False})
        kithome.flip_ref(home, name, release)
    return (link, link if plan.apply else tree), kit_ref


def _ref_note(kit_ref: dict) -> str:
    if kit_ref["kind"] == "pin":
        return (f"pinned to {kit_ref['ref']} @ {kit_ref['commit'][:8]}: "
                "moves only on 'devkit profile sync NAME --pin REF --apply'")
    return (f"tracking {kit_ref['ref']} @ {kit_ref['commit'][:8]}: "
            "moves on 'devkit update fetch' + 'devkit update apply --apply'")


def cmd_create(args) -> int:
    user = privilege.refuse_root(getattr(args, "user", None))
    home = Path(user.pw_dir)
    spec = ref_spec(args)
    with contextlib.ExitStack() as stack:
        tree = None
        if spec:
            tree, facts = stack.enter_context(ref_checkout(home, spec, args.name))
        profile = load_for_create(args.name, getattr(args, "type", None), kit_root=tree)
        _refuse_duplicate(home, profile["name"])
        instances.apply_headless(profile, getattr(args, "headless", None), home)
        plan = Plan(args.apply)
        if profile["headless"]:
            if getattr(args, "color", None):
                raise DevkitError("--color has no meaning for a headless profile",
                                  "drop --color, or drop --headless")
        else:
            pair = instances.assign_profile_color(
                profile, home, explicit=getattr(args, "color", None))
            plan.record(f"color  {pair['light']}")
        extra = {}
        if spec:
            content, kit_ref = install_ref(home, plan, profile["name"], tree, facts, None)
            extra = {"content": content, "kit_ref": kit_ref, "source_commit": facts["commit"]}
        materialize(profile, args.vendor, home, plan, args.force, **extra)
    uninstaller.ensure(home, plan)
    globalignore.ensure(home, plan)
    cli_link.ensure(home, plan)
    result = plan.report(f"profile {args.name}")
    if spec:
        print(_ref_note(kit_ref).replace("NAME", args.name))
    if plan.apply and plan.actions:
        _report_home_root_rules(home)
        finish_appforks(home, profile, user.pw_name)
    return result


def cmd_sync(args) -> int:
    user = privilege.refuse_root(getattr(args, "user", None))
    home = Path(user.pw_dir)
    spec = ref_spec(args)
    unpin = bool(getattr(args, "unpin", False))
    rows = [row for row in instances.discover_instances(home) if row[0] == args.name]
    prior = next((row[3].get("kit_ref") for row in rows if row[3].get("kit_ref")), None)
    if unpin and rows and not prior:
        raise DevkitError(f"{args.name} is not on a kit ref, so there is nothing to unpin",
                          f"devkit profile sync {args.name} --apply")
    if spec and not spec["source"] and prior:
        spec["source"] = prior["source"]  # a profile keeps the source it came from
    plan = Plan(args.apply)
    extra: dict = {}
    with contextlib.ExitStack() as stack:
        kit_root = None
        if spec:
            kit_root, facts = stack.enter_context(ref_checkout(home, spec, args.name))
        elif prior and not unpin:
            if kithome.ref_release(home, args.name) is None:
                raise DevkitError(
                    f"{args.name}: its {prior['kind']} {prior['ref']} release is gone "
                    f"(refs/{args.name} is missing or dangling)",
                    f"devkit profile sync {args.name} --{prior['kind']} {prior['ref']} --apply")
            kit_root = kithome.ref_link(home, args.name)
        profile = load_for_instance(args.name, home, kit_root=kit_root,
                                    headless=getattr(args, "headless", None))
        if not profile["headless"]:
            prov = next(row[3] for row in rows)
            if not prov.get("color"):
                instances.assign_profile_color(profile, home)
        if spec:
            content, kit_ref = install_ref(home, plan, args.name, kit_root, facts, prior)
            extra = {"content": content, "kit_ref": kit_ref, "source_commit": facts["commit"]}
        elif prior and not unpin:
            link = kithome.ref_link(home, args.name)
            extra = {"content": (link, link), "kit_ref": prior,
                     "source_commit": prior["commit"]}
        if unpin:
            plan.record(f"unref  {args.name} ({prior['kind']} {prior['ref']}): back to current")
        materialize(profile, None, home, plan, force=True, **extra)
    if unpin and plan.apply:
        kithome.drop_ref(home, args.name)
    uninstaller.ensure(home, plan)
    globalignore.ensure(home, plan)
    cli_link.ensure(home, plan)
    if plan.apply:
        migrations.run_needed(home, plan)
    result = plan.report(f"profile {args.name} (sync)")
    if spec:
        print(_ref_note(extra["kit_ref"]).replace("NAME", args.name))
    if plan.apply:
        finish_appforks(home, profile, user.pw_name)
    return result


def cmd_list(args) -> int:
    home = Path.home()
    found = instances.discover_instances(home)
    if not found:
        print("no installed profiles.")
        return 0
    print(f"{'PROFILE':16s} {'TYPE':14s} {'VENDOR':8s} {'STATE':12s} CONFIG DIR")
    for name, vendor, config_dir, prov in found:
        type_name = instances.instance_type(prov, name)
        ref = prov.get("kit_ref")
        state = f"{ref['kind']} {ref['ref']}" if ref else "installed"
        print(f"{name:16s} {type_name:14s} {vendor:8s} "
              f"{state:12s} {relative_to_home(config_dir)}")
    return 0


def cmd_show(args) -> int:
    home = Path.home()
    installed = [row for row in instances.discover_instances(home) if row[0] == args.name]
    stored_headless = False
    if installed:
        # Judge from the stored value: DEVKIT_HEADLESS must not misreport a desktop profile.
        stored_headless = bool(installed[0][3].get("headless"))
        profile = load_for_instance(args.name, home, headless=stored_headless)
    elif manifest.profile_path(args.name).is_file():
        profile = manifest.load(args.name)
        profile = instances.bind_instance(profile, args.name, args.name)
    else:
        raise DevkitError(
            f"no profile named {args.name!r}",
            "pass an installed instance name, or a type under profiles/")
    summary = {
        "name": profile["name"],
        "type": profile.get("type") or profile["name"],
        "lineage": profile.get("lineage"),
    }
    if stored_headless:
        summary["headless"] = True
    else:
        summary["colors"] = list(instances.profile_colors(profile))
    summary |= {
        "skills": len(profile.get("skills", [])),
        "rules": len(profile.get("rules", [])),
        "kb": len(profile.get("kb", [])),
        "mcp": profile.get("mcp", []),
        "instances": profile.get("instances", []),
        "required_binaries": manifest.provided_binaries(profile, include_optional=False),
        "optional_binaries": [b for b in manifest.provided_binaries(profile)
                              if b not in manifest.provided_binaries(profile, False)],
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_adopt(args) -> int:
    """Record an existing config dir as an instance without relocating anything."""
    user = privilege.refuse_root(getattr(args, "user", None))
    home = Path(user.pw_dir)
    profile = load_for_create(args.name, getattr(args, "type", None))
    config_dir = Path(args.config_dir).expanduser().resolve()
    if not config_dir.is_dir():
        raise DevkitError(f"{config_dir} is not a directory",
                          "pass --config-dir pointing at the existing vendor config")
    # Discovery only walks ~/.agents-profiles/<name>/<dir>; provenance written
    # anywhere else (a stock ~/.claude) is an instance no command can find again.
    expected_parent = (home / ".agents-profiles" / args.name).resolve()
    if (config_dir.parent != expected_parent
            or config_dir.name in instances.PROFILE_SKIP_DIRS):
        raise DevkitError(
            f"{config_dir} is not under {relative_to_home(expected_parent)}/, "
            "so devkit could not find the adopted instance again",
            f"use 'devkit profile create {args.name} --type TYPE' instead, or move the "
            f"directory to {relative_to_home(expected_parent)}/{args.vendor} first")

    plan = Plan(args.apply)
    prov = instances.provenance(profile, args.vendor, home, _kit_metadata(),
                                instances.kit_commit())
    prov["adopted"] = True
    prov["config_dir"] = str(config_dir)
    target = config_dir / instances.PROVENANCE_NAME
    if instances.read_provenance(config_dir):
        print(f"{config_dir} is already an adopted instance; nothing relocates.")
        return 0
    plan.record(f"write  {relative_to_home(target)} (adopt, nothing relocates)")
    if args.apply:
        write_json(target, prov)
    return plan.report(f"adopt {args.vendor} into profile {args.name}")


def cmd_migrate(args) -> int:
    from . import update
    return update.migrate_profile(args)


def cmd_auth_restore(args) -> int:
    return auth.cmd_restore(args)


def cmd_doctor(args) -> int:
    home = Path.home()
    uid = os.getuid()
    kit_commit = instances.kit_commit()
    problems: list[str] = []
    checked = 0

    installed: list[str] = []
    desktop_seen = False
    seen_legacy: set[str] = set()

    for name, vendor, config_dir, prov in instances.discover_instances(home):
        if args.profile and name != args.profile:
            continue
        checked += 1
        desktop_seen = desktop_seen or not prov.get("headless")
        if name not in installed:
            installed.append(name)
        label = f"{name}/{vendor}"
        ref = prov.get("kit_ref")
        expected = ref["commit"] if ref else kit_commit
        if ref and kithome.ref_release(home, name) is None:
            link = kithome.ref_link(home, name)
            problems.append(
                f"{label}: its {ref['kind']} {ref['ref']} release is gone "
                f"(refs/{name} is {'dangling' if link.is_symlink() else 'missing'})\n"
                f"    fix: devkit profile sync {name} --{ref['kind']} {ref['ref']} --apply")
        elif _bare_commit(prov.get("source_commit")) != _bare_commit(expected):
            problems.append(
                f"{label}: stale — installed from {str(prov.get('source_commit'))[:8]}, "
                f"{'its ref is at' if ref else 'kit is at'} {expected[:8]}\n"
                f"    fix: devkit profile sync {name} --apply")
        if prov.get("profile_schema_version", 0) > instances.PROFILE_SCHEMA_VERSION:
            problems.append(
                f"{label}: installed by a newer devkit "
                f"(schema {prov['profile_schema_version']} > {instances.PROFILE_SCHEMA_VERSION})\n"
                f"    fix: update this kit; there is no override")
        problems += _legacy_problems(home, name, config_dir, seen_legacy)
        shim = instances.paths_for(name, vendor, home)["bin_dir"] / "python3"
        if shim.is_symlink() and not shim.exists():
            problems.append(
                f"{label}: {relative_to_home(shim)} points at {shim.readlink()}, "
                f"which is gone; every hook would fail\n"
                f"    fix: devkit profile sync {name} --apply")
        offenders = privilege.find_root_owned(config_dir, uid, limit=5)
        if offenders:
            listed = ", ".join(relative_to_home(p) for p in offenders[:3])
            problems.append(
                f"{label}: {len(offenders)}+ path(s) not owned by you: {listed}\n"
                f"    fix: sudo chown -R {uid} {config_dir} "
                f"— and stop installing config with sudo")

    if installed:
        stale_cli = kithome.legacy_cli_link(home)
        if stale_cli:
            problems.append(
                f"legacy: {relative_to_home(home / '.local' / 'bin' / 'devkit')} is linked "
                f"to {stale_cli}, outside the kit home\n"
                f"    fix: devkit profile sync {installed[0]} --apply")
        undo = home / ".local" / "bin" / uninstaller.DEST_NAME
        if not undo.is_file():
            problems.append(
                f"{relative_to_home(undo)}: missing — {len(installed)} profile(s) "
                f"are installed and nothing on PATH removes them\n"
                f"    fix: devkit profile sync {installed[0]} --apply")

    for migration, reasons in migrations.needs_list(home):
        problems.append(f"migration {migration.name}: {'; '.join(reasons)}\n"
                        f"    fix: {migration.fix(home)}")

    problems += _home_root_problems(home)
    headless_only = instances.env_headless() or (checked > 0 and not desktop_seen)
    auth_lines = [] if headless_only else auth.doctor_lines(home)
    auth_ok = [line for line in auth_lines if "(want " not in line]
    problems += [line for line in auth_lines if "(want " in line]
    problems += appfork.doctor_lines(home)

    if not problems:
        print(f"doctor: clean ({checked} instance(s) checked).")
        for line in auth_ok:
            print(f"  {line}")
        return 0
    for problem in problems:
        print(f"  {problem}")
    print(f"\ndoctor: {len(problems)} problem(s).")
    return 1


def _bare_commit(commit: object) -> str:
    return str(commit or "").removesuffix("-dirty")


def _legacy_problems(home: Path, name: str, config_dir: Path,
                     seen: set[str]) -> list[str]:
    """Projections that still point at a checkout. One report per profile."""
    if name in seen:
        return []
    links = kithome.legacy_links(home, config_dir)
    if not links:
        return []
    seen.add(name)
    link, target = links[0]
    return [(f"legacy: {name}: {len(links)} link(s) point outside the kit home, "
             f"e.g. {relative_to_home(link)} -> {target}\n"
             f"    fix: devkit profile sync {name} --apply")]


# ---------------------------------------------------------- home-root rules

def _home_root_problems(home: Path) -> list[str]:
    problems = []
    for filename, (config_dirname, vendor) in HOME_ROOT_RULES.items():
        path = home / filename
        if not path.exists():
            continue
        try:
            size = path.stat().st_size
            readable = os.access(path, os.R_OK)
        except OSError:
            continue
        if size <= 1 and not readable:
            continue  # the recommended stub: present, unreadable, fails closed
        if size > 1:
            problems.append(
                f"home-root {filename} is populated ({size} bytes)\n"
                f"    {vendor} walks up to $HOME collecting instruction files, so this\n"
                f"    loads in ADDITION to {config_dirname}/{filename} and leaks into every profile\n"
                f"    fix: devkit fix-home-rules --apply")
    return problems


def _report_home_root_rules(home: Path) -> None:
    for problem in _home_root_problems(home):
        print(f"\n  note: {problem}")


def _appfork_steps() -> list[str]:
    return [
        "copy worker to /usr/local/bin/sync-devkit-profile-apps.py",
        "install profile emblem under /usr/lib/devkit/",
        "write /etc/apt/apt.conf.d/99-devkit-profile-apps",
        "write /etc/dpkg/dpkg.cfg.d/60devkit-profile-apps",
        "rsync stock Claude/ChatGPT/Cursor into /usr/lib/devkit/<vendor>-<profile>/",
        "patch desktopName / WM_CLASS in the copy only (never stock)",
        "badge in-tree icons from stock with a coloured shield emblem; " +
        "keep chrome-sandbox mode 4755",
    ]


def _devkit_cmd(*args: str) -> list[str]:
    return [sys.executable, str(REPO_ROOT / "devkit"), *args]


def finish_appforks(home: Path, profile: dict, user: str) -> None:
    if profile.get("headless"):
        return
    rc = escalate_appforks(home, profile, user)
    if rc:
        print(
            f"note: desktop forks were not applied (exit {rc}).\n"
            f"      Re-run after reviewing the plan above:\n"
            f"      devkit profile apps-sync --user {user} "
            f"--profile {profile['name']} --install-hook --apply"
        )


def escalate_appforks(home: Path, profile: dict | None, user: str) -> int:
    """Print the fork plan, then elevate. Config writes must already have finished."""
    missing = appfork.doctor_lines(home)
    if profile:
        prefix = f"{profile['name']}/"
        missing = [line for line in missing
                   if line.startswith(prefix) or "hooks are not installed" in line]
    if not missing:
        return 0
    profile_name = None if profile is None else profile["name"]
    env = appfork.Env()
    if privilege.regain_root():
        for line in appfork.install_hook(env, dry_run=False):
            print(line)
        return appfork.sync_homes(
            [home], env, dry_run=False, profile=profile_name)
    print("Desktop identity forks need a copy of each stock app under /usr/lib/devkit/.")
    for line in appfork.install_hook(env, dry_run=True):
        print(f"  {line}")
    appfork.sync_homes([home], env, dry_run=True, profile=profile_name)
    argv = _devkit_cmd(
        "profile", "apps-sync", "--user", user, "--install-hook", "--apply")
    if profile_name:
        argv += ["--profile", profile_name]
    return privilege.run_privileged(
        argv,
        reason="they copy vendor apps into /usr/lib/devkit and install apt/dpkg hooks.",
        steps=_appfork_steps(),
    )


def cmd_apps_sync(args) -> int:
    """Rebuild per-profile app forks. --apply prints the plan, then sudo."""
    if instances.env_headless():
        print("skip: headless devkit, no desktop forks or badges")
        return 0
    env = appfork.Env()
    user = getattr(args, "user", None) or pwd_name()
    dry_run = not args.apply
    if dry_run:
        if args.install_hook:
            for line in appfork.install_hook(env, dry_run=True):
                print(line)
            print("dry-run: no writes")
        homes = appfork.resolve_homes(getattr(args, "user", None), env)
        return appfork.sync_homes(
            homes, env, dry_run=True,
            profile=getattr(args, "profile", None),
            vendor=getattr(args, "vendor", None),
            icons_only=getattr(args, "icons_only", False),
        )
    if not privilege.is_root():
        if args.install_hook:
            for line in appfork.install_hook(env, dry_run=True):
                print(line)
        homes = appfork.resolve_homes(getattr(args, "user", None), env)
        appfork.sync_homes(
            homes, env, dry_run=True,
            profile=getattr(args, "profile", None),
            vendor=getattr(args, "vendor", None),
            icons_only=getattr(args, "icons_only", False),
        )
        argv = _devkit_cmd("profile", "apps-sync", "--user", user, "--apply")
        if args.install_hook:
            argv.append("--install-hook")
        if getattr(args, "profile", None):
            argv += ["--profile", args.profile]
        if getattr(args, "vendor", None):
            argv += ["--vendor", args.vendor]
        if getattr(args, "icons_only", False):
            argv.append("--icons-only")
        return privilege.run_privileged(
            argv,
            reason="they copy vendor apps into /usr/lib/devkit and install apt/dpkg hooks.",
            steps=_appfork_steps(),
        )
    if args.install_hook:
        for line in appfork.install_hook(env, dry_run=False):
            print(line)
    homes = appfork.resolve_homes(getattr(args, "user", None), env)
    return appfork.sync_homes(
        homes, env, dry_run=False,
        profile=getattr(args, "profile", None),
        vendor=getattr(args, "vendor", None),
        icons_only=getattr(args, "icons_only", False),
    )


def pwd_name() -> str:
    import pwd
    return pwd.getpwuid(os.getuid()).pw_name


def cmd_fix_home_rules(args) -> int:
    user = privilege.refuse_root(getattr(args, "user", None))
    home = Path(user.pw_dir)
    plan = Plan(args.apply)
    wanted = args.vendor or None

    for filename, (config_dirname, vendor) in HOME_ROOT_RULES.items():
        if wanted and vendor not in wanted:
            continue
        source = home / filename
        if not source.exists():
            continue
        try:
            size = source.stat().st_size
            readable = os.access(source, os.R_OK)
        except OSError:
            continue
        if size <= 1 and not readable:
            continue  # already the stub; a no-op, which is what re-running must be
        if not readable:
            raise DevkitError(f"{source} is unreadable but not the 1-byte stub",
                              "inspect it by hand; devkit will not guess at its contents")

        target = home / config_dirname / filename
        content = source.read_text(encoding="utf-8")

        if target.exists():
            existing = target.read_text(encoding="utf-8")
            if not args.force:
                raise DevkitError(
                    f"{target} already exists; it owns this content",
                    "re-run with --force to back it up and append under a marked block")
            merged = (existing.rstrip("\n") + "\n\n"
                      f"<!-- devkit: merged from {filename} at home root -->\n"
                      + content.lstrip("\n"))
            plan.record(f"append {relative_to_home(target)} (under a marked block)")
            if args.apply:
                back_up(target)
                target.write_text(merged, encoding="utf-8")
        else:
            plan.record(f"move   {filename} -> {relative_to_home(target)}")
            if args.apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

        plan.record(f"stub   {relative_to_home(source)} (1 byte, mode 000)")
        if args.apply:
            back_up(source)
            source.write_bytes(STUB_BYTES)
            source.chmod(STUB_MODE)

    if not plan.actions:
        print("fix-home-rules: nothing to do; home-root instruction files already fail closed.")
        return 0
    return plan.report("home-root instruction files")
