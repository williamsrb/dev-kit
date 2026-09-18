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
# rendered per context at install time (D6, section 4.5). `~` is never used:
# it expands only in a shell, unquoted, at word start.
HOME_TOKEN = "${HOME}"


def repo_file(name: str) -> Path:
    return REPO_ROOT / name


def load_json(path: Path, what: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise DevkitError(f"{what} not found at {path}",
                          f"check out the kit again, or pass an explicit path") from None
    except ValueError as exc:
        raise DevkitError(f"{what} at {path} is not valid JSON: {exc}") from None


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


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
    """Copy target aside before it is overwritten (D5). Returns the backup path."""
    dest = backup_path(target)
    if target.is_dir():
        shutil.copytree(target, dest, symlinks=True)
    else:
        shutil.copy2(target, dest, follow_symlinks=False)
    return dest


def guard_collision(target: Path, force: bool) -> Path | None:
    """D5: any write to an existing path aborts and names it; --force backs up first."""
    if not target.exists() and not target.is_symlink():
        return None
    if not force:
        raise DevkitError(f"{target} already exists",
                          "re-run with --force to back it up and proceed")
    return back_up(target)


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
