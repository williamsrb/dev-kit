"""Plan create/resolve/validate/progress for agentctl.

Plan pack logic lives here. bin/agentctl only registers the group.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from agentctl_common import (
    HEADING_RE,
    agents_home,
    emit,
    git,
    markdown_sections,
)

PLACEHOLDER_TOKENS = (
    "ISSUE-KEY", "ISSUE_KEY", "ISSUE-ID", "TASK-ID", "TASK_ID", "TASK-KEY", "EPIC-KEY",
    "JIRA-KEY", "ENV", "ENVIRONMENT", "DATE", "DATETIME", "ISO-DATE", "ISO-DATETIME",
    "PLACEHOLDER", "FILL-ME", "FIXME", "XXX",
)
# Only template tokens count. Generic angle brackets are ordinary plan content:
# TypeScript generics, JSX tags, regex character classes, and documented path
# conventions such as `services/<name>/<name>.ts` are not unresolved placeholders.
PLACEHOLDER_RE = re.compile(
    r"<(?:" + "|".join(re.escape(token) for token in PLACEHOLDER_TOKENS) + r")>|\bTODO\b",
    re.IGNORECASE,
)

PLAN_HEADINGS = {
    "implementation": ("overview", "functional-requirements", "non-goals", "constraints",
                       "tbd", "implicit-requirements", "already-delivered",
                       "implementation-plan", "validation"),
    "evidence": ("auth-required", "acceptance-criteria", "evidence-steps", "artifacts",
                 "posting-gate"),
}

def plans_root() -> Path:
    return agents_home() / "plans"

INDEX_FILE_RE = re.compile(r"([a-z0-9][a-z0-9._-]+\.md)", re.IGNORECASE)
FOLDER_COMPANIONS = (
    "plan.md", "requirements.md", "implementation.md", "validation.md",
    "evidence.md", "tbd.md", "implicit.md", "decisions.md",
)
# Run state, not spec. Excluded from validation so a half-finished run can never
# make a plan invalid, and so re-planning never clobbers recorded progress.
PROGRESS_FILE = "progress.md"


def plan_template(kind: str, issue: str) -> str:
    if kind == "implementation":
        return f"""# {issue}: Implementation plan

## Overview

## Functional Requirements

## Non-Goals

## Constraints

## TBD

## Implicit requirements

## Already delivered

- Nothing delivered yet. This is the first increment.

## Implementation Plan

## Validation
"""
    return f"""# {issue}: Evidence plan

## Auth Required?

- Required: unknown
- Surfaces:
- Storage state: `~/.agents/.auth/<env>.json`

## Acceptance Criteria

## Evidence Steps

## Artifacts

## Posting Gate

Post a Jira evidence comment only when every criterion and step passes.
"""


def folder_plan_md(issue: str, kind: str) -> str:
    if kind == "evidence":
        rows = [
            ("Overview, Non-Goals, Constraints", "plan.md"),
            ("Evidence", "evidence.md"),
        ]
        title = "Evidence plan"
    else:
        rows = [
            ("Overview, Non-Goals, Constraints", "plan.md"),
            ("User Stories, Functional Requirements", "requirements.md"),
            ("TBD", "tbd.md"),
            ("Implicit requirements", "implicit.md"),
            ("Already delivered, Implementation Plan", "implementation.md"),
            ("Validation", "validation.md"),
        ]
        title = "Implementation plan"
    table = "\n".join(f"| {section} | {file} |" for section, file in rows)
    return f"""# {issue}: {title}

## Overview

## Non-Goals

## Constraints

## Section index

