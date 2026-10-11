"""State-based migrations: repairs the incoming version can make for what an
older one left behind.

Each entry asks the real state whether it is needed (`needs`), so there is no
ledger of what ran. `devkit doctor` reports the entries that are needed; an
`update apply` runs them after the flip, and `profile sync` runs them after it
syncs. To add one, append a `Migration` to `REGISTRY`: `needs` must be cheap,
read state only and tolerate a missing `current`; `run` must be safe to repeat.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import instances, kithome, kitsource
from .common import Plan


@dataclass(frozen=True)
class Migration:
    name: str
    needs: Callable[[Path], list[str]]  # reasons; empty when nothing is needed
    run: Callable[[Path, Plan], None]
    fix: Callable[[Path], str]          # the command that repairs it by hand


def _incomplete_release(home: Path) -> list[str]:
    current = kithome.current_release(home)
    return kithome.verify_release(current) if current else []


def _payload_fix(home: Path) -> str:
    current = kithome.current_release(home)
    source = (kithome.read_stamp(current) if current else None) or {}
    source = source.get("source")
    if source and not kitsource.is_git_url(source) and \
            (Path(source) / "devkit.py").is_file() and \
            (Path(source) / "devkit_cli").is_dir():
        return f"devkit update apply --from {source} --apply"
    found = instances.discover_instances(home)
    name = found[0][0] if found else "<name>"
    return f"<path to a devkit checkout>/devkit profile sync {name} --apply"


def _report_payload_fix(home: Path, plan: Plan) -> None:
    """Report-only: repairing means installing the source's current HEAD, an
    upgrade the owner has to order."""
    print(f"release-payload-complete: the current release is incomplete; "
          f"fix: {_payload_fix(home)}")


REGISTRY: list[Migration] = [
    Migration("release-payload-complete", _incomplete_release,
              _report_payload_fix, _payload_fix),
]


def needs_list(home: Path) -> list[tuple[Migration, list[str]]]:
    needed = ((migration, migration.needs(home)) for migration in REGISTRY)
    return [(migration, reasons) for migration, reasons in needed if reasons]


def run_needed(home: Path, plan: Plan) -> list[str]:
    """Run every migration whose `needs` is true; return their names."""
    ran = []
    for migration, _reasons in needs_list(home):
        migration.run(home, plan)
        ran.append(migration.name)
    return ran
