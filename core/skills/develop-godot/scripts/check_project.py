#!/usr/bin/env python3
"""Verify a Godot 4 project headless: import, parse all scripts, tests, boot smoke.

Example:
  check_project.py --path ~/.local/share/godot/examples/2d-platformer \\
    --tests res://tests/run_tests.gd --json

Exit codes: 0 ok, 1 failed, 2 blocked (no godot binary, or it fails the version probe).

Parse check: one headless run of a throwaway SceneTree script that loads every
res://**/*.gd (skipping .godot/ and addons/) at runtime and fails on any null.
`--check-only --script` per file also exits 1 on parse errors but false-fails
any script that names an autoload, because autoloads are unknown at that
compile time.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ERROR_RE = re.compile(r"SCRIPT ERROR|^ERROR:|Parse Error|Parse error|PARSE FAIL")
TEST_FAIL_RE = re.compile(r"^\s*FAIL ")
VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?\.\w+", re.MULTILINE)
MAX_ERRORS = 8

PARSE_LOADER = """extends SceneTree


func _initialize() -> void:
	_run.call_deferred()


func _scan(dir: String, out: Array[String]) -> void:
	for d: String in DirAccess.get_directories_at(dir):
		if d != ".godot" and d != "addons":
			_scan(dir.path_join(d), out)
	for f: String in DirAccess.get_files_at(dir):
		if f.ends_with(".gd"):
			out.append(dir.path_join(f))


func _run() -> void:
	var files: Array[String] = []
	_scan("res://", files)
	var bad: int = 0
	for f: String in files:
		if ResourceLoader.load(f, "", ResourceLoader.CACHE_MODE_IGNORE) == null:
			bad += 1
			printerr("PARSE FAIL: ", f)
	print("scripts checked: %d, failed: %d" % [files.size(), bad])
	quit(1 if bad > 0 else 0)
"""


def find_godot(explicit: str | None) -> str | None:
    if explicit:  # an explicit choice never falls back silently
        candidates = [explicit]
    else:
        candidates = [
            os.environ.get("GODOT"),
            shutil.which("godot"),
            str(Path.home() / ".local/bin/godot"),
        ]
    for c in candidates:
        if (
            c
            and Path(c).expanduser().is_file()
            and os.access(Path(c).expanduser(), os.X_OK)
        ):
            return str(Path(c).expanduser())
    return None


def run(cmd: list[str], timeout: int) -> tuple[int, str, float]:
    """Return (exit code, combined output, seconds). Exit 124 on timeout."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        code, out = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or b"") + (exc.stderr or b"")
        code = 124
        out = (
            partial.decode(errors="replace") if isinstance(partial, bytes) else partial
        ) + f"\nERROR: timeout after {timeout}s"
    return code, out, round(time.monotonic() - start, 2)


def error_lines(output: str, *, test_fail: bool = False) -> list[str]:
    def hit(ln: str) -> bool:
        return bool(ERROR_RE.search(ln) or (test_fail and TEST_FAIL_RE.search(ln)))

    lines = [ln.strip() for ln in output.splitlines() if hit(ln)]
    return lines[:MAX_ERRORS]


def skipped(step_id: str, reason: str) -> dict:
    return {
        "id": step_id,
        "status": "skipped",
        "seconds": 0,
        "errors": [],
        "reason": reason,
    }


def step(step_id: str, code: int, output: str, seconds: float) -> dict:
    errors = error_lines(output, test_fail=step_id == "tests")
    failed = code != 0 or bool(errors)
    if failed and not errors:
        errors = [f"exit code {code}"] + [
            ln for ln in output.splitlines() if ln.strip()
        ][-3:]
    return {
        "id": step_id,
        "status": "failed" if failed else "ok",
        "seconds": seconds,
        "errors": errors if failed else [],
    }


