"""Chat digest: deterministic friction signals from one Claude transcript (factory-kb-harvest RC1, RC3, RC4).

Pure over files: no model call. Output keeps the factory digest's top-level shape (source, signals, kit_reads,
rejections, has_signals) so `harvest-kb` reads one shape. Chat keys are not measured; they group signals.
"""

from __future__ import annotations

import contextlib
import json
import re
from pathlib import Path
from typing import Any

from agentctl_harness import COMMAND_RE, _user_texts, root_files, transcript_roots
from agentctl_kb import KbError
from agentctl_kb_proposals import PROPOSALS_NAME, kit_relative, read_ledger

VALIDATORS = ("validate-plan", "validate-impl")
REJECTION_LIMIT = 20
DENIAL_RE = re.compile(r"permission|denied|hook", re.IGNORECASE)
INTERRUPT_MARK = "[Request interrupted by user"
DEFAULT_LIMITS = {"excerpt_bytes": 4096, "supervisor_bytes": 6144}


def _bound(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: max(limit - 1, 0)] + "…"


def _first_line(text: str, limit: int = 80) -> str:
    line = " ".join(text.strip().splitlines()[:1]) if text.strip() else ""
    return " ".join(line.split())[:limit]


def project_folder(cwd: Path) -> str:
    """Claude names a project folder after the cwd: '/' and '.' become '-'."""
    return str(cwd).replace("/", "-").replace(".", "-")


def read_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            row = json.loads(line)
            if isinstance(row, dict):
                records.append(row)
    return records


def factory_session_ids(home: Path) -> set[str]:
    """Session ids that a factory worker used (step_started.session_id). Chat digests refuse these."""
    ids: set[str] = set()
    for events in (home / "factory").glob("*/events.jsonl"):
        for row in read_records(events):
            if row.get("type") == "step_started" and row.get("session_id"):
                ids.add(str(row["session_id"]))
    return ids


def resolve_transcript(user_home: Path | None, session: str | None = None, latest: bool = False,
                       cwd: Path | None = None) -> Path:
    """One Claude transcript by session id (its file stem), or the newest one of the cwd's project folder.
    Transcripts live under the user's home (~/.claude, ~/.agents-profiles/*/claude), not the agents home."""
    roots = transcript_roots(user_home or Path.home(), ("claude", "profiles"))
    files = [f for root in roots for f in root_files(root)]
    if session:
        matches = sorted(f for f in files if f.stem == session)
        if not matches:
            raise KbError(f"no Claude transcript for session {session}")
        return matches[0]
    if latest:
        folder = project_folder((cwd or Path.cwd()).resolve())
        candidates = [f for f in files if f.parent.name == folder]
        if not candidates:
            raise KbError(f"no Claude transcript for the project folder {folder}")
        return max(candidates, key=lambda f: f.stat().st_mtime)
    raise KbError("pass --session <id> or --latest")


def _blocks(record: dict[str, Any]) -> list[dict[str, Any]]:
    content = (record.get("message") or {}).get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def _is_operator_text(record: dict[str, Any]) -> bool:
    if record.get("type") != "user":
        return False
    texts = _user_texts((record.get("message") or {}).get("content"))
    if not texts or any(not t.strip() for t in texts):
        return False
    joined = "\n".join(texts)
    return "<command-name>" not in joined and "<system-reminder>" not in joined and INTERRUPT_MARK not in joined


def _command_of(record: dict[str, Any]) -> str | None:
    if record.get("type") != "user":
        return None
    match = COMMAND_RE.search("\n".join(_user_texts((record.get("message") or {}).get("content"))))
    return match.group(1).strip() if match else None


