"""`agentctl harness proposals`: review and apply skill, rule, hook and MCP changes (factory-kb-harvest RC4).

Only this command may change skills/, rules/, hooks/ or mcp/ from a proposal. The rules live in
agentctl_kb_proposals (scope "harness"); this module is the CLI over them.
"""

from __future__ import annotations

import argparse
from typing import Any

from agentctl_common import emit
from agentctl_jira import agents_home
from agentctl_kb_proposals import (
    ProposalError,
    apply,
    check,
    collect,
    find,
    load_proposal,
    reject,
    scope_of_file,
)


def _error(message: str) -> int:
    emit({"status": "error", "message": message})
    return 2


def cmd_list(args: argparse.Namespace) -> int:
    rows = collect(agents_home(), "harness")
    if args.source != "all":
        rows = [r for r in rows if r["source"] == args.source]
    if args.state != "all":
        rows = [r for r in rows if r["state"] == args.state]
    if args.json:
        emit({"status": "ok", "count": len(rows), "rows": rows})
    else:
        for r in rows:
            print(f"{r['state']:<9} {r['ref']}  {r['kind']:<6} {r['target']}")
        if not rows:
            print("no harness proposals")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    try:
        row = find(agents_home(), args.ref, "harness")
        proposal = load_proposal(row)
    except ProposalError as exc:
        return _error(str(exc))
    body = proposal.body if len(proposal.body) <= 8000 else proposal.body[:8000] + "\n[truncated]"
    if args.json:
        emit({"status": "ok", "row": row, "body": body})
    else:
        print(f"{row['ref']}  {row['state']}  {row['kind']}  {row['target']}")
        print(f"evidence: {row['evidence']}")
        for reason in row["reasons"]:
            print(f"invalid: {reason}")
        print(body)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    from pathlib import Path

    path = Path(args.path).expanduser()
    if scope_of_file(path) != "harness":
        return _error(f"not a harness-proposals.md file: {path}")
    results: list[dict[str, Any]] = check(path, agents_home())
    ok = all(r["valid"] for r in results)
    if args.json:
        emit({"status": "ok" if ok else "invalid", "file": str(path), "proposals": results})
    else:
        for r in results:
            mark = "valid" if r["valid"] else "invalid: " + "; ".join(r["reasons"])
            print(f"{r['n']}  {r['target']}  {mark}")
        if not results:
            print("no proposals")
    return 0 if ok else 1


def cmd_apply(args: argparse.Namespace) -> int:
    try:
        result = apply(args.ref, agents_home(), scope="harness")
    except ProposalError as exc:
        return _error(str(exc))
    if args.json:
        emit({"status": "ok", **result})
    else:
        print(f"applied {result['ref']} {result['kind']} {result['target']} (unstaged)")
        for item in result.get("checks", []):
            print(f"check {item['check']}: exit {item['exit']}")
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    try:
        result = reject(args.ref, agents_home(), reason=args.reason, scope="harness")
    except ProposalError as exc:
        return _error(str(exc))
    if args.json:
        emit({"status": "ok", **result})
    else:
        print(f"rejected {result['ref']}: {result['reason']}")
    return 0


def add_proposal_parsers(group: argparse._SubParsersAction) -> None:
    proposals = group.add_parser(
        "proposals",
        help="Review and apply harness change proposals (skills, rules, hooks, MCP catalog).",
        description=(
            "Lists harness-proposals.md proposals from factory runs, kb-inbox folders and harness/proposals. "
            "apply writes unstaged, refuses while a factory run is running, and reports the checks for the touched "
            "folder without reverting."
        ),
    )
    sub = proposals.add_subparsers(dest="harness_proposals_cmd", required=True)

    p_list = sub.add_parser("list", help="List harness proposals and their state.")
    p_list.add_argument("--source", choices=("factory", "chat", "review", "all"), default="all")
    p_list.add_argument("--state", choices=("pending", "applied", "rejected", "invalid", "all"), default="pending")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show one harness proposal by ref.")
    p_show.add_argument("ref")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=cmd_show)

    p_check = sub.add_parser("check", help="Validate every proposal in one harness-proposals.md; exit 1 if any is invalid.")
    p_check.add_argument("path")
    p_check.add_argument("--json", action="store_true")
    p_check.set_defaults(func=cmd_check)

    p_apply = sub.add_parser("apply", help="Apply one pending harness proposal (unstaged).")
    p_apply.add_argument("ref")
    p_apply.add_argument("--json", action="store_true")
    p_apply.set_defaults(func=cmd_apply)

    p_reject = sub.add_parser("reject", help="Reject one pending or invalid harness proposal.")
    p_reject.add_argument("ref")
    p_reject.add_argument("--reason", required=True)
    p_reject.add_argument("--json", action="store_true")
    p_reject.set_defaults(func=cmd_reject)
