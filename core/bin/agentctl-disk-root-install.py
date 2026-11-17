#!/usr/bin/env python3
"""Install or remove the root-level disk scan used by `agentctl disk report root`.

Dry run by default: prints every path, mode and owner it would touch and writes
nothing. `--apply` performs it and needs root. The cron job runs only system
binaries and a root-owned copy of the scanner, never anything under a home
directory. Run it yourself with sudo; the agent only runs the dry run.
"""

from __future__ import annotations

import argparse
import grp
import os
import shutil
import sys
from pathlib import Path

SCANNER_SRC = Path(__file__).resolve().parent / "agentctl_disk_scan.py"
LIB_DIR = "/usr/local/lib/agentctl-disk"
SCANNER_DEST = f"{LIB_DIR}/agentctl_disk_scan.py"
CACHE_DIR = "/var/lib/agentctl-disk"
WRAPPER = "/etc/cron.daily/agentctl-disk"
WRAPPER_TEXT = (
    "#!/bin/sh\n"
    "umask 027\n"
    f"exec nice -n 19 ionice -c3 /usr/bin/python3 -I {SCANNER_DEST} scan --target / --id root "
    f"--cache-dir {CACHE_DIR} --quiet\n"
)
FIRST_RUN = f"sudo sh {WRAPPER}"


class InstallError(Exception):
    pass


def plan_install() -> list[tuple[str, str, str, str]]:
    """(action, path, mode, owner) for each step, in order."""
    return [
        ("mkdir", LIB_DIR, "0755", "root:root"),
        ("copy", SCANNER_DEST, "0644", "root:root"),
        ("mkdir", CACHE_DIR, "2750", "root:adm"),
        ("write", WRAPPER, "0755", "root:root"),
    ]


def plan_uninstall() -> list[tuple[str, str, str, str]]:
    return [("remove", WRAPPER, "", ""), ("remove", LIB_DIR, "", ""), ("remove", CACHE_DIR, "", "")]


def under(prefix: str, path: str) -> Path:
    return Path(prefix + path) if prefix else Path(path)


def refuse_symlink(path: Path) -> None:
    if path.is_symlink():
        raise InstallError(f"{path} is a symlink; refusing to write through it")


def chown(path: Path, owner: str, prefix: str) -> None:
    if prefix:
        return
    user, group = owner.split(":")
    shutil.chown(path, user, group)


def apply_install(prefix: str) -> None:
    if not prefix:
        try:
            grp.getgrnam("adm")
        except KeyError:
            raise InstallError("group adm does not exist; create it or pick another group") from None
    for action, path, mode, owner in plan_install():
        target = under(prefix, path)
        refuse_symlink(target)
        if action == "mkdir":
            target.mkdir(parents=True, exist_ok=True)
        elif action == "copy":
            shutil.copyfile(SCANNER_SRC, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(WRAPPER_TEXT, encoding="utf-8")
        os.chmod(target, int(mode, 8))
        chown(target, owner, prefix)
        print(f"done {action} {path} mode {mode} owner {owner}")


def apply_uninstall(prefix: str) -> None:
    for _action, path, _mode, _owner in plan_uninstall():
        target = under(prefix, path)
        refuse_symlink(target)
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)
        print(f"done remove {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install (or remove) the root-level disk scan: a root-owned scanner copy, a daily cron wrapper in\n"
            "/etc/cron.daily and a cache directory readable by group adm. Dry run unless --apply."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="Perform the changes (needs root). Default is a dry run.")
    parser.add_argument("--uninstall", action="store_true", help="Remove the wrapper, scanner copy and root cache.")
    parser.add_argument("--prefix", default="", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    steps = plan_uninstall() if args.uninstall else plan_install()
    for action, path, mode, owner in steps:
        detail = f" mode {mode} owner {owner}" if mode else ""
        print(f"{'would ' if not args.apply else ''}{action} {under(args.prefix, path)}{detail}")
    if not args.apply:
        print("dry run: nothing written. Re-run with sudo and --apply to perform these steps.")
        return 0
    if os.geteuid() != 0 and not args.prefix:
        print("error: --apply must run as root: sudo python3 " + str(Path(__file__).resolve()) + " --apply",
              file=sys.stderr)
        return 1
    try:
        (apply_uninstall if args.uninstall else apply_install)(args.prefix)
    except (InstallError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not args.uninstall:
        print(f"first scan now (optional, otherwise tonight via cron.daily): {FIRST_RUN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
