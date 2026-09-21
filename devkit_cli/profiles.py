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

from . import appfork, auth, instances, manifest, privilege
from .common import (EXEC_MODE, FILE_MODE, Plan, REPO_ROOT, back_up,
                     ensure_dir, relative_to_home, write_json)
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
                core_root: Path) -> None:
    """Project one layer (skills/rules/kb) into the instance as per-entry symlinks.

    Symlinks, not copies: this is the contract sync-skill-projections.sh already
    uses, and it means an update to core/ reaches every profile without a re-copy.
    """
    dest_root = config_dir / name
    wanted: dict[str, Path] = {}
    for entry in entries:
        source = core_root / name / entry.split("/")[0].replace("**", "").rstrip("/")
        if not source.exists():
            continue
        wanted[source.name] = source
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
    """Write one profile's instances from a checkout of the kit.

    `kit_root` and `source_commit` name which checkout: `update apply` installs
    from the staged payload rather than from whatever the local tree happens to
    be at: apply reads the staged payload.
    """
    root = kit_root or REPO_ROOT
    kit = _kit_metadata(root)
    commit = source_commit or instances.kit_commit()
    core_root = root / "core"
    if not core_root.is_dir():
        raise DevkitError(f"{core_root} has not been exported yet",
                          "run 'devkit export --apply' first")

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

        # The harness itself is shared, projected once per profile.
        harness_link = layout["harness_dir"] / "core"
        if not (harness_link.is_symlink() and harness_link.readlink() == core_root):
            plan.record(f"link   {relative_to_home(harness_link)} -> core/")
            if plan.apply:
                if harness_link.is_symlink() or harness_link.exists():
                    harness_link.unlink()
                harness_link.symlink_to(core_root)

        for layer in ("skills", "rules", "kb"):
            _link_layer(plan, layout["config_dir"], layer,
                        profile.get(layer, []), core_root)

        _write_vendor_config(plan, vendor, layout, tokens, force, root)
        _write_wrapper(plan, vendor, layout, tokens, force, root)
        if "desktop" in instance.get("kind", ""):
            _write_desktop(plan, vendor, profile, layout, tokens, force, root)

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


def _write_vendor_config(plan: Plan, vendor: str, layout: dict,
                         tokens: dict, force: bool, root: Path) -> None:
    template_dir = root / "templates" / vendor
    if not template_dir.is_dir():
        return
    for template in sorted(template_dir.iterdir()):
        if not template.is_file():
            continue
        rendered = instances.render(template.read_text(encoding="utf-8"), tokens)
        _write(plan, layout["config_dir"] / template.name, rendered, force,
               label=f"{vendor}/{template.name}")


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
                   tokens: dict, force: bool, root: Path) -> None:
    if not instances.first_existing(instances.VENDOR_GUI_CANDIDATES.get(vendor, [])):
        plan.record(f"skip   desktop {vendor} (GUI not installed)")
        return
    template = root / "templates" / "desktop" / f"{vendor}.desktop"
    if not template.is_file():
        return
    rendered = instances.render(template.read_text(encoding="utf-8"), tokens)
    _write(plan, layout["desktop"], rendered, force,
           label=relative_to_home(layout["desktop"]))

    light, _dark = instances.profile_colors(profile)
    source_icon = _find_vendor_icon(vendor)
    if source_icon and not layout["icon"].is_file():
        plan.record(f"icon   {relative_to_home(layout['icon'])} ({light})")
        if plan.apply:
            if not instances.recolor_icon(source_icon, layout["icon"], light):
                print(f"  note: could not recolour {vendor} icon "
                      f"(ImageMagick missing?); the launcher falls back to the stock icon")


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

    It is a flat file of `key: value` lines by design — YAML is kept only where
    nothing parses it at runtime — so a line reader is honest here. Inline `#`
    comments are stripped: the file documents itself heavily.
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
    return instances.bind_instance(manifest.load(type_name, kit_root=kit_root),
                                   name, type_name)


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
    plan = Plan(args.apply)
    materialize(profile, args.vendor, home, plan, args.force)
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

    for name, vendor, config_dir, prov in instances.discover_instances(home):
        if args.profile and name != args.profile:
            continue
        checked += 1
        label = f"{name}/{vendor}"
        if prov.get("source_commit") != kit_commit:
            problems.append(
                f"{label}: stale — installed from {str(prov.get('source_commit'))[:8]}, "
                f"kit is at {kit_commit[:8]}\n"
                f"    fix: devkit profile sync {name} --apply")
        if prov.get("profile_schema_version", 0) > instances.PROFILE_SCHEMA_VERSION:
            problems.append(
                f"{label}: installed by a newer devkit "
                f"(schema {prov['profile_schema_version']} > {instances.PROFILE_SCHEMA_VERSION})\n"
                f"    fix: update this kit; there is no override")
        offenders = privilege.find_root_owned(config_dir, uid, limit=5)
        if offenders:
            listed = ", ".join(relative_to_home(p) for p in offenders[:3])
            problems.append(
                f"{label}: {len(offenders)}+ path(s) not owned by you: {listed}\n"
                f"    fix: sudo chown -R {uid} {config_dir} "
                f"— and stop installing config with sudo")

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
        "write /etc/apt/apt.conf.d/99-devkit-profile-apps",
        "write /etc/dpkg/dpkg.cfg.d/60devkit-profile-apps",
        "rsync stock Claude/ChatGPT/Cursor into /usr/lib/devkit/<vendor>-<profile>/",
        "patch desktopName / WM_CLASS in the copy only (never stock, never Personal)",
        "recolor in-tree icons from stock; keep chrome-sandbox mode 4755",
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
    """Print the fork plan, then sudo. Config writes must already have finished."""
    missing = appfork.doctor_lines(home)
    if profile:
        prefix = f"{profile['name']}/"
        missing = [line for line in missing
                   if line.startswith(prefix) or "hooks are not installed" in line]
    if not missing:
        return 0
    profile_name = None if profile is None else profile["name"]
    env = appfork.Env()
    if privilege.is_root():
        for line in appfork.install_hook(env, dry_run=False):
            print(line)
        return appfork.sync_homes(
            [home], env, dry_run=False, profile=profile_name)
    print("Desktop identity forks need a Personal-style copy of each stock app.")
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
