"""Argument parsing for `devkit`, including the help contract.

The contract: bare invocation and `--help` produce identical stdout and exit 0,
recursively for every group. Only a genuine mistake — an unknown subcommand or
a bad flag — writes usage to stderr and exits 2.

Argparse does not do this by default, so each group carries an explicit default
action that prints its own help, and `main` checks unknown arguments *before*
the no-command branch. Getting that order wrong makes `devkit --nope` exit 0.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from . import docsgen, export, paths, profiles, update
from .errors import DevkitError

DESCRIPTION = """\
Install and manage isolated agent-harness profiles.

devkit keeps several agent harnesses on one machine without collision: each
profile has its own config dir, skills, rules, kb, MCP set, CLI wrapper,
desktop launcher, and a Personal-style GUI fork (unique desktopName / WM_CLASS).
Wrappers export DEVKIT_PROFILE and AGENTS_HOME and prepend the profile bin to
PATH, so agentctl and other harness tools see only that profile. PATH alone is
not enough: those tools read AGENTS_HOME, not $HOME/.agents.

Common examples:
  devkit export --check              # is core/ behind the export source?
  devkit lint-paths                  # no home paths in machine-consumed positions
  devkit profile list
  devkit profile create dummy --type enonic
  devkit profile create enonic
  devkit profile apps-sync --apply   # prints the fork plan, then asks sudo
  devkit profile auth restore
  devkit update check
  devkit doctor

