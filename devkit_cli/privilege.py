"""Privilege, ownership, and target-user resolution (section 4.9, D18).

The rule is: escalate for packages, never for configuration. `bootstrap.sh`
scopes sudo to package transactions; `install.py` and `devkit` refuse to run as
root, because a config file written by root in a user's home is a support
ticket, not an install.
"""

from __future__ import annotations

import os
import pwd
from pathlib import Path

from .errors import DevkitError


def is_root() -> bool:
    return os.geteuid() == 0


def invoking_user() -> str:
    """The human behind a sudo, if there is one."""
    return os.environ.get("SUDO_USER") or os.environ.get("DOAS_USER") or ""


def resolve_target_user(explicit: str | None) -> pwd.struct_passwd:
    """Who the install is for. Refuses root and /root homes outright."""
    name = explicit or invoking_user() or pwd.getpwuid(os.getuid()).pw_name
    try:
        entry = pwd.getpwnam(name)
    except KeyError:
        raise DevkitError(f"no such user: {name}",
                          "pass --user with an existing account name") from None
    if entry.pw_uid == 0:
        raise DevkitError("refusing to install for uid 0",
                          "pass --user <name> naming the account that will use the harness")
    home = Path(entry.pw_dir)
    if home == Path("/root") or home.parts[:2] == ("/", "root"):
        raise DevkitError(f"refusing to install into {home}",
                          "pass --user <name> naming a real user account")
    return entry


def refuse_root(target_user: str | None = None) -> pwd.struct_passwd:
    """Guard for every configuration write."""
    if is_root() and not target_user:
        who = invoking_user()
        hint = (f"re-run without sudo, or pass --user {who}" if who
                else "re-run as the user who will use the harness, or pass --user <name>")
        raise DevkitError("refusing to write configuration as root (D18)", hint)
    return resolve_target_user(target_user)


def owned_by(path: Path, uid: int) -> bool:
    try:
        return path.stat().st_uid == uid
    except OSError:
        return False


def find_root_owned(root: Path, uid: int, limit: int = 20) -> list[Path]:
    """Paths under an instance that the target user does not own.

    A root-owned file inside a profile is the signature of an install run with
    sudo that should not have been; `devkit doctor` reports it (4.9).
    """
    offenders: list[Path] = []
    if not root.exists():
        return offenders
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        if not owned_by(path, uid):
            offenders.append(path)
            if len(offenders) >= limit:
                break
    return offenders
