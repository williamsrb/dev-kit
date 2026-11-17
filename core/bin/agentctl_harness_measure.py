"""`agentctl harness measure`: before and after counts of the keys of applied proposals (factory-kb-harvest FR-23).

For every applied proposal in both decision ledgers that names `keys:`, count each key in factory digests and chat
digests in [applied_at - window, applied_at) and [applied_at, min(applied_at + window, now)). The after count is scaled
to the window length when the after span is shorter. A proposal under 7 days old is `too recent`; one without keys is
`not measurable`. Deterministic: no model call.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from agentctl_common import emit
from agentctl_jira import agents_home
from agentctl_kb_proposals import collect

TOO_RECENT_DAYS = 7
DEFAULT_WINDOW = "30d"
WINDOW_RE = re.compile(r"^(\d+)d$")


def parse_ts(text: str) -> datetime:
    return datetime.fromisoformat(str(text)).astimezone(UTC)


def applied_rows(home: Path) -> list[dict[str, Any]]:
    rows = []
    for scope in ("kb", "harness"):
        for row in collect(home, scope):
            if row["state"] == "applied":
                rows.append({**row, "scope": scope})
    return rows


def signal_times(home: Path, user_home: Path | None = None) -> list[tuple[datetime, str]]:
    """(time, key) of every factory and chat digest signal that has a key and a timestamp."""
    import agentctl_factory as factory
    from agentctl_harness import root_files, transcript_roots
    from agentctl_kb import KbError
    from agentctl_kb_digest import digest_transcript

    found: list[tuple[datetime, str]] = []
    factory_root = factory.factory_root()
    for events in sorted(factory_root.glob("*/events.jsonl")) if factory_root.is_dir() else []:
        for signal in factory.run_digest(events.parent)["signals"]:
            if signal.get("ts"):
                found.append((parse_ts(signal["ts"]), signal["key"]))
    paths = [path for root in transcript_roots(user_home or Path.home(), ("claude", "profiles"))
             for path in root_files(root)]
    for path in paths:
        try:
            digest = digest_transcript(path, home)
        except KbError:
            continue
        for signal in digest["signals"]:
            if signal.get("ts") and signal.get("key"):
                found.append((parse_ts(signal["ts"]), signal["key"]))
    return found


def measure(home: Path, window_days: int, now: datetime, user_home: Path | None = None) -> dict[str, Any]:
    rows = applied_rows(home)
    times = signal_times(home, user_home) if rows else []
    report: list[dict[str, Any]] = []
    for row in rows:
        applied_at = parse_ts(row["applied_at"])
        age = now - applied_at
        if not row.get("keys"):
            report.append({"ref": row["ref"], "scope": row["scope"], "target": row["target"],
                           "status": "not measurable", "reason": "no keys:"})
            continue
        if age < timedelta(days=TOO_RECENT_DAYS):
            report.append({"ref": row["ref"], "scope": row["scope"], "target": row["target"],
                           "applied_at": row["applied_at"], "status": "too recent"})
            continue
        before_start = applied_at - timedelta(days=window_days)
        after_end = min(applied_at + timedelta(days=window_days), now)
        after_span = max((after_end - applied_at).total_seconds() / 86400, 1e-9)
        scale = window_days / after_span
        keys = {}
        for key in row["keys"]:
            before = sum(1 for t, k in times if k == key and before_start <= t < applied_at)
            after = sum(1 for t, k in times if k == key and applied_at <= t < after_end)
            keys[key] = {"before": before, "after": after, "after_scaled": round(after * scale, 2)}
        report.append({"ref": row["ref"], "scope": row["scope"], "target": row["target"],
                       "applied_at": row["applied_at"], "status": "measured", "window_days": window_days,
                       "keys": keys})
    return {"status": "ok", "until": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "rows": report}


def write_measurements(home: Path, result: dict[str, Any], now: datetime) -> Path:
    folder = home / "harness" / "signals"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{now:%Y-%m-%d}_measure.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def cmd_measure(args: argparse.Namespace) -> int:
    match = WINDOW_RE.match(args.window)
    if not match:
        emit({"status": "error", "message": f"--window takes whole days, like 30d: {args.window}"})
        return 2
    home = agents_home()
    now = datetime.now(UTC)
    result = measure(home, int(match.group(1)), now)
    target = write_measurements(home, result, now)
    result["written"] = str(target)
    if args.json:
        emit(result)
    else:
        for row in result["rows"]:
            print(f"{row['status']:<14} {row['ref']}  {row['target']}")
        print(f"written: {target}")
    return 0


def add_measure_parser(group: argparse._SubParsersAction) -> None:
    parser = group.add_parser(
        "measure",
        help="Before and after counts of the keys of applied proposals (no model call).",
        description="Counts each proposal's keys in factory and chat digests around its apply date.",
    )
    parser.add_argument("--window", default=DEFAULT_WINDOW, help="Window in whole days (default 30d).")
    parser.add_argument("--json", action="store_true")
    parser.set_defaults(func=cmd_measure)