def main_scene(project: Path) -> str | None:
    match = re.search(
        r'^run/main_scene="([^"]+)"',
        (project / "project.godot").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return match.group(1) if match else None


def check(args: argparse.Namespace, godot: str, project: Path) -> list[dict]:
    base = [godot, "--headless", "--path", str(project)]
    steps: list[dict] = []

    code, out, secs = run(base + ["--import"], args.timeout)
    steps.append(step("import", code, out, secs))

    with tempfile.TemporaryDirectory(prefix="godot-check-") as tmp:
        loader = Path(tmp) / "parse_all.gd"
        loader.write_text(PARSE_LOADER, encoding="utf-8")
        code, out, secs = run(base + ["--script", str(loader)], args.timeout)
    steps.append(step("parse", code, out, secs))

    if args.tests:
        code, out, secs = run(base + ["--script", args.tests], args.timeout)
        steps.append(step("tests", code, out, secs))

    if args.no_boot:
        steps.append(skipped("boot", "--no-boot given"))
    elif not main_scene(project):
        steps.append(skipped("boot", "project has no run/main_scene"))
    else:
        code, out, secs = run(base + ["--quit-after", "120"], args.timeout)
        steps.append(step("boot", code, out, secs))
    return steps


def report(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2))
        return
    print(f"{result['status'].upper()}: {result['summary']}")
    for s in result["steps"]:
        print(f"  [{s['status']:>6}] {s['id']} ({s['seconds']}s)")
        if s.get("reason"):
            print(f"           skipped: {s['reason']}")
        for line in s["errors"]:
            print(f"           {line}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--path", required=True, help="Godot project directory (contains project.godot)"
    )
    ap.add_argument(
        "--tests", help="res:// path of a SceneTree test script; exit code is pass/fail"
    )
    ap.add_argument(
        "--godot", help="godot binary (default: $GODOT, PATH, ~/.local/bin/godot)"
    )
    ap.add_argument(
        "--json", action="store_true", help="print JSON instead of a summary"
    )
    ap.add_argument(
        "--timeout", type=int, default=120, help="seconds per step (default 120)"
    )
    ap.add_argument(
        "--no-boot", action="store_true", help="skip the main-scene boot smoke step"
    )
    args = ap.parse_args()

    project = Path(args.path).expanduser().resolve()
    result: dict = {
        "status": "failed",
        "godot_version": None,
        "project": str(project),
        "steps": [],
        "summary": "",
    }

    godot = find_godot(args.godot)
    if godot is None:
        result.update(
            status="blocked",
            summary="no godot binary found (--godot, $GODOT, PATH, ~/.local/bin/godot)",
        )
        report(result, args.json)
        return 2
    vcode, vout, _ = run([godot, "--headless", "--version"], 30)
    lines = vout.strip().splitlines()
    version = lines[-1].strip() if lines else ""
    if vcode != 0 or not VERSION_RE.match(version):
        reason = f"{godot} is not a working godot (--headless --version: exit {vcode}, output {version[:80]!r})"
        result.update(status="blocked", summary=reason)
        report(result, args.json)
        return 2
    result["godot_version"] = version

    if not (project / "project.godot").is_file():
        result.update(
            summary=f"project.godot not found in {project}",
            steps=[
                {
                    "id": "project",
                    "status": "failed",
                    "seconds": 0,
                    "errors": ["project.godot missing"],
                }
            ],
        )
        report(result, args.json)
        return 1

    result["steps"] = check(args, godot, project)
    failed = [s["id"] for s in result["steps"] if s["status"] == "failed"]
    result["status"] = "failed" if failed else "ok"
    skips = [
        f"{s['id']} ({s['reason']})"
        for s in result["steps"]
        if s["status"] == "skipped"
    ]
    ran = len(result["steps"]) - len(skips)
    result["summary"] = (
        f"failed steps: {', '.join(failed)}" if failed else f"{ran} steps passed"
    )
    if skips:
        result["summary"] += f"; skipped: {', '.join(skips)}"
    report(result, args.json)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
