"""The one exception type devkit raises for expected, actionable failures."""

from __future__ import annotations


class DevkitError(Exception):
    """A failure that names the command which fixes it (Definition of Done 10).

    Raise this for anything the user can act on: a missing manifest, a collision,
    a refused update. Programming errors stay as ordinary exceptions so they keep
    their traceback.
    """

    def __init__(self, message: str, fix: str | None = None) -> None:
        super().__init__(message)
        self.fix = fix