def digest_transcript(path: Path, home: Path, limits: dict[str, int] | None = None) -> dict[str, Any]:
    """The chat digest of one transcript. Refuses a factory worker session."""
    limits = limits or DEFAULT_LIMITS
    excerpt, budget = limits["excerpt_bytes"], limits["supervisor_bytes"]
    session_id = path.stem
    if session_id in factory_session_ids(home):
        raise KbError(f"session {session_id} is a factory worker; its run already has a digest")
    records = read_records(path)
    signals: list[dict[str, Any]] = []
    kb_reads: list[str] = []
    skills: list[str] = []
    used = 0
    dropped = 0
    first_prompt = ""
    pending: dict[str, str] = {}
    open_error: dict[str, dict[str, Any]] = {}
    validators: list[dict[str, Any]] = []

    def add(kind: str, key: str, detail: str, uuid: str | None, ts: str | None) -> dict[str, Any] | None:
        nonlocal used, dropped
        text = _bound(detail, excerpt)
        if used + len(text) > budget:
            dropped += 1
            return None
        used += len(text)
        signal = {"id": f"S{len(signals) + 1}", "key": key, "kind": kind, "uuid": uuid, "ts": ts,
                  "detail": text, "retry": None}
        signals.append(signal)
        return signal

    first_index: int | None = None
    for index, record in enumerate(records):
        uuid, ts = record.get("uuid"), record.get("timestamp")
        blocks = _blocks(record)
        if record.get("type") == "user" and first_index is None and _command_of(record) is None:
            texts = _user_texts((record.get("message") or {}).get("content"))
            if texts and not any("<system-reminder>" in t for t in texts) and _is_operator_text(record):
                first_prompt = _bound(" ".join(texts), 200)
                first_index = index
        if record.get("type") == "user" and any(b.get("type") == "tool_result" for b in blocks):
            for block in blocks:
                if block.get("type") != "tool_result" or not block.get("is_error"):
                    continue
                tool = pending.get(str(block.get("tool_use_id")), "unknown")
                content = block.get("content")
                text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                line = _first_line(text)
                kind = "denial" if DENIAL_RE.search(text[:400]) else "error"
                signal = add(kind, f"{kind}:{tool}:{line[:60].lower()}", f"{tool}: {line}", uuid, ts)
                if signal is not None and kind == "error":
                    open_error[tool] = signal
            continue
        if _is_operator_text(record) and first_index is not None and index > first_index:
            text = " ".join(_user_texts((record.get("message") or {}).get("content")))
            add("correction", f"correction:{_first_line(text, 40).lower()}", _first_line(text, 300), uuid, ts)
        if record.get("type") == "user":
            joined = "\n".join(_user_texts((record.get("message") or {}).get("content")))
            if INTERRUPT_MARK in joined:
                add("interrupt", "interrupt", "Request interrupted by user", uuid, ts)
        for block in blocks:
            if block.get("type") != "tool_use":
                continue
            name = str(block.get("name") or "")
            args = block.get("input") or {}
            pending[str(block.get("id"))] = name
            if name in open_error:
                open_error.pop(name)["retry"] = uuid
            if name == "Skill" and args.get("skill") and args["skill"] not in skills:
                skills.append(str(args["skill"]))
            if name == "Read" and args.get("file_path"):
                rel = kit_relative(str(args["file_path"]))
                if rel and rel not in kb_reads:
                    kb_reads.append(rel)
            file_path = str(args.get("file_path") or "")
            if name in ("Write", "Edit") and file_path.endswith(".md") and "/memory/" in file_path \
                    and Path(file_path).name != "MEMORY.md":
                body = str(args.get("content") or args.get("new_string") or "")
                add("memory", f"memory:{Path(file_path).name}", f"{file_path}: {_first_line(body, 200)}", uuid, ts)
        command = _command_of(record)
        if command in VALIDATORS or any(b.get("type") == "tool_use" and b.get("name") == "Skill"
                                        and (b.get("input") or {}).get("skill") in VALIDATORS for b in blocks):
            name = command or next((b["input"]["skill"] for b in blocks if b.get("type") == "tool_use"
                                    and b.get("name") == "Skill"), "")
            validators.append({"name": name, "start": index, "uuid": uuid, "ts": ts})

    for number, v in enumerate(validators):
        end = next((i for i in range(v["start"] + 1, len(records)) if _is_operator_text(records[i])), len(records))
        report = None
        paths: list[str] = []
        for record in records[v["start"] + 1:end]:
            for block in _blocks(record):
                if record.get("type") == "assistant" and block.get("type") == "text" and block.get("text", "").strip():
                    report = block["text"]
                if record.get("type") == "assistant" and block.get("type") == "tool_use" \
                        and block.get("name") in ("Write", "Edit") and (block.get("input") or {}).get("file_path"):
                    path = str(block["input"]["file_path"])
                    if path not in paths:
                        paths.append(path)
        if report is None:
            continue
        add("validator_report", f"validator_report:{v['name']}",
            f"{v['name']}: {report.strip()} | changed: {', '.join(paths) or 'none'}", v["uuid"], v["ts"])

    rejections: list[dict[str, Any]] = []
    decided: list[dict[str, Any]] = []
    for ledger in sorted((home / "factory").glob("*/kb-decisions.jsonl")) + sorted(
            (home / "kb-inbox").glob("*/kb-decisions.jsonl")):
        for row in read_ledger(ledger):
            if row.get("state") == "rejected":
                decided.append({"ref": row.get("ref"), "target": row.get("target"), "reason": row.get("reason")})
    rejections = decided[-REJECTION_LIMIT:]

    return {
        "schema_version": 1, "source": "chat", "session_id": session_id, "transcript": str(path),
        "first_prompt": first_prompt, "signals": signals, "kb_reads": kb_reads, "skills": skills,
        "rejections": rejections, "dropped": dropped, "has_signals": bool(signals),
    }


