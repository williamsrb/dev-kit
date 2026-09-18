#!/usr/bin/env python3
"""Run minted Jira attachment downloadCommands in one process.

Reads JSON from a file or stdin. Accepts either a list of objects or an object
with a ``commands`` array. Each item must include ``downloadCommand`` (the
exact string returned by ``downloadJiraIssueAttachment``). Optional ``id`` and
``outputPath`` are echoed in the report.

Does not invent curl flags. Does not mint URLs. Exit 2 if any command fails.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_commands(raw: str) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("commands") or payload.get("attachments") or []
    else:
        raise ValueError("JSON must be a list or an object with commands[]")
    if not isinstance(items, list):
        raise ValueError("commands must be a list")
    commands = []
    for item in items:
        if not isinstance(item, dict) or not item.get("downloadCommand"):
            raise ValueError("each item needs a downloadCommand string")
        commands.append(item)
    return commands


def run_commands(items: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for item in items:
        command = str(item["downloadCommand"])
        output = item.get("outputPath")
        if output:
            Path(str(output)).expanduser().parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            command, shell=True, text=True, capture_output=True, check=False
        )
        ok = completed.returncode == 0
        results.append({
            "id": item.get("id") or item.get("attachmentId"),
            "outputPath": output,
            "ok": ok,
            "returncode": completed.returncode,
            "stderr": (completed.stderr or "")[:500],
        })
    failed = [row for row in results if not row["ok"]]
    return {
        "ok": len(results) - len(failed),
        "failed": len(failed),
        "total": len(results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="JSON file of minted downloadCommands. Defaults to stdin.",
    )
    parser.add_argument("--json", action="store_true", help="always emit JSON (default)")
    args = parser.parse_args()
    raw = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    try:
        items = load_commands(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    if not items:
        print(json.dumps({"ok": 0, "failed": 0, "total": 0, "results": []}, indent=2))
        return 0
    payload = run_commands(items)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if payload["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
