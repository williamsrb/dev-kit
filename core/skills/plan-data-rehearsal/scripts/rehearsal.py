#!/usr/bin/env python3
"""Scaffold and check the data rehearsal of one task: plans/<ID>/rehearsal.md and rehearsal.json.

Usage:
    rehearsal.py init <ID>     write the skeleton files (no overwrite) and create the backup folder
    rehearsal.py check <ID>    validate both files; prints JSON and exits 1 on any error

Paths follow agents_home() (AGENTS_HOME, else ~/.agents), so a profile's own tree is used.
Standard library only. Every path inside rehearsal.json is relative to the backup folder
<agents home>/prds/<ID>/review-backup/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SECTIONS = ("Inventory", "Backups", "Prediction", "Canary", "Restore", "Gate", "Server writes (operator)")
COVERS = ("created", "updated", "deleted")
PLACEHOLDER = "<fill in>"
HEADING_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
NA_RE = re.compile(r"^n/a\s+[—-]\s+\S")
STUB: dict[str, Any] = {
    "task_id": "",
    "gate": {"argv": None, "reason_if_null": "", "output": "", "expected": {}, "keys": [],
             "source_hashes": {}, "timeout_s": 600},
    "prediction": {"created": 0, "updated": 0, "deleted": 0},
    "backups": [],
    "canary": None,
    "restore": [],
    "server_writes": [],
}


def agents_home() -> Path:
    raw = os.environ.get("AGENTS_HOME")
    return Path(raw).expanduser() if raw else Path.home() / ".agents"


def plan_dir(task: str) -> Path:
    return agents_home() / "plans" / task


def backup_dir(task: str) -> Path:
    return agents_home() / "prds" / task / "review-backup"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def init(task: str) -> dict[str, Any]:
    plan = plan_dir(task)
    md = plan / "rehearsal.md"
    js = plan / "rehearsal.json"
    backup = backup_dir(task)
    plan.mkdir(parents=True, exist_ok=True)
    backup.mkdir(parents=True, exist_ok=True)
    if not md.exists():
        body = f"# {task}: data rehearsal\n\n" + "".join(f"## {name}\n\n{PLACEHOLDER}\n\n" for name in SECTIONS)
        md.write_text(body, encoding="utf-8")
    if not js.exists():
        stub = dict(STUB, task_id=task)
        js.write_text(json.dumps(stub, indent=2) + "\n", encoding="utf-8")
    return {"status": "ok", "rehearsal_md": str(md), "rehearsal_json": str(js), "backup_dir": str(backup)}


def sections(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    matches = list(HEADING_RE.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        found[match.group(1).strip()] = text[match.end():end].strip()
    return found


def check_markdown(text: str, data: dict[str, Any]) -> list[str]:
    errors = []
    found = sections(text)
    for name in SECTIONS:
        body = found.get(name)
        if body is None:
            errors.append(f"rehearsal.md: missing section '{name}'")
        elif not body or PLACEHOLDER in body:
            errors.append(f"rehearsal.md: section '{name}' is empty or still a placeholder")
        elif body.startswith("n/a") and not NA_RE.match(body):
            errors.append(f"rehearsal.md: section '{name}' needs a reason: 'n/a — <reason>'")
    server_body = found.get("Server writes (operator)", "")
    for write in data.get("server_writes") or []:
        command = write.get("command", "") if isinstance(write, dict) else ""
        if command and command not in server_body:
            errors.append(f"rehearsal.md: server write not listed under 'Server writes (operator)': {command}")
    return errors


def check_relative(backup: Path, rel: Any, label: str) -> str | None:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        return f"{label}: path must be relative to the backup folder: {rel!r}"
    if not (backup / rel).is_file():
        return f"{label}: file not found in the backup folder: {rel}"
    return None


def check_hash(backup: Path, rel: Any, digest: Any, label: str) -> list[str]:
    problem = check_relative(backup, rel, label)
    if problem:
        return [problem]
    if not isinstance(digest, str) or sha256(backup / rel) != digest:
        return [f"{label}: sha256 differs from the recorded value: {rel}"]
    return []


def check_json(data: Any, backup: Path) -> list[str]:
    if not isinstance(data, dict):
        return ["rehearsal.json must be an object"]
    errors: list[str] = []
    gate = data.get("gate")
    if not isinstance(gate, dict):
        return errors + ["gate must be an object"]
    prediction = data.get("prediction")
    if not isinstance(prediction, dict):
        errors.append("prediction must be an object")
        prediction = {}
    for key in COVERS:
        value = prediction.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"prediction.{key} must be a non-negative integer")
    restore = data.get("restore") or []
    covers = set()
    for entry in restore:
        if not isinstance(entry, dict) or entry.get("covers") not in COVERS or not str(entry.get("command", "")).strip():
            errors.append("restore entries need covers (created|updated|deleted) and a command")
        else:
            covers.add(entry["covers"])
    deleted = prediction.get("deleted")
    if isinstance(deleted, int) and deleted > 0 and "deleted" not in covers:
        errors.append("prediction expects deletions but restore lists no entry covering deleted")
    for entry in data.get("backups") or []:
        if not isinstance(entry, dict):
            errors.append("backups entries need path and sha256")
            continue
        errors.extend(check_hash(backup, entry.get("path"), entry.get("sha256"), "backups"))
    argv = gate.get("argv")
    if argv is None:
        if not str(gate.get("reason_if_null", "")).strip():
            errors.append("gate.argv is null: reason_if_null is required")
        return errors
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        errors.append("gate.argv must be a non-empty list of strings")
    source = gate.get("source_hashes")
    if not isinstance(source, dict):
        errors.append("gate.source_hashes must be an object")
        source = {}
    if isinstance(argv, list) and argv and argv[0] not in source:
        errors.append(f"gate.argv[0] {argv[0]} must be listed in gate.source_hashes")
    for rel, digest in source.items():
        errors.extend(check_hash(backup, rel, digest, "gate.source_hashes"))
    output = gate.get("output")
    if not isinstance(output, str) or not output.strip():
        errors.append("gate.output is required when gate.argv is set")
    elif Path(output).is_absolute() or ".." in Path(output).parts:
        errors.append(f"gate.output must be relative to the backup folder: {output!r}")
    expected = gate.get("expected")
    keys = gate.get("keys")
    if not isinstance(expected, dict):
        errors.append("gate.expected must be an object")
        expected = {}
    if not isinstance(keys, list) or not keys:
        errors.append("gate.keys must be a non-empty list")
    else:
        for key in keys:
            if key not in expected:
                errors.append(f"gate.keys entry {key} is missing from gate.expected")
    timeout = gate.get("timeout_s", 600)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        errors.append("gate.timeout_s must be a positive integer")
    return errors


def check(task: str) -> dict[str, Any]:
    md = plan_dir(task) / "rehearsal.md"
    js = plan_dir(task) / "rehearsal.json"
    backup = backup_dir(task)
    result: dict[str, Any] = {"task_id": task, "rehearsal_md": str(md), "rehearsal_json": str(js),
                              "backup_dir": str(backup)}
    try:
        data = json.loads(js.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return result | {"status": "failed", "errors": [f"rehearsal.json unreadable: {exc}"]}
    try:
        text = md.read_text(encoding="utf-8")
    except OSError as exc:
        return result | {"status": "failed", "errors": [f"rehearsal.md unreadable: {exc}"]}
    errors = check_markdown(text, data if isinstance(data, dict) else {}) + check_json(data, backup)
    return result | {"status": "ok" if not errors else "failed", "errors": errors}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Write the rehearsal.md and rehearsal.json skeleton.").add_argument("task")
    sub.add_parser("check", help="Validate rehearsal.md and rehearsal.json.").add_argument("task")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        print(json.dumps(init(args.task), indent=2))
        return 0
    result = check(args.task)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