| Section | File |
|---------|------|
{table}
"""


def folder_companion_bodies(issue: str) -> dict[str, str]:
    return {
        "requirements.md": f"# {issue}: Requirements\n\n## User Stories\n\n## Functional Requirements\n",
        "implementation.md": (
            f"# {issue}: Implementation\n\n"
            "## Already delivered\n\n"
            "- Nothing delivered yet. This is the first increment.\n\n"
            "## Implementation Plan\n"
        ),
        "validation.md": f"# {issue}: Validation\n\n## Validation\n",
        "tbd.md": f"# {issue}: TBD\n\n## TBD\n",
        "implicit.md": (
            f"# {issue}: Implicit requirements\n\n"
            "## Implicit requirements\n\n"
            "- Implicit: none\n"
        ),
        "evidence.md": plan_template("evidence", issue),
        "decisions.md": f"# {issue}: Decisions\n\n## Decisions\n",
    }


def plan_dir_files(directory: Path) -> list[Path]:
    files = []
    for name in FOLDER_COMPANIONS:
        path = directory / name
        if path.is_file():
            files.append(path)
    for path in sorted(directory.glob("*.md")):
        if not is_progress_name(path.name) and path not in files:
            files.append(path)
    return files


def is_progress_name(name: str) -> bool:
    return name == PROGRESS_FILE or name.endswith(".progress.md")


def progress_path(plan: Path, kind: str | None = None) -> Path:
    """One progress file per plan and kind. A folder holds several plan kinds, and a
    shared plans/ directory holds several plans, so neither can share one file."""
    if plan.is_dir():
        if kind in (None, "implementation"):
            return plan / PROGRESS_FILE
        return plan / f"{kind}.progress.md"
    return plan.with_name(f"{plan.stem}.progress.md")


def read_kind_progress(plan: Path, kind: str) -> tuple[dict[str, Any] | None, Path | None]:
    """Recorded state for this kind, and the file it came from.

    Before per-kind files, every kind of a folder plan wrote progress.md. That file
    is still read for the kind it records, and ignored for any other kind."""
    own = progress_path(plan, kind)
    candidates = [own]
    legacy = progress_path(plan)
    if plan.is_dir() and legacy != own:
        candidates.append(legacy)
    for path in candidates:
        state = read_progress_state(path)
        if state is None:
            continue
        recorded_kind = state.get("kind")
        if recorded_kind and recorded_kind != kind:
            continue
        return state, path
    return None, None


def displace_foreign_progress(path: Path, kind: str) -> None:
    """Move a legacy progress.md that records another kind to that kind's file before
    this kind overwrites it."""
    state = read_progress_state(path)
    other = (state or {}).get("kind")
    if not other or other == kind or path.name != PROGRESS_FILE:
        return
    target = progress_path(path.parent, other)
    if target != path and not target.exists():
        path.replace(target)


def collect_headings(paths: list[Path]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for path in paths:
        for section in markdown_sections(path):
            item = dict(section)
            item["file"] = str(path.resolve())
            sections.append(item)
    return sections


def index_files(plan_md: Path) -> list[str]:
    if not plan_md.is_file():
        return []
    names: list[str] = []
    in_index = False
    for line in plan_md.read_text(encoding="utf-8").splitlines():
        if HEADING_RE.match(line):
            in_index = "section index" in line.lower()
            continue
        if not in_index:
            continue
        for match in INDEX_FILE_RE.findall(line):
            if match not in names:
                names.append(match)
    return names


def infer_plan_kind(target: Path) -> str:
    if target.is_dir():
        if (target / "implementation.md").is_file() or (target / "requirements.md").is_file():
            return "implementation"
        if (target / "evidence.md").is_file() and not (target / "implementation.md").is_file():
            return "evidence"
        return "implementation"
    name = target.name.lower()
    if name.endswith("-evidence-plan.md") or name == "evidence.md":
        return "evidence"
    return "implementation"


def resolve_plan_target(task_id: str, *, plans_dir: Path, kind: str | None = None) -> dict[str, Any]:
    raw = task_id.strip()
    candidate = Path(raw).expanduser()
    folder: Path | None = None
    file_path: Path | None = None

    if candidate.exists():
        if candidate.is_dir():
            folder = candidate
        else:
            file_path = candidate
    else:
        folder_hit = plans_dir / raw
        if folder_hit.is_dir() and (folder_hit / "plan.md").is_file():
            folder = folder_hit
        else:
            evidence = plans_dir / f"{raw}-evidence-plan.md"
            impl = plans_dir / f"{raw}.md"
            if kind == "evidence" and evidence.is_file():
                file_path = evidence
            elif impl.is_file():
                file_path = impl
            elif evidence.is_file():
                file_path = evidence

    if folder is not None:
        detected = kind or infer_plan_kind(folder)
        if detected == "evidence" and (folder / "evidence.md").is_file():
            entry = folder / "evidence.md"
        else:
            entry = folder / "plan.md"
        sections = []
        for path in plan_dir_files(folder):
            sections.append({
                "name": path.stem,
                "file": str(path.resolve()),
                "bytes": path.stat().st_size,
            })
        return {
            "status": "ok",
            "entry": str(entry.resolve()) if entry.is_file() else str((folder / "plan.md").resolve()),
            "kind": detected,
            "layout": "folder",
            "root": str(folder.resolve()),
            "sections": sections,
        }

    if file_path is not None and file_path.is_file():
        detected = kind or infer_plan_kind(file_path)
        sections = []
        for section in markdown_sections(file_path):
            sections.append({
                "name": section["slug"],
                "file": str(file_path.resolve()),
                "bytes": len(section["text"].encode("utf-8")),
            })
        return {
            "status": "ok",
            "entry": str(file_path.resolve()),
            "kind": detected,
            "layout": "file",
            "root": str(file_path.resolve()),
            "sections": sections,
        }

    return {
        "status": "unresolved",
        "entry": None,
        "kind": kind,
        "layout": None,
        "root": None,
        "sections": [],
        "task_id": raw,
        "plans_dir": str(plans_dir.resolve()),
    }


def validate_plan_paths(paths: list[Path], kind: str, label: str) -> dict[str, Any]:
    sections = collect_headings(paths)
    present = {slug for section in sections for slug in section["slugs"]}
    required = set(PLAN_HEADINGS[kind])
    missing = sorted(required - present)
    unresolved = []
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PLACEHOLDER_RE.search(line):
                unresolved.append({"file": str(path), "line": number, "text": line[:240]})
    payload = {
        "valid": not missing and not unresolved,
        "file": label,
        "kind": kind,
        "missing_sections": missing,
        "unresolved_placeholders": unresolved,
    }
    return payload


# --- plan progress -------------------------------------------------------
# Resume support. A plan is a spec; progress is state. State lives in
# progress.md next to the plan, is excluded from validation, and is keyed by a
# hash of the steps text so an edited plan cannot inherit stale ticks.
#
# Backward compatibility: when no progress.md exists, state is INFERRED from
# the plan itself (an "Already delivered" ledger, inline [x]/DONE step marks)
# and, for evidence plans, from artifacts already on disk. Plans written before
# this feature therefore resume correctly without being migrated first.

PROGRESS_MARKER_RE = re.compile(r"<!--\s*agentctl:progress\s*(\{.*?\})\s*-->", re.DOTALL)
STEP_EXPLICIT_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\[[ xX~]\]\s+)?\*{0,2}(S\d+)\b[.):\u2014\u2013-]*\*{0,2}\s*(.*)$"
)
STEP_BOLD_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\[[ xX~]\]\s+)?\*\*Step\s+([0-9]+[A-Za-z]?)\b\s*[.:\u2014\u2013-]*\s*(.*?)\*\*"
)
STEP_ORDINAL_RE = re.compile(r"^\s{0,3}(?:[-*]\s+)?(\d+)\.\s+(.*)$")
STEP_DONE_RE = re.compile(r"\[[xX]\]")
DONE_TOKEN_RE = re.compile(r"\bDONE\b")
REQ_ID_RE = re.compile(r"\b(FR|AC|US|S|E)-?(\d+)\b")
ARTIFACT_RE = re.compile(r"\b([0-9A-Za-z][\w.\-]*\.(?:png|jpe?g|webp|pdf))\b", re.IGNORECASE)
STEP_SECTION_SLUGS = ("implementation-steps", "evidence-steps", "steps")
DELIVERED_SLUG = "already-delivered"
PROGRESS_STATUSES = ("pending", "done", "skipped", "blocked")


def normalise_req_id(prefix: str, number: str) -> str:
    prefix = prefix.upper()
    return f"{prefix}{number}" if prefix in ("S", "E") else f"{prefix}-{number}"


def strip_markdown(text: str) -> str:
    text = re.sub(r"^\s*\[[ xX~]\]\s*", "", text)
    text = re.sub(r"[`*_]+", "", text).strip()
    return re.sub(r"\s+", " ", text)[:160]


def plan_section_text(paths: list[Path], slugs: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for path in paths:
        for section in markdown_sections(path):
            if any(slug in slugs for slug in section["slugs"]):
                chunks.append(section["text"])
    return "\n".join(chunks)


def steps_source_paths(paths: list[Path], kind: str) -> list[Path]:
    """A folder plan holds both implementation.md and evidence.md, and both have a
    steps section. Read the one this kind owns, or the counterpart's steps leak in."""
    own, other = ("implementation.md", "evidence.md")
    if kind == "evidence":
        own, other = other, own
    owned = [path for path in paths if path.name == own]
    if owned:
        return owned
    return [path for path in paths if path.name != other]


