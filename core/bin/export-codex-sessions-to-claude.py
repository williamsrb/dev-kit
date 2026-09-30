#!/usr/bin/env python3
"""Export native Codex user threads (and Codex-side forks) into Claude Desktop.

Claude already imports into Codex. This is the reverse, one-way:

  ~/.codex/sessions/**/rollout-*.jsonl
    -> ~/.claude/projects/<slug>/<cliSessionId>.jsonl
    -> ~/.config/Claude/claude-code-sessions/<account>/<org>/local_<id>.json

Rules:
  - Native user threads (not in Codex's import ledger) become new Claude chats.
  - Imported threads that gained Codex-only user turns after import:
      * Claude unchanged since import (no new user turns there) -> merge the
        Codex continuation into the original Claude transcript/index.
      * Claude also continued independently -> export as a sibling fork chat.
  - Frozen imports (no extra Codex turns after import) are skipped.
  - Subagent threads are skipped.
  - Text turns only (user prompts + assistant text). No tool replay.

Loop guard: native/fork destinations use UUID5 of the Codex thread id with
entrypoint codex-export. Merges append to the import source_path only when
Claude has not gained new user turns since import.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

HOME = Path.home()
DEFAULT_CODEX_SESSIONS = HOME / ".codex" / "sessions"
DEFAULT_IMPORT_LEDGER = HOME / ".codex" / "external_agent_session_imports.json"
DEFAULT_CLAUDE_PROJECTS = HOME / ".claude" / "projects"
DEFAULT_CLAUDE_INDEX_ROOT = HOME / ".config" / "Claude" / "claude-code-sessions"
DEFAULT_STATE_DIR = HOME / ".local" / "share" / "codex-to-claude-sync"
DEFAULT_EXPORT_LEDGER = DEFAULT_STATE_DIR / "exports.json"
DEFAULT_LOCK = DEFAULT_STATE_DIR / "export.lock"
DEFAULT_LOG = DEFAULT_STATE_DIR / "export.log"

UUID_NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://agents.local/codex-to-claude")
ENTRYPOINT = "codex-export"
CLAUDE_VERSION = "2.1.229"
TITLE_PREFIX = "[codex] "
FORK_SLACK = timedelta(seconds=60)
SKIP_USER_PREFIXES = (
    "<recommended_plugins>",
    "# AGENTS.md",
    "<skills_instructions>",
    "<environment_context>",
    "<INSTRUCTIONS>",
    "<in-app-browser-context",
)


@dataclass
class Turn:
    role: str
    text: str
    ts: datetime


@dataclass
class CodexSession:
    path: Path
    thread_id: str
    cwd: str
    thread_source: Optional[str]
    originator: Optional[str]
    created: datetime
    mtime_ns: int
    sha256: str
    turns: List[Turn] = field(default_factory=list)


def sha256_file(path: Path, bufsize: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(bufsize)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def parse_ts(value: object) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 1e14:
            raw /= 1e9
        elif raw > 1e11:
            raw /= 1e3
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def iso_z(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def epoch_ms(ts: datetime) -> int:
    return int(ts.timestamp() * 1000)


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def is_injected_user_text(text: str) -> bool:
    stripped = (text or "").lstrip()
    return stripped.startswith(SKIP_USER_PREFIXES)


def project_slug(cwd: str) -> str:
    return cwd.replace("/", "-").replace(".", "-")


def claude_ids(codex_thread_id: str) -> Tuple[str, str]:
    cli = str(uuid.uuid5(UUID_NS, f"codex:{codex_thread_id}"))
    return cli, f"local_{cli}"


def message_uuid(codex_thread_id: str, index: int) -> str:
    return str(uuid.uuid5(UUID_NS, f"codex:{codex_thread_id}:msg:{index}"))


def load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        logging.warning("unreadable json %s: %s", path, e)
        return default


def atomic_write_text(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.chmod(tmp, mode)
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def iter_org_dirs(root: Path) -> Iterator[Path]:
    if not root.is_dir():
        return
    try:
        accounts = list(root.iterdir())
    except OSError as e:
        logging.warning("skip unreadable %s: %s", root, e)
        return
    for account in accounts:
        try:
            if account.is_symlink() or not account.is_dir():
                continue
            for org in account.iterdir():
                try:
                    if org.is_symlink() or not org.is_dir():
                        continue
                    yield org
                except OSError as e:
                    logging.warning("skip %s: %s", org, e)
        except OSError as e:
            logging.warning("skip %s: %s", account, e)


def pick_org_dir(root: Path) -> Path:
    orgs = list(iter_org_dirs(root))
    if not orgs:
        raise SystemExit(f"no Claude account/org directories under {root}")
    return max(orgs, key=lambda org: sum(1 for _ in org.glob("local_*.json")))


def load_import_ledger(path: Path) -> Dict[str, dict]:
    data = load_json(path, {})
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        return {}
    out: Dict[str, dict] = {}
    for rec in records:
        if isinstance(rec, dict) and rec.get("imported_thread_id"):
            out[str(rec["imported_thread_id"])] = rec
    return out


def load_export_ledger(path: Path) -> Dict[str, dict]:
    data = load_json(path, {})
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        return {}
    out: Dict[str, dict] = {}
    for rec in records:
        if isinstance(rec, dict) and rec.get("codex_session_id"):
            out[str(rec["codex_session_id"])] = rec
    return out


def save_export_ledger(path: Path, records: Dict[str, dict]) -> None:
    payload = {
        "updated_at": iso_z(datetime.now(timezone.utc)),
        "records": [records[k] for k in sorted(records)],
    }
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def first_session_meta(path: Path) -> Optional[dict]:
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i > 40:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "session_meta" and isinstance(obj.get("payload"), dict):
                return obj["payload"]
    return None


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: List[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text)
    return "\n".join(parts)


def extract_turns(path: Path) -> List[Turn]:
    event_turns: List[Turn] = []
    item_turns: List[Turn] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            typ = obj.get("type")
            payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
            ts = parse_ts(obj.get("timestamp") or payload.get("timestamp"))
            if ts is None:
                continue
            if typ == "event_msg":
                et = payload.get("type")
                if et == "user_message":
                    text = (payload.get("message") or "").strip()
                    if text and not is_injected_user_text(text):
                        event_turns.append(Turn("user", text, ts))
                elif et == "agent_message":
                    text = (payload.get("message") or "").strip()
                    if text:
                        event_turns.append(Turn("assistant", text, ts))
            elif typ == "response_item" and payload.get("type") == "message":
                role = payload.get("role")
                if role not in ("user", "assistant"):
                    continue
                text = content_text(payload.get("content")).strip()
                if not text:
                    continue
                if role == "user" and is_injected_user_text(text):
                    continue
                item_turns.append(Turn(role, text, ts))
    turns = event_turns if any(t.role == "user" for t in event_turns) else item_turns
    return _dedupe_turns(turns)


def _dedupe_turns(turns: List[Turn]) -> List[Turn]:
    out: List[Turn] = []
    for turn in turns:
        text = turn.text.strip()
        if not text:
            continue
        if out and out[-1].role == turn.role and out[-1].text == text:
            continue
        out.append(Turn(turn.role, text, turn.ts))
    return out


def claude_user_texts(path: Path) -> List[str]:
    if not path.is_file():
        return []
    texts: List[str] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "user" or obj.get("isMeta"):
                continue
            message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
            text = norm_text(content_text(message.get("content")))
            if text:
                texts.append(text)
    return texts


def import_source_path(import_rec: dict) -> Path:
    return Path(str(import_rec.get("source_path") or ""))


def claude_cli_id_from_import(import_rec: dict) -> str:
    return import_source_path(import_rec).stem


def is_continued_on_codex(session: CodexSession, import_rec: dict) -> bool:
    imported_at = parse_ts(import_rec.get("imported_at"))
    if imported_at is None:
        return False
    cutoff = imported_at + FORK_SLACK
    claude_texts = {
        norm_text(t)[:200] for t in claude_user_texts(import_source_path(import_rec))
    }
    for turn in session.turns:
        if turn.role != "user" or turn.ts <= cutoff:
            continue
        if norm_text(turn.text)[:200] not in claude_texts:
            return True
    return False


def claude_updated_since_import(import_rec: dict) -> bool:
    """True when Claude gained substantive user turns after Codex imported it.

    Turns we previously merged/exported (entrypoint=codex-export) do not count as
    Claude-side evolution, otherwise a merge would look like a fork on the next run.
    """
    source = import_source_path(import_rec)
    imported_at = parse_ts(import_rec.get("imported_at"))
    if imported_at is None or not source.is_file():
        return True
    cutoff = imported_at + FORK_SLACK
    with source.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "user" or obj.get("isMeta"):
                continue
            if obj.get("entrypoint") == ENTRYPOINT:
                continue
            ts = parse_ts(obj.get("timestamp"))
            if ts is None or ts <= cutoff:
                continue
            message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
            if norm_text(content_text(message.get("content"))):
                return True
    return False


def codex_continuation_turns(
    session: CodexSession, import_rec: dict
) -> List[Turn]:
    """Codex user/assistant turns not already present in the Claude import."""
    source = import_source_path(import_rec)
    claude_users = {
        norm_text(t)[:200] for t in claude_user_texts(source)
    }
    cutoff = (parse_ts(import_rec.get("imported_at")) or session.created) + FORK_SLACK
    out: List[Turn] = []
    i = 0
    while i < len(session.turns):
        turn = session.turns[i]
        if turn.role == "user":
            key = norm_text(turn.text)[:200]
            if turn.ts > cutoff and key not in claude_users:
                out.append(turn)
                j = i + 1
                while j < len(session.turns) and session.turns[j].role == "assistant":
                    out.append(session.turns[j])
                    j += 1
                i = j
                continue
        i += 1
    return out


def title_from_session(session: CodexSession, import_rec: Optional[dict], kind: str) -> str:
    raw = ""
    if import_rec and import_rec.get("title"):
        raw = str(import_rec["title"]).strip()
    if not raw:
        for turn in session.turns:
            if turn.role == "user":
                raw = norm_text(turn.text)
                break
    if not raw:
        raw = session.thread_id
    raw = raw[:80]
    if kind == "fork" and not raw.lower().startswith("[codex"):
        raw = f"{raw} (codex fork)"
    if raw.startswith(TITLE_PREFIX.strip()):
        return raw
    return TITLE_PREFIX + raw


def classify(
    session: CodexSession, import_by_id: Dict[str, dict]
) -> Tuple[str, Optional[dict]]:
    if session.thread_source == "subagent":
        return "skip-subagent", None
    import_rec = import_by_id.get(session.thread_id)
    if import_rec is not None:
        if not is_continued_on_codex(session, import_rec):
            return "skip-import", import_rec
        if claude_updated_since_import(import_rec):
            return "fork", import_rec
        return "merge", import_rec
    if session.thread_source == "user":
        if not any(t.role == "user" for t in session.turns):
            return "skip-empty", None
        return "native", None
    return "skip-other", None


def iter_codex_sessions(root: Path) -> Iterator[CodexSession]:
    if not root.is_dir():
        logging.warning("codex sessions dir missing: %s", root)
        return
    for path in sorted(root.rglob("rollout-*.jsonl")):
        try:
            st = path.stat()
            meta = first_session_meta(path)
        except OSError as e:
            logging.warning("skip %s: %s", path, e)
            continue
        if not meta:
            continue
        thread_id = str(meta.get("id") or meta.get("session_id") or "")
        cwd = str(meta.get("cwd") or str(HOME))
        if not thread_id:
            continue
        created = parse_ts(meta.get("timestamp")) or datetime.fromtimestamp(
            st.st_mtime, tz=timezone.utc
        )
        thread_source = meta.get("thread_source")
        if thread_source == "subagent":
            yield CodexSession(
                path=path,
                thread_id=thread_id,
                cwd=cwd,
                thread_source=thread_source,
                originator=meta.get("originator"),
                created=created,
                mtime_ns=st.st_mtime_ns,
                sha256="",
                turns=[],
            )
            continue
        try:
            turns = extract_turns(path)
            digest = sha256_file(path)
        except OSError as e:
            logging.warning("skip %s: %s", path, e)
            continue
        yield CodexSession(
            path=path,
            thread_id=thread_id,
            cwd=cwd,
            thread_source=thread_source,
            originator=meta.get("originator"),
            created=created,
            mtime_ns=st.st_mtime_ns,
            sha256=digest,
            turns=turns,
        )


def build_jsonl(session: CodexSession, cli_id: str, title: str) -> str:
    cwd = session.cwd
    records: List[dict] = [
        {"type": "ai-title", "aiTitle": title, "sessionId": cli_id},
    ]
    parent: Optional[str] = None
    last_uuid = ""
    for i, turn in enumerate(session.turns):
        msg_id = message_uuid(session.thread_id, i)
        last_uuid = msg_id
        ts = iso_z(turn.ts)
        if turn.role == "user":
            message: dict = {"role": "user", "content": turn.text}
        else:
            message = {
                "role": "assistant",
                "content": [{"type": "text", "text": turn.text}],
            }
        rec = {
            "parentUuid": parent,
            "isSidechain": False,
            "type": turn.role,
            "message": message,
            "uuid": msg_id,
            "timestamp": ts,
            "userType": "external",
            "entrypoint": ENTRYPOINT,
            "cwd": cwd,
            "sessionId": cli_id,
            "version": CLAUDE_VERSION,
        }
        records.append(rec)
        parent = msg_id
    if last_uuid:
        records.append(
            {"type": "last-prompt", "leafUuid": last_uuid, "sessionId": cli_id}
        )
    return "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records)


def find_session_indexes(index_roots: Iterable[Path], cli_id: str) -> List[Path]:
    """Locate Desktop indexes for a CLI transcript id.

    Native Claude chats are stored as local_<sessionId>.json with cliSessionId
    equal to the jsonl stem. Exports use local_<cliId>.json. Search both.
    """
    index_name = f"local_{cli_id}.json"
    found: List[Path] = []
    seen: set[str] = set()
    for index_root in index_roots:
        for org in iter_org_dirs(index_root):
            by_name = org / index_name
            candidates = [by_name] if by_name.is_file() else []
            try:
                extra = list(org.glob("local_*.json"))
            except OSError as e:
                logging.warning("skip unreadable %s: %s", org, e)
                extra = []
            for candidate in candidates + extra:
                if not candidate.is_file():
                    continue
                key = str(candidate)
                if key in seen:
                    continue
                if candidate.name == index_name:
                    seen.add(key)
                    found.append(candidate)
                    continue
                data = load_json(candidate, {})
                if isinstance(data, dict) and str(data.get("cliSessionId") or "") == cli_id:
                    seen.add(key)
                    found.append(candidate)
    return found


def find_session_index(index_root: Path, cli_id: str) -> Optional[Path]:
    found = find_session_indexes((index_root,), cli_id)
    return found[0] if found else None


def read_transcript_lines(path: Path) -> List[dict]:
    records: List[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                records.append(obj)
    return records


def last_message_uuid(records: List[dict]) -> Tuple[Optional[str], Optional[dict]]:
    for obj in reversed(records):
        if obj.get("type") in ("user", "assistant", "system") and obj.get("uuid"):
            return str(obj["uuid"]), obj
    return None, None


def build_turn_record(
    turn: Turn,
    msg_id: str,
    parent: Optional[str],
    cli_id: str,
    cwd: str,
    template: Optional[dict],
) -> dict:
    if turn.role == "user":
        message: dict = {"role": "user", "content": turn.text}
    else:
        message = {
            "role": "assistant",
            "content": [{"type": "text", "text": turn.text}],
        }
    rec = {
        "parentUuid": parent,
        "isSidechain": False,
        "type": turn.role,
        "message": message,
        "uuid": msg_id,
        "timestamp": iso_z(turn.ts),
        "userType": "external",
        "entrypoint": ENTRYPOINT,
        "cwd": cwd,
        "sessionId": cli_id,
        "version": CLAUDE_VERSION,
    }
    if template:
        for key in ("gitBranch", "promptId", "effort"):
            if key in template:
                rec[key] = template[key]
    return rec


def remove_stale_fork_export(
    previous: Optional[dict],
    merge_dest: Path,
    dry_run: bool,
    projects_roots: tuple[Path, ...] = (DEFAULT_CLAUDE_PROJECTS,),
    index_roots: tuple[Path, ...] = (DEFAULT_CLAUDE_INDEX_ROOT,),
) -> None:
    if not previous or previous.get("kind") != "fork":
        return
    stale_jsonl = Path(str(previous.get("dest_path") or ""))
    stale_name = stale_jsonl.name
    stale_cli_id = stale_jsonl.stem
    stale_index_name = f"local_{stale_cli_id}.json"
    try:
        same = stale_jsonl.resolve() == merge_dest.resolve()
    except OSError:
        same = stale_jsonl == merge_dest
    if stale_name:
        for root in projects_roots:
            candidate = root / stale_jsonl.parent.name / stale_name
            if candidate.is_file() and not same:
                logging.info("REMOVE stale fork transcript %s", candidate)
                if not dry_run:
                    candidate.unlink()
        if stale_jsonl.is_file() and not same:
            logging.info("REMOVE stale fork transcript %s", stale_jsonl)
            if not dry_run:
                stale_jsonl.unlink()
    for index_root in index_roots:
        for org in iter_org_dirs(index_root):
            candidate = org / stale_index_name
            if candidate.is_file():
                logging.info("REMOVE stale fork index %s", candidate)
                if not dry_run:
                    candidate.unlink()
    stale_index = Path(str(previous.get("dest_index") or ""))
    if stale_index.is_file():
        logging.info("REMOVE stale fork index %s", stale_index)
        if not dry_run:
            stale_index.unlink()


def write_merge(
    session: CodexSession,
    import_rec: dict,
    index_roots: Iterable[Path],
    dry_run: bool,
    previous: Optional[dict],
    projects_roots: tuple[Path, ...] = (DEFAULT_CLAUDE_PROJECTS,),
) -> Tuple[str, Path, Optional[Path], str, int]:
    source = import_source_path(import_rec)
    if not source.is_file():
        raise RuntimeError(f"merge target missing: {source}")
    cli_id = claude_cli_id_from_import(import_rec)
    turns = codex_continuation_turns(session, import_rec)
    if not turns:
        raise RuntimeError(f"merge requested but no Codex continuation turns for {session.thread_id}")
    title = str(import_rec.get("title") or session.thread_id).strip()
    index_paths = find_session_indexes(index_roots, cli_id)
    index_path = index_paths[0] if index_paths else None
    if dry_run:
        logging.info(
            "DRY merge %s -> %s (%d appended turns) indexes=%d title=%s",
            session.thread_id,
            source,
            len(turns),
            len(index_paths),
            title,
        )
        remove_stale_fork_export(
            previous,
            source,
            dry_run=True,
            projects_roots=projects_roots,
            index_roots=tuple(index_roots),
        )
        return title, source, index_path, "", len(turns)

    records = read_transcript_lines(source)
    records = [r for r in records if r.get("type") != "last-prompt"]
    parent, template = last_message_uuid(records)
    cwd = str(template.get("cwd") if template else session.cwd)
    start_index = len(records)
    for offset, turn in enumerate(turns):
        msg_id = message_uuid(session.thread_id, start_index + offset)
        records.append(
            build_turn_record(turn, msg_id, parent, cli_id, cwd, template)
        )
        parent = msg_id
    if parent:
        records.append({"type": "last-prompt", "leafUuid": parent, "sessionId": cli_id})
    text = "".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
        for r in records
    )
    atomic_write_text(source, text)
    activity_ms = epoch_ms(turns[-1].ts)
    for path in index_paths:
        index = load_json(path, {})
        if isinstance(index, dict):
            index["lastActivityAt"] = activity_ms
            atomic_write_text(
                path,
                json.dumps(index, ensure_ascii=False, separators=(",", ":")),
            )
            logging.info("UPDATE merge index %s lastActivityAt=%s", path, activity_ms)
    if not index_paths:
        logging.warning("merge index missing for cliSessionId=%s", cli_id)
    remove_stale_fork_export(
        previous,
        source,
        dry_run=False,
        projects_roots=projects_roots,
        index_roots=tuple(index_roots),
    )
    dest_sha = sha256_file(source)
    logging.info(
        "MERGE %s -> %s appended=%d title=%s",
        session.thread_id,
        source,
        len(turns),
        title,
    )
    return title, source, index_path, dest_sha, len(turns)


def build_index(
    session: CodexSession, cli_id: str, index_id: str, title: str
) -> dict:
    first_ts = session.turns[0].ts if session.turns else session.created
    last_ts = session.turns[-1].ts if session.turns else session.created
    return {
        "sessionId": index_id,
        "cliSessionId": cli_id,
        "cwd": session.cwd,
        "originCwd": session.cwd,
        "createdAt": epoch_ms(first_ts),
        "lastActivityAt": epoch_ms(last_ts),
        "isArchived": False,
        "permissionMode": "default",
        "title": title,
        "titleSource": "imported",
        "alwaysAllowedReasons": [],
        "sessionPermissionUpdates": [],
    }


def transcript_entrypoint(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i > 40:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and obj.get("entrypoint"):
                    return str(obj["entrypoint"])
    except OSError:
        return None
    return None


def forbidden_dest(dest: Path, import_rec: Optional[dict]) -> bool:
    if not import_rec:
        return False
    source = import_rec.get("source_path")
    if not source:
        return False
    try:
        return dest.resolve() == Path(str(source)).resolve()
    except OSError:
        return dest == Path(str(source))


def dest_was_edited(dest: Path, previous: Optional[dict]) -> bool:
    if previous is None or not dest.is_file():
        return False
    prev_dest = previous.get("dest_path")
    if prev_dest:
        try:
            if dest.resolve() != Path(str(prev_dest)).resolve():
                return False
        except OSError:
            if dest != Path(str(prev_dest)):
                return False
    old = previous.get("dest_sha256")
    if not old:
        return False
    return sha256_file(dest) != old


def write_export(
    session: CodexSession,
    kind: str,
    import_rec: Optional[dict],
    projects_root: Path,
    org_dir: Path,
    dry_run: bool,
) -> Tuple[str, Path, Path, str]:
    cli_id, index_id = claude_ids(session.thread_id)
    title = title_from_session(session, import_rec, kind)
    jsonl_path = projects_root / project_slug(session.cwd) / f"{cli_id}.jsonl"
    index_path = org_dir / f"{index_id}.json"
    if forbidden_dest(jsonl_path, import_rec):
        raise RuntimeError(f"refusing to overwrite Claude import source {jsonl_path}")
    existing_ep = transcript_entrypoint(jsonl_path)
    if existing_ep and existing_ep != ENTRYPOINT:
        raise RuntimeError(
            f"refusing to overwrite non-export transcript {jsonl_path} entrypoint={existing_ep}"
        )
    jsonl = build_jsonl(session, cli_id, title)
    index = build_index(session, cli_id, index_id, title)
    if dry_run:
        logging.info(
            "DRY %s %s -> %s (%d turns) title=%s",
            kind,
            session.thread_id,
            jsonl_path,
            len(session.turns),
            title,
        )
        return title, jsonl_path, index_path, ""
    atomic_write_text(jsonl_path, jsonl)
    atomic_write_text(
        index_path, json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    )
    dest_sha = sha256_file(jsonl_path)
    logging.info(
        "EXPORT %s %s -> %s turns=%d title=%s",
        kind,
        session.thread_id,
        jsonl_path,
        len(session.turns),
        title,
    )
    return title, jsonl_path, index_path, dest_sha


def acquire_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "w", encoding="utf-8")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EAGAIN):
            fh.close()
            raise SystemExit("another export is already running") from e
        raise
    fh.write(str(os.getpid()))
    fh.flush()
    return fh


def setup_logging(log_path: Path, verbose: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
        force=True,
    )


def main(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--log", type=Path, default=DEFAULT_LOG)
    p.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    p.add_argument("--codex-sessions", type=Path, default=DEFAULT_CODEX_SESSIONS)
    p.add_argument("--import-ledger", type=Path, default=DEFAULT_IMPORT_LEDGER)
    p.add_argument("--projects", type=Path, default=DEFAULT_CLAUDE_PROJECTS)
    p.add_argument(
        "--extra-projects",
        type=Path,
        action="append",
        default=[],
        help="Additional Claude projects roots (repeatable). Not used unless passed.",
    )
    p.add_argument("--index-root", type=Path, default=DEFAULT_CLAUDE_INDEX_ROOT)
    p.add_argument(
        "--extra-index-root",
        type=Path,
        action="append",
        default=[],
        help="Additional Claude session-index roots (repeatable). Not used unless passed.",
    )
    p.add_argument("--export-ledger", type=Path, default=DEFAULT_EXPORT_LEDGER)
    p.add_argument("--skip-native", action="store_true")
    p.add_argument("--skip-merges", action="store_true")
    p.add_argument("--skip-forks", action="store_true")
    p.add_argument(
        "--since",
        help="Optional ISO date; only export continuations whose extra Codex turns start on/after this instant.",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    since: Optional[datetime] = None
    if args.since:
        since = parse_ts(args.since)
        if since is None:
            p.error(f"invalid --since {args.since!r}")

    setup_logging(args.log, args.verbose)
    lock_fh = acquire_lock(args.lock)
    t0 = time.time()
    exported = skipped = failed = 0
    try:
        import_by_id = load_import_ledger(args.import_ledger.expanduser())
        export_by_id = load_export_ledger(args.export_ledger.expanduser())
        org_dir = pick_org_dir(args.index_root.expanduser())
        projects_root = args.projects.expanduser()
        extra_projects = tuple(p.expanduser() for p in args.extra_projects)
        extra_index_roots = tuple(p.expanduser() for p in args.extra_index_root)
        projects_roots = (projects_root, *extra_projects)
        index_roots = (args.index_root.expanduser(), *extra_index_roots)
        logging.info(
            "export start dry_run=%s org=%s projects=%s extra_projects=%s extra_index=%s imports=%d",
            args.dry_run,
            org_dir,
            projects_root,
            extra_projects,
            extra_index_roots,
            len(import_by_id),
        )

        for session in iter_codex_sessions(args.codex_sessions.expanduser()):
            kind, import_rec = classify(session, import_by_id)
            if kind == "native" and args.skip_native:
                skipped += 1
                continue
            if kind == "fork" and args.skip_forks:
                skipped += 1
                continue
            if kind == "merge" and args.skip_merges:
                skipped += 1
                continue
            if kind.startswith("skip-"):
                skipped += 1
                logging.debug("SKIP %s %s", kind, session.thread_id)
                continue
            if kind in ("fork", "merge") and since is not None:
                extra_ts = [
                    t.ts
                    for t in codex_continuation_turns(session, import_rec or {})
                    if t.role == "user"
                ]
                if extra_ts and min(extra_ts) < since:
                    skipped += 1
                    logging.info(
                        "SKIP %s-before-since %s title=%s",
                        kind,
                        session.thread_id,
                        (import_rec or {}).get("title"),
                    )
                    continue

            previous = export_by_id.get(session.thread_id)
            if (
                previous
                and previous.get("source_sha256") == session.sha256
                and previous.get("kind") == kind
            ):
                skipped += 1
                continue

            try:
                if kind == "merge":
                    assert import_rec is not None
                    merge_dest = import_source_path(import_rec)
                    if dest_was_edited(merge_dest, previous):
                        skipped += 1
                        logging.warning(
                            "SKIP claude-diverged %s dest=%s (will not overwrite)",
                            session.thread_id,
                            merge_dest,
                        )
                        continue
                    title, jsonl_path, index_path, dest_sha, appended = write_merge(
                        session,
                        import_rec,
                        index_roots,
                        args.dry_run,
                        previous,
                        projects_roots=projects_roots,
                    )
                    cli_id = claude_cli_id_from_import(import_rec)
                    index_id = f"local_{cli_id}"
                else:
                    cli_id, index_id = claude_ids(session.thread_id)
                    dest = projects_root / project_slug(session.cwd) / f"{cli_id}.jsonl"
                    if dest_was_edited(dest, previous):
                        skipped += 1
                        logging.warning(
                            "SKIP claude-diverged %s dest=%s (will not overwrite)",
                            session.thread_id,
                            dest,
                        )
                        continue
                    title, jsonl_path, index_path, dest_sha = write_export(
                        session,
                        kind,
                        import_rec,
                        projects_root,
                        org_dir,
                        args.dry_run,
                    )
                    appended = len(session.turns)
            except Exception:
                failed += 1
                logging.exception("export failed %s", session.thread_id)
                continue
            exported += 1
            if args.dry_run:
                continue
            export_by_id[session.thread_id] = {
                "codex_session_id": session.thread_id,
                "kind": kind,
                "claude_cli_session_id": cli_id,
                "claude_index_id": index_id,
                "source_path": str(session.path),
                "source_sha256": session.sha256,
                "source_mtime_ns": session.mtime_ns,
                "dest_path": str(jsonl_path),
                "dest_index": str(index_path) if index_path else "",
                "dest_sha256": dest_sha,
                "imported_from_claude": (import_rec or {}).get("source_path"),
                "title": title,
                "appended_turns": appended,
                "exported_at": iso_z(datetime.now(timezone.utc)),
            }

        if not args.dry_run:
            save_export_ledger(args.export_ledger.expanduser(), export_by_id)
        logging.info(
            "export done wrote=%d unchanged=%d failed=%d elapsed=%.2fs",
            exported,
            skipped,
            failed,
            time.time() - t0,
        )
        return 1 if failed else 0
    except Exception:
        logging.exception("export failed")
        return 1
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fh.close()


if __name__ == "__main__":
    raise SystemExit(main())