Run 'devkit GROUP --help' or 'devkit GROUP COMMAND --help' for details.
"""


def _help_action(parser: argparse.ArgumentParser) -> Callable[[argparse.Namespace], int]:
    def run(_args: argparse.Namespace) -> int:
        parser.print_help()
        return 0
    return run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devkit",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    top = parser.add_subparsers(
        dest="group", required=False, title="command groups", metavar="GROUP"
    )

    def group(name: str, summary: str) -> argparse._SubParsersAction:
        group_parser = top.add_parser(
            name, help=summary, description=summary,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        group_parser.set_defaults(func=_help_action(group_parser))
        return group_parser.add_subparsers(
            dest="action", required=False, title="commands", metavar="COMMAND"
        )

    def flat(name: str, summary: str) -> argparse.ArgumentParser:
        """A command with no subcommands of its own."""
        sub = top.add_parser(
            name, help=summary, description=summary,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        return sub

    # -- export -------------------------------------------------------------
    exp = flat("export", "Copy the allowlisted subset of the harness into core/.")
    exp.add_argument("--check", action="store_true",
                     help="Exit 1 when core/ is behind the source. Writes nothing.")
    exp.add_argument("--apply", action="store_true",
                     help="Write the export. Without it, this is a dry run.")
    exp.add_argument("--source", metavar="DIR",
                     help="Export source. Default: the allowlist's source key.")
    exp.add_argument("--no-scan", action="store_true",
                     help="Skip the gitleaks gate. For offline use only.")
    exp.set_defaults(func=export.cmd_export)

    # -- lint-paths ---------------------------------------------------------
    lint = flat("lint-paths", "Fail on home paths in machine-consumed positions.")
    lint.add_argument("paths", nargs="*", metavar="PATH",
                      help="Files or directories to check. Default: the whole repo.")
    lint.add_argument("--contract", metavar="FILE",
                      help="Path contract. Default: path-contract.json.")
    lint.set_defaults(func=paths.cmd_lint_paths)

    # -- doctor -------------------------------------------------------------
    doc = flat("doctor",
               "Check instances for staleness, ownership, auth handlers, and desktop forks.")
    doc.add_argument("--profile", metavar="NAME", help="Check only this profile.")
    doc.set_defaults(func=profiles.cmd_doctor)

    # -- profile ------------------------------------------------------------
    profile = group("profile",
                    "Create, inspect, sync, and rebuild isolated harness profiles.")

    p_list = profile.add_parser("list", help="Show known profiles and their instances.")
    p_list.set_defaults(func=profiles.cmd_list)

    p_show = profile.add_parser("show", help="Show one profile's resolved manifest.")
    p_show.add_argument("name")
    p_show.set_defaults(func=profiles.cmd_show)

    p_create = profile.add_parser(
        "create",
        help="Materialize a named instance from a profile type.",
    )
    p_create.add_argument("name")
    p_create.add_argument("--type", metavar="TYPE",
                          help="Profile type (profiles/<TYPE>.json). Default: NAME when that type exists.")
    p_create.add_argument("--vendor", action="append", metavar="VENDOR",
                          help="Limit to these vendors (repeatable).")
    p_create.add_argument("--apply", action="store_true",
                          help="Write user-owned config, then print the desktop-fork "
                               "plan and ask sudo. Default: dry run.")
    p_create.add_argument("--force", action="store_true",
                          help="Proceed past a collision, after a timestamped backup. Does not bypass a duplicate name.")
    p_create.set_defaults(func=profiles.cmd_create)

    p_sync = profile.add_parser("sync", help="Re-materialize after a manifest change.")
    p_sync.add_argument("name")
    p_sync.add_argument("--apply", action="store_true",
                        help="Write user-owned config, then print the desktop-fork "
                             "plan and ask sudo. Default: dry run.")
    p_sync.set_defaults(func=profiles.cmd_sync)

    p_adopt = profile.add_parser("adopt", help="Record an existing dir as an instance.")
    p_adopt.add_argument("name")
    p_adopt.add_argument("--type", metavar="TYPE",
                         help="Profile type. Default: NAME when that type exists.")
    p_adopt.add_argument("--vendor", required=True)
    p_adopt.add_argument("--config-dir", required=True)
    p_adopt.add_argument("--apply", action="store_true", help="Write. Default: dry run.")
    p_adopt.set_defaults(func=profiles.cmd_adopt)

    p_migrate = profile.add_parser("migrate", help="Move an instance to another fork.")
    p_migrate.add_argument("name")
    p_migrate.add_argument("--to-fork", required=True)
    p_migrate.add_argument("--apply", action="store_true", help="Write. Default: dry run.")
    p_migrate.set_defaults(func=profiles.cmd_migrate)

    p_auth = profile.add_parser(
        "auth",
        help="Install or restore URL-redirect auth handlers.",
        description=(
            "Linux allows one default handler per URL scheme. Profile launchers "
            "do not claim vendor schemes; a NoDisplay dispatcher routes the "
            "callback to the profile that started login."
        ),
    )
    p_auth.set_defaults(func=_help_action(p_auth))
    auth_cmds = p_auth.add_subparsers(
        dest="auth_action", required=False, title="commands", metavar="COMMAND"
    )
    p_auth_restore = auth_cmds.add_parser(
        "restore", help="Put stock/Personal scheme handlers back.")
    p_auth_restore.add_argument("--apply", action="store_true",
                                help="Write. Default: dry run.")
    p_auth_restore.set_defaults(func=profiles.cmd_auth_restore)

    p_apps = profile.add_parser(
        "apps-sync",
        help="Rebuild per-profile desktop app forks (Personal-style rsync + asar identity).",
        description=(
            "Rebuild per-profile desktop app forks from the stock packages. "
            "Same recipe as Claude Personal: rsync into /usr/lib/devkit/, patch "
            "desktopName / WM_CLASS, recolor in-tree icons. Never writes stock "
            "trees or Claude Personal. --apply prints the plan, then asks sudo."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_apps.add_argument("--user", metavar="NAME",
                        help="Account whose ~/.agents-profiles to sync. Default: you, or all homes from the apt hook.")
    p_apps.add_argument("--profile", metavar="NAME", help="Only this profile.")
    p_apps.add_argument("--vendor", metavar="VENDOR", help="Only this vendor.")
    p_apps.add_argument("--install-hook", action="store_true",
                        help="Install apt + dpkg post-invoke hooks and copy the worker to /usr/local/bin.")
    p_apps.add_argument("--icons-only", action="store_true",
                        help="Recolor fork icons from stock; skip rsync/asar.")
    p_apps.add_argument("--apply", action="store_true",
                        help="Write. Prints the plan, then asks sudo. Default: dry run.")
    p_apps.set_defaults(func=profiles.cmd_apps_sync)

    # -- update -------------------------------------------------------------
    upd = group("update", "Check, stage, and apply kit updates (one direction).")

    u_check = upd.add_parser("check", help="Report available updates. Never writes.")
    u_check.add_argument("--profile", metavar="NAME")
    u_check.set_defaults(func=update.cmd_check)

    u_fetch = upd.add_parser("fetch", help="Download and verify into the staging cache.")
    u_fetch.add_argument("--ref", default="HEAD")
    u_fetch.set_defaults(func=update.cmd_fetch)

    u_apply = upd.add_parser("apply", help="Install a staged update. Offline.")
    u_apply.add_argument("--profile", metavar="NAME")
    u_apply.add_argument("--apply", action="store_true", help="Write. Default: dry run.")
    u_apply.set_defaults(func=update.cmd_apply)

    # -- origin -------------------------------------------------------------
    origin = group("origin", "Inspect and adopt the kit this instance came from.")
    o_show = origin.add_parser("show", help="Show lineage, fork and upstream.")
    o_show.set_defaults(func=update.cmd_origin_show)
    o_adopt = origin.add_parser("adopt", help="Point an instance at a different fork.")
    o_adopt.add_argument("--fork-id", required=True)
    o_adopt.add_argument("--upstream", required=True)
    o_adopt.add_argument("--apply", action="store_true", help="Write. Default: dry run.")
    o_adopt.set_defaults(func=update.cmd_origin_adopt)

    # -- docs ---------------------------------------------------------------
    docs = group("docs", "Generate and verify the documentation tree.")
    d_gen = docs.add_parser("generate", help="Regenerate the generated docs sections.")
    d_gen.add_argument("--check", action="store_true", help="Exit 1 on any diff.")
    d_gen.set_defaults(func=docsgen.cmd_generate)

    # -- fix-home-rules -----------------------------------------------------
    fix = flat("fix-home-rules",
               "Move a home-root CLAUDE.md/AGENTS.md into its vendor config dir.")
    fix.add_argument("--vendor", action="append", metavar="VENDOR")
    fix.add_argument("--apply", action="store_true", help="Write. Default: dry run.")
    fix.add_argument("--force", action="store_true",
                     help="Append under a marked block when the target already exists.")
    fix.set_defaults(func=profiles.cmd_fix_home_rules)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)

    # Order matters: a bad flag on a bare invocation must not reach the help
    # branch and exit 0.
    if unknown:
        parser.error("unrecognized arguments: " + " ".join(unknown))
    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except DevkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.fix:
            print(f"fix:   {exc.fix}", file=sys.stderr)
        return 1
