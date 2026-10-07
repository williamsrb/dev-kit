"""Privilege, ownership, and target-user resolution.

The rule is: escalate for packages and identity forks, never for configuration.
`bootstrap.sh` scopes sudo to package transactions; `install.py` and `devkit`
refuse to write config as root, because a config file written by root into a
user's home is a support ticket, not an install.

Every elevation prints the plan first, then asks for administrator privileges.
Never the other way around.

Package elevation is the start of `bootstrap.sh`. Desktop-fork elevation is the
end of `install.py` / `devkit profile apps-sync`. Each of those is a separate
command, so it can be run on its own before or after the rest of the workflow.

A terminal on stdin or stdout uses `sudo`. When neither is a terminal, that
path uses `pkexec`, or `sudo -A` when `pkexec` is not on PATH.
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
    """Guard for every configuration write.

    Root with --user becomes that account before anything is written, so every
    created path is owned by it.
    """
    if is_root() and not target_user:
        who = invoking_user()
        hint = (f"re-run without sudo, or pass --user {who}" if who
                else "re-run as the user who will use the harness, or pass --user <name>")
        raise DevkitError("refusing to write configuration as root", hint)
    entry = resolve_target_user(target_user)
    if is_root():
        act_as(entry)
    return entry


def act_as(entry: pwd.struct_passwd) -> None:
    """Switch real and effective ids to `entry`, keeping root as the saved uid.

    Real and effective must both change: bash resets its effective uid to the
    real one, so a child shell of a seteuid-only process would write as root.
    The saved uid survives here but not across exec, so only this process can
    take root back, through `regain_root`.
    """
    os.setgroups(os.getgrouplist(entry.pw_name, entry.pw_gid))
    os.setresgid(entry.pw_gid, entry.pw_gid, 0)
    os.setresuid(entry.pw_uid, entry.pw_uid, 0)
    os.environ["HOME"] = entry.pw_dir
    os.environ["USER"] = os.environ["LOGNAME"] = entry.pw_name


def regain_root() -> bool:
    """Take root back after `act_as`. False when this process never had it."""
    if os.getresuid()[2] != 0 or os.geteuid() == 0:
        return is_root()
    os.setresuid(0, 0, 0)
    os.setresgid(0, 0, 0)
    os.setgroups([0])
    return True


def shell_is_interactive() -> bool:
    """True when stdin or stdout is a terminal."""
    return sys.stdin.isatty() or sys.stdout.isatty()


def explain_elevation(reason: str, steps: list[str]) -> None:
    """Print why root is needed and what will run, before the prompt."""
    print(f"These steps need administrator privileges: {reason}")
    for step in steps:
        print(f"  {step}")
    print(ELEVATION_BANNER)
    sys.stdout.flush()


def run_privileged(argv: list[str], reason: str, steps: list[str]) -> int:
    """Print the privileged plan, then run it as root.

    Returns the elevation command's exit code. Does not re-exec this process,
    so a caller can still write user-owned config afterwards.
    """
    if is_root():
        raise DevkitError(
            "already running as root",
            "run the privileged command directly rather than escalating")
    explain_elevation(reason, steps)
    interactive = shell_is_interactive()
    sudo = shutil.which("sudo")
    pkexec = shutil.which("pkexec")
    if interactive:
        if not sudo:
            raise DevkitError(
                "sudo is not on PATH",
                "install sudo, or re-run the printed commands as root")
        command = [sudo, "--", *argv]
    elif pkexec:
        command = [pkexec, *argv]
    elif sudo:
        command = [sudo, "-A", "--", *argv]
    else:
        raise DevkitError(
            "pkexec and sudo are not on PATH",
            "install pkexec or sudo, or re-run the printed commands as root")
    if not interactive:
        print("Non-interactive shell: stdin and stdout are not terminals.")
        print("Run the elevated command below on its own, before or after the "
              "rest of this workflow, if the dialog does not appear here.")
    printed = " ".join(command)
    print(f"  + {printed}")
    sys.stdout.flush()
    return subprocess.run(command, check=False).returncode


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
