"""Profile commands: create, sync, adopt, list, show, doctor, fix-home-rules.

Every write goes through Plan so `--dry-run` is the default and `--apply` is the
exception (Definition of Done 7), and through `_write`, so an existing path the
kit did not author aborts and names itself unless `--force` backs it up first.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import (
    appfork,
    auth,
    cli_link,
    globalignore,
    instances,
    kithome,
    manifest,
    mcp,
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
                core_root: Path, link_core: Path) -> None:
    """Project one layer (skills/rules/kb) into the instance as per-entry symlinks.

    Symlinks, not copies: this is the contract sync-skill-projections.sh already
    uses, and it means an update to core/ reaches every profile without a re-copy.
    Existence is checked under `core_root` (the tree being read) while each link
    names `link_core` (the stable `current` tree), which dry run cannot read.
    """
    dest_root = config_dir / name
    wanted: dict[str, Path] = {}
    for entry in entries:
        leaf = manifest.layer_leaf(entry)
        if not (core_root / name / leaf).exists():
            continue
        wanted[leaf] = link_core / name / leaf
    for link_name, source in sorted(wanted.items()):
        link = dest_root / link_name
        if link.is_symlink() and link.readlink() == source:
            continue
        plan.record(f"link   {name}/{link_name}")
        if plan.apply:
            ensure_dir(dest_root)
            if link.is_symlink() or link.exists():
                if link.is_dir() and not link.is_symlink():
                    raise DevkitError(f"{link} is a real directory, not a projection",
                                      "move it aside by hand, then re-run")
                link.unlink()
            link.symlink_to(source)
    # Prune projections the profile no longer names.
    if dest_root.is_dir():
        for link in sorted(dest_root.iterdir()):
            if link.is_symlink() and link.name not in wanted:
                plan.record(f"prune  {name}/{link.name}")
                if plan.apply:
                    link.unlink()


def materialize(profile: dict, vendors: list[str] | None, home: Path,
                plan: Plan, force: bool, kit_root: Path | None = None,
                source_commit: str | None = None) -> None:
    """Write one profile's instances from the kit.

    The kit is first installed into the kit home (a no-op when `kit_root`, or
    the running tree, already is `current`). Everything is then read from and
    linked through `current`, so nothing devkit writes names the checkout. A
    dry run installs nothing: it reads the source tree and prints the `current`
    paths the links would have.
    """
    src = kit_root or REPO_ROOT
    link_core = kithome.current_link(home) / "core"
    root = kithome.ensure_installed(src, home, plan)
    kit = _kit_metadata(root)
    commit = source_commit or instances.kit_commit(root)
    core_root = root / "core"
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
            _link_layer(plan, layout["config_dir"], layer,
                        profile.get(layer, []), core_root, link_core)
        hooks_dir = layout["harness_dir"] / "hooks"
        if hooks_dir.is_dir():
            _symlink(plan, layout["config_dir"] / "hooks", hooks_dir,
                     f"{vendor}/hooks")

        _write_vendor_config(plan, vendor, profile, layout, tokens, force, root)
        _write_wrapper(plan, vendor, layout, tokens, force, root)
        if ("desktop" in instance.get("kind", "")
                and _write_desktop(plan, vendor, profile, layout, tokens,
                                 force, root)):
            wrote_desktop = True

        prov = instances.provenance(profile, vendor, home, kit, commit)
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
                rendered, profile, root, Path(tokens["HOME"]), target)
        elif template.name == "config.toml" and vendor == "codex":
            rendered = _fill_codex_mcp(
                rendered, profile, root, Path(tokens["HOME"]), target)
        _write(plan, target, rendered, force, label=f"{vendor}/{template.name}")
    if vendor == "claude":
        _write_claude_mcp(plan, profile, layout, force, root, Path(tokens["HOME"]))


def _fill_cursor_mcp(rendered: str, profile: dict, root: Path, home: Path,
                     target: Path) -> str:
    catalog = mcp.load_catalog(root)
    data = json.loads(rendered)
    comment = data.get("_comment") or []
    existing = {}
    if target.is_file():
        try:
            existing = json.loads(target.read_text()).get("mcpServers") or {}
        except json.JSONDecodeError:
            existing = {}
    payload = mcp.cursor_payload(profile, catalog, home, comment, existing)
    return json.dumps(payload, indent=2) + "\n"


def _fill_codex_mcp(rendered: str, profile: dict, root: Path, home: Path,
                    target: Path) -> str:
    catalog = mcp.load_catalog(root)
    existing = target.read_text(encoding="utf-8") if target.is_file() else ""
    extra = mcp.codex_toml_sections(profile, catalog, home, existing)
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
        profile, catalog, home, existing=current.get("mcpServers") or {})}
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
                    link_core)
    for name in ("bin", "mcp", "share", "config"):
        if name == "config" and profile.get("client_overlay"):
            _write_client_config(plan, agents_dir / name, profile["client_overlay"],
                                 core_root, link_core, force)
        elif (core_root / name).exists():
            _symlink(plan, agents_dir / name, link_core / name, f"agents/{name}")
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


def load_for_instance(name: str, home: Path,
                      kit_root: Path | None = None) -> dict:
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
    return profile


def _refuse_duplicate(home: Path, name: str) -> None:
    existing = home / ".agents-profiles" / name
    if existing.exists():
        raise DevkitError(
            f"profile {name!r} already exists at {existing}",
            "pick a unique name, or run 'devkit profile sync "
            f"{name} --apply' to re-materialize")


def cmd_create(args) -> int:
    user = privilege.refuse_root(getattr(args, "user", None))
    home = Path(user.pw_dir)
    profile = load_for_create(args.name, getattr(args, "type", None))
    _refuse_duplicate(home, profile["name"])
    pair = instances.assign_profile_color(
        profile, home, explicit=getattr(args, "color", None))
    plan = Plan(args.apply)
    plan.record(f"color  {pair['light']}")
    materialize(profile, args.vendor, home, plan, args.force)
    uninstaller.ensure(home, plan)
    globalignore.ensure(home, plan)
    cli_link.ensure(home, plan)
    result = plan.report(f"profile {args.name}")
    if plan.apply and plan.actions:
        _report_home_root_rules(home)
        finish_appforks(home, profile, user.pw_name)
    return result


def cmd_sync(args) -> int:
    user = privilege.refuse_root(getattr(args, "user", None))
    home = Path(user.pw_dir)
    profile = load_for_instance(args.name, home)
    plan = Plan(args.apply)
    materialize(profile, None, home, plan, force=True)
    uninstaller.ensure(home, plan)
    globalignore.ensure(home, plan)
    cli_link.ensure(home, plan)
    result = plan.report(f"profile {args.name} (sync)")
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
        print(f"{name:16s} {type_name:14s} {vendor:8s} "
              f"{'installed':12s} {relative_to_home(config_dir)}")
    return 0


def cmd_show(args) -> int:
    home = Path.home()
    installed = [row for row in instances.discover_instances(home) if row[0] == args.name]
    if installed:
        profile = load_for_instance(args.name, home)
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
        "colors": list(instances.profile_colors(profile)),
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
    seen_legacy: set[str] = set()

    for name, vendor, config_dir, prov in instances.discover_instances(home):
        if args.profile and name != args.profile:
            continue
        checked += 1
        if name not in installed:
            installed.append(name)
        label = f"{name}/{vendor}"
        if _bare_commit(prov.get("source_commit")) != _bare_commit(kit_commit):
            problems.append(
                f"{label}: stale — installed from {str(prov.get('source_commit'))[:8]}, "
                f"kit is at {kit_commit[:8]}\n"
                f"    fix: devkit profile sync {name} --apply")
        if prov.get("profile_schema_version", 0) > instances.PROFILE_SCHEMA_VERSION:
            problems.append(
                f"{label}: installed by a newer devkit "
                f"(schema {prov['profile_schema_version']} > {instances.PROFILE_SCHEMA_VERSION})\n"
                f"    fix: update this kit; there is no override")
        problems += _legacy_problems(home, name, config_dir, seen_legacy)
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

    problems += _home_root_problems(home)
    auth_lines = auth.doctor_lines(home)
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
