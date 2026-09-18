"""Placeholder for the docsgen command group. Implemented in a later phase."""

from __future__ import annotations

from .errors import DevkitError


def _not_yet(command: str, phase: str):
    raise DevkitError(f"'devkit {command}' is not implemented yet ({phase})",
                      "run 'devkit --help' for the commands that are")


def cmd_generate(args):
    return _not_yet("docs generate", "A8")
