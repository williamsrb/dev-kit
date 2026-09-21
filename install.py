#!/usr/bin/env python3
"""devkit step 2: write settings and materialize profiles.

Step 1 (bootstrap.sh) installs dependencies and writes no configuration. This
writes configuration and installs no packages. Neither assumes the other had
network access.

This refuses to write configuration as root. A config file written by root
into a user's home is a support ticket, not an install. When you must run the
whole thing under sudo for some other reason, pass --user so every path is
created owned by that account.

After user-owned config is written, `--apply` prints the desktop-fork plan
(rsync into /usr/lib/devkit, asar identity, apt/dpkg hooks) and then asks
sudo. That elevation is a separate step from configuration, with the plan
visible before the password prompt.

Usage:
    ./install.py                            # dry run; offers a first profile on --apply
    ./install.py --apply                    # TTY: offer name + type. Non-TTY: type core
    ./install.py --profile enonic --apply   # skip the offer; name = type
    ./install.py --name dummy --profile enonic --apply
    ./install.py --verify

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from devkit_cli import instances, manifest, privilege  # noqa: E402
from devkit_cli.common import Plan, repo_file  # noqa: E402
from devkit_cli.errors import DevkitError  # noqa: E402
from devkit_cli.profiles import (_home_root_problems, choose_first_profile,  # noqa: E402
                                 cmd_fix_home_rules, finish_appforks,
                                 flag_given, load_for_create, materialize)


def verify(profile: dict, home: Path) -> int:
    """Report what is installed and what is missing, without writing."""
    problems = 0
    print(f"profile {profile['name']} (lineage: {' -> '.join(profile.get('lineage', []))})")

    core = repo_file("core")
    print(f"  core export        {'ok' if core.is_dir() else 'MISSING — run devkit export --apply'}")
    problems += 0 if core.is_dir() else 1

    for instance in profile.get("instances", []):
        vendor = instance["vendor"]
        layout = instances.paths_for(profile["name"], vendor, home)
        prov = instances.read_provenance(layout["config_dir"])
        state = "installed" if prov else "not installed"
        print(f"  {vendor:18s} {state}")
        if prov:
            wrapper = layout["wrapper"]
            print(f"    wrapper          {'ok' if wrapper.is_file() else 'MISSING'} {wrapper}")
            problems += 0 if wrapper.is_file() else 1

    for problem in _home_root_problems(home):
        print(f"  {problem}")
        problems += 1

    print(f"\nverify: {'clean' if not problems else f'{problems} problem(s)'}")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--profile", default="core",
                        help="Profile type to install (default: core). Passing this "
                             "skips the first-profile offer.")
    parser.add_argument("--name", metavar="NAME",
                        help="Instance name. Default: the type. Unique across all types.")
    parser.add_argument("--vendor", action="append", metavar="VENDOR",
                        help="Limit to these vendors (repeatable).")
    parser.add_argument("--apply", action="store_true",
                        help="Write user-owned config, then print the desktop-fork "
                             "plan and ask sudo. Without it this is a dry run.")
    parser.add_argument("--force", action="store_true",
                        help="Proceed past a collision, after a timestamped backup.")
    parser.add_argument("--user", metavar="NAME",
                        help="Install for this account. Required when running under sudo.")
    parser.add_argument("--verify", action="store_true",
                        help="Report installed state and exit. Writes nothing.")
    parser.add_argument("--fix-home-rules", action="store_true",
                        help="Also move a populated home-root CLAUDE.md/AGENTS.md "
                             "into its vendor config dir.")
    args = parser.parse_args()

    try:
        user = privilege.refuse_root(args.user)
        home = Path(user.pw_dir)

        if args.verify:
            return verify(manifest.load(args.profile), home)

        if not repo_file("core").is_dir():
            raise DevkitError("core/ has not been exported yet",
                              "run './devkit export --apply' first")

        empty = not instances.discover_instances(home)
        offer = (
            args.apply
            and sys.stdin.isatty()
            and empty
            and not flag_given("--profile")
            and not flag_given("--name")
        )
        if empty and not args.apply and not flag_given("--profile") and not flag_given("--name"):
            print("note: no profile is installed yet. --apply will offer to create one.")
            print("      Non-interactive: pass --name NAME and/or --profile TYPE.")

        chosen = choose_first_profile(
            home, args.profile, name=args.name, offer=offer)
        if chosen is None:
            print("No profile created.")
            return 0
        name, type_name = chosen
        profile = load_for_create(name, type_name)

        plan = Plan(args.apply)
        materialize(profile, args.vendor, home, plan, args.force)
        result = plan.report(f"profile {name} (type {type_name}) for {user.pw_name}")

        if args.fix_home_rules:
            fix_args = argparse.Namespace(vendor=None, apply=args.apply,
                                          force=args.force, user=args.user)
            cmd_fix_home_rules(fix_args)
        else:
            for problem in _home_root_problems(home):
                print(f"\n  note: {problem}")

        if args.apply:
            finish_appforks(home, profile, user.pw_name)
            print(f"\nInstalled. Start it with the wrappers in {home}/.local/bin, "
                  f"e.g. claude-{name}")
        return result

    except DevkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.fix:
            print(f"fix:   {exc.fix}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
