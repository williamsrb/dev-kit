"""Placeholder for the profiles command group. Implemented in a later phase."""

from __future__ import annotations

from .errors import DevkitError


def _not_yet(command: str, phase: str):
    raise DevkitError(f"'devkit {command}' is not implemented yet ({phase})",
                      "run 'devkit --help' for the commands that are")


def cmd_list(args):
    return _not_yet("profile list", "A7")


def cmd_show(args):
    return _not_yet("profile show", "A7")


def cmd_create(args):
    return _not_yet("profile create", "A5")


def cmd_sync(args):
    return _not_yet("profile sync", "A5")


def cmd_adopt(args):
    return _not_yet("profile adopt", "A5")


def cmd_migrate(args):
    return _not_yet("profile migrate", "A5b")


def cmd_doctor(args):
    return _not_yet("doctor", "A7")


def cmd_fix_home_rules(args):
    return _not_yet("fix-home-rules", "A5")
