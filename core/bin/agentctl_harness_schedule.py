"""`agentctl harness schedule` and `agentctl harness weekly` (factory-kb-harvest FR-24).

A systemd user timer runs `agentctl harness weekly`: scan, measure and inbox prune. Neither calls a model. The unit
files are written with AGENTS_HOME set to the installing home, so a devkit profile gets its own timer.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentctl_common import emit
from agentctl_jira import agents_home

SERVICE = "agentctl-harness-weekly.service"
TIMER = "agentctl-harness-weekly.timer"
CALENDAR = "Mon 07:00"
WEEKLY_SINCE = "60d"
PRUNE_OLDER_THAN_DAYS = 30
Runner = Callable[[list[str]], subprocess.CompletedProcess]


def unit_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "systemd" / "user"


def agentctl_path() -> str:
    """Absolute path: a systemd user unit does not inherit the shell's PATH."""
    found = shutil.which("agentctl")
    if not found:
        raise FileNotFoundError("agentctl is not on PATH; the timer needs an absolute ExecStart")
    return str(Path(found).resolve())


def service_text(home: Path) -> str:
    return (
        "[Unit]\n"
        "Description=agentctl harness weekly (scan, measure, inbox prune; no model call)\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"Environment=AGENTS_HOME={home}\n"
        f"ExecStart={agentctl_path()} harness weekly\n"
    )


def timer_text() -> str:
    return (
        "[Unit]\n"
        "Description=Weekly agentctl harness run\n\n"
        "[Timer]\n"
        f"OnCalendar={CALENDAR}\n"
        "Persistent=true\n"
        f"Unit={SERVICE}\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def _systemctl(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, check=False)


def install(home: Path, *, directory: Path | None = None, runner: Runner | None = None) -> dict[str, Any]:
    run = runner or _systemctl
    target = directory or unit_dir()
    target.mkdir(parents=True, exist_ok=True)
    (target / SERVICE).write_text(service_text(home), encoding="utf-8")
    (target / TIMER).write_text(timer_text(), encoding="utf-8")
    reload_ = run(["daemon-reload"])
    enable = run(["enable", "--now", TIMER])
    return {"status": "ok" if enable.returncode == 0 else "error", "units": str(target),
            "daemon_reload": reload_.returncode, "enable": enable.returncode,
            "message": (enable.stderr or "").strip()[:300]}


def remove(*, directory: Path | None = None, runner: Runner | None = None) -> dict[str, Any]:
    run = runner or _systemctl
    target = directory or unit_dir()
    disable = run(["disable", "--now", TIMER])
    removed = []
    for name in (SERVICE, TIMER):
        path = target / name
        if path.is_file():
            path.unlink()
            removed.append(name)
    run(["daemon-reload"])
    return {"status": "ok", "removed": removed, "disable": disable.returncode}


def status(*, runner: Runner | None = None) -> dict[str, Any]:
    run = runner or _systemctl
    proc = run(["list-timers", TIMER])
    return {"status": "ok", "output": (proc.stdout or proc.stderr or "").strip()}


def weekly(home: Path, *, now: datetime | None = None) -> dict[str, Any]:
    """scan --since 60d, measure, inbox prune. In-process, deterministic, no adapter."""
    import agentctl_harness as hv
    from agentctl_harness_measure import measure, write_measurements
    from agentctl_kb_digest import prune_inbox

    current = now or datetime.now(UTC)
    scan = hv.run_scan(since=WEEKLY_SINCE, until=None, top=hv.DEFAULT_TOP, sources=hv.DEFAULT_SOURCES,
                       mcp_size=hv.DEFAULT_MCP_SIZE, output_dir=None, home=Path.home(), agents=home, now=current)
    measured = measure(home, 30, current)
    measurement_file = write_measurements(home, measured, current)
    pruned = prune_inbox(home, PRUNE_OLDER_THAN_DAYS, now=current.timestamp())
    return {"status": "ok", "scan_stats": (scan or {}).get("stats") if isinstance(scan, dict) else None,
            "measurements": str(measurement_file), "measured_rows": len(measured["rows"]), "pruned": pruned}


def _cmd_install(args: argparse.Namespace) -> int:
    emit(install(agents_home()))
    return 0


def _cmd_remove(args: argparse.Namespace) -> int:
    emit(remove())
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    emit(status())
    return 0


def _cmd_weekly(args: argparse.Namespace) -> int:
    emit(weekly(agents_home()))
    return 0


def add_schedule_parsers(group: argparse._SubParsersAction) -> None:
    schedule = group.add_parser("schedule", help="Install, remove or show the weekly systemd user timer.")
    sub = schedule.add_subparsers(dest="schedule_cmd", required=True)
    sub.add_parser("install", help="Write the unit files, daemon-reload and enable --now the timer.").set_defaults(
        func=_cmd_install)
    sub.add_parser("remove", help="Disable the timer and delete the unit files.").set_defaults(func=_cmd_remove)
    sub.add_parser("status", help="Show the timer in systemctl list-timers.").set_defaults(func=_cmd_status)
    group.add_parser("weekly", help="Scan, measure and prune once (what the timer runs; no model call).").set_defaults(
        func=_cmd_weekly)
