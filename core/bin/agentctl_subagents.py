"""Recover Claude Code subagent work that stopped before its final report.

Every subagent transcript is saved under ~/.claude/projects/<project>/<session>/subagents/.
A usage limit, crash or stop leaves the work in that transcript and in the worker's
checkpoint file (orchestrate skill), but nothing reads them back. `list` finds the
stopped workers; `brief` turns one into a resume brief for a fresh worker.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from agentctl_common import agents_home, emit

EDIT_TOOL_RE = re.compile(r"(?i)(^|__)(write|edit|multiedit|notebookedit|replace_\w+|insert_\w+|rename_symbol|create_text_file)$")
CHECKPOINT_RE = re.compile(r"(?:~|/home/[^/\s]+)/\.agents/runs/[^\s`'\")\]]+\.md")
STOPPED = ("rate_limit", "api_error", "interrupted", "stopped_by_user")


def projects_root() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")).expanduser() / "projects"


def load_entries(path: Path) -> list[dict[str, Any]]:
    entries = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def load_meta(path: Path) -> dict[str, Any]:
    meta_path = path.with_name(path.name.removesuffix(".jsonl") + ".meta.json")
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def blocks(entry: dict[str, Any]) -> list[dict[str, Any]]:
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [b for b in content or [] if isinstance(b, dict)]


def turns(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in entries if e.get("type") in ("user", "assistant") and not e.get("isMeta")]


def text_of(entry: dict[str, Any]) -> str:
    return "\n".join(b.get("text", "") for b in blocks(entry) if b.get("type") == "text").strip()


def classify(entries: list[dict[str, Any]], meta: dict[str, Any]) -> tuple[str, str]:
    if meta.get("stoppedByUser"):
        return "stopped_by_user", ""
    convo = turns(entries)
    if not convo:
        return "interrupted", "empty transcript"
    last = convo[-1]
    if last.get("isApiErrorMessage"):
        return ("rate_limit" if last.get("error") == "rate_limit" else "api_error"), text_of(last)
    if last.get("type") == "assistant" and {b.get("type") for b in blocks(last)} == {"text"}:
        return "finished", ""
    return "interrupted", "transcript ends mid-step"


def tool_calls(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = {}
    for entry in entries:
        for b in blocks(entry):
            if b.get("type") == "tool_result":
                content = b.get("content")
                if isinstance(content, list):
                    content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                results[b.get("tool_use_id")] = str(content or "")
    calls = []
    for entry in entries:
        for b in blocks(entry):
            if b.get("type") == "tool_use":
                calls.append({"name": b.get("name", ""), "input": b.get("input") or {},
                              "result": results.get(b.get("id")), "timestamp": entry.get("timestamp")})
    return calls


def changed_files(calls: list[dict[str, Any]]) -> list[str]:
    files: list[str] = []
    for call in calls:
        if not EDIT_TOOL_RE.search(call["name"]):
            continue
        path = call["input"].get("file_path") or call["input"].get("relative_path") or call["input"].get("notebook_path")
        if path and path not in files:
            files.append(path)
    return files


def summarize(path: Path) -> dict[str, Any]:
    entries = load_entries(path)
    meta = load_meta(path)
    status, error = classify(entries, meta)
    stamps = [e["timestamp"] for e in entries if e.get("timestamp")]
    calls = tool_calls(entries)
    convo = turns(entries)
    return {
        "agent_id": path.stem.removeprefix("agent-"),
        "session_id": path.parent.parent.name,
        "project": path.parent.parent.parent.name,
        "cwd": next((e["cwd"] for e in entries if e.get("cwd")), None),
        "description": meta.get("description") or (clip(text_of(convo[0]).split("\n", 1)[0], 80) if convo else None),
        "agent_type": meta.get("agentType"),
        "model": meta.get("model"),
        "effort": meta.get("effort"),
        "status": status,
        "error": error,
        "started": stamps[0] if stamps else None,
        "last_activity": stamps[-1] if stamps else None,
        "tool_calls": len(calls),
        "files_changed": changed_files(calls),
        "transcript": str(path),
    }


def transcripts() -> list[Path]:
    return sorted(projects_root().glob("*/*/subagents/agent-*.jsonl"))


def find_transcript(agent_id: str) -> Path:
    key = agent_id.removeprefix("agent-")
    matches = [p for p in transcripts() if p.stem.removeprefix("agent-").startswith(key)]
    if not matches:
        raise ValueError(f"no subagent transcript matches {agent_id!r} under {projects_root()}")
    if len(matches) > 1:
        raise ValueError(f"{agent_id!r} matches {len(matches)} transcripts; pass more of the id")
    return matches[0]


def cmd_subagents_list(args: argparse.Namespace) -> int:
    since = args.since.isoformat() if args.since else ""
    rows = []
    for path in transcripts():
        if args.project and args.project not in path.parent.parent.parent.name:
            continue
        row = summarize(path)
        if not args.all and row["status"] not in STOPPED:
            continue
        if since and (row["last_activity"] or "") < since:
            continue
        rows.append(row)
    rows.sort(key=lambda r: r["last_activity"] or "", reverse=True)
    emit({"root": str(projects_root()), "count": len(rows), "subagents": rows[: args.limit]})
    return 0


def clip(value: str, limit: int) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[:limit] + f" …[{len(value) - limit} more chars]"


def render_brief(summary: dict[str, Any], entries: list[dict[str, Any]], steps: int) -> tuple[str, str | None]:
    convo = turns(entries)
    assignment = text_of(convo[0]) if convo else ""
    runs = (agents_home() / "runs").resolve()
    named = (Path(m).expanduser().resolve() for m in CHECKPOINT_RE.findall(assignment))
    checkpoint = next((p for p in named if p.is_relative_to(runs)), None)
    calls = tool_calls(entries)
    notes = [t for t in (text_of(e) for e in convo if e.get("type") == "assistant" and not e.get("isApiErrorMessage")) if t]

    lines = [
        f"# Resume brief: {summary['description'] or summary['agent_id']}",
        "",
        (f"A previous worker (`{summary['agent_id']}`, {summary['model'] or 'model unknown'}) stopped before its "
        f"final report: **{summary['status']}**{' (' + summary['error'] + ')' if summary['error'] else ''}. "
        f"It made {summary['tool_calls']} tool calls; last activity {summary['last_activity']}."),
        f"Full transcript: `{summary['transcript']}`",
        "",
        ("Continue its assignment from where it stopped. Do not redo completed steps: check that the files below "
        "are in the state the steps describe, then take the next step. Keep updating the checkpoint file if the "
        "assignment names one. End with the final report the assignment asks for."),
        "",
        "## Original assignment",
        "",
        assignment,
        "",
    ]
    if checkpoint:
        lines += ["## Checkpoint file", "", f"`{checkpoint}`", ""]
        lines += ["```markdown", checkpoint.read_text(encoding="utf-8").strip(), "```", ""] if checkpoint.is_file() else ["(not written yet)", ""]
    if summary["files_changed"]:
        lines += ["## Files the worker changed", "", *[f"- `{f}`" for f in summary["files_changed"]], ""]
    if calls:
        lines += [f"## Last {min(steps, len(calls))} of {len(calls)} steps", ""]
        for call in calls[-steps:]:
            lines.append(f"- `{call['name']}` {clip(json.dumps(call['input'], ensure_ascii=False), 300)}")
            if call["result"] is None:
                lines.append("  - result: none (stopped here)")
            else:
                lines.append(f"  - result: {clip(call['result'], 400).replace(chr(10), ' ')}")
        lines.append("")
    if notes:
        lines += ["## Last notes from the worker", "", *[clip(n, 1500) + "\n" for n in notes[-3:]]]
    return "\n".join(lines).rstrip() + "\n", str(checkpoint) if checkpoint else None


def cmd_subagents_brief(args: argparse.Namespace) -> int:
    try:
        path = find_transcript(args.agent_id)
    except ValueError as exc:
        emit({"status": "error", "error": str(exc)})
        return 2
    summary = summarize(path)
    body, checkpoint = render_brief(summary, load_entries(path), args.steps)
    out = (args.out or agents_home() / "runs" / "resume" / f"{summary['agent_id']}.md").expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    emit({"status": "ok", "brief": str(out), "checkpoint": checkpoint, "subagent": summary,
          "same_session_resume": f"claude --resume {summary['session_id']}, then SendMessage to {summary['agent_id']}"})
    return 0


def add_subagents_parsers(group) -> None:
    listing = group.add_parser(
        "list",
        help="List Claude Code subagents that stopped before their final report.",
        description=(
            "Scans ~/.claude/projects/*/*/subagents/ ($CLAUDE_CONFIG_DIR overrides ~/.claude). Status is "
            "rate_limit, api_error, interrupted (transcript ends mid-step), stopped_by_user, or finished. "
            "Newest first."
        ),
    )
    listing.add_argument("--project", help="Substring of the project folder name, e.g. Projects-client.")
    listing.add_argument("--since", type=datetime.fromisoformat, help="Only activity on or after this ISO date.")
    listing.add_argument("--all", action="store_true", help="Include finished subagents.")
    listing.add_argument("--limit", type=int, default=20)
    listing.set_defaults(func=cmd_subagents_list)

    brief = group.add_parser(
        "brief",
        help="Write a resume brief for one stopped subagent.",
        description=(
            "Builds a Markdown brief from the transcript: original assignment, checkpoint file (an "
            "~/.agents/runs/... .md path named in the assignment), files changed, last steps with results, "
            "and the worker's last notes. Default output: ~/.agents/runs/resume/<agent-id>.md."
        ),
    )
    brief.add_argument("agent_id", help="Subagent id or unique prefix (agent-<id> also accepted).")
    brief.add_argument("--out", type=Path, help="Write the brief here instead.")
    brief.add_argument("--steps", type=int, default=15, help="How many trailing tool calls to include.")
    brief.set_defaults(func=cmd_subagents_brief)
