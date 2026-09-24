#!/usr/bin/env python3
"""Pre-scan a ticket PRD for Human-in-the-loop signals, and check a verdict file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SIGNALS = SKILL_DIR / "references" / "signals.json"
VERDICTS = {"Autonomous", "Human-in-the-loop"}
OWNERS = {"analyst", "client", "frontend", "other-team", "tech-lead", "vendor", "hosting", "operator"}
MAX_HITS_PER_CRITERION = 8


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "scan":
        print(json.dumps(scan(Path(args.prd).expanduser()), indent=2, ensure_ascii=False))
        return 0
    errors = check(Path(args.verdict).expanduser())
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("scan", help="List criterion signal hits in a PRD as bounded JSON.")
    s.add_argument("prd", help="Path to ~/.agents/prds/<TASK-ID>.md")
    c = sub.add_parser("check", help="Validate a verdict JSON file against the contract.")
    c.add_argument("verdict", help="Path to ~/.agents/prds/<TASK-ID>.autonomy.json")
    return parser


def scan(prd: Path) -> dict:
    text = prd.read_text(errors="ignore")
    lines = text.splitlines()
    assignee = header_field(text, "Assignee")
    signals = json.loads(SIGNALS.read_text())
    scopes = scoped_lines(lines, assignee)
    hits: dict[str, list[dict]] = {}
    for criterion in signals["criteria"]:
        pattern = re.compile("|".join(criterion["patterns"]), re.I)
        found = []
        for lineno, scope, line in scopes:
            if pattern.search(line):
                found.append({"line": lineno, "scope": scope, "text": line.strip()[:220]})
        if found:
            hits[criterion["id"]] = found[:MAX_HITS_PER_CRITERION] + (
                [{"more": len(found) - MAX_HITS_PER_CRITERION}] if len(found) > MAX_HITS_PER_CRITERION else []
            )
    return {
        "prd": str(prd),
        "task_id": prd.stem,
        "type": header_field(text, "Type"),
        "status": header_field(text, "Status"),
        "has_acceptance_criteria": bool(re.search(r"^## Acceptance Criteria", text, re.M)),
        "figma_links": len(re.findall(r"figma\.com/", text)),
        "attachments": int(m.group(1)) if (m := re.search(r"^## Attachments \((\d+)\)", text, re.M)) else 0,
        "comments": int(m.group(1)) if (m := re.search(r"^## Comments \((\d+)\)", text, re.M)) else 0,
        "hits": hits,
        "note": "Hits are leads, not verdicts. Read each cited line before judging a criterion.",
    }


def header_field(text: str, name: str) -> str | None:
    m = re.search(rf"^\*\*{name}:\*\* (.+)$", text, re.M)
    return m.group(1).strip() if m else None


def scoped_lines(lines: list[str], assignee: str | None) -> list[tuple[int, str, str]]:
    """Description/AC lines and comments not written by the assignee (their own reports are post-hoc)."""
    out = []
    scope = "header"
    author_is_assignee = False
    for i, line in enumerate(lines, 1):
        if i == 1:
            out.append((i, "title", line))
            continue
        if line.startswith("## Description"):
            scope = "description"
        elif line.startswith("## Acceptance Criteria"):
            scope = "acceptance-criteria"
        elif line.startswith("## Comments"):
            scope = "comments"
        elif line.startswith("## Attachments"):
            scope = "attachments"
        elif scope == "comments" and (m := re.match(r"^### Comment \d+ — (.+?) — ", line)):
            author_is_assignee = bool(assignee) and m.group(1).strip() == assignee
            continue
        if "mentioned this issue in" in line:
            continue
        if scope in {"description", "acceptance-criteria"} or (scope == "comments" and not author_is_assignee):
            out.append((i, scope, line))
    return out


def check(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"unreadable: {exc}"]
    ids = {c["id"] for c in json.loads(SIGNALS.read_text())["criteria"]}
    errors = []
    for key in ("task_id", "mode", "verdict", "criteria", "blockers", "auto_resolved", "classified_at"):
        if key not in data:
            errors.append(f"missing key: {key}")
    if data.get("verdict") not in VERDICTS:
        errors.append(f"verdict must be one of {sorted(VERDICTS)}")
    criteria = data.get("criteria", {})
    if set(criteria) != ids:
        errors.append(f"criteria keys must be exactly {sorted(ids)}")
    for cid, entry in criteria.items():
        if entry.get("result") not in {"pass", "blocker"}:
            errors.append(f"{cid}: result must be pass or blocker")
        if entry.get("result") == "blocker" and not entry.get("evidence"):
            errors.append(f"{cid}: a blocker needs evidence")
    blocked = {b.get("criterion") for b in data.get("blockers", [])}
    failing = {cid for cid, e in criteria.items() if e.get("result") == "blocker"}
    if blocked != failing:
        errors.append("blockers[] must list exactly the criteria whose result is blocker")
    for b in data.get("blockers", []):
        for key in ("criterion", "evidence", "human_action", "owner"):
            if not b.get(key):
                errors.append(f"blocker {b.get('criterion')}: missing {key}")
        if b.get("owner") and b["owner"] not in OWNERS:
            errors.append(f"blocker {b.get('criterion')}: owner must be one of {sorted(OWNERS)}")
        if not isinstance(b.get("pre_resolvable"), bool):
            errors.append(f"blocker {b.get('criterion')}: pre_resolvable must be true or false")
    expected = "Human-in-the-loop" if failing else "Autonomous"
    if data.get("verdict") in VERDICTS and data["verdict"] != expected:
        errors.append(f"verdict must be {expected} given the criteria results")
    for a in data.get("auto_resolved", []):
        for key in ("decision", "chosen", "source"):
            if not a.get(key):
                errors.append(f"auto_resolved entry missing {key}")
    return errors


if __name__ == "__main__":
    sys.exit(main())
