#!/usr/bin/env python3
"""devkit step 2: write settings and materialize profiles.

Step 1 (bootstrap.sh) installs dependencies and writes no configuration. This
writes configuration and installs no packages. Neither assumes the other had
network access, and neither escalates privilege for the other's job.

This refuses to run as root. A config file written by root into a user's home is
a support ticket, not an install. When you must run the whole thing under sudo
for some other reason, pass --user so every path is created owned by that
account.

Usage:
    ./install.py                            # dry run for the core profile
    ./install.py --profile enonic --apply
    ./install.py --profile enonic --apply --force
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
from devkit_cli.profiles import (_home_root_problems, cmd_fix_home_rules,  # noqa: E402
                                 materialize)


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
                        help="Profile to install (default: core).")
    parser.add_argument("--vendor", action="append", metavar="VENDOR",
                        help="Limit to these vendors (repeatable).")
    parser.add_argument("--apply", action="store_true",
                        help="Write. Without it this is a dry run.")
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
        profile = manifest.load(args.profile)

        if args.verify:
            return verify(profile, home)

        if not repo_file("core").is_dir():
            raise DevkitError("core/ has not been exported yet",
                              "run './devkit export --apply' first")

        plan = Plan(args.apply)
        materialize(profile, args.vendor, home, plan, args.force)
        result = plan.report(f"profile {args.profile} for {user.pw_name}")

        if args.fix_home_rules:
            fix_args = argparse.Namespace(vendor=None, apply=args.apply,
                                          force=args.force, user=args.user)
            cmd_fix_home_rules(fix_args)
        else:
            for problem in _home_root_problems(home):
                print(f"\n  note: {problem}")

        if args.apply:
            print(f"\nInstalled. Start it with the wrappers in {home}/.local/bin, "
                  f"e.g. claude-{args.profile}")
        return result

    except DevkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.fix:
            print(f"fix:   {exc.fix}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
