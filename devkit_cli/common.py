"""Paths, manifest loading, and the dry-run/backup conventions every command shares."""

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
from pathlib import Path

from .errors import DevkitError

REPO_ROOT = Path(__file__).resolve().parent.parent

# Written into kit source wherever a home-anchored path is unavoidable, and
# rendered per context at install time. `~` is never used:
# it expands only in a shell, unquoted, at word start.
HOME_TOKEN = "${HOME}"

# Modes are set explicitly rather than inherited from umask: an install under
# umask 077 must produce the same tree as one under umask 022. These are the
# umask-022 values, which is what the clean-room build verified.
FILE_MODE = 0o644
EXEC_MODE = 0o755
DIR_MODE = 0o755


def ensure_dir(path: Path) -> None:
    """`mkdir -p` that sets the mode of every level it creates."""
    created = [p for p in (path, *path.parents) if not p.exists()]
    path.mkdir(parents=True, exist_ok=True)
    for directory in created:
        directory.chmod(DIR_MODE)


def repo_file(name: str) -> Path:
    return REPO_ROOT / name


def load_json(path: Path, what: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DevkitError(f"{what} not found at {path}",
                          "check out the kit again, or pass an explicit path") from None
    except ValueError as exc:
        raise DevkitError(f"{what} at {path} is not valid JSON: {exc}") from None


def write_json(path: Path, payload: dict) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    path.chmod(FILE_MODE)


def render_home(text: str, home: str | os.PathLike[str] | None = None) -> str:
    """Expand ${HOME} for a machine-consumed file at install time."""
    return text.replace(HOME_TOKEN, str(home or Path.home()))


def unrender_home(text: str, home: str | os.PathLike[str] | None = None) -> str:
    """Replace a literal home path with ${HOME}, for export back into kit source."""
    return text.replace(str(home or Path.home()), HOME_TOKEN)


def resolve_source(explicit: str | None, allowlist: dict) -> Path:
    raw = explicit or allowlist.get("source") or "${HOME}/.agents"
    source = Path(render_home(raw)).expanduser()
    if not source.is_dir():
        raise DevkitError(f"export source {source} is not a directory",
                          "pass --source, or set 'source' in export-allowlist.json")
    return source


def timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def backup_path(target: Path) -> Path:
    return target.with_name(f"{target.name}.devkit-backup-{timestamp()}")


def back_up(target: Path) -> Path:
    """Copy target aside before it is overwritten. Returns the backup path."""
    dest = backup_path(target)
    if target.is_dir():
        shutil.copytree(target, dest, symlinks=True)
    else:
        shutil.copy2(target, dest, follow_symlinks=False)
    return dest


def relative_to_home(path: Path) -> str:
    """Display form for messages. Never written into a machine-consumed position."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


class Plan:
    """Collects intended writes so every command can offer a real dry run.

    Definition of Done 7: every installer step is idempotent and offers
    --dry-run. Commands build a Plan, print it, and only execute on --apply.
    """

    def __init__(self, apply: bool) -> None:
        self.apply = apply
        self.actions: list[str] = []
        self.changed = False

    def record(self, action: str) -> None:
        self.actions.append(action)
        self.changed = True

    def report(self, noun: str) -> int:
        if not self.actions:
            print(f"{noun}: already up to date, nothing to do.")
            return 0
        verb = "Wrote" if self.apply else "Would write"
        print(f"{verb} {len(self.actions)} change(s) for {noun}:")
        for action in self.actions:
            print(f"  {action}")
        if not self.apply:
            print("\nDry run. Re-run with --apply to write.")
        return 0
