"""Placeholder for the update command group. Implemented in a later phase."""

from __future__ import annotations

from .errors import DevkitError


def _not_yet(command: str, phase: str):
    raise DevkitError(f"'devkit {command}' is not implemented yet ({phase})",
                      "run 'devkit --help' for the commands that are")


def cmd_check(args):
    return _not_yet("update check", "A5b")


def cmd_fetch(args):
    return _not_yet("update fetch", "A5b")


def cmd_apply(args):
    return _not_yet("update apply", "A5b")


def cmd_origin_show(args):
    return _not_yet("origin show", "A5b")


def cmd_origin_adopt(args):
    return _not_yet("origin adopt", "A5b")
