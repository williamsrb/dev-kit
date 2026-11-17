"""Chat digest readers for Codex and Cursor transcripts (factory-kb-harvest follow-up to RC1 and RC4).

Same output shape as `agentctl_kb_digest.digest_transcript` (source `chat`, signals, kb_reads, skills, rejections), plus a
`vendor` field. Pure over files: no model call. What each vendor's transcript records limits the signals:

- Codex rollout files hold user messages and tool outputs with exit codes: `error`, `denial`, `correction`.
- Cursor agent transcripts hold only user and assistant messages and tool calls, no results and no timestamps:
  `correction` only. Validator reports are not extracted for either vendor (no command markers in the file).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agentctl_kb import KbError
from agentctl_kb_digest import (
    DEFAULT_LIMITS,
    DENIAL_RE,
    REJECTION_LIMIT,
    _bound,
    _first_line,
    digest_transcript,
    factory_session_ids,
    read_records,
    resolve_transcript,
)
from agentctl_kb_proposals import kit_relative, read_ledger

VENDORS = ("claude", "codex", "cursor")
EXIT_RE = re.compile(r'exit_code\\*"?\s*:\s*(-?\d+)')
PATH_RE = re.compile(r"(?:~|/)[\w./~+@-]+")
SKILL_FILE_RE = re.compile(r"(?:^|/)skills/([\w.-]+)/SKILL\.md$")
QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.DOTALL)
CODEX_CALLS = ("custom_tool_call", "function_call")
CODEX_OUTPUTS = ("custom_tool_call_output", "function_call_output")
CURSOR_READ_TOOLS = ("ReadFile", "Read")


def vendor_roots(user_home: Path, vendor: str) -> list[Path]:
    if vendor == "codex":
        return [user_home / ".codex" / "sessions"]
    if vendor == "cursor":
        return [user_home / ".cursor" / "projects"]
    raise KbError(f"unsupported vendor: {vendor}")


def vendor_files(user_home: Path, vendor: str) -> list[Path]:
    """Every transcript file of one non-Claude vendor."""
    found: list[Path] = []
    for root in vendor_roots(user_home, vendor):
        if not root.is_dir():
            continue
        pattern = "rollout-*.jsonl" if vendor == "codex" else "*/agent-transcripts/*/*.jsonl"
        found.extend(path for path in root.rglob(pattern) if path.is_file())
    return found


def codex_session_id(path: Path) -> str:
    """The uuid at the end of `rollout-<timestamp>-<uuid>.jsonl`."""
    match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", path.stem)
    return match.group(1) if match else path.stem


def resolve_for(vendor: str, session: str | None, latest: bool, user_home: Path | None = None) -> Path:
    """One transcript of a vendor by session id, or the newest one (Codex and Cursor: newest overall)."""
    if vendor == "claude":
        return resolve_transcript(user_home, session=session, latest=latest)
    files = vendor_files(user_home or Path.home(), vendor)
    if session:
        wanted = [f for f in files if (codex_session_id(f) if vendor == "codex" else f.stem) == session]
        if not wanted:
            raise KbError(f"no {vendor} transcript for session {session}")
        return min(wanted)
    if latest and files:
        return max(files, key=lambda f: f.stat().st_mtime)
    raise KbError(f"pass --session <id> or --latest ({vendor})")


class _Collector:
    def __init__(self, limits: dict[str, int]) -> None:
        self.excerpt = limits["excerpt_bytes"]
        self.budget = limits["supervisor_bytes"]
        self.used = 0
        self.dropped = 0
        self.signals: list[dict[str, Any]] = []
        self.kb_reads: list[str] = []
        self.skills: list[str] = []

    def add(self, kind: str, key: str, detail: str, ts: str | None) -> None:
        text = _bound(detail, self.excerpt)
        if self.used + len(text) > self.budget:
            self.dropped += 1
            return
        self.used += len(text)
        self.signals.append({"id": f"S{len(self.signals) + 1}", "key": key, "kind": kind, "uuid": None, "ts": ts,
                             "detail": text, "retry": None})

    def note_path(self, raw: str) -> None:
        rel = kit_relative(raw)
        if rel and rel not in self.kb_reads:
            self.kb_reads.append(rel)
        match = SKILL_FILE_RE.search(raw)
        if match and match.group(1) not in self.skills:
            self.skills.append(match.group(1))


def _rejections(home: Path) -> list[dict[str, Any]]:
    decided: list[dict[str, Any]] = []
    for ledger in sorted((home / "factory").glob("*/kb-decisions.jsonl")) + sorted(
            (home / "kb-inbox").glob("*/kb-decisions.jsonl")):
        decided.extend({"ref": row.get("ref"), "target": row.get("target"), "reason": row.get("reason")}
                       for row in read_ledger(ledger) if row.get("state") == "rejected")
    return decided[-REJECTION_LIMIT:]


def _result(vendor: str, session_id: str, path: Path, first_prompt: str, c: _Collector, home: Path) -> dict[str, Any]:
    return {
        "schema_version": 1, "source": "chat", "vendor": vendor, "session_id": session_id, "transcript": str(path),
        "first_prompt": first_prompt, "signals": c.signals, "kb_reads": c.kb_reads, "skills": c.skills,
        "rejections": _rejections(home), "dropped": c.dropped, "has_signals": bool(c.signals),
    }


def _output_text(output: Any) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        return "\n".join(str(b.get("text", "")) for b in output if isinstance(b, dict))
    return json.dumps(output, ensure_ascii=False)


def _is_context_text(text: str) -> bool:
    """Harness-injected user text (environment, instructions) is not an operator message."""
    stripped = text.lstrip()
    return not stripped or stripped.startswith(("<", "# AGENTS.md"))


def digest_codex(path: Path, home: Path, limits: dict[str, int] | None = None) -> dict[str, Any]:
    c = _Collector(limits or DEFAULT_LIMITS)
    session_id = codex_session_id(path)
    first_prompt = ""
    pending: dict[str, str] = {}
    first_seen = False
    for record in read_records(path):
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        ts = record.get("timestamp")
        if record.get("type") == "session_meta" and payload.get("id"):
            session_id = str(payload["id"])
        elif record.get("type") == "event_msg" and payload.get("type") == "item_completed":
            item = payload.get("item") or {}
            if item.get("type") != "UserMessage":
                continue
            text = " ".join(str(b.get("text", "")) for b in item.get("content") or [] if isinstance(b, dict)).strip()
            if _is_context_text(text):
                continue
            if not first_seen:
                first_seen, first_prompt = True, _bound(text, 200)
            else:
                c.add("correction", f"correction:{_first_line(text, 40).lower()}", _first_line(text, 300), ts)
        elif record.get("type") == "response_item" and payload.get("type") in CODEX_CALLS:
            name = str(payload.get("name") or "")
            raw_input = str(payload.get("input") or payload.get("arguments") or "")
            pending[str(payload.get("call_id"))] = name
            for token in PATH_RE.findall(raw_input):
                c.note_path(token)
        elif record.get("type") == "response_item" and payload.get("type") in CODEX_OUTPUTS:
            text = _output_text(payload.get("output"))
            match = EXIT_RE.search(text)
            if not match or int(match.group(1)) == 0:
                continue
            tool = pending.get(str(payload.get("call_id")), "unknown")
            body = text.split("Output:", 1)[-1]
            line = _first_line(body)
            kind = "denial" if DENIAL_RE.search(body[:400]) else "error"
            c.add(kind, f"{kind}:{tool}:{line[:60].lower()}", f"{tool}: exit {match.group(1)}: {line}", ts)
    return _result("codex", session_id, path, first_prompt, c, home)


def _cursor_text(record: dict[str, Any]) -> str:
    blocks = (record.get("message") or {}).get("content")
    parts = [str(b.get("text", "")) for b in blocks if isinstance(b, dict) and b.get("type") == "text"] \
        if isinstance(blocks, list) else []
    text = "\n".join(parts)
    query = QUERY_RE.search(text)
    return (query.group(1) if query else text).strip()


def digest_cursor(path: Path, home: Path, limits: dict[str, int] | None = None) -> dict[str, Any]:
    c = _Collector(limits or DEFAULT_LIMITS)
    first_prompt = ""
    first_seen = False
    for record in read_records(path):
        if record.get("role") == "user":
            text = _cursor_text(record)
            if not text:
                continue
            if not first_seen:
                first_seen, first_prompt = True, _bound(" ".join(text.split()), 200)
            else:
                c.add("correction", f"correction:{_first_line(text, 40).lower()}", _first_line(text, 300), None)
        elif record.get("role") == "assistant":
            blocks = (record.get("message") or {}).get("content")
            for block in blocks if isinstance(blocks, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in CURSOR_READ_TOOLS:
                    args = block.get("input") or {}
                    c.note_path(str(args.get("path") or args.get("file_path") or ""))
    return _result("cursor", path.stem, path, first_prompt, c, home)


def digest_for(vendor: str, path: Path, home: Path) -> dict[str, Any]:
    """The digest of one transcript of any supported vendor."""
    if vendor == "claude":
        digest = digest_transcript(path, home)
        digest["vendor"] = "claude"
        return digest
    if vendor == "codex":
        digest = digest_codex(path, home)
        if digest["session_id"] in factory_session_ids(home):
            raise KbError(f"session {digest['session_id']} is a factory worker; its run already has a digest")
        return digest
    if vendor == "cursor":
        return digest_cursor(path, home)
    raise KbError(f"unsupported vendor: {vendor}")