def write_digest(home: Path, path: Path, digest: dict[str, Any]) -> Path:
    folder = home / "kb-inbox" / digest["session_id"]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "digest.json"
    target.write_text(json.dumps(digest, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def memory_digest(home: Path, limits: dict[str, int] | None = None, user_home: Path | None = None) -> dict[str, Any]:
    """Feedback memories under the transcript roots' memory folders, minus those a decided proposal cites."""
    limits = limits or DEFAULT_LIMITS
    cited: set[str] = set()
    for ledger in sorted((home / "factory").glob("*/steps/*/kb-proposals.md")) + sorted(
            (home / "kb-inbox").glob(f"*/{PROPOSALS_NAME}")):
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if line.startswith("- evidence:"):
                cited.update(re.findall(r"\S*/memory/\S+\.md", line))
    signals: list[dict[str, Any]] = []
    for root in transcript_roots(user_home or Path.home(), ("claude", "profiles")):
        base = Path(root["path"])
        if not base.is_dir():
            continue
        for memory in sorted(base.glob("*/memory/*.md")):
            if memory.name == "MEMORY.md" or str(memory) in cited:
                continue
            body = memory.read_text(encoding="utf-8", errors="replace")
            meta = re.search(r"^---\n(.*?)\n---", body, re.DOTALL)
            kind = None
            if meta:
                found = re.search(r"^\s*(?:metadata:\s*\n\s+)?type:\s*(\S+)", meta.group(1), re.MULTILINE)
                kind = found.group(1) if found else None
            if kind != "feedback":
                continue
            signals.append({"id": f"S{len(signals) + 1}", "key": f"memory:{memory.name}", "kind": "memory",
                            "path": str(memory), "detail": _bound(body, limits["excerpt_bytes"])})
    return {"schema_version": 1, "source": "memories", "signals": signals, "has_signals": bool(signals)}


def parse_age(text: str) -> int:
    """'30d' -> 30 days. Only whole days are accepted."""
    match = re.fullmatch(r"(\d+)d", text.strip())
    if not match:
        raise KbError(f"--older-than takes whole days, like 30d: {text}")
    return int(match.group(1))


def prune_inbox(home: Path, older_than_days: int, now: float | None = None) -> list[str]:
    """Remove kb-inbox/<id>/ folders whose newest file is older than the cutoff and that hold no proposals and no
    decision log. Returns the removed folder names."""
    import shutil
    import time

    cutoff = (now if now is not None else time.time()) - older_than_days * 86400
    removed: list[str] = []
    for folder in sorted((home / "kb-inbox").glob("*")):
        if not folder.is_dir() or folder.name == "memories":
            continue
        keep = any(folder.joinpath(name).is_file() for name in (PROPOSALS_NAME, "harness-proposals.md",
                                                                  "kb-decisions.jsonl", "harness-decisions.jsonl"))
        newest = max((f.stat().st_mtime for f in folder.rglob("*") if f.is_file()), default=0.0)
        if not keep and newest < cutoff:
            shutil.rmtree(folder)
            removed.append(folder.name)
    return removed


HARVEST_PROMPT = (
    "Run the skill `harvest-kb` headless (called_from: factory). Its digest is {digest}; write the proposals into "
    "{folder} (kb-proposals.md for knowledge, harness-proposals.md for skill lessons), append only, run "
    "`agentctl kb proposals check` on each file, and report status ok with one line per signal group. Change nothing "
    "under kb/, skills/, rules/, hooks/ or mcp/. Do not ask questions."
)


def pending_inbox(home: Path, limit: int) -> list[Path]:
    """Inbox folders with a digest that has signals and no kb-proposals.md yet, oldest digest first."""
    rows: list[tuple[float, Path]] = []
    for folder in (home / "kb-inbox").glob("*"):
        digest = folder / "digest.json"
        if folder.name == "memories" or not digest.is_file() or (folder / PROPOSALS_NAME).exists():
            continue
        with contextlib.suppress(json.JSONDecodeError, OSError):
            if json.loads(digest.read_text(encoding="utf-8")).get("has_signals"):
                rows.append((digest.stat().st_mtime, folder))
    return [folder for _, folder in sorted(rows)[:limit]]


def harvest_pending(home: Path, *, limit: int = 5, dry_run: bool = False, adapter: Any = None,
                    budget_usd: float | None = None) -> list[dict[str, Any]]:
    """Run harvest-kb once per pending inbox folder through the Claude adapter (role follow, kit deny on).
    Operator command only: a hook or timer never calls this."""
    import uuid

    folders = pending_inbox(home, limit)
    if dry_run:
        return [{"folder": str(f), "action": "would harvest"} for f in folders]
    import agentctl_factory as factory

    adapter = adapter or factory.ClaudeAdapter()
    model, effort = factory.resolve_role("follow", "claude")
    budget = budget_usd if budget_usd is not None else factory.DEFAULT_FOLLOW_BUDGET
    results: list[dict[str, Any]] = []
    for folder in folders:
        step_dir = folder / "harvest-run"
        step_dir.mkdir(exist_ok=True)
        prompt = HARVEST_PROMPT.format(digest=folder / "digest.json", folder=folder)
        req = factory.WorkerRequest(
            prompt=prompt, model=model, effort=effort, cwd=home, step_dir=step_dir, session_id=str(uuid.uuid4()),
            timeout_s=900, budget_usd=budget,
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash(agentctl:*)", "Bash(rg:*)"],
            disallowed_tools=factory.kit_deny_rules(home), permission_mode="acceptEdits",
        )
        result = adapter.run(req)
        results.append({"folder": str(folder), "exit": result.exit_code, "timed_out": result.timed_out,
                        "proposals": (folder / PROPOSALS_NAME).is_file()})
    return results

