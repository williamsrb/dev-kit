#!/usr/bin/env python3
"""Run the deterministic per-shot gate over a task's evidence folder.

Planned shots come from ``agentctl plan progress <TASK-ID> --kind evidence``. Each
shot is checked for presence, pixel size, the pixel-size stamp, the whitespace
overlay rule and (optionally) expected OCR text. The model still reads the images:
this only removes the per-file loop.

Usage:
    gate-evidence-folder.py PROJ-427
    gate-evidence-folder.py PROJ-427 --expect 01-part.png='Hubspot Form' --expect 01-part.png=hubspot-form

Exit 0: every planned shot passes. Exit 1: a gate failed. Exit 2: tooling or input error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

OVERLAY_BLANK_PERCENT = 85
OVERLAY_MIN_EDGE = 1200
OVERLAY_GRID_CELL = 0.95
OVERLAY_GRID_CELLS = 6


def die(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def agents_home() -> Path:
    raw = os.environ.get("AGENTS_HOME")
    return Path(raw).expanduser() if raw else Path.home() / ".agents"


def agentctl_bin() -> str:
    found = shutil.which("agentctl")
    if found:
        return found
    for candidate in (Path.home() / ".local/bin/agentctl", agents_home() / "bin/agentctl"):
        if candidate.is_file():
            return str(candidate)
    die("agentctl not found on PATH, ~/.local/bin or ~/.agents/bin")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def run_json(cmd: list[str]) -> dict:
    proc = run(cmd)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        die(f"{' '.join(cmd[:4])} gave no JSON ({proc.returncode}): {proc.stderr[:300]}")
    return data if isinstance(data, dict) else {}


def image_size(path: Path) -> tuple[int, int] | None:
    proc = run(["identify", "-format", "%w %h", f"{path}[0]"])
    parts = proc.stdout.split()
    if proc.returncode != 0 or len(parts) != 2:
        return None
    return int(parts[0]), int(parts[1])


def overlay_suspect(whitespace: dict, longest: int) -> bool:
    cells = [c for row in whitespace.get("grid", {}).get("blank_ratio_per_cell", []) for c in row]
    blank_cells = sum(1 for c in cells if c >= OVERLAY_GRID_CELL)
    full_page_blank = whitespace.get("blank_percent", 0) >= OVERLAY_BLANK_PERCENT and longest >= OVERLAY_MIN_EDGE
    return full_page_blank or blank_cells >= OVERLAY_GRID_CELLS


def check_shot(agentctl: str, path: Path, expects: list[str]) -> dict:
    shot: dict = {"exists": path.is_file()}
    if not shot["exists"]:
        return shot
    size = image_size(path)
    if size is None:
        shot["readable"] = False
        return shot
    shot["readable"] = True
    shot["width"], shot["height"] = size
    shot["stamped"] = run([agentctl, "image", "stamp", "--check", str(path)]).returncode == 0
    whitespace = run_json([agentctl, "image", "whitespace", str(path), "--background", "auto", "--tolerance", "18", "--grid", "3"])
    shot["blank_percent"] = whitespace.get("blank_percent")
    # An unstamped capture has no border, so the corner sample reads the whole page as blank.
    shot["overlay_suspect"] = overlay_suspect(whitespace, max(size)) if shot["stamped"] else None
    shot["expect"] = [
        {"text": text, "found": bool(run_json([agentctl, "evidence", "inspect", str(path), "--ocr", "--expected-text", text]).get("checks", {}).get("text", {}).get("matches"))}
        for text in expects
    ]
    return shot


def shot_failures(shot: dict) -> list[str]:
    if not shot["exists"]:
        return ["missing"]
    if not shot.get("readable"):
        return ["unreadable"]
    problems = []
    if not shot["stamped"]:
        problems.append("not-stamped")
    if shot["overlay_suspect"]:
        problems.append("overlay-suspect")
    problems += [f"text-not-found:{e['text']}" for e in shot["expect"] if not e["found"]]
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("task_id")
    parser.add_argument("--evidence-dir", type=Path, help="default: <AGENTS_HOME>/prds/<TASK-ID>/evidence")
    parser.add_argument("--expect", action="append", default=[], metavar="FILE=TEXT", help="OCR token that must appear in FILE; repeatable")
    args = parser.parse_args()

    expects: dict[str, list[str]] = {}
    for item in args.expect:
        name, sep, text = item.partition("=")
        if not sep or not text:
            parser.error(f"--expect needs FILE=TEXT, got {item!r}")
        expects.setdefault(name, []).append(text)

    agentctl = agentctl_bin()
    progress = run_json([agentctl, "plan", "progress", args.task_id, "--kind", "evidence", "--json"])
    if progress.get("status") != "ok":
        print(f"error: no evidence plan for {args.task_id} (status={progress.get('status')!r})", file=sys.stderr)
        return 2
    folder = args.evidence_dir or agents_home() / "prds" / args.task_id / "evidence"
    all_steps = progress.get("steps", [])
    steps = [s for s in all_steps if s["id"].lower().endswith(".png")]
    unmapped = [s["id"] for s in all_steps if s not in steps]
    planned = {s["id"] for s in steps}

    shots = []
    for step in steps:
        shot = {"file": step["id"], "title": step.get("title", ""), "progress": step.get("status")}
        shot.update(check_shot(agentctl, folder / step["id"], expects.get(step["id"], [])))
        # A skipped step is a recorded decision to capture nothing, so its absence is not a failure.
        skipped = step.get("status") == "skipped" and not shot["exists"]
        shot["failures"] = [] if skipped else shot_failures(shot)
        shots.append(shot)

    orphans = sorted(p.name for p in folder.glob("*.png") if p.name not in planned) if folder.is_dir() else []
    unknown = sorted(set(expects) - planned)
    failed = [s["file"] for s in shots if s["failures"]]
    report = {
        "task": args.task_id,
        "evidence_dir": str(folder),
        "planned": len(shots),
        "failed": failed,
        "orphans": orphans,
        "expect_files_not_in_plan": unknown,
        "steps_without_a_screenshot_file": unmapped,
        "shots": shots,
    }
    print(json.dumps(report, indent=2))
    return 1 if failed or unknown or unmapped else 0


if __name__ == "__main__":
    sys.exit(main())
