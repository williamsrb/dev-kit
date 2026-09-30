#!/usr/bin/env python3
"""Export native Cursor Agent parent chats into Claude Desktop.

Cursor already imports Claude Code sessions into its sidebar. This is the
reverse, one-way:

  ~/.cursor/projects/<slug>/agent-transcripts/<id>/<id>.jsonl
    -> ~/.claude/projects/<slug>/<cliSessionId>.jsonl
    -> ~/.config/Claude/claude-code-sessions/<account>/<org>/local_<id>.json

Rules:
  - Parent JSONL only (skip subagents/ paths and composerHeaders.isSubagent=1).
  - Drafts (isDraft=true) are skipped.
  - Text turns only (user prompts + assistant text). No tool replay.
  - Destinations use UUID5 of the Cursor composer id with entrypoint
    cursor-export. Do not reuse the raw composer UUID.
  - JSONL cwd is the real workspace folder (same as Codex). Cursor may list
    the export next to the native composer; that echo is bounded by skip-echo
    unless the composer is already in the export ledger, the Cursor title
    starts with "[cursor]" and no other Claude session has that dest title,
    or --force --composer-id is set. "[codex]" and "Claude Code session"
    stay skip-only. Registry association alone is not a hard skip.

This script must not write ~/.agents/history/*_prompt.md or *_result.md.
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
import sqlite3
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple

HOME = Path.home()
DEFAULT_CURSOR_PROJECTS = HOME / ".cursor" / "projects"
DEFAULT_STATE_DB = HOME / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
DEFAULT_WORKSPACE_STORAGE = HOME / ".config" / "Cursor" / "User" / "workspaceStorage"
DEFAULT_CLAUDE_PROJECTS = HOME / ".claude" / "projects"
DEFAULT_CLAUDE_INDEX_ROOT = HOME / ".config" / "Claude" / "claude-code-sessions"
DEFAULT_STATE_DIR = HOME / ".local" / "share" / "cursor-to-claude-sync"
DEFAULT_EXPORT_LEDGER = DEFAULT_STATE_DIR / "exports.json"
DEFAULT_LOCK = DEFAULT_STATE_DIR / "export.lock"
DEFAULT_LOG = DEFAULT_STATE_DIR / "export.log"

UUID_NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://agents.local/cursor-to-claude")
ENTRYPOINT = "cursor-export"
CLAUDE_VERSION = "2.1.229"
TITLE_PREFIX = "[cursor] "
FORCE_TITLE_PREFIX = "[cursor]"
ISOLATED_CWD_SUFFIX = "/.cursor-export"
ECHO_TITLE_PREFIXES = ("[codex]",)
ECHO_GENERIC_TITLES = frozenset({"Claude Code session"})
CLAUDE_SESSION_REGISTRY_KEY = "glass.claudeCodeSessionRegistry.v1"
SKIP_USER_PREFIXES = (
    "Briefly inform the user about the task result",
    "<recommended_plugins>",
    "# AGENTS.md",
    "<skills_instructions>",
    "<environment_context>",
    "<INSTRUCTIONS>",
    "<in-app-browser-context",
    "<manually_attached_skills>",
    "<agent_skills>",
    "<always_applied_workspace_rules>",
    "<user_info>",
    "<user_rules>",
    "<agent_requestable_workspace_rules>",
    "<dynamic_tools>",
)
TIMESTAMP_RE = re.compile(r"<timestamp>(.*?)</timestamp>", re.DOTALL)
USER_QUERY_RE = re.compile(r"<user_query>(.*?)</user_query>", re.DOTALL)
TIMESTAMP_INNER_RE = re.compile(
    r"^(.*?)\s*\(UTC([+-]\d{1,2})(?::(\d{2}))?\)$"
)
TIMESTAMP_DATE_RE = re.compile(
    r"^[A-Za-z]+, ([A-Za-z]+) (\d{1,2}), (\d{4}), (\d{1,2}):(\d{2}) (AM|PM)$"
)
MONTHS = {
    name: i
    for i, name in enumerate(
        (
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ),
        1,
    )
}


@dataclass
class Turn:
    role: str
    text: str
    ts: datetime


@dataclass
class CursorSession:
    path: Path
    composer_id: str
    cwd: str
    created: datetime
    mtime_ns: int
    sha256: str
    title_hint: str = ""
    is_subagent: bool = False
    is_draft: bool = False
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


def claude_ids(composer_id: str) -> Tuple[str, str]:
    cli = str(uuid.uuid5(UUID_NS, f"cursor:{composer_id}"))
    return cli, f"local_{cli}"


def message_uuid(composer_id: str, index: int) -> str:
    return str(uuid.uuid5(UUID_NS, f"cursor:{composer_id}:msg:{index}"))


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
            logging.warning("skip unreadable %s: %s", account, e)


def pick_org_dir(root: Path) -> Path:
    orgs = list(iter_org_dirs(root))
    if not orgs:
        raise SystemExit(f"no Claude account/org directories under {root}")
    return max(orgs, key=lambda org: sum(1 for _ in org.glob("local_*.json")))


def load_export_ledger(path: Path) -> Dict[str, dict]:
    data = load_json(path, {})
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        return {}
    out: Dict[str, dict] = {}
    for rec in records:
        if isinstance(rec, dict) and rec.get("cursor_composer_id"):
            out[str(rec["cursor_composer_id"])] = rec
    return out


def save_export_ledger(path: Path, records: Dict[str, dict]) -> None:
    payload = {
        "updated_at": iso_z(datetime.now(timezone.utc)),
        "records": [records[k] for k in sorted(records)],
    }
    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: List[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") and item.get("type") != "text":
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text)
    return "\n".join(parts)


def parse_cursor_timestamp(blob: str, fallback: datetime) -> datetime:
    match = TIMESTAMP_RE.search(blob or "")
    if not match:
        return fallback
    inner = match.group(1).strip()
    um = TIMESTAMP_INNER_RE.match(inner)
    if not um:
        parsed = parse_ts(inner)
        return parsed or fallback
    dm = TIMESTAMP_DATE_RE.match(um.group(1).strip())
    if not dm:
        return fallback
    month = MONTHS.get(dm.group(1)[:3])
    if month is None:
        return fallback
    hour = int(dm.group(4))
    ampm = dm.group(6)
    if ampm == "PM" and hour != 12:
        hour += 12
    elif ampm == "AM" and hour == 12:
        hour = 0
    offset_hours = int(um.group(2))
    offset_minutes = int(um.group(3) or 0)
    if offset_hours < 0:
        offset_minutes = -offset_minutes
    tz = timezone(timedelta(hours=offset_hours, minutes=offset_minutes))
    try:
        return datetime(
            int(dm.group(3)),
            month,
            int(dm.group(2)),
            hour,
            int(dm.group(5)),
            tzinfo=tz,
        )
    except ValueError:
        return fallback


def extract_user_text(raw: str) -> str:
    match = USER_QUERY_RE.search(raw or "")
    if match:
        return match.group(1).strip()
    stripped = TIMESTAMP_RE.sub("", raw or "").strip()
    return stripped


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


def extract_turns(path: Path, fallback_ts: datetime) -> List[Turn]:
    turns: List[Turn] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get("type") == "turn_ended":
                continue
            role = obj.get("role")
            if role not in ("user", "assistant"):
                continue
            message = obj.get("message") if isinstance(obj.get("message"), dict) else {}
            raw = content_text(message.get("content"))
            if not raw.strip():
                continue
            ts = parse_cursor_timestamp(raw, fallback_ts)
            if role == "user":
                text = extract_user_text(raw)
                if not text or is_injected_user_text(text):
                    continue
            else:
                text = raw.strip()
                if not text:
                    continue
            turns.append(Turn(role, text, ts))
    return _dedupe_turns(turns)


def folder_from_uri(uri: str) -> str:
    text = (uri or "").strip()
    if text.startswith("file://"):
        text = text[7:]
    return text.rstrip("/")


def cursor_project_slug(folder: str) -> str:
    path = folder_from_uri(folder).lstrip("/")
    return path.replace(".", "").replace("/", "-")


def load_workspace_folders(storage_root: Path) -> Dict[str, str]:
    """Map Cursor project slug -> workspace folder path."""
    out: Dict[str, str] = {}
    if not storage_root.is_dir():
        return out
    try:
        entries = list(storage_root.iterdir())
    except OSError as e:
        logging.warning("skip unreadable %s: %s", storage_root, e)
        return out
    for entry in entries:
        data = load_json(entry / "workspace.json", {})
        if not isinstance(data, dict):
            continue
        folder = folder_from_uri(str(data.get("folder") or ""))
        if not folder:
            continue
        slug = cursor_project_slug(folder)
        if slug:
            out[slug] = folder
    return out


def load_composer_headers(db_path: Path) -> Dict[str, dict]:
    if not db_path.is_file():
        logging.warning("composerHeaders db missing: %s", db_path)
        return {}
    uri = f"file:{db_path}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=1)
    except sqlite3.Error as e:
        logging.warning("composerHeaders unavailable: %s", e)
        return {}
    con.row_factory = sqlite3.Row
    out: Dict[str, dict] = {}
    try:
        rows = con.execute(
            "SELECT composerId, workspaceId, createdAt, isSubagent, value "
            "FROM composerHeaders"
        )
        for row in rows:
            composer_id = str(row["composerId"] or "")
            if not composer_id:
                continue
            try:
                value = json.loads(row["value"] or "{}")
            except (TypeError, json.JSONDecodeError):
                value = {}
            if not isinstance(value, dict):
                value = {}
            out[composer_id] = {
                "workspaceId": row["workspaceId"],
                "createdAt": row["createdAt"],
                "isSubagent": int(row["isSubagent"] or 0),
                "value": value,
            }
    except sqlite3.Error as e:
        logging.warning("composerHeaders query failed: %s", e)
        return {}
    finally:
        con.close()
    return out


def load_associated_composer_ids(db_path: Path) -> Set[str]:
    if not db_path.is_file():
        logging.warning("claude session registry db missing: %s", db_path)
        return set()
    uri = f"file:{db_path}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=1)
    except sqlite3.Error as e:
        logging.warning("claude session registry unavailable: %s", e)
        return set()
    try:
        row = con.execute(
            "SELECT value FROM ItemTable WHERE key=?",
            (CLAUDE_SESSION_REGISTRY_KEY,),
        ).fetchone()
    except sqlite3.Error as e:
        logging.warning("claude session registry query failed: %s", e)
        return set()
    finally:
        con.close()
    if not row or not row[0]:
        return set()
    try:
        data = json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as e:
        logging.warning("claude session registry unreadable: %s", e)
        return set()
    associations = data.get("composerAssociations") if isinstance(data, dict) else None
    if not isinstance(associations, dict):
        return set()
    out: Set[str] = set()
    for items in associations.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            composer_id = str(item.get("localComposerId") or "").strip()
            if composer_id:
                out.add(composer_id)
    return out


def header_cwd(header: Optional[dict], slug: str, folders_by_slug: Dict[str, str]) -> str:
    if header:
        value = header.get("value") if isinstance(header.get("value"), dict) else {}
        repos = value.get("trackedGitRepos")
        if isinstance(repos, list) and repos:
            repo = repos[0]
            if isinstance(repo, dict):
                repo_path = str(repo.get("repoPath") or "").strip()
                if repo_path:
                    return repo_path
        ident = value.get("workspaceIdentifier")
        if isinstance(ident, dict):
            uri = ident.get("uri")
            if isinstance(uri, dict):
                fs_path = str(uri.get("fsPath") or "").strip()
                if fs_path:
                    return fs_path
            external = ""
            if isinstance(uri, dict):
                external = str(uri.get("external") or "")
            folder = folder_from_uri(external)
            if folder:
                return folder
    folder = folders_by_slug.get(slug)
    if folder:
        return folder
    return str(HOME)


def header_title(header: Optional[dict]) -> str:
    if not header:
        return ""
    value = header.get("value") if isinstance(header.get("value"), dict) else {}
    return str(value.get("name") or "").strip()


def cursor_slug_from_transcript(path: Path) -> str:
    try:
        idx = path.parts.index("projects")
        return path.parts[idx + 1]
    except (ValueError, IndexError):
        return path.parent.parent.parent.name


def iter_parent_jsonl(root: Path) -> Iterator[Path]:
    if not root.is_dir():
        logging.warning("cursor projects dir missing: %s", root)
        return
    try:
        paths = root.glob("*/agent-transcripts/*/*.jsonl")
    except OSError as e:
        logging.warning("skip unreadable %s: %s", root, e)
        return
    for path in sorted(paths):
        if "subagents" in path.parts:
            continue
        if path.parent.name != path.stem:
            continue
        yield path


def index_cli_id(data: dict) -> str:
    cli = str(data.get("cliSessionId") or "").strip()
    if cli:
        return cli
    sid = str(data.get("sessionId") or "").strip()
    if sid.startswith("local_"):
        return sid[len("local_") :]
    return sid


class ClaudeTitleIndex:
    """Dest titles already present on work Claude, keyed by CLI session id."""

    def __init__(self) -> None:
        self.by_title: Dict[str, Set[str]] = defaultdict(set)

    def add(self, title: str, cli_id: str) -> None:
        title = (title or "").strip()
        cli_id = (cli_id or "").strip()
        if title and cli_id:
            self.by_title[title].add(cli_id)

    def taken_by_other(self, title: str, own_cli_id: str) -> bool:
        owners = self.by_title.get((title or "").strip()) or set()
        own = (own_cli_id or "").strip()
        return any(sid != own for sid in owners)


def jsonl_ai_title(path: Path) -> Tuple[str, str]:
    """Return (title, sessionId) from the first ai-title record, else empty."""
    if not path.is_file():
        return "", ""
    try:
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i > 15:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                title = ""
                if obj.get("type") == "ai-title":
                    title = str(obj.get("aiTitle") or "").strip()
                elif obj.get("aiTitle"):
                    title = str(obj.get("aiTitle") or "").strip()
                if title:
                    return title, str(obj.get("sessionId") or "").strip()
    except OSError:
        return "", ""
    return "", ""


def load_claude_title_index(projects_root: Path, org_dir: Path) -> ClaudeTitleIndex:
    index = ClaudeTitleIndex()
    if org_dir.is_dir():
        try:
            paths = org_dir.glob("local_*.json")
        except OSError as e:
            logging.warning("skip unreadable %s: %s", org_dir, e)
            paths = []
        for path in paths:
            data = load_json(path, {})
            if not isinstance(data, dict):
                continue
            index.add(str(data.get("title") or ""), index_cli_id(data))
    if projects_root.is_dir():
        try:
            jsonl_paths = projects_root.glob("*/*.jsonl")
        except OSError as e:
            logging.warning("skip unreadable %s: %s", projects_root, e)
            jsonl_paths = []
        for path in jsonl_paths:
            title, sid = jsonl_ai_title(path)
            if not sid:
                sid = path.stem
            index.add(title, sid)
    return index


def ledger_owns(previous: Optional[dict]) -> bool:
    if not previous:
        return False
    return (
        previous.get("entrypoint") == ENTRYPOINT or previous.get("kind") == "native"
    )


def prefer_transcript(paths: List[Path], folders_by_slug: Dict[str, str]) -> Path:
    def score(path: Path) -> Tuple[int, int]:
        slug = cursor_slug_from_transcript(path)
        cwd = folders_by_slug.get(slug, "")
        real = 0
        if slug != "empty-window":
            real = 2 if cwd and Path(cwd).is_dir() else 1
        try:
            mtime = path.stat().st_mtime_ns
        except OSError:
            mtime = 0
        return (real, mtime)

    return max(paths, key=score)


def classify(
    session: CursorSession,
    associated_ids: Optional[Set[str]] = None,
    *,
    in_ledger: bool = False,
    title_index: Optional[ClaudeTitleIndex] = None,
    force: bool = False,
) -> str:
    if session.is_subagent:
        return "skip-subagent"
    if session.is_draft:
        return "skip-draft"
    if not any(t.role == "user" for t in session.turns):
        return "skip-empty"
    if in_ledger:
        return "native"
    hint = session.title_hint.strip()
    dest_title = title_from_session(session)
    want_force = force or hint.startswith(FORCE_TITLE_PREFIX)
    if want_force:
        own_cli, _ = claude_ids(session.composer_id)
        if title_index is not None and title_index.taken_by_other(dest_title, own_cli):
            return "skip-echo"
        return "native"
    if associated_ids and session.composer_id in associated_ids:
        return "skip-echo"
    if hint.startswith(ECHO_TITLE_PREFIXES):
        return "skip-echo"
    if hint in ECHO_GENERIC_TITLES:
        return "skip-echo"
    return "native"


def title_from_session(session: CursorSession) -> str:
    raw = session.title_hint.strip()
    if not raw:
        for turn in session.turns:
            if turn.role == "user":
                raw = norm_text(turn.text)
                break
    if not raw:
        raw = session.composer_id
    raw = raw[:80]
    if raw.startswith(TITLE_PREFIX.strip()):
        return raw
    return TITLE_PREFIX + raw


def iter_cursor_sessions(
    root: Path,
    headers: Dict[str, dict],
    folders_by_slug: Dict[str, str],
    composer_id: Optional[str] = None,
) -> Iterator[CursorSession]:
    grouped: Dict[str, List[Path]] = defaultdict(list)
    for path in iter_parent_jsonl(root):
        cid = path.stem
        if composer_id and cid != composer_id:
            continue
        grouped[cid].append(path)
    for cid, paths in sorted(grouped.items()):
        path = prefer_transcript(paths, folders_by_slug)
        header = headers.get(cid)
        slug = cursor_slug_from_transcript(path)
        try:
            st = path.stat()
        except OSError as e:
            logging.warning("skip %s: %s", path, e)
            continue
        created = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        is_subagent = False
        is_draft = False
        title_hint = ""
        if header:
            is_subagent = bool(header.get("isSubagent"))
            value = header.get("value") if isinstance(header.get("value"), dict) else {}
            is_draft = value.get("isDraft") is True
            title_hint = header_title(header)
            created = parse_ts(header.get("createdAt")) or created
        cwd = header_cwd(header, slug, folders_by_slug)
        if is_subagent:
            yield CursorSession(
                path=path,
                composer_id=cid,
                cwd=cwd,
                created=created,
                mtime_ns=st.st_mtime_ns,
                sha256="",
                title_hint=title_hint,
                is_subagent=True,
                is_draft=is_draft,
                turns=[],
            )
            continue
        try:
            turns = extract_turns(path, created)
            digest = sha256_file(path)
        except OSError as e:
            logging.warning("skip %s: %s", path, e)
            continue
        yield CursorSession(
            path=path,
            composer_id=cid,
            cwd=cwd,
            created=created,
            mtime_ns=st.st_mtime_ns,
            sha256=digest,
            title_hint=title_hint,
            is_subagent=False,
            is_draft=is_draft,
            turns=turns,
        )


def build_jsonl(session: CursorSession, cli_id: str, title: str) -> str:
    cwd = session.cwd
    records: List[dict] = [
        {"type": "ai-title", "aiTitle": title, "sessionId": cli_id},
    ]
    parent: Optional[str] = None
    last_uuid = ""
    for i, turn in enumerate(session.turns):
        msg_id = message_uuid(session.composer_id, i)
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
    return "".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records
    )


def build_index(
    session: CursorSession, cli_id: str, index_id: str, title: str
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


def jsonl_recorded_cwd(path: Path) -> Optional[str]:
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
                if isinstance(obj, dict) and obj.get("cwd"):
                    return str(obj["cwd"])
    except OSError:
        return None
    return None


def dest_has_isolated_cwd(dest: Path) -> bool:
    """True when a prior run wrote /.cursor-export into JSONL cwd."""
    if not dest.is_file():
        return False
    if transcript_entrypoint(dest) not in (None, ENTRYPOINT):
        return False
    cwd = jsonl_recorded_cwd(dest) or ""
    return cwd.endswith(ISOLATED_CWD_SUFFIX)


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


def existing_jsonl_stems(projects_root: Path) -> set[str]:
    stems: set[str] = set()
    if not projects_root.is_dir():
        return stems
    try:
        for path in projects_root.glob("*/*.jsonl"):
            stems.add(path.stem)
    except OSError as e:
        logging.warning("skip unreadable %s: %s", projects_root, e)
    return stems


def write_export(
    session: CursorSession,
    projects_root: Path,
    org_dir: Path,
    dry_run: bool,
    existing_stems: set[str],
) -> Tuple[str, Path, Path, str]:
    cli_id, index_id = claude_ids(session.composer_id)
    title = title_from_session(session)
    jsonl_path = projects_root / project_slug(session.cwd) / f"{cli_id}.jsonl"
    index_path = org_dir / f"{index_id}.json"
    existing_ep = transcript_entrypoint(jsonl_path)
    if existing_ep and existing_ep != ENTRYPOINT:
        raise RuntimeError(
            f"refusing to overwrite non-export transcript {jsonl_path} "
            f"entrypoint={existing_ep}"
        )
    if (
        not jsonl_path.is_file()
        and cli_id in existing_stems
    ):
        raise RuntimeError(
            f"refusing to collide with existing Claude stem {cli_id}"
        )
    jsonl = build_jsonl(session, cli_id, title)
    index = build_index(session, cli_id, index_id, title)
    if dry_run:
        logging.info(
            "DRY native %s -> %s (%d turns) title=%s",
            session.composer_id,
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
        "EXPORT native %s -> %s turns=%d title=%s",
        session.composer_id,
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
    p.add_argument("--cursor-projects", type=Path, default=DEFAULT_CURSOR_PROJECTS)
    p.add_argument("--state-db", type=Path, default=DEFAULT_STATE_DB)
    p.add_argument(
        "--workspace-storage", type=Path, default=DEFAULT_WORKSPACE_STORAGE
    )
    p.add_argument("--projects", type=Path, default=DEFAULT_CLAUDE_PROJECTS)
    p.add_argument("--index-root", type=Path, default=DEFAULT_CLAUDE_INDEX_ROOT)
    p.add_argument("--export-ledger", type=Path, default=DEFAULT_EXPORT_LEDGER)
    p.add_argument("--composer-id", help="Export a single Cursor composer id.")
    p.add_argument(
        "--force",
        action="store_true",
        help="Export --composer-id even if associated. Requires --composer-id.",
    )
    args = p.parse_args(list(argv) if argv is not None else None)
    if args.force and not args.composer_id:
        raise SystemExit("--force requires --composer-id")

    setup_logging(args.log, args.verbose)
    lock_fh = acquire_lock(args.lock)
    t0 = time.time()
    wrote = failed = 0
    skip_subagent = skip_draft = skip_empty = skip_ledger = skip_diverged = skip_echo = 0
    try:
        export_by_id = load_export_ledger(args.export_ledger.expanduser())
        org_dir = pick_org_dir(args.index_root.expanduser())
        projects_root = args.projects.expanduser()
        headers = load_composer_headers(args.state_db.expanduser())
        associated_ids = load_associated_composer_ids(args.state_db.expanduser())
        folders_by_slug = load_workspace_folders(args.workspace_storage.expanduser())
        existing_stems = existing_jsonl_stems(projects_root)
        title_index = load_claude_title_index(projects_root, org_dir)
        logging.info(
            "export start dry_run=%s force=%s org=%s projects=%s "
            "headers=%d associated=%d claude-titles=%d",
            args.dry_run,
            args.force,
            org_dir,
            projects_root,
            len(headers),
            len(associated_ids),
            len(title_index.by_title),
        )

        seen = False
        for session in iter_cursor_sessions(
            args.cursor_projects.expanduser(),
            headers,
            folders_by_slug,
            composer_id=args.composer_id,
        ):
            seen = True
            previous = export_by_id.get(session.composer_id)
            kind = classify(
                session,
                associated_ids,
                in_ledger=ledger_owns(previous),
                title_index=title_index,
                force=args.force,
            )
            if kind == "skip-subagent":
                skip_subagent += 1
                logging.debug("SKIP %s %s", kind, session.composer_id)
                continue
            if kind == "skip-draft":
                skip_draft += 1
                logging.debug("SKIP %s %s", kind, session.composer_id)
                continue
            if kind == "skip-empty":
                skip_empty += 1
                logging.debug("SKIP %s %s", kind, session.composer_id)
                continue
            if kind == "skip-echo":
                skip_echo += 1
                hint = session.title_hint.strip()
                if args.force or hint.startswith(FORCE_TITLE_PREFIX):
                    logging.info(
                        "SKIP skip-echo %s title=%r dest_title=%r "
                        "(Claude already has this title on another session)",
                        session.composer_id,
                        hint,
                        title_from_session(session),
                    )
                else:
                    logging.debug("SKIP %s %s", kind, session.composer_id)
                continue

            cli_id, index_id = claude_ids(session.composer_id)
            dest = projects_root / project_slug(session.cwd) / f"{cli_id}.jsonl"
            restore_cwd = dest_has_isolated_cwd(dest)
            if dest_was_edited(dest, previous) and not restore_cwd:
                skip_diverged += 1
                logging.warning(
                    "SKIP claude-diverged %s dest=%s (will not overwrite)",
                    session.composer_id,
                    dest,
                )
                continue
            if (
                previous
                and previous.get("source_sha256") == session.sha256
                and previous.get("kind") == kind
                and not restore_cwd
            ):
                skip_ledger += 1
                continue

            try:
                title, jsonl_path, index_path, dest_sha = write_export(
                    session,
                    projects_root,
                    org_dir,
                    args.dry_run,
                    existing_stems,
                )
            except Exception:
                failed += 1
                logging.exception("export failed %s", session.composer_id)
                continue
            wrote += 1
            title_index.add(title, cli_id)
            if args.dry_run:
                continue
            existing_stems.add(cli_id)
            export_by_id[session.composer_id] = {
                "cursor_composer_id": session.composer_id,
                "kind": kind,
                "claude_cli_session_id": cli_id,
                "claude_index_id": index_id,
                "source_path": str(session.path),
                "source_sha256": session.sha256,
                "source_mtime_ns": session.mtime_ns,
                "dest_path": str(jsonl_path),
                "dest_index": str(index_path) if index_path else "",
                "dest_sha256": dest_sha,
                "entrypoint": ENTRYPOINT,
                "title": title,
                "exported_at": iso_z(datetime.now(timezone.utc)),
            }

        if args.composer_id and not seen:
            logging.warning("no parent transcript for composer-id %s", args.composer_id)

        if not args.dry_run:
            save_export_ledger(args.export_ledger.expanduser(), export_by_id)
        logging.info(
            "export done wrote=%d skip-subagent=%d skip-draft=%d skip-empty=%d "
            "skip-echo=%d unchanged=%d claude-diverged=%d failed=%d elapsed=%.2fs",
            wrote,
            skip_subagent,
            skip_draft,
            skip_empty,
            skip_echo,
            skip_ledger,
            skip_diverged,
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