def parse_implementation_steps(text: str) -> list[dict[str, Any]]:
    """Explicit S-ids win outright. Otherwise bold `**Step N**` headers and
    ordinal list items are both steps, kept in document order. Ordinals are
    flagged unstable: inserting a step renumbers them, which is why the steps
    hash exists."""
    explicit: list[dict[str, Any]] = []
    fallback: list[dict[str, Any]] = []

    def marked(line: str) -> bool:
        return bool(STEP_DONE_RE.search(line) or DONE_TOKEN_RE.search(line))

    for line in text.splitlines():
        match = STEP_EXPLICIT_RE.match(line)
        if match:
            explicit.append({
                "id": match.group(1).upper(),
                "title": strip_markdown(match.group(2)),
                "marked_done": marked(line),
                "id_source": "explicit",
            })
            continue
        match = STEP_BOLD_RE.match(line)
        if match:
            fallback.append({
                "id": f"STEP-{match.group(1).upper()}",
                "title": strip_markdown(match.group(2)),
                "marked_done": marked(line),
                "id_source": "bold",
            })
            continue
        match = STEP_ORDINAL_RE.match(line)
        if match:
            fallback.append({
                "id": f"N{match.group(1)}",
                "title": strip_markdown(match.group(2)),
                "marked_done": marked(line),
                "id_source": "ordinal",
            })
    chosen = explicit or fallback
    seen: set[str] = set()
    steps: list[dict[str, Any]] = []
    for step in chosen:
        if step["id"] in seen:
            continue
        seen.add(step["id"])
        steps.append(step)
    return steps


