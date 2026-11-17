"""agentctl harness: deterministic, read-only usage, bloat and drift scan.

Reads Claude transcripts, profile copies and factory events for a time window and
writes a versioned signals JSON plus a Markdown report under the output directory.
No model, Ollama or network call. Writes only under <output-dir>/signals and
<output-dir>/reports. Transcript text is never copied: only identifiers, counts and
timestamps leave this module.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import stat
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import agentctl_harness_measure
import agentctl_harness_proposals
import agentctl_harness_schedule
import agentctl_skills
from agentctl_common import agents_home, emit
from agentctl_disk import DiskError, parse_duration

SCHEMA_VERSION = 2
SEQUENCE_MIN_SESSIONS = 5
REPEAT_TOP = 25
DEFAULT_SINCE = "60d"
DEFAULT_TOP = 25
DEFAULT_MCP_SIZE = "measure"
ALL_SOURCES = ("claude", "profiles", "factory", "cursor", "codex")
DEFAULT_SOURCES = ("claude", "profiles", "factory")
MCP_SIZE_MODES = ("measure", "skip")
BLOAT_BYTES = 20 * 1024
BLOAT_DIRS = ("kb", "skills", "rules")
EXPORT_VENDORS = {"cursor-export": "cursor", "codex-export": "codex"}
PREFILTER = ('"tool_use"', "<command-name>", '"hookName"')
USAGE_TYPES = ("assistant", "user", "attachment")
COMMAND_RE = re.compile(r"<command-name>/?([^<]+)</command-name>")
HOOK_LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T[^\]]+)\]\s?(.*)$")
TS_FMT = "%Y-%m-%dT%H:%M:%S.000Z"
NOT_MEASURED = "not measured"
NOT_MEASURED_SKIPPED = "not measured (skipped by option)"
NEVER_READ = "never read in window"
NOT_COUNTED = [
    "Reads of a SKILL.md file are not skill use; only Skill tool calls and slash commands count.",
    "Per-hook-script call counts are not measured: transcripts record hookName events only.",
    "Mentions of a skill name in assistant or user prose are not counted.",
]


class HarnessError(Exception):
    """User-facing harness failure; main() prints it as JSON."""


# --- options and window ---------------------------------------------------

def parse_sources(value: str) -> tuple[str, ...]:
    picked = {part.strip().lower() for part in value.split(",") if part.strip()}
    if not picked:
        raise HarnessError(f"--sources: empty list; accepted: {','.join(ALL_SOURCES)}")
    unknown = sorted(picked - set(ALL_SOURCES))
    if unknown:
        raise HarnessError(f"--sources: unknown {','.join(unknown)}; accepted: {','.join(ALL_SOURCES)}")
    return tuple(name for name in ALL_SOURCES if name in picked)


def build_window(since_text: str, until_text: str | None, now: datetime) -> tuple[datetime, datetime, timedelta]:
    try:
        delta = parse_duration(since_text, "--since")
    except DiskError as exc:
        raise HarnessError(str(exc)) from None
    if delta <= timedelta(0):
        raise HarnessError("--since: must be a positive duration")
    if until_text is None:
        until = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            until = datetime.strptime(until_text, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            raise HarnessError(f"--until: cannot parse {until_text!r}; use YYYY-MM-DD") from None
    return until - delta, until, delta


def since_label(delta: timedelta) -> str:
    hours = int(delta.total_seconds() // 3600)
    return f"{hours // 24}d" if hours % 24 == 0 else f"{hours}h"


def norm_ts(text: str) -> str | None:
    """Return a timestamp in the fixed TS_FMT form, or None when it does not parse."""
    try:
        parsed = datetime.fromisoformat(text)
    except (AttributeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).strftime(TS_FMT)


# --- inventory ------------------------------------------------------------

def installed_skills(agents: Path) -> dict[str, list[str]]:
    """Installed skill name -> alias list, read from each SKILL.md frontmatter."""
    base = agents / "skills"
    found: dict[str, list[str]] = {}
    if not base.is_dir():
        return found
    for entry in sorted(base.iterdir()):
        skill = entry / "SKILL.md"
        if not skill.is_file() or agentctl_skills.is_alias_bound_symlink(entry):
            continue
        try:
            data = agentctl_skills.parse_frontmatter(skill)
        except (OSError, ValueError):
            continue
        name = data.get("name") or entry.name
        aliases = [a.strip().strip("'\"") for a in (data.get("aliases") or "").split(",")]
        found[name] = [a for a in aliases if a]
    return found


def alias_targets(installed: dict[str, list[str]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for name in sorted(installed):
        for alias in installed[name]:
            if alias not in installed:
                mapping.setdefault(alias, name)
    return mapping


def catalog_servers(agents: Path) -> list[str]:
    path = agents / "mcp" / "catalog.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HarnessError("mcp/catalog.json: unreadable or not JSON") from None
    servers = data.get("servers") if isinstance(data, dict) else None
    return sorted(servers) if isinstance(servers, dict) else []


def hook_inventory(agents: Path, home: Path) -> dict[str, Any]:
    hooks_dir = agents / "hooks"
    scripts = sorted(p.name for p in hooks_dir.iterdir() if p.is_file()) if hooks_dir.is_dir() else []
    settings = home / ".claude" / "settings.json"
    configured: dict[str, int] = {}
    status = "missing"
    if settings.is_file():
        status = "ok"
        try:
            data = json.loads(settings.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data, status = {}, "unreadable"
        if not isinstance(data, dict):
            data = {}
        for event, groups in sorted((data.get("hooks") or {}).items()):
            if isinstance(groups, list):
                configured[event] = sum(len(g.get("hooks") or []) for g in groups if isinstance(g, dict))
    return {"scripts": scripts, "configured_events": configured, "settings": status}


def bloat_candidates(agents: Path) -> list[dict[str, Any]]:
    """Markdown files over BLOAT_BYTES, found the way `find -size +20k` does (no symlinks)."""
    found: list[dict[str, Any]] = []
    for folder in BLOAT_DIRS:
        base = agents / folder
        if not base.is_dir():
            continue
        for dirpath, _dirs, files in os.walk(base):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                path = Path(dirpath) / fname
                try:
                    st = os.lstat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode) or st.st_size <= BLOAT_BYTES:
                    continue
                found.append({
                    "path": path.relative_to(agents).as_posix(),
                    "size": st.st_size,
                    "real": os.path.realpath(path),
                })
    return found


def rule_first_commit(agents: Path, rule: str, cache: dict[str, str | None]) -> str | None:
    if rule not in cache:
        try:
            out = subprocess.run(
                ["git", "-C", str(agents), "log", "--diff-filter=A", "--reverse", "--format=%cI", "--", rule],
                capture_output=True, text=True, timeout=60, check=False,
            )
            lines = [line for line in out.stdout.splitlines() if line.strip()]
            cache[rule] = lines[0][:10] if out.returncode == 0 and lines else None
        except (OSError, subprocess.SubprocessError):
            cache[rule] = None
    return cache[rule]


def load_checks(agents: Path) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    """Return (drift checks, builtin skill names) from harness/checks.json."""
    path = agents / "harness" / "checks.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HarnessError(f"{path}: missing or not JSON") from None
    checks = data.get("checks") if isinstance(data, dict) else None
    if not isinstance(checks, list):
        raise HarnessError(f"{path}: expected a 'checks' list")
    builtin = data.get("builtin_skills") or []
    if not isinstance(builtin, list):
        raise HarnessError(f"{path}: 'builtin_skills' must be a list")
    return [c for c in checks if isinstance(c, dict)], tuple(str(b) for b in builtin)


# --- transcript reader and collectors --------------------------------------

def _touch(table: dict[str, dict[str, Any]], key: str, vendor: str, ts: str, n: int = 1) -> None:
    row = table.get(key)
    if row is None:
        row = table[key] = {"count": 0, "vendors": Counter(), "first": ts, "last": ts, "raw": Counter()}
    row["count"] += n
    row["vendors"][vendor] += n
    row["first"] = min(row["first"], ts)
    row["last"] = max(row["last"], ts)


def _user_texts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b["text"] for b in content
                if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
    return []


class Transcripts:
    """Accumulates usage from transcript records. Every table is keyed by identifier."""

    def __init__(self, start: str, end: str, native_vendors: set[str], candidates: dict[str, dict[str, Any]]):
        self.start, self.end = start, end
        self.native_vendors = native_vendors
        self.candidates = candidates
        self.seen_uuid: set[str] = set()
        self.seen_tool: set[str] = set()
        self.tools: dict[str, dict[str, Any]] = {}
        self.skills: dict[str, dict[str, Any]] = {}
        self.hooks: dict[str, dict[str, Any]] = {}
        self.vendor_records: Counter = Counter()
        self.vendor_tools: Counter = Counter()
        self.skipped: Counter = Counter()
        self.ignored_types: Counter = Counter()
        self.duplicates = 0
        self.dropped_exports = 0
        self.bytes_read = 0
        self.files_read = 0
        self._realpaths: dict[str, str] = {}

    def scan_file(self, path: Path, root: dict[str, Any], default_vendor: str, since_epoch: float) -> None:
        try:
            st = path.stat()
        except OSError:
            self.skipped["unreadable file"] += 1
            return
        if st.st_mtime < since_epoch:
            return
        try:
            handle = path.open("rb")
        except OSError:
            self.skipped["unreadable file"] += 1
            return
        self.files_read += 1
        self.bytes_read += st.st_size
        root["files"] += 1
        with handle:
            try:
                for raw in handle:
                    self._line(raw, root, default_vendor)
            except OSError:
                self.skipped["read error"] += 1

    def scan_native(self, path: Path, root: dict[str, Any], since_epoch: float) -> None:
        """Read a Cursor or Codex native transcript, one line at a time, through its adapter."""
        try:
            st = path.stat()
            if st.st_mtime < since_epoch:
                return
            handle = path.open("rb")
        except OSError:
            self.skipped["unreadable file"] += 1
            return
        self.files_read += 1
        self.bytes_read += st.st_size
        root["files"] += 1
        mtime_ts = datetime.fromtimestamp(st.st_mtime, UTC).strftime(TS_FMT)
        with handle:
            for lineno, raw in enumerate(handle, 1):
                complete = raw.endswith(b"\n")
                try:
                    obj = json.loads(raw.decode("utf-8", errors="replace"))
                except ValueError:
                    self.skipped["malformed json" if complete else "incomplete last line"] += 1
                    continue
                if not isinstance(obj, dict):
                    self.skipped["not an object"] += 1
                    continue
                for rec in native_records(root["native"], obj, path.stem, lineno, mtime_ts):
                    self._record(rec, root, root["vendor"])

    def _line(self, raw: bytes, root: dict[str, Any], default_vendor: str) -> None:
        complete = raw.endswith(b"\n")
        text = raw.decode("utf-8", errors="replace")
        matched = any(token in text for token in PREFILTER)
        if not matched and complete:
            return
        try:
            rec = json.loads(text)
        except ValueError:
            self.skipped["malformed json" if complete else "incomplete last line"] += 1
            return
        if not isinstance(rec, dict):
            self.skipped["not an object"] += 1
            return
        if matched:
            self._record(rec, root, default_vendor)

    def _ignored(self, kind: Any) -> None:
        self.ignored_types[str(kind)] += 1

    def _record(self, rec: dict[str, Any], root: dict[str, Any], default_vendor: str) -> None:
        if rec.get("type") not in USAGE_TYPES:
            self._ignored(rec.get("type"))
            return
        ts = rec.get("timestamp")
        if not isinstance(ts, str) or not ts:
            self.skipped["no timestamp"] += 1
            return
        if not (self.start <= ts < self.end):
            return
        uuid = rec.get("uuid")
        if not isinstance(uuid, str) or not uuid:
            self.skipped["no uuid"] += 1
            return
        if uuid in self.seen_uuid:
            self.duplicates += 1
            return
        self.seen_uuid.add(uuid)
        entry = rec.get("entrypoint")
        vendor = EXPORT_VENDORS.get(entry, default_vendor) if isinstance(entry, str) else default_vendor
        if vendor != default_vendor and vendor in self.native_vendors:
            self.dropped_exports += 1
            return
        root["records"] += 1
        session = rec.get("sessionId")
        if isinstance(session, str) and session:
            root["sessions"].add(session)
        self.vendor_records[vendor] += 1
        kind = rec.get("type")
        message = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        content = message.get("content")
        if kind == "assistant" and isinstance(content, list):
            for block in content:
                self._tool_use(block, vendor, ts)
        elif kind == "user":
            for text in _user_texts(content):
                for match in COMMAND_RE.findall(text):
                    name = match.strip().lstrip("/").strip()
                    if name:
                        _touch(self.skills, name, vendor, ts)
        elif kind == "attachment":
            att = rec.get("attachment") if isinstance(rec.get("attachment"), dict) else {}
            hook = att.get("hookName")
            if isinstance(hook, str) and hook:
                _touch(self.hooks, hook, vendor, ts)

    def _tool_use(self, block: Any, vendor: str, ts: str) -> None:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            return
        tool_id = block.get("id")
        if isinstance(tool_id, str):
            if tool_id in self.seen_tool:
                return
            self.seen_tool.add(tool_id)
        name = block.get("name")
        if not isinstance(name, str) or not name:
            return
        inp = block.get("input") if isinstance(block.get("input"), dict) else {}
        _touch(self.tools, name, vendor, ts)
        self.vendor_tools[vendor] += 1
        if name == "Skill":
            skill = str(inp.get("skill") or "").strip().lstrip("/").strip()
            if skill:
                _touch(self.skills, skill, vendor, ts)
        elif name == "Read":
            path = inp.get("file_path") or inp.get("path")
            if isinstance(path, str) and path.endswith(".md"):
                self._read(path, ts)

    def _read(self, path: str, ts: str) -> None:
        real = self._realpaths.get(path)
        if real is None:
            real = self._realpaths[path] = os.path.realpath(os.path.expanduser(path))
        row = self.candidates.get(real)
        if row is None:
            return
        row["reads"] += 1
        if row["last"] is None or ts > row["last"]:
            row["last"] = ts


def native_records(native: str, obj: dict[str, Any], stem: str, lineno: int, mtime_ts: str) -> list[dict[str, Any]]:
    """Map one Cursor or Codex line onto the Claude record shape the collectors read.

    Cursor transcripts carry no timestamp or uuid, so each record takes the file's mtime and a
    per-line uuid. Codex keeps its own timestamp and ordinal.
    """
    if native == "cursor":
        role, message = obj.get("role"), obj.get("message")
        if role in ("user", "assistant") and isinstance(message, dict):
            return [{"type": role, "uuid": f"cursor:{stem}:{lineno}", "timestamp": mtime_ts,
                     "sessionId": stem, "message": message}]
        return []
    if native == "codex":
        payload = obj.get("payload")
        if obj.get("type") != "response_item" or not isinstance(payload, dict):
            return []
        kind = payload.get("type")
        if kind not in ("function_call", "custom_tool_call"):
            return []
        ts = norm_ts(str(obj.get("timestamp") or ""))
        if ts is None:
            return []
        if kind == "function_call":
            try:
                parsed = json.loads(payload.get("arguments") or "{}")
            except ValueError:
                parsed = {}
            args = parsed if isinstance(parsed, dict) else {}
        else:
            args = {"input": payload.get("input")}
        block = {"type": "tool_use", "id": payload.get("call_id") or payload.get("id"),
                 "name": payload.get("name"), "input": args}
        ordinal = obj.get("ordinal", lineno)
        return [{"type": "assistant", "uuid": f"codex:{stem}:{ordinal}", "timestamp": ts,
                 "sessionId": stem, "message": {"content": [block]}}]
    return []


def scan_factory(agents: Path, start: str, end: str, root: dict[str, Any], since_epoch: float) -> dict[str, Any]:
    """Count factory events per type and per vendor from events.jsonl files in the window."""
    events_by_type: Counter = Counter()
    runs_by_vendor: Counter = Counter()
    steps_by_vendor: Counter = Counter()
    for path in sorted(agents.glob("factory/*/events.jsonl")):
        try:
            if path.stat().st_mtime < since_epoch:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        root["files"] += 1
        vendor = "unknown"
        for line in lines:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get("type")
            if kind == "run_started" and isinstance(event.get("vendor"), str):
                vendor = event["vendor"]
            ts = norm_ts(event.get("ts") or "")
            if not ts or not (start <= ts < end) or not isinstance(kind, str):
                continue
            events_by_type[kind] += 1
            root["records"] += 1
            if kind == "run_started":
                runs_by_vendor[vendor] += 1
            elif kind == "step_started":
                steps_by_vendor[vendor] += 1
    return {
        "events_by_type": dict(sorted(events_by_type.items())),
        "runs_by_vendor": dict(sorted(runs_by_vendor.items())),
        "steps_by_vendor": dict(sorted(steps_by_vendor.items())),
    }


def transcript_roots(home: Path, selected: tuple[str, ...]) -> list[dict[str, Any]]:
    """Transcript roots to read, in a fixed order, each with its vendor and reliability."""
    roots: list[dict[str, Any]] = []
    if "claude" in selected:
        roots.append(_root("claude", home / ".claude" / "projects", "claude"))
    if "profiles" in selected:
        for path in sorted((home / ".agents-profiles").glob("*/claude/projects")):
            roots.append(_root(f"profile:{path.parent.parent.name}", path, "claude"))
    if "cursor" in selected:
        roots.append(_root("cursor", home / ".cursor" / "projects", "cursor", "best_effort", "cursor"))
    if "codex" in selected:
        roots.append(_root("codex", home / ".codex" / "sessions", "codex", "best_effort", "codex"))
    return roots


def root_files(root: dict[str, Any]) -> list[Path]:
    base = Path(root["path"])
    if not base.is_dir():
        return []
    if root["native"] == "cursor":
        return sorted(base.glob("*/agent-transcripts/**/*.jsonl"))
    return sorted(base.glob("**/*.jsonl"))


def _root(label: str, path: Path, vendor: str, reliability: str = "primary",
          native: str | None = None) -> dict[str, Any]:
    return {"label": label, "path": str(path), "vendor": vendor, "reliability": reliability,
            "native": native, "files": 0, "records": 0, "sessions": set()}


# --- hook errors ------------------------------------------------------------

def normalize_message(message: str) -> str:
    text = re.sub(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z?", "<ts>", message)
    text = re.sub(r"'[^']*'|\"[^\"]*\"", "<v>", text)
    text = re.sub(r"\d+", "<n>", text)
    return re.sub(r"\s+", " ", text).strip()[:200]


def _hook_message(lines: list[str]) -> str:
    first = lines[0].strip()
    if first.startswith("Traceback"):
        tail = [line.strip() for line in lines[1:] if line.strip()]
        return tail[-1] if tail else first
    return first


def hook_error_groups(path: Path) -> dict[str, Any]:
    """Group hook-errors.log entries by normalized message. Not window-filtered (AC-11)."""
    if not path.is_file():
        return {"status": "missing", "entries": 0, "groups": []}
    entries: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = HOOK_LINE_RE.match(raw)
        if match:
            entries.append({"ts": match.group(1), "lines": [match.group(2)]})
        elif entries:
            entries[-1]["lines"].append(raw)
        else:
            entries.append({"ts": None, "lines": [raw]})
    groups: dict[str, dict[str, Any]] = {}
    for entry in entries:
        key = normalize_message(_hook_message(entry["lines"])) or "(empty)"
        row = groups.setdefault(key, {"count": 0, "first": None, "last": None})
        row["count"] += 1
        ts = entry["ts"]
        if ts:
            row["first"] = ts if row["first"] is None else min(row["first"], ts)
            row["last"] = ts if row["last"] is None else max(row["last"], ts)
    ranked = sorted(groups.items(), key=lambda item: (-item[1]["count"], item[0]))
    return {"status": "ok", "entries": len(entries),
            "groups": [{"message": key, **row} for key, row in ranked]}


# --- signals assembly ---------------------------------------------------------

def _day(ts: str | None) -> str | None:
    return ts[:10] if ts else None


def _finalize(table: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {key: {"count": row["count"], "vendors": dict(sorted(row["vendors"].items())),
                  "first": _day(row["first"]), "last": _day(row["last"])}
            for key, row in sorted(table.items())}


def classify_skill(raw: str, installed: dict[str, list[str]], aliases: dict[str, str],
                   builtin: tuple[str, ...]) -> tuple[str, str]:
    if raw in installed:
        return "installed", raw
    if raw in aliases:
        return "alias", aliases[raw]
    if ":" in raw:
        return "plugin", raw
    if raw in builtin:
        return "builtin", raw
    return "retired_or_unknown", raw


def skill_usage(installed: dict[str, list[str]], aliases: dict[str, str], builtin: tuple[str, ...],
                table: dict[str, dict[str, Any]], locations: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    alias_rows: dict[str, Any] = {}

    def row_for(name: str, cls: str) -> dict[str, Any]:
        if name not in out:
            out[name] = {"class": cls, "count": 0, "vendors": Counter(), "first": None, "last": None, "raw": Counter()}
            if cls == "installed":
                out[name]["aliases"] = sorted(installed.get(name, []))
                out[name]["location"] = locations.get(name, "agents")
        return out[name]

    for name in sorted(installed):
        row_for(name, "installed")
    for raw, row in sorted(table.items()):
        cls, target = classify_skill(raw, installed, aliases, builtin)
        if cls == "alias":
            alias_rows[raw] = {"resolves_to": target, "count": row["count"], "last": _day(row["last"])}
        entry = row_for(target, "installed" if cls == "alias" else cls)
        entry["count"] += row["count"]
        entry["vendors"].update(row["vendors"])
        entry["raw"][raw] += row["count"]
        entry["first"] = row["first"] if entry["first"] is None else min(entry["first"], row["first"])
        entry["last"] = row["last"] if entry["last"] is None else max(entry["last"], row["last"])
    for entry in out.values():
        entry["vendors"] = dict(sorted(entry["vendors"].items()))
        entry["raw"] = dict(sorted(entry["raw"].items()))
        entry["first"] = _day(entry["first"])
        entry["last"] = _day(entry["last"])
    return dict(sorted(out.items())), dict(sorted(alias_rows.items()))


def mcp_usage(tools: dict[str, dict[str, Any]], servers: list[str], mcp_size: str) -> dict[str, Any]:
    by_server: dict[str, dict[str, Any]] = {name: {"calls": 0, "tools": Counter()} for name in servers}
    for name, row in tools.items():
        parts = name.split("__", 2)
        if len(parts) != 3 or parts[0] != "mcp" or not parts[1]:
            continue
        entry = by_server.setdefault(parts[1], {"calls": 0, "tools": Counter()})
        entry["calls"] += row["count"]
        entry["tools"][parts[2]] += row["count"]
    out: dict[str, Any] = {}
    for server, entry in sorted(by_server.items()):
        seen = len(entry["tools"])
        if mcp_size == "skip":
            size: Any = NOT_MEASURED_SKIPPED
        else:
            size = seen if seen else NOT_MEASURED
        out[server] = {"calls": entry["calls"], "tool_list_size": size,
                       "tools": dict(sorted(entry["tools"].items()))}
    return out


def mcp_ranking(mcp: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [{"server": server, "calls": entry["calls"], "tool_list_size": entry["tool_list_size"]}
            for server, entry in mcp.items()]
    return sorted(rows, key=lambda r: (-r["calls"], r["server"]))


def drift_rows(checks: list[dict[str, Any]], tools: dict[str, dict[str, Any]],
               skills: dict[str, Any], agents: Path, commit_cache: dict[str, str | None]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for check in checks:
        match = check.get("match") if isinstance(check.get("match"), dict) else {}
        kind, pattern = match.get("kind"), str(match.get("pattern") or "")
        hits: dict[str, dict[str, Any]] = {}
        if kind == "tool_name_regex":
            try:
                regex = re.compile(pattern)
            except re.error as exc:
                raise HarnessError(f"checks.json {check.get('name')!r}: bad pattern: {exc}") from None
            hits = {name: row for name, row in tools.items() if regex.search(name)}
        elif kind == "skill_not_installed":
            hits = {name: row for name, row in skills.items() if row["class"] == "retired_or_unknown"}
        else:
            raise HarnessError(f"checks.json {check.get('name')!r}: unknown match kind {kind!r}")
        vendors: Counter = Counter()
        firsts = [row["first"] for row in hits.values() if row.get("first")]
        lasts = [row["last"] for row in hits.values() if row.get("last")]
        for row in hits.values():
            vendors.update(row["vendors"])
        rule = str(check.get("rule") or "")
        rows.append({
            "name": check.get("name"),
            "rule": rule,
            "severity": check.get("severity"),
            "match": {"kind": kind, "pattern": pattern},
            "count": sum(row["count"] for row in hits.values()),
            "vendors": dict(sorted(vendors.items())),
            "first": _day(min(firsts)) if firsts else None,
            "last": _day(max(lasts)) if lasts else None,
            "matched": {name: row["count"] for name, row in sorted(hits.items())},
            "rule_first_commit": rule_first_commit(agents, rule, commit_cache) if rule else None,
        })
    return rows


def bloat_rows(candidates: list[dict[str, Any]], read_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for cand in candidates:
        read = read_rows[cand["real"]]
        rows.append({
            "path": cand["path"],
            "size": cand["size"],
            "reads": read["reads"],
            "last_read": read["last"][:10] if read["last"] else NEVER_READ,
        })
    return sorted(rows, key=lambda r: (-r["size"], r["path"]))


# --- orchestration ----------------------------------------------------------

def scan_kb_reads_and_sequences(roots: list[dict[str, Any]], since_epoch: float, agents: Path) -> tuple[Counter, dict[str, set[str]]]:
    """KB How-to reads and Bash 3-grams (first two tokens of each command) per Claude-style transcript in the window."""
    reads: Counter = Counter()
    sessions: dict[str, set[str]] = {}
    for root in roots:
        if root["native"]:
            continue
        for path in root_files(root):
            if path.stat().st_mtime < since_epoch:
                continue
            commands: list[str] = []
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = (obj.get("message") or {}).get("content") if isinstance(obj, dict) else None
                for block in content if isinstance(content, list) else []:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    args = block.get("input") or {}
                    if block.get("name") == "Read" and args.get("file_path"):
                        try:
                            rel = Path(str(args["file_path"])).resolve().relative_to(agents.resolve()).as_posix()
                        except (ValueError, OSError):
                            continue
                        if rel.startswith("kb/") and Path(rel).name.startswith(("How-to", "llm-index")):
                            reads[rel] += 1
                    if block.get("name") == "Bash" and args.get("command"):
                        commands.append(" ".join(str(args["command"]).split()[:2]))
            for i in range(len(commands) - 2):
                gram = " | ".join(commands[i:i + 3])
                sessions.setdefault(gram, set()).add(path.stem)
    return reads, sessions


def scan_factory_kit_reads(agents: Path, since_epoch: float, reads: Counter) -> None:
    for events in sorted((agents / "factory").glob("*/events.jsonl")):
        if events.stat().st_mtime < since_epoch:
            continue
        for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
            with contextlib.suppress(json.JSONDecodeError):
                ev = json.loads(line)
                if isinstance(ev, dict) and ev.get("type") == "step_finished":
                    for rel in ev.get("kit_reads") or []:
                        if str(rel).startswith("kb/"):
                            reads[str(rel)] += 1


def kb_read_section(agents: Path, reads: Counter, top: int) -> dict[str, Any]:
    owned = []
    for bucket in ("_shared", "implementation", "testing", "validation", "worklog"):
        for path in sorted((agents / "kb" / bucket).glob("**/How-to*.md")):
            owned.append(path.relative_to(agents).as_posix())
    never = [rel for rel in owned if reads[rel] == 0]
    most = [{"path": rel, "reads": count} for rel, count in reads.most_common(top) if rel in set(owned)]
    return {"owned": len(owned), "never_read": never, "most_read": most}


def proposal_section(agents: Path) -> dict[str, Any]:
    from agentctl_kb_proposals import collect

    out: dict[str, Any] = {}
    for scope in ("kb", "harness"):
        rows = collect(agents, scope)
        counts: Counter = Counter()
        by_folder: Counter = Counter()
        for row in rows:
            counts[f"{row['state']}|{row['source']}"] += 1
            if row["state"] == "applied" or row["state"] == "pending":
                by_folder[row["target"].split("/", 1)[0]] += 1
        out[scope] = {"counts": dict(sorted(counts.items())), "targets": dict(sorted(by_folder.items())),
                      "applied": [{"ref": r["ref"], "target": r["target"], "applied_at": r["applied_at"]}
                                  for r in rows if r["state"] == "applied"]}
    return out


def run_scan(*, since: str, until: str | None, top: int, sources: tuple[str, ...], mcp_size: str,
             output_dir: Path | None, home: Path, agents: Path, now: datetime) -> dict[str, Any]:
    started = time.monotonic()
    if top < 1:
        raise HarnessError("--top: must be at least 1")
    if mcp_size not in MCP_SIZE_MODES:
        raise HarnessError(f"--mcp-tool-size: {mcp_size!r}; accepted: {', '.join(MCP_SIZE_MODES)}")
    start_dt, end_dt, delta = build_window(since, until, now)
    start, end = start_dt.strftime(TS_FMT), end_dt.strftime(TS_FMT)
    default_out = agents / "harness"
    out_dir = output_dir if output_dir is not None else default_out

    checks, builtin = load_checks(agents)
    agent_skills = installed_skills(agents)
    claude_skills = {n: a for n, a in installed_skills(home / ".claude").items() if n not in agent_skills}
    locations = {**{n: "agents" for n in agent_skills}, **{n: "claude" for n in claude_skills}}
    installed = {**agent_skills, **claude_skills}
    aliases = alias_targets(installed)
    servers = catalog_servers(agents)
    candidates = bloat_candidates(agents)
    read_state = {cand["real"]: {"reads": 0, "last": None} for cand in candidates}
    native = set(sources) & {"cursor", "codex"}
    tx = Transcripts(start, end, native, read_state)

    roots = transcript_roots(home, sources)
    since_epoch = start_dt.timestamp()
    for root in roots:
        for path in root_files(root):
            if root["native"]:
                tx.scan_native(path, root, since_epoch)
            else:
                tx.scan_file(path, root, root["vendor"], since_epoch)

    factory_root = _root("factory", agents / "factory", "factory")
    factory = None
    if "factory" in sources:
        factory = scan_factory(agents, start, end, factory_root, since_epoch)

    source_rows = [{"label": r["label"], "path": r["path"], "vendor": r["vendor"],
                    "reliability": r["reliability"], "files": r["files"], "records": r["records"],
                    "sessions": len(r["sessions"]),
                    "record_time": "file mtime (no per-record timestamp)" if r["native"] == "cursor" else "record"}
                   for r in roots]
    if factory is not None:
        source_rows.append({"label": "factory", "path": str(agents / "factory" / "*" / "events.jsonl"),
                            "vendor": "factory", "reliability": "primary", "files": factory_root["files"],
                            "records": factory_root["records"], "sessions": 0, "record_time": "record"})
    not_read = [{"source": name, "reason": "not selected"} for name in ALL_SOURCES if name not in sources]

    skills, alias_rows = skill_usage(installed, aliases, builtin, tx.skills, locations)
    tools = _finalize(tx.tools)
    builtin_tools = {name: row for name, row in tools.items() if not name.startswith("mcp__") and name != "Skill"}
    mcp = mcp_usage(tx.tools, servers, mcp_size)
    commit_cache: dict[str, str | None] = {}
    drift = drift_rows(checks, tx.tools, skills, agents, commit_cache)
    bloat_md = bloat_rows(candidates, read_state)
    hook_errors = hook_error_groups(agents / "history" / ".state" / "hook-errors.log")
    skipped_total = sum(tx.skipped.values())

    options = {
        "sources": {"value": list(sources), "default": sources == DEFAULT_SOURCES},
        "since": {"value": since, "default": since == DEFAULT_SINCE},
        "until": {"value": end_dt.strftime("%Y-%m-%d"),
                  "default": end_dt == now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)},
        "top": {"value": top, "default": top == DEFAULT_TOP},
        "mcp_tool_size": {"value": mcp_size, "default": mcp_size == DEFAULT_MCP_SIZE},
        "output_dir": {"value": str(out_dir), "default": out_dir == default_out},
    }
    slug_parts = []
    if not options["sources"]["default"]:
        slug_parts.append("src-" + "+".join(sources))
    if not options["mcp_tool_size"]["default"]:
        slug_parts.append("mcp-" + mcp_size)
    if not options["top"]["default"]:
        slug_parts.append(f"top{top}")
    if not options["output_dir"]["default"]:
        slug_parts.append("outdir")
    name = f"{end_dt:%Y-%m-%d}_{since_label(delta)}"
    if slug_parts:
        name += "_" + "_".join(slug_parts)

    generated = now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    kb_reads_counter, sequences = scan_kb_reads_and_sequences(roots, since_epoch, agents)
    scan_factory_kit_reads(agents, since_epoch, kb_reads_counter)
    kb_reads_section = kb_read_section(agents, kb_reads_counter, top)
    repeated_section = [{"sequence": gram, "sessions": len(found)}
                        for gram, found in sorted(sequences.items(), key=lambda kv: -len(kv[1]))
                        if len(found) >= SEQUENCE_MIN_SESSIONS][:REPEAT_TOP]
    signals: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated,
        "options": options,
        "window": {"since": start, "until": end, "days": round(delta.total_seconds() / 86400, 3)},
        "sources": source_rows,
        "not_read": not_read,
        "skipped": {"total": skipped_total, "by_reason": dict(sorted(tx.skipped.items()))},
        "ignored_record_types": dict(sorted(tx.ignored_types.items())),
        "duplicates": tx.duplicates,
        "dropped_exports": tx.dropped_exports,
        "usage": {
            "skills": skills,
            "aliases": alias_rows,
            "tools": tools,
            "builtin_tools": builtin_tools,
            "mcp_servers": mcp,
            "hook_events": _finalize(tx.hooks),
            "vendors": {v: {"records": tx.vendor_records[v], "tool_calls": tx.vendor_tools[v]}
                        for v in sorted(set(tx.vendor_records) | set(tx.vendor_tools))},
            "factory": factory,
        },
        "bloat": {"markdown": bloat_md, "mcp_servers": mcp_ranking(mcp)},
        "kb_reads": kb_reads_section,
        "proposals": proposal_section(agents),
        "repeated_sequences": repeated_section,
        "drift": drift,
        "hooks": {"inventory": hook_inventory(agents, home), "errors": hook_errors},
        "not_counted": list(NOT_COUNTED),
        "stats": {"duration_s": round(time.monotonic() - started, 3),
                  "bytes_read": tx.bytes_read, "files_read": tx.files_read},
    }

    signals_dir, reports_dir = out_dir / "signals", out_dir / "reports"
    try:
        signals_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HarnessError(f"--output-dir: cannot create {out_dir}: {exc.strerror or exc}") from None
    signals_path = signals_dir / f"{name}.json"
    report_path = reports_dir / f"{name}.md"
    signals_path.write_text(json.dumps(signals, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    report_text, truncated = render_report(signals, name, top)
    report_path.write_text(report_text, encoding="utf-8")

    return {
        "status": "ok",
        "signals": str(signals_path),
        "report": str(report_path),
        "window": signals["window"],
        "options": options,
        "totals": {
            "installed_skills": len(installed),
            "zero_use_installed_skills": sum(1 for n, e in skills.items() if e["class"] == "installed" and e["count"] == 0),
            "skill_names_seen": len(tx.skills),
            "mcp_servers": len(mcp),
            "tool_names": len(tools),
            "hook_events": len(tx.hooks),
            "records": sum(tx.vendor_records.values()),
            "files_read": tx.files_read,
        },
        "sources_read": [row["label"] for row in source_rows],
        "not_read": [row["source"] for row in not_read],
        "skipped": skipped_total,
        "truncated": truncated,
        "stats": signals["stats"],
    }


# --- report -----------------------------------------------------------------

def _cut(rows: list[Any], top: int, section: str, truncated: dict[str, int]) -> list[Any]:
    if len(rows) > top:
        truncated[section] = len(rows) - top
    return rows[:top]


def render_report(signals: dict[str, Any], name: str, top: int) -> tuple[str, dict[str, int]]:
    truncated: dict[str, int] = {}
    usage = signals["usage"]
    lines = [f"# Harness scan {name}", "",
             f"- Window: {signals['window']['since']} to {signals['window']['until']} ({signals['window']['days']} days)",
             f"- Generated: {signals['generated_at']}",
             (f"- Duration: {signals['stats']['duration_s']} s, {signals['stats']['files_read']} files, "
              f"{signals['stats']['bytes_read']} bytes read"), "", "## Options", ""]
    for key, opt in signals["options"].items():
        marker = "default" if opt["default"] else "non-default"
        lines.append(f"- {key}: {opt['value']} ({marker})")
    lines += ["", "## Sources read", ""]
    for row in signals["sources"]:
        lines.append(f"- {row['label']} ({row['reliability']}): {row['path']}; files {row['files']}, "
                     f"sessions {row['sessions']}, records {row['records']}")
    lines += ["", "Not read:"]
    lines += [f"- {row['source']}: {row['reason']}" for row in signals["not_read"]] or ["- none"]
    kb = signals["kb_reads"]
    lines += ["", "## Knowledge reads", "",
              f"- Owned How-tos: {kb['owned']}; never read in the window: {len(kb['never_read'])}"]
    lines += [f"- most read: {row['path']} ({row['reads']})" for row in kb["most_read"][:top]]
    lines += ["", "## Proposals", ""]
    for scope in ("kb", "harness"):
        section = signals["proposals"][scope]
        counts = ", ".join(f"{k}: {v}" for k, v in section["counts"].items()) or "none"
        lines.append(f"- {scope}: {counts}")
    lines += ["", f"## Repeated sequences (Bash, 3-grams in at least {SEQUENCE_MIN_SESSIONS} sessions)", ""]
    lines += [f"- {row['sequence']}: {row['sessions']} sessions" for row in signals["repeated_sequences"][:top]] or ["- none"]
    reasons = ", ".join(f"{k}: {v}" for k, v in signals["skipped"]["by_reason"].items()) or "none"
    lines += ["",
              f"Skipped lines and files: {signals['skipped']['total']} ({reasons})",
              (f"Duplicates dropped by uuid: {signals['duplicates']}; "
               f"export copies dropped: {signals['dropped_exports']}")]

    skills = usage["skills"]
    ranked = sorted((n, e) for n, e in skills.items() if e["count"] > 0 and e["class"] in ("installed", "builtin", "plugin"))
    ranked.sort(key=lambda item: (-item[1]["count"], item[0]))
    lines += ["", "## Top skills", "", "| Skill | Class | Count | Last |", "|---|---|---|---|"]
    for skill, entry in _cut(ranked, top, "top_skills", truncated):
        lines.append(f"| {skill} | {entry['class']} | {entry['count']} | {entry['last']} |")
    zero = [n for n, e in skills.items() if e["class"] == "installed" and e["count"] == 0]
    lines += ["", f"## Zero-use installed skills ({len(zero)})", ""] + [f"- {n}" for n in zero]
    retired = [(n, e) for n, e in skills.items() if e["class"] == "retired_or_unknown"]
    lines += ["", f"## Retired or unknown names ({len(retired)})", ""]
    lines += [f"- {n}: {e['count']}, last {e['last']}" for n, e in retired] or ["- none"]
    if usage["aliases"]:
        lines += ["", "## Aliases", ""]
        lines += [f"- {a} -> {row['resolves_to']}: {row['count']}" for a, row in usage["aliases"].items()]

    mcp_rank = signals["bloat"]["mcp_servers"]
    lines += ["", "## MCP servers (ranked by calls)", "", "| Server | Calls | Tool-list size |", "|---|---|---|"]
    for row in _cut(mcp_rank, top, "mcp_servers", truncated):
        lines.append(f"| {row['server']} | {row['calls']} | {row['tool_list_size']} |")
    zero_servers = [r["server"] for r in mcp_rank if r["calls"] == 0]
    lines += ["", f"Zero-use catalog servers ({len(zero_servers)}): " + (", ".join(zero_servers) or "none")]

    builtin = sorted(usage["builtin_tools"].items(), key=lambda item: (-item[1]["count"], item[0]))
    lines += ["", "## Built-in tools", ""]
    lines += [f"- {n}: {r['count']}" for n, r in _cut(builtin, top, "builtin_tools", truncated)]
    hooks = sorted(usage["hook_events"].items(), key=lambda item: (-item[1]["count"], item[0]))
    lines += ["", "## Hook events", ""]
    lines += [f"- {n}: {r['count']}, first {r['first']}, last {r['last']}"
              for n, r in _cut(hooks, top, "hook_events", truncated)]
    lines += ["", "Per-hook-script counts: not measured (transcripts record hookName events only)."]

    lines += ["", "## Rule drift", ""]
    for row in signals["drift"]:
        lines.append(f"- {row['name']} ({row['severity']}): {row['count']} calls, first {row['first']}, "
                     f"last {row['last']}, vendors {row['vendors']}; rule {row['rule']} first committed "
                     f"{row['rule_first_commit'] or 'not in git'}")
        matched = sorted(row["matched"].items(), key=lambda item: (-item[1], item[0]))
        lines += [f"  - {n}: {c}" for n, c in _cut(matched, top, f"drift:{row['name']}", truncated)]

    bloat = signals["bloat"]["markdown"]
    lines += ["", f"## Bloat: Markdown over 20 KB ({len(bloat)})", "", "| Path | Size | Reads | Last read |", "|---|---|---|---|"]
    for row in _cut(bloat, top, "bloat_markdown", truncated):
        lines.append(f"| {row['path']} | {row['size']} | {row['reads']} | {row['last_read']} |")

    errors = signals["hooks"]["errors"]
    lines += ["", f"## Hook errors ({errors['status']}, {errors['entries']} entries)", ""]
    lines += [f"- {g['count']}x {g['message']} (first {g['first']}, last {g['last']})"
              for g in _cut(errors["groups"], top, "hook_error_groups", truncated)]

    lines += ["", "## Not counted", ""] + [f"- {text}" for text in signals["not_counted"]]
    if truncated:
        lines += ["", "## Truncated", ""] + [f"- {k}: {v} more" for k, v in truncated.items()]
    return "\n".join(lines) + "\n", truncated


# --- CLI ---------------------------------------------------------------------

def cmd_harness_scan(args: argparse.Namespace) -> int:
    agents = Path(agents_home())
    home = Path(os.path.expanduser("~"))
    output = Path(args.output_dir).expanduser().resolve() if args.output_dir else None
    summary = run_scan(
        since=args.since,
        until=args.until,
        top=args.top,
        sources=parse_sources(args.sources),
        mcp_size=args.mcp_size,
        output_dir=output,
        home=home,
        agents=agents,
        now=datetime.now(UTC),
    )
    emit(summary)
    return 0


def add_harness_parsers(group: argparse._SubParsersAction) -> None:
    scan = group.add_parser(
        "scan",
        help="Usage, bloat and drift scan over transcripts and factory events (read-only).",
        description=(
            "Count skill, MCP, tool, hook and vendor use over a UTC window, flag bloat and rule drift, "
            "and write a signals JSON plus a Markdown report under the output directory."
        ),
    )
    scan.add_argument("--since", default=DEFAULT_SINCE, help="Window length, e.g. 60d (default) or 30d.")
    scan.add_argument("--until", default=None, metavar="YYYY-MM-DD",
                      help="Window end, UTC midnight (default: start of the current UTC day).")
    scan.add_argument("--top", type=int, default=DEFAULT_TOP, help="Detail rows per report section (default 25).")
    scan.add_argument("--sources", default=",".join(DEFAULT_SOURCES),
                      help="Comma list from claude,profiles,factory,cursor,codex (default claude,profiles,factory).")
    scan.add_argument("--mcp-tool-size", default=DEFAULT_MCP_SIZE, dest="mcp_size",
                      help="measure (default) or skip.")
    scan.add_argument("--output-dir", default=None,
                      help="Folder for signals/ and reports/ (default ~/.agents/harness).")
    scan.set_defaults(func=cmd_harness_scan)
    agentctl_harness_proposals.add_proposal_parsers(group)
    agentctl_harness_measure.add_measure_parser(group)
    agentctl_harness_schedule.add_schedule_parsers(group)
