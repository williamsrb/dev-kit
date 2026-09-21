"""Privilege, ownership, and target-user resolution.

The rule is: escalate for packages and identity forks, never for configuration.
`bootstrap.sh` scopes sudo to package transactions; `install.py` and `devkit`
refuse to write config as root, because a config file written by root into a
user's home is a support ticket, not an install.

Every elevation prints the plan first, then asks sudo for a password. Never
the other way around.
"""

from __future__ import annotations

import os
import pwd
import shutil
import subprocess
import sys
from pathlib import Path

from .errors import DevkitError

ELEVATION_BANNER = "Asking for administrator privileges."


def is_root() -> bool:
    return os.geteuid() == 0


def invoking_user() -> str:
    """The human behind a sudo, if there is one."""
    return os.environ.get("SUDO_USER") or os.environ.get("DOAS_USER") or ""


def resolve_target_user(explicit: str | None) -> pwd.struct_passwd:
    """Who the install is for. Refuses root and /root homes outright."""
    name = explicit or pwd.getpwuid(os.getuid()).pw_name
    try:
        entry = pwd.getpwnam(name)
    except KeyError:
        raise DevkitError(f"no such user: {name}",
                          "pass --user with an existing account name") from None
    if entry.pw_uid == 0:
        raise DevkitError("refusing to install for uid 0",
                          "pass --user <name> naming the account that will use the harness")
    home = Path(entry.pw_dir)
    if home.parts[:2] == ("/", "root"):
        raise DevkitError(f"refusing to install into {home}",
                          "pass --user <name> naming a real user account")
    return entry


def refuse_root(target_user: str | None = None) -> pwd.struct_passwd:
    """Guard for every configuration write."""
    if is_root() and not target_user:
        who = invoking_user()
        hint = (f"re-run without sudo, or pass --user {who}" if who
                else "re-run as the user who will use the harness, or pass --user <name>")
        raise DevkitError("refusing to write configuration as root", hint)
    return resolve_target_user(target_user)


def explain_elevation(reason: str, steps: list[str]) -> None:
    """Print why root is needed and what will run, before sudo prompts."""
    print(f"These steps need administrator privileges: {reason}")
    for step in steps:
        print(f"  {step}")
    print(ELEVATION_BANNER)
    sys.stdout.flush()


def run_privileged(argv: list[str], reason: str, steps: list[str]) -> int:
    """Print the privileged plan, then run it under sudo.

    Returns sudo's exit code. Does not re-exec this process, so a caller can
    still write user-owned config afterwards.
    """
    if is_root():
        raise DevkitError(
            "already running as root",
            "run the privileged command directly rather than escalating")
    explain_elevation(reason, steps)
    sudo = shutil.which("sudo")
    if not sudo:
        raise DevkitError(
            "sudo is not on PATH",
            "install sudo, or re-run the printed commands as root")
    printed = " ".join(argv)
    print(f"  + sudo -- {printed}")
    sys.stdout.flush()
    return subprocess.run([sudo, "--", *argv]).returncode


def owned_by(path: Path, uid: int) -> bool:
    try:
        return path.stat().st_uid == uid
    except OSError:
        return False


def find_root_owned(root: Path, uid: int, limit: int = 20) -> list[Path]:
    """Paths under an instance that the target user does not own.

    A root-owned file inside a profile is the signature of an install run with
    sudo that should not have been; `devkit doctor` reports it.
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