def parse_evidence_steps(text: str, artifacts_dir: Path | None) -> list[dict[str, Any]]:
    """Evidence steps are keyed by their planned artifact filename: the strongest
    id available, and one that lets existence on disk answer "is this done"."""
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or set(stripped) <= set("|- :"):
            continue
        found = ARTIFACT_RE.findall(stripped)
        if not found:
            continue
        artifact = found[-1]
        if artifact in seen or "<" in stripped.split(artifact)[0][-3:]:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        goal = strip_markdown(cells[1]) if len(cells) > 1 else ""
        seen.add(artifact)
        entry = {
            "id": artifact,
            "title": goal,
            "marked_done": False,
            "id_source": "artifact",
        }
        if artifacts_dir is not None:
            entry["artifact_path"] = str(artifacts_dir / artifact)
            entry["artifact_exists"] = (artifacts_dir / artifact).is_file()
        steps.append(entry)
    return steps


def delivered_ids(paths: list[Path]) -> list[str]:
    """Ids on ticked lines of an `Already delivered` section. Only explicit ids
    count; prose is never guessed at."""
    text = plan_section_text(paths, (DELIVERED_SLUG,))
    ids: list[str] = []
    for line in text.splitlines():
        if not re.match(r"^\s*[-*]\s+\[[xX]\]", line):
            continue
        for prefix, number in REQ_ID_RE.findall(line):
            value = normalise_req_id(prefix, number)
            if value not in ids:
                ids.append(value)
    return ids


def steps_fingerprint(text: str) -> str:
    normalised = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:16]


def evidence_artifacts_dir(issue: str) -> Path:
    return agents_home() / "prds" / issue / "evidence"


def read_progress_state(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    match = PROGRESS_MARKER_RE.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Hand-edited file with the machine block lost: trust the checkboxes.
    steps: dict[str, Any] = {}
    for line in text.splitlines():
        entry = re.match(r"^\s*[-*]\s+\[([ xX~])\]\s+`?([^`\s]+)`?", line)
        if entry:
            mark = entry.group(1).lower()
            steps[entry.group(2)] = {
                "status": "done" if mark == "x" else "skipped" if mark == "~" else "pending",
            }
    return {"version": 1, "steps": steps, "steps_hash": None, "source": "checkboxes"}


def render_progress(issue: str, kind: str, state: dict[str, Any],
                    steps: list[dict[str, Any]]) -> str:
    mark = {"done": "x", "skipped": "~", "blocked": " ", "pending": " "}
    lines = [f"# {issue}: Progress", ""]
    lines.append(
        f"Run state for `{kind}`. Written by run-plan, not by hand. Excluded from "
        "`agentctl plan validate`."
    )
    lines.append("")
    meta = [f"Steps hash: `{state.get('steps_hash')}`"]
    if state.get("branch"):
        meta.append(f"Branch: `{state['branch']}`")
    if state.get("updated"):
        meta.append(f"Updated: {state['updated']}")
    lines.append(" · ".join(meta))
    lines.append("")
    delivered = state.get("delivered") or []
    if delivered:
        lines.append(f"Closed before this run (from `Already delivered`): {', '.join(delivered)}")
        lines.append("")
    for step in steps:
        record = state["steps"].get(step["id"], {})
        status = record.get("status", "pending")
        suffix = ""
        if status == "blocked":
            suffix = " — **blocked**"
        elif status == "skipped":
            suffix = " — skipped"
        note = record.get("note")
        if note:
            suffix += f" ({note})"
        lines.append(f"- [{mark.get(status, ' ')}] `{step['id']}` {step['title']}{suffix}")
    lines.append("")
    # `-->` inside a note would close the comment and drop the machine block.
    blob = json.dumps(state, sort_keys=True).replace("-->", r"--\u003e")
    lines.append(f"<!-- agentctl:progress {blob} -->")
    return "\n".join(lines) + "\n"


def build_progress(directory: Path, kind: str, issue: str,
                   artifacts_dir: Path | None) -> dict[str, Any]:
    paths = plan_dir_files(directory) if directory.is_dir() else [directory]
    section = plan_section_text(steps_source_paths(paths, kind), STEP_SECTION_SLUGS)
    if kind == "evidence":
        steps = parse_evidence_steps(section, artifacts_dir)
    else:
        steps = parse_implementation_steps(section)
    fingerprint = steps_fingerprint(section)
    closed = delivered_ids(paths)

    recorded, _ = read_kind_progress(directory, kind)
    stale = bool(recorded and recorded.get("steps_hash")
                 and recorded["steps_hash"] != fingerprint)
    unstable = any(step["id_source"] == "ordinal" for step in steps)

    state: dict[str, Any] = {
        "version": 1,
        "kind": kind,
        "issue": issue,
        "steps_hash": fingerprint,
        "branch": (recorded or {}).get("branch") or current_branch(),
        "delivered": closed,
        "steps": {},
    }
    carry = {}
    if recorded and not (stale and unstable):
        # Explicit ids survive an edit; ordinals do not, because the number moves.
        carry = recorded.get("steps") or {}
    for step in steps:
        record = dict(carry.get(step["id"], {}))
        status = record.get("status")
        source = "recorded" if status else None
        if not status:
            if step["marked_done"] or step["id"] in closed:
                status, source = "done", "inferred-plan"
            elif step.get("artifact_exists"):
                status, source = "done", "inferred-artifact"
            else:
                status, source = "pending", "default"
        record["status"] = status
        record["source"] = source
        state["steps"][step["id"]] = record
    state["updated"] = dt.date.today().isoformat()
    state["stale"] = stale
    sources = sorted({step["id_source"] for step in steps})
    state["id_source"] = "+".join(sources) if sources else None
    state["unstable_ids"] = unstable
    return {"state": state, "steps": steps, "paths": paths}


def current_branch() -> str | None:
    try:
        result = git(Path.cwd(), "branch", "--show-current")
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def cmd_plan_progress(args: argparse.Namespace) -> int:
    resolved = resolve_plan_target(
        args.target, plans_dir=(args.plans_dir or plans_root()).resolve(), kind=args.kind,
    )
    if resolved["status"] != "ok":
        emit(resolved)
        return 2
    entry = Path(resolved["entry"])
    # A folder plan resolves to plan.md; its steps live in implementation.md, so
    # progress must read the whole folder, not the entry file.
    root = Path(resolved["root"]) if resolved.get("root") else entry
    source = root if root.is_dir() else entry
    kind = args.kind or resolved["kind"]
    if source.is_dir():
        issue = source.name
    else:
        stem = source.stem
        suffix = "-evidence-plan"
        issue = stem.removesuffix(suffix)
    issue = resolved.get("task_id") or issue
    progress_file = progress_path(source, kind)
    artifacts_dir = args.artifacts_dir.resolve() if args.artifacts_dir else (
        evidence_artifacts_dir(issue) if kind == "evidence" else None
    )

    if args.reset:
        # A legacy progress.md holding this kind's state goes too, or it would be read back.
        _, legacy_file = read_kind_progress(source, kind)
        displace_foreign_progress(progress_file, kind)
        removed = []
        for path in {progress_file, legacy_file} - {None}:
            if path.is_file():
                path.unlink()
                removed.append(str(path))
        emit({"status": "reset", "file": str(progress_file), "existed": bool(removed),
              "removed": removed})
        return 0

    built = build_progress(source, kind, issue, artifacts_dir)
    state, steps = built["state"], built["steps"]
    known = {step["id"] for step in steps}
    unknown: list[str] = []
    for assignment in args.set or []:
        step_id, _, status = assignment.partition("=")
        step_id, status = step_id.strip(), (status or "done").strip().lower()
        if status not in PROGRESS_STATUSES:
            emit({"status": "bad-status", "value": status,
                  "allowed": list(PROGRESS_STATUSES)})
            return 2
        if step_id not in known:
            unknown.append(step_id)
            continue
        record = state["steps"].setdefault(step_id, {})
        record["status"] = status
        record["source"] = "recorded"
        record["at"] = dt.datetime.now().isoformat(timespec="seconds")
        if args.note:
            record["note"] = args.note
    if unknown:
        emit({"status": "unknown-steps", "steps": unknown, "known": sorted(known)})
        return 2

    wrote = None
    if args.set or args.write:
        displace_foreign_progress(progress_file, kind)
        progress_file.write_text(render_progress(issue, kind, state, steps), encoding="utf-8")
        wrote = str(progress_file)

    def ids_with(status: str) -> list[str]:
        return [step["id"] for step in steps
                if state["steps"][step["id"]]["status"] == status]

    pending = ids_with("pending")
    done = ids_with("done")
    blocked = ids_with("blocked")
    # done and skipped are finished. blocked stays next so a re-run stops on it.
    nxt = next(
        (step["id"] for step in steps
         if state["steps"][step["id"]]["status"] not in ("done", "skipped")),
        None,
    )
    emit({
        "status": "ok",
        "issue": issue,
        "kind": kind,
        "plan": str(source),
        "progress_file": str(progress_file),
        "progress_file_exists": progress_file.is_file(),
        "steps_hash": state["steps_hash"],
        "stale": state["stale"],
        "id_source": state["id_source"],
        "unstable_ids": state["unstable_ids"],
        "delivered": state["delivered"],
        "total": len(steps),
        "done": done,
        "pending": pending,
        "blocked": blocked,
        "next": nxt,
        "steps": [{"id": step["id"], "title": step["title"],
                   **state["steps"][step["id"]]} for step in steps],
        "wrote": wrote,
    })
    return 0


PLAN_STUBS = {
    "already-delivered": (
        "## Already delivered\n\n"
        "- Nothing delivered yet. This is the first increment.\n"
    ),
}


def cmd_plan_migrate(args: argparse.Namespace) -> int:
    target = args.file.resolve()
    if not target.exists():
        emit({"status": "missing", "file": str(target)})
        return 2
    kind = args.kind or infer_plan_kind(target)
    paths = plan_dir_files(target) if target.is_dir() else [target]
    sections = collect_headings(paths)
    present = {slug for section in sections for slug in section["slugs"]}
    missing = [slug for slug in PLAN_HEADINGS[kind] if slug not in present]
    addable = [slug for slug in missing if slug in PLAN_STUBS]
    host = target
    if target.is_dir():
        preferred = target / "implementation.md"
        host = preferred if preferred.is_file() else target / "plan.md"
    if args.apply and addable:
        text = host.read_text(encoding="utf-8") if host.is_file() else ""
        blocks = [PLAN_STUBS[slug] for slug in addable]
        text = text.rstrip("\n") + "\n\n" + "\n".join(blocks)
        host.write_text(text, encoding="utf-8")
    emit({
        "status": "applied" if (args.apply and addable) else "ok",
        "file": str(target),
        "kind": kind,
        "missing_sections": missing,
        "added": addable if args.apply else [],
        "needs": addable,
        "host": str(host),
        "unfixable": [slug for slug in missing if slug not in PLAN_STUBS],
    })
    return 0


def cmd_plan_init(args: argparse.Namespace) -> int:
    output = args.output.resolve()
    folder_mode = output.suffix.lower() != ".md"
    if folder_mode:
        if output.exists() and not output.is_dir():
            emit({"status": "not-a-directory", "output": str(output)})
            return 2
        output.mkdir(parents=True, exist_ok=True)
        created: list[str] = []
        plan_md = output / "plan.md"
        if plan_md.exists() and not args.force:
            emit({"status": "exists", "output": str(plan_md)})
            return 2
        plan_md.write_text(folder_plan_md(args.issue.upper(), args.kind), encoding="utf-8")
        created.append(str(plan_md))
        bodies = folder_companion_bodies(args.issue.upper())
        names = ["evidence.md"] if args.kind == "evidence" else [
            "requirements.md", "implementation.md", "validation.md", "tbd.md",
            "implicit.md",
        ]
        for name in names:
            path = output / name
            if path.exists() and not args.force:
                continue
            path.write_text(bodies[name], encoding="utf-8")
            created.append(str(path))
        emit({
            "status": "created",
            "kind": args.kind,
            "issue": args.issue.upper(),
            "output": str(output),
            "layout": "folder",
            "files": created,
        })
        return 0
    if output.exists() and not args.force:
        emit({"status": "exists", "output": str(output)})
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(plan_template(args.kind, args.issue.upper()), encoding="utf-8")
    emit({
        "status": "created",
        "kind": args.kind,
        "issue": args.issue.upper(),
        "output": str(output),
        "layout": "file",
    })
    return 0


def cmd_plan_validate(args: argparse.Namespace) -> int:
    target = args.file.resolve()
    if not target.exists():
        emit({"valid": False, "file": str(target), "error": "missing"})
        return 2
    kind = args.kind or infer_plan_kind(target)
    missing_index: list[str] = []
    if target.is_dir():
        paths = plan_dir_files(target)
        plan_md = target / "plan.md"
        for name in index_files(plan_md):
            if not (target / name).is_file():
                missing_index.append(name)
        payload = validate_plan_paths(paths, kind, str(target))
        payload["layout"] = "folder"
        payload["missing_index_files"] = missing_index
        if missing_index:
            payload["valid"] = False
        emit(payload)
        return 0 if payload["valid"] else 2
    payload = validate_plan_paths([target], kind, str(target))
    payload["layout"] = "file"
    emit(payload)
    return 0 if payload["valid"] else 2


def cmd_plan_resolve(args: argparse.Namespace) -> int:
    payload = resolve_plan_target(
        args.task_id, plans_dir=(args.plans_dir or plans_root()).resolve(), kind=args.kind,
    )
    emit(payload)
    return 0 if payload["status"] == "ok" else 2



def add_plan_parsers(group) -> None:
    init = group.add_parser(
        "init",
        help="Create a deterministic plan skeleton.",
        description=(
            "Create the required headings for a plan without inventing plan content. "
            "A path that does not end in .md is a folder layout (plan.md plus companions). "
            "A .md path stays a single-file plan."
        ),
    )
    init.add_argument("--kind", choices=sorted(PLAN_HEADINGS), required=True, help="Plan schema.")
    init.add_argument("--issue", required=True, help="Issue key used in the plan title.")
    init.add_argument("--output", type=Path, required=True, help="Destination Markdown file or plan directory.")
    init.add_argument("--force", action="store_true", help="Replace an existing output file.")
    init.set_defaults(func=cmd_plan_init)
    validate = group.add_parser(
        "validate",
        help="Check required plan structure.",
        description=(
            "Report missing required sections without editing the plan. "
            "Accepts a single Markdown file or a plan folder."
        ),
    )
    validate.add_argument("file", type=Path, help="Plan Markdown file or plan directory.")
    validate.add_argument(
        "--kind",
        choices=sorted(PLAN_HEADINGS),
        help="Plan schema. Inferred from layout or filename when omitted.",
    )
    validate.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    validate.set_defaults(func=cmd_plan_validate)
    progress = group.add_parser(
        "progress",
        help="Read or record per-step progress so a re-run skips finished work.",
        description=(
            "Report which plan steps are done, which are pending, and which step is "
            "next. With no progress file the state is INFERRED from the plan's "
            "'Already delivered' ledger, inline [x]/DONE step marks, and (evidence "
            "plans) artifacts already on disk, so plans written before this command "
            "resume correctly. A folder plan stores implementation progress in "
            "progress.md and every other kind in <kind>.progress.md (evidence: "
            "evidence.progress.md), so kinds never overwrite each other; a legacy "
            "progress.md is still read for the kind it records. A single-file plan "
            "stores <stem>.progress.md beside it, so files that share a directory do "
            "not share state. All are excluded from validation. next is the first "
            "step that is not done or skipped, so a blocked step stays next."
        ),
    )
    progress.add_argument("target", help="Issue key, plan folder, or plan file path.")
    progress.add_argument(
        "--kind",
        choices=sorted(PLAN_HEADINGS),
        help="Plan schema. Inferred from layout or filename when omitted.",
    )
    progress.add_argument(
        "--set",
        action="append",
        metavar="ID=STATUS",
        help=f"Record a step, e.g. S3=done. Status one of {', '.join(PROGRESS_STATUSES)}. Implies --write.",
    )
    progress.add_argument("--note", help="Short note stored with the --set steps.")
    progress.add_argument("--write", action="store_true",
                          help="Materialise the progress file from the current state.")
    progress.add_argument("--reset", action="store_true",
                          help="Delete the progress file. State falls back to inference.")
    progress.add_argument("--artifacts-dir", type=Path,
                          help="Evidence artifacts dir. Defaults to ~/.agents/prds/<TASK-ID>/evidence.")
    progress.add_argument(
        "--plans-dir", type=Path, default=None,
        help="Plans root. Defaults to ~/.agents/plans.",
    )
    progress.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    progress.set_defaults(func=cmd_plan_progress)
    migrate = group.add_parser(
        "migrate",
        help="Add required sections a plan predates, without touching its content.",
        description=(
            "Report (default) or insert (--apply) required headings an older plan "
            "lacks. Only appends an empty stub; never rewrites existing sections."
        ),
    )
    migrate.add_argument("file", type=Path, help="Plan Markdown file or plan directory.")
    migrate.add_argument(
        "--kind",
        choices=sorted(PLAN_HEADINGS),
        help="Plan schema. Inferred from layout or filename when omitted.",
    )
    migrate.add_argument("--apply", action="store_true",
                         help="Write the stub sections. Default is a dry run.")
    migrate.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    migrate.set_defaults(func=cmd_plan_migrate)
    plan_resolve = group.add_parser(
        "resolve",
        help="Resolve a task id to plan entry, kind, and section index.",
        description=(
            "Look up ~/.agents/plans/{TASK-ID}/ first, then {TASK-ID}.md and "
            "{TASK-ID}-evidence-plan.md. Return bounded JSON: entry, kind, sections."
        ),
    )
    plan_resolve.add_argument("task_id", help="Issue key, plan folder, or plan file path.")
    plan_resolve.add_argument(
        "--kind",
        choices=sorted(PLAN_HEADINGS),
        help="Prefer implementation or evidence when both exist.",
    )
    plan_resolve.add_argument(
        "--plans-dir",
        type=Path,
        default=None,
        help="Plans root. Defaults to ~/.agents/plans.",
    )
    plan_resolve.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    plan_resolve.set_defaults(func=cmd_plan_resolve)

