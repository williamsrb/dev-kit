"""`agentctl factory`: run the standard task pipelines end to end in fresh headless sessions.

The engine is deterministic. Models are workers (one fresh headless session per step) and
judges (one short supervisor call, only when gates cannot decide). State is plain files under
`<harness root>/factory/TASK-ID/`: `run.json` is derived from the append-only `events.jsonl`,
so a crash between a worker exit and a snapshot write is safe. The factory never commits,
stages or pushes only through its own git steps (commit, integrate, push), which `.agentctl` can switch off,
and writes to the issue tracker only through the post step. Every default lives in `.agentctl`.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import fnmatch
import hashlib
import json
import os
import random
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import agentctl_bench
import agentctl_config
import agentctl_githost
import agentctl_release
import agentctl_sync
from agentctl_common import agents_home, emit
from agentctl_kb_proposals import KIT_TOP_FOLDERS, kit_relative, run_rows
from agentctl_sync import sign_message

SCHEMA_VERSION = 1
STATE_DIR_ENV = "AGENTS_FACTORY_DIR"
DECISIONS = ("proceed", "retry", "retry_other_model", "dual_run", "park", "escalate")
PATHS = ("standard", "plan_only", "skip_evidence", "park")
EVIDENCE_STEPS = ("plan-evidence", "validate-plan-evidence", "await-review", "run-evidence", "validate-evidence",
                  "post-evidence")
# reviewer step -> the step it sends back, with its blockers as bounded findings
REVIEW_LOOPS = {"validate-impl": "run-plan", "validate-evidence": "run-evidence"}
PLAN_STAGE_STEPS = ("plan-implementation", "validate-plan")
# Hard stops a factory-drafted rehearsal can clear (the operator still approves it; see plan-rehearsal).
REHEARSABLE = ("irreversible-operation", "existing-data")
# An escalated step keeps its model and climbs these; max stays an operator pick.
ESCALATION_EFFORTS = ("low", "medium", "high", "xhigh")
COMMAND_SPLIT_RE = re.compile(r"&&|\|\||[;|&\n]")
GIT_WRITE_RE = (r"git\s+(?:-C\s+\S+\s+)?(?:commit|add|push|reset|merge|stash|rebase|checkout|switch|clean|restore)(?=\s|$)")
TRANSIENT_RE = re.compile(
    r"rate.?limit|overloaded|timed out|timeout|ECONN|temporar|529|503|502|network|socket", re.IGNORECASE
)
# Git writes that are never allowed to a worker, whatever .agentctl says: fast-forward and force.
ALWAYS_DENIED_GIT = ("Bash(git merge --ff:*)", "Bash(git merge --ff-only:*)", "Bash(git pull --ff-only:*)",
                     "Bash(git push --force:*)", "Bash(git push -f:*)", "Bash(git push --force-with-lease:*)")
WORKER_GIT_WRITES = ("Bash(git commit:*)", "Bash(git add:*)", "Bash(git push:*)", "Bash(git reset:*)",
                     "Bash(git merge:*)", "Bash(git stash:*)")


class FactoryError(Exception):
    """User-facing failure of the factory group."""


# --------------------------------------------------------------------------- settings (.agentctl)


def settings() -> dict[str, Any]:
    """The whole .agentctl file, read at call time. A missing file stops the factory."""
    try:
        return agentctl_config.load()
    except agentctl_config.ConfigError as exc:
        raise FactoryError(str(exc)) from exc


def tracker_settings(cfg: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        return agentctl_config.tracker(cfg or settings())
    except agentctl_config.ConfigError as exc:
        raise FactoryError(str(exc)) from exc


def factory_env_name(cfg: dict[str, Any] | None = None) -> str:
    return str(agentctl_config.section(cfg or settings(), "factory")["env"])


def worker_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    """Worker tool lists. Git writes are denied unless .agentctl hands them to workers; ff and force never."""
    worker = dict(agentctl_config.section(cfg, "factory.worker"))
    git = agentctl_config.section(cfg, "git.factory")
    denied = list(worker.get("disallowed_tools", [])) + list(ALWAYS_DENIED_GIT)
    if not git.get("worker_git_writes"):
        denied += list(WORKER_GIT_WRITES)
    worker["disallowed_tools"] = denied
    return worker


def forbidden_denial(denial: dict[str, Any], cfg: dict[str, Any] | None = None) -> bool:
    """A denied git write, tracker write or rm -rf, matched where a command starts (not inside a quoted message)."""
    tracker = tracker_settings(cfg)
    tool_re = tracker and tracker.get("write_tool_re")
    if tool_re and re.search(tool_re, str(denial.get("tool_name") or "")):
        return True
    command = str((denial.get("tool_input") or {}).get("command") or "")
    patterns = [GIT_WRITE_RE, r"rm\s+-rf?\b"] + ([tracker["write_command_re"]] if tracker else [])
    forbidden = re.compile(r"^\s*(?:" + "|".join(patterns) + ")")
    return any(forbidden.match(part) for part in COMMAND_SPLIT_RE.split(command))


# --------------------------------------------------------------------------- paths and files


def factory_root() -> Path:
    raw = os.environ.get(STATE_DIR_ENV)
    if raw:
        return Path(raw).expanduser()
    return agents_home() / str(agentctl_config.section(settings(), "factory")["state_dir"])


def run_dir(task: str) -> Path:
    return factory_root() / task


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def read_events(directory: Path) -> list[dict[str, Any]]:
    path = directory / "events.jsonl"
    if not path.is_file():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            events.append(json.loads(line))
    return events


def append_event(directory: Path, kind: str, **data: Any) -> dict[str, Any]:
    event = {"ts": now(), "type": kind, **data}
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def bound(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: max(limit - 1, 0)] + "…"


# --------------------------------------------------------------------------- lock


class RunLock:
    """flock plus a pid file. A lock nobody holds is stale and is reaped by taking it."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / "lock"
        self.handle: Any = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        self.handle = handle
        return True

    def release(self) -> None:
        if self.handle:
            with contextlib.suppress(OSError):
                self.path.unlink()
            self.handle.close()
            self.handle = None


def lock_holder(directory: Path) -> int | None:
    """Pid of the live engine for this run, else None (and a stale lock file is removed)."""
    path = directory / "lock"
    if not path.is_file():
        return None
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.seek(0)
            raw = handle.read().strip()
            return int(raw) if raw.isdigit() else -1
        fcntl.flock(handle, fcntl.LOCK_UN)
    with contextlib.suppress(OSError):
        path.unlink()
    return None


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def kill_worker(pid: int | None, session_id: str | None) -> bool:
    """Kill a recorded worker group only if its cmdline still carries the step's session id."""
    if not pid or not session_id or not pid_alive(pid):
        return False
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="ignore")
    except OSError:
        return False
    if session_id not in cmdline:
        return False
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    return True


# --------------------------------------------------------------------------- state replay


def rehearsable(verdict: dict[str, Any]) -> bool:
    """Only rehearsable hard stops, and the verdict asks for a factory-drafted rehearsal, continue past route."""
    criteria = {b["criterion"] for b in verdict.get("blockers", [])}
    return (verdict.get("verdict") == "Human-in-the-loop" and bool(criteria) and criteria <= set(REHEARSABLE)
            and bool((verdict.get("rehearsal") or {}).get("required")))


def derive(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold the event log into the run snapshot (the content of run.json)."""
    snap: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "state": "new", "steps": [], "cost_usd": 0.0,
                            "park": None, "loops": 0, "events": len(events), "route": None, "dual": None,
                            "rehearsal": None}
    by_id: dict[str, dict[str, Any]] = {}
    for ev in events:
        kind = ev["type"]
        if kind == "run_started":
            for key, value in ev.items():
                if key not in ("type", "ts"):
                    snap[key] = value
            snap["created_at"] = ev["ts"]
            snap["state"] = "running"
            snap["steps"] = []
            for index, spec in enumerate(ev["step_specs"]):
                step = {"index": index, "id": spec["id"], "skill": spec["skill"], "role": spec["role"],
                        "status": "pending", "attempts": 0, "retries": {}, "escalations": 0, "model": None,
                        "vendor": None, "session_id": None, "cost_usd": 0.0, "started_at": None,
                        "finished_at": None, "summary": None, "reason": None}
                snap["steps"].append(step)
                by_id[spec["id"]] = step
        elif kind in ("resume", "reset_park"):
            snap["state"] = "running"
            snap["park"] = None
            if kind == "resume":
                snap["single_step"] = ev.get("single_step")
            for step in snap["steps"]:
                if step["status"] in ("parked", "running", "interrupted", "failed"):
                    step["status"] = "pending"
        elif kind == "step_started":
            step = by_id[ev["id"]]
            step.update(status="running", model=ev.get("model"), vendor=ev.get("vendor"), role_used=ev.get("role"),
                        session_id=ev.get("session_id"), pid=ev.get("pid"), started_at=ev["ts"], finished_at=None)
            snap["current"] = ev["id"]
        elif kind == "worker_pid":
            by_id[ev["id"]]["pid"] = ev.get("pid")
        elif kind == "step_finished":
            step = by_id[ev["id"]]
            step["status"] = ev["status"]
            step["attempts"] += 1
            step["finished_at"] = ev["ts"]
            step["summary"] = ev.get("summary")
            step["cost_usd"] = round(step["cost_usd"] + (ev.get("cost_usd") or 0.0), 6)
            snap["cost_usd"] = round(snap["cost_usd"] + (ev.get("cost_usd") or 0.0), 6)
            step["reason"] = ev.get("reason")
            step["artifacts"] = ev.get("artifacts", [])
        elif kind == "engine_stopped":
            snap["elapsed_s"] = round(snap.get("elapsed_s", 0.0) + ev["elapsed_s"], 1)
        elif kind == "interrupted":
            step = by_id[ev["id"]]
            step["status"] = "interrupted"
            snap["cost_usd"] = round(snap["cost_usd"] + (ev.get("cost_usd") or 0.0), 6)
        elif kind == "retry":
            step = by_id[ev["id"]]
            step["retries"][ev["class"]] = step["retries"].get(ev["class"], 0) + 1
        elif kind == "escalate":
            by_id[ev["id"]]["escalations"] += 1
        elif kind == "step_skipped":
            by_id[ev["id"]].update(status="skipped", reason=ev.get("reason"))
        elif kind == "reset":
            step = by_id[ev["id"]]
            step.update(status="pending", retries={}, escalations=0, reason=None)
            step["attempts"] = 0
            if ev.get("loop"):
                snap["loops"] += 1
        elif kind == "baseline_updated":
            snap["git_baseline"] = ev["git_baseline"]
        elif kind == "sync_scan":
            snap["sync"] = {"step": ev["id"], "status": ev["status"], "inbox": ev["inbox"], "outbox": ev["outbox"]}
        elif kind in ("sync_proposal", "sync_notice"):
            snap.setdefault("sync_writes", []).append({k: v for k, v in ev.items() if k not in ("type", "ts")} | {"type": kind})
        elif kind == "author_override":
            by_id[ev["id"]]["model"] = ev["model"]
        elif kind == "decision":
            snap["cost_usd"] = round(snap["cost_usd"] + (ev.get("cost_usd") or 0.0), 6)
        elif kind == "route":
            snap["route"] = {k: v for k, v in ev.items() if k not in ("type", "ts")}
        elif kind == "rehearsal_approved":
            snap["rehearsal"] = {**(snap["rehearsal"] or {}), "approved_sha256": ev["sha256"],
                                 "approved_at": ev["approved_at"]}
        elif kind == "rehearsal_required":
            snap["rehearsal"] = {"required": True, "criteria": ev.get("criteria", []),
                                 "isolation": ev.get("isolation"), "sync_delete": ev.get("sync_delete")}
        elif kind in ("dual_trigger", "dual_decided"):
            snap["dual"] = {**(snap["dual"] or {}), **{k: v for k, v in ev.items() if k not in ("type", "ts")},
                            "stage": kind}
        elif kind == "park":
            snap["state"] = "parked"
            snap["park"] = {"reason": ev["reason"], "action": ev.get("action"), "step": ev.get("id"),
                            "detail": ev.get("detail")}
            if ev.get("id") in by_id and by_id[ev["id"]]["status"] in ("pending", "running"):
                by_id[ev["id"]]["status"] = "parked"
        elif kind == "stopped":
            snap["state"] = "stopped"
        elif kind == "run_finished":
            snap["state"] = ev["state"]
            snap["finished_at"] = ev["ts"]
            snap["outcome"] = {k: v for k, v in ev.items() if k not in ("type", "ts", "state")}
    return snap

DIGEST_NAME = "digest.json"
AUTO_HARVEST_EXEMPT = ("cap_cost", "cap_time")
DEFAULT_FOLLOW_BUDGET = 2.0
NO_LEARNINGS_ROLES = ("deterministic", "explore")
LEARNING_LIMIT = 3
LEARNING_CHARS = 300
REJECTION_LIMIT = 20
OUTLIER_WINDOW = 20
OUTLIER_MIN_SAMPLES = 5
OUTLIER_FACTOR = 2.0


def _input_head(tool_input: Any, limit: int = 60) -> str:
    if isinstance(tool_input, dict) and "command" in tool_input:
        text = str(tool_input["command"])
    else:
        text = json.dumps(tool_input, sort_keys=True, ensure_ascii=False) if tool_input is not None else ""
    return " ".join(text.split())[:limit]


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _step_samples(factory_root: Path, exclude: str, step_id: str) -> tuple[list[float], list[float]]:
    """Turns and cost of the newest finished-ok runs of one step id, the current run excluded."""
    folders = sorted((p for p in factory_root.iterdir() if p.is_dir() and p.name != exclude
                      and (p / "events.jsonl").is_file()),
                     key=lambda p: (p / "events.jsonl").stat().st_mtime, reverse=True)
    turns: list[float] = []
    costs: list[float] = []
    for folder in folders:
        if len(turns) >= OUTLIER_WINDOW:
            break
        last = None
        for ev in read_events(folder):
            if ev.get("type") == "step_finished" and ev.get("id") == step_id and ev.get("status") == "ok":
                last = ev
        if last is None:
            continue
        if isinstance((last.get("usage") or {}).get("turns"), int | float):
            turns.append(float(last["usage"]["turns"]))
        if isinstance(last.get("cost_usd"), int | float):
            costs.append(float(last["cost_usd"]))
    return turns, costs


def run_digest(directory: Path, after: int = 0, limits: dict[str, Any] | None = None) -> dict[str, Any]:
    """Bounded friction digest of one run: retries, escalations, parks, failed gates, denials, kit writes,
    findings, learnings and outliers. Pure over files. `after` keeps only events numbered above it, so an
    auto harvest and the tail harvest do not repeat each other. Event numbers are 1-based line numbers."""
    limits = limits or {"excerpt_bytes": 4096, "supervisor_bytes": 6144}
    excerpt, budget = limits["excerpt_bytes"], limits["supervisor_bytes"]
    events = read_events(directory)
    signals: list[dict[str, Any]] = []
    kit_reads: dict[str, list[str]] = {}
    used = 0
    dropped = 0

    def add(kind: str, key: str, step: str | None, detail: str, ts: str | None, number: int | None) -> None:
        nonlocal used, dropped
        text = bound(detail, excerpt)
        if used + len(text) > budget:
            dropped += 1
            return
        used += len(text)
        signals.append({"id": f"S{len(signals) + 1}", "key": key, "kind": kind, "step": step, "ts": ts,
                        "event": number, "detail": text})

    for number, ev in enumerate(events, start=1):
        if number <= after:
            continue
        kind, ts, step = ev.get("type"), ev.get("ts"), ev.get("id")
        if kind == "retry":
            add("retry", f"retry:{step}:{ev.get('class')}", step, str(ev.get("reason") or ""), ts, number)
        elif kind == "escalate":
            add("escalate", f"escalate:{step}", step, str(ev.get("reason") or ""), ts, number)
        elif kind == "park":
            add("park", f"park:{ev.get('reason')}", step,
                f"action={ev.get('action')} {ev.get('detail') or ''}".strip(), ts, number)
        elif kind == "gate" and ev.get("result") == "fail":
            add("gate", f"gate:{step}:{ev.get('name')}", step, f"{ev.get('phase')}: {ev.get('detail') or ''}", ts, number)
        elif kind == "kit_changed":
            add("kit_changed", f"kit_changed:{step}", step, "; ".join(ev.get("paths") or []), ts, number)
        elif kind == "denials_noted":
            path = Path(str(ev.get("file") or ""))
            entries: Any = []
            if path.is_file():
                with contextlib.suppress(json.JSONDecodeError):
                    entries = json.loads(path.read_text(encoding="utf-8"))
            for entry in entries if isinstance(entries, list) else []:
                tool = str(entry.get("tool_name") or "")
                head = _input_head(entry.get("tool_input"))
                add("denial", f"denial:{tool}:{head}", step, f"{tool}: {head}", ts, number)
        elif kind == "step_finished":
            for path in ev.get("kit_reads") or []:
                kit_reads.setdefault(str(step), [])
                if path not in kit_reads[str(step)]:
                    kit_reads[str(step)].append(str(path))
            for text in ev.get("learnings") or []:
                add("learning", f"learning:{step}", step, str(text), ts, number)

    if after == 0:
        for findings in sorted((directory / "findings").glob("*.md")):
            add("finding", f"finding:{findings.stem}", findings.stem,
                findings.read_text(encoding="utf-8"), None, None)

    factory_root = directory.parent
    for number, ev in enumerate(events, start=1):
        if number > after and ev.get("type") == "step_finished" and ev.get("status") == "ok" and factory_root.is_dir():
            step = str(ev.get("id"))
            turns, costs = _step_samples(factory_root, directory.name, step)
            turns_now = (ev.get("usage") or {}).get("turns")
            if len(turns) >= OUTLIER_MIN_SAMPLES and isinstance(turns_now, int | float):
                med = _median(turns)
                if med > 0 and turns_now > OUTLIER_FACTOR * med:
                    add("outlier", f"outlier:{step}", step, f"turns {turns_now} vs median {med:g}", ev.get("ts"), number)
            cost_now = ev.get("cost_usd")
            if len(costs) >= OUTLIER_MIN_SAMPLES and isinstance(cost_now, int | float):
                med = _median(costs)
                if med > 0 and cost_now > OUTLIER_FACTOR * med:
                    add("outlier", f"outlier:{step}", step, f"cost {cost_now:g} vs median {med:g}", ev.get("ts"), number)

    # the harvest's own output is not friction; after a cursor only new signals justify another harvest
    proposals = sorted(str(p) for p in directory.glob("steps/*/kb-proposals.md") if not p.parent.name.endswith("-kb-harvest"))
    if after:
        proposals = []
    decided: list[dict[str, Any]] = []
    for ledger in sorted(directory.parent.glob("*/kb-decisions.jsonl")):
        for line in ledger.read_text(encoding="utf-8").splitlines():
            with contextlib.suppress(json.JSONDecodeError):
                row = json.loads(line)
                if isinstance(row, dict) and row.get("state") == "rejected":
                    decided.append({"ref": row.get("ref"), "target": row.get("target"), "reason": row.get("reason")})
    rejections = decided[-REJECTION_LIMIT:]

    return {
        "schema_version": 1, "source": "factory", "task": directory.name,
        "through": len(events), "signals": signals, "kit_reads": kit_reads,
        "step_proposals": proposals, "rejections": rejections, "dropped": dropped,
        "has_signals": bool(signals) or bool(proposals),
    }


def progress_of(snap: dict[str, Any]) -> dict[str, Any]:
    """Completed share of the run: ok and skipped steps over the step total fixed at run_started."""
    steps = snap["steps"]
    if snap.get("single_step"):
        steps = [s for s in steps if s["id"] == snap["single_step"]]
    done = sum(1 for s in steps if s["status"] in ("ok", "skipped"))
    total = len(steps)
    current = next((s["id"] for s in steps if s["status"] == "running"), None)
    return {"done": done, "total": total, "percent": round(100 * done / total) if total else 0,
            "current": current, "loop": snap.get("loops", 0)}


def snapshot(directory: Path) -> dict[str, Any]:
    snap = derive(read_events(directory))
    holder = lock_holder(directory)
    snap["engine_pid"] = holder
    snap["live"] = holder is not None
    for step in snap["steps"]:
        step["interrupted"] = step["status"] == "running" and not snap["live"]
    return snap


def write_snapshot(directory: Path, snap: dict[str, Any]) -> None:
    stored = {k: v for k, v in snap.items() if k not in ("engine_pid", "live")}
    atomic_write(directory / "run.json", json.dumps(stored, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


# --------------------------------------------------------------------------- pipelines and roles


def pipelines_dir() -> Path:
    return agents_home() / "config" / "factory" / "pipelines"


def skill_role(skill: str) -> str:
    path = agents_home() / "skills" / skill / "SKILL.md"
    if not path.is_file():
        raise FactoryError(f"pipeline names skill {skill!r} but {path} does not exist")
    match = re.search(r"^\s*recommendedRole:\s*([a-z-]+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise FactoryError(f"skill {skill!r} has no metadata.recommendedRole")
    return match.group(1)


def expand(value: Any, tracker: dict[str, Any] | None, step: str) -> Any:
    """Resolve `@tracker.<key>` placeholders (a string, or a list item that expands in place)."""
    if isinstance(value, list):
        out: list[Any] = []
        for item in value:
            piece = expand(item, tracker, step)
            out += piece if isinstance(item, str) and item.startswith("@") and isinstance(piece, list) else [piece]
        return out
    if isinstance(value, str) and value.startswith("@tracker."):
        if tracker is None:
            raise FactoryError(f"step {step} needs an issue tracker but .agentctl has tracker.kind = \"none\"")
        key = value[len("@tracker."):]
        if key not in tracker:
            raise FactoryError(f"step {step}: .agentctl tracker.{tracker['kind']} has no {key!r}")
        return tracker[key]
    return value


STEP_KINDS = ("model", "deterministic", "builtin")
BUILTINS = ("commit", "integrate", "push", "rehearsal-gate", "deploy-review", "await-review", "sync-inbox", "sync-outbox",
            "sync-notice")


def load_pipeline(name: str) -> dict[str, Any]:
    cfg = settings()
    factory_cfg = agentctl_config.section(cfg, "factory")
    if name not in factory_cfg.get("pipelines", []):
        raise FactoryError(f"pipeline {name!r} is not listed in .agentctl [factory] pipelines")
    tracker = tracker_settings(cfg)

    def read(stem: str) -> dict[str, Any]:
        path = pipelines_dir() / f"{stem}.json"
        if not path.is_file():
            raise FactoryError(f"pipeline {stem!r} not found at {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FactoryError(f"pipeline {stem!r} is not valid JSON: {exc}") from exc
        if data.get("schema_version") != SCHEMA_VERSION:
            raise FactoryError(f"pipeline {stem!r}: schema_version must be {SCHEMA_VERSION}")
        return data

    data = read(name)
    if data["mode"] == "tracker" and tracker is None:
        raise FactoryError(f"pipeline {name!r} needs an issue tracker but .agentctl has tracker.kind = \"none\"")
    steps = list(data.get("head", []))
    if data.get("include"):
        steps += read(data["include"]).get("steps", [])
    if not steps:
        raise FactoryError(f"pipeline {name!r} has no steps")
    seen: set[str] = set()
    for step in steps:
        if not step.get("id"):
            raise FactoryError(f"pipeline {name!r}: step missing id: {step}")
        for key in ("skill", "allowed_tools_extra"):
            if key in step:
                step[key] = expand(step[key], tracker, step["id"])
        step.setdefault("kind", "model")
        if step["kind"] not in STEP_KINDS:
            raise FactoryError(f"step {step['id']}: kind must be one of {STEP_KINDS}")
        if step["kind"] == "builtin":
            if step.get("builtin") not in BUILTINS:
                raise FactoryError(f"step {step['id']}: builtin must be one of {BUILTINS}")
            step["skill"] = step.get("skill") or f"builtin:{step['builtin']}"
            step["role"] = step.get("role") or "build"
        elif not step.get("skill"):
            raise FactoryError(f"pipeline {name!r}: step missing skill: {step}")
        if step["id"] in seen:
            raise FactoryError(f"pipeline {name!r}: duplicate step id {step['id']}")
        seen.add(step["id"])
        if step["kind"] != "builtin":
            step["role"] = step.get("role") or skill_role(step["skill"])
        if step["role"] not in agentctl_bench.ROLE_ORDER:
            raise FactoryError(f"step {step['id']}: unknown role {step['role']}")
        step.setdefault("pre", [])
        step.setdefault("post", [])
    limits = {**agentctl_config.section(cfg, "factory.limits"), **data.get("limits", {})}
    return {"name": data.get("name", name), "mode": data["mode"], "steps": steps, "limits": limits,
            "worker": worker_settings(cfg), "settings": cfg,
            "supervisor_role": factory_cfg["supervisor_role"], "route_step": factory_cfg["route_step"]}


def role_cells() -> dict[tuple[str, str], str]:
    return agentctl_bench.read_role_cells(agents_home() / "skills-vendor" / "ROLES.md")


def resolve_role(role: str, vendor: str, level: int = 0) -> tuple[str, str]:
    """Model and effort for a role on a vendor; an escalated `level` raises the effort one step, same model."""
    cell = role_cells().get((role, vendor))
    if not cell:
        raise FactoryError(f"ROLES.md has no {vendor} cell for role {role}")
    parts = re.findall(r"`([^`]+)`", cell)
    if not parts:
        raise FactoryError(f"ROLES.md cell for {role}/{vendor} is unreadable: {cell!r}")
    model, effort = parts[0], (parts[1] if len(parts) > 1 else "medium")
    if level and effort in ESCALATION_EFFORTS:
        effort = ESCALATION_EFFORTS[min(ESCALATION_EFFORTS.index(effort) + 1, len(ESCALATION_EFFORTS) - 1)]
    return model, effort


# --------------------------------------------------------------------------- adapters


@dataclass
class WorkerRequest:
    prompt: str
    model: str
    effort: str
    cwd: Path
    step_dir: Path
    session_id: str
    timeout_s: float
    budget_usd: float
    allowed_tools: list[str]
    disallowed_tools: list[str]
    permission_mode: str
    json_schema: dict[str, Any] | None = None
    mcp_config: Path | None = None
    on_pid: Callable[[int], None] | None = None
    label: str = "worker"
    env_extra: dict[str, str] = field(default_factory=lambda: worker_env())
    writable_roots: list[str] = field(default_factory=list)


def worker_env() -> dict[str, str]:
    """Factory flag plus a PATH that resolves `agentctl` by name, so workers never prefix `export PATH=...`."""
    path = os.pathsep.join([str(agents_home() / "bin"), str(Path.home() / ".local" / "bin"), os.environ.get("PATH", "")])
    return {factory_env_name(): "1", "PATH": path}


@dataclass
class WorkerResult:
    exit_code: int = 0
    text: str = ""
    session_id: str | None = None
    cost_usd: float | None = None
    denials: list[dict[str, Any]] = field(default_factory=list)
    timed_out: bool = False
    stderr: str = ""
    argv: list[str] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    kit_reads: list[str] = field(default_factory=list)
    kit_writes: list[str] = field(default_factory=list)
    skills_invoked: list[str] = field(default_factory=list)


KIT_PATH_RE = re.compile(r"(?:~|/)[\w./~+@-]+")


def _usage_of(event: dict[str, Any]) -> dict[str, Any]:
    usage = event.get("usage") or {}
    models = {name: {"input": m.get("inputTokens"), "output": m.get("outputTokens"),
                     "cache_read": m.get("cacheReadInputTokens"), "cache_creation": m.get("cacheCreationInputTokens"),
                     "cost": m.get("costUSD")}
              for name, m in (event.get("modelUsage") or {}).items()}
    return {"input": usage.get("input_tokens"), "output": usage.get("output_tokens"),
            "cache_read": usage.get("cache_read_input_tokens"),
            "cache_creation": usage.get("cache_creation_input_tokens"),
            "turns": event.get("num_turns"), "duration_ms": event.get("duration_ms"), "models": models}


def _note_tool_use(block: dict[str, Any], reads: list[str], skills: list[str],
                   writes: list[str] | None = None) -> None:
    name, args = block.get("name"), block.get("input") or {}
    if name == "Skill" and args.get("skill") and args["skill"] not in skills:
        skills.append(args["skill"])
    if writes is not None and name in ("Write", "Edit", "NotebookEdit"):
        raw = args.get("file_path") or args.get("notebook_path")
        rel = kit_relative(str(raw)) if raw else None
        if rel and rel not in writes:
            writes.append(rel)
    paths = [args["file_path"]] if name == "Read" and args.get("file_path") else []
    if name == "Bash" and args.get("command"):
        paths = KIT_PATH_RE.findall(args["command"])
    for raw_path in paths:
        rel = kit_relative(raw_path)
        if rel and rel not in reads:
            reads.append(rel)


def parse_raw(raw: str) -> WorkerResult:
    """Fold a stream-json transcript into a WorkerResult (no process facts: exit code, stderr, argv)."""
    result = WorkerResult()
    for line in raw.splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            event = json.loads(line)
            if event.get("type") == "assistant":
                content = (event.get("message") or {}).get("content")
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        _note_tool_use(block, result.kit_reads, result.skills_invoked, result.kit_writes)
            elif event.get("type") == "result":
                result.text = event.get("structured_output") and json.dumps(event["structured_output"]) \
                    or event.get("result") or ""
                result.session_id = event.get("session_id")
                result.cost_usd = event.get("total_cost_usd")
                result.denials = event.get("permission_denials") or []
                result.usage = _usage_of(event)
                if event.get("is_error"):
                    result.exit_code = 1
    return result


def kit_deny_rules(home: Path | None = None) -> list[str]:
    """Claude deny rules for the kit: Edit covers Write and NotebookEdit too. `//` makes the path absolute."""
    root = (home or agents_home()).resolve().as_posix().lstrip("/")
    return [f"Edit(//{root}/{folder}/**)" for folder in KIT_TOP_FOLDERS]


def measurement(result: WorkerResult) -> dict[str, Any]:
    """The additive step_finished fields a worker call contributes; usage is None when no result event arrived."""
    return {"usage": result.usage, "kit_reads": result.kit_reads, "kit_writes": result.kit_writes,
            "skills_invoked": result.skills_invoked}


def run_process(argv: list[str], req: WorkerRequest, raw_name: str) -> tuple[int, str, str, bool]:
    """Detached process group, raw stdout kept on disk, killed whole on timeout."""
    req.step_dir.mkdir(parents=True, exist_ok=True)
    raw = req.step_dir / raw_name
    err = req.step_dir / "stderr.log"
    with raw.open("w", encoding="utf-8") as out, err.open("w", encoding="utf-8") as errh:
        proc = subprocess.Popen(argv, cwd=req.cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=errh,
                                start_new_session=True, env={**os.environ, **req.env_extra})
        if req.on_pid:
            req.on_pid(proc.pid)
        try:
            code = proc.wait(timeout=req.timeout_s)
            timed_out = False
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            code, timed_out = 124, True
    return code, raw.read_text(encoding="utf-8", errors="replace"), err.read_text(errors="replace"), timed_out


class ClaudeAdapter:
    name = "claude"

    def argv(self, req: WorkerRequest) -> list[str]:
        argv = ["claude", "-p", req.prompt, "--session-id", req.session_id, "--model", req.model,
                "--effort", req.effort, "--max-budget-usd", f"{req.budget_usd:.2f}",
                "--output-format", "stream-json", "--verbose", "--include-hook-events",
                "--permission-mode", req.permission_mode, "--allowedTools", *req.allowed_tools]
        if req.disallowed_tools:
            argv += ["--disallowedTools", *req.disallowed_tools]
        if req.json_schema:
            argv += ["--json-schema", json.dumps(req.json_schema)]
        if req.mcp_config:
            argv += ["--mcp-config", str(req.mcp_config)]
        return argv

    def run(self, req: WorkerRequest) -> WorkerResult:
        argv = self.argv(req)
        code, raw, err, timed_out = run_process(argv, req, "raw.jsonl")
        result = parse_raw(raw)
        result.exit_code = code or result.exit_code
        result.stderr, result.timed_out, result.argv = err, timed_out, argv
        return result


class CodexAdapter:
    name = "codex"

    def argv(self, req: WorkerRequest, last_message: Path) -> list[str]:
        argv = ["codex", "exec", "--json", "-m", req.model, "-c", f'model_reasoning_effort="{req.effort}"',
                "-s", "workspace-write", "-C", str(req.cwd), "--skip-git-repo-check",
                "-o", str(last_message)]
        if req.writable_roots:
            # `-c` replaces the config's array instead of merging (probed 2026-11-06, codex-cli 0.166.0), so the
            # list is the whole writable set for the run: the kit (~/.agents/kb, skills, rules) is not in it.
            roots = ", ".join(json.dumps(root) for root in req.writable_roots)
            argv += ["-c", f"sandbox_workspace_write.writable_roots=[{roots}]"]
        if req.json_schema:
            schema = req.step_dir / "schema.json"
            schema.write_text(json.dumps(req.json_schema), encoding="utf-8")
            argv += ["--output-schema", str(schema)]
        return [*argv, req.prompt]

    def run(self, req: WorkerRequest) -> WorkerResult:
        req.step_dir.mkdir(parents=True, exist_ok=True)
        last = req.step_dir / "last-message.txt"
        argv = self.argv(req, last)
        code, _raw, err, timed_out = run_process(argv, req, "raw.jsonl")
        text = last.read_text(encoding="utf-8") if last.is_file() else ""
        # Codex reports no cost: recorded as unknown, bounded by wall-clock and attempts.
        return WorkerResult(exit_code=code, text=text, cost_usd=None, stderr=err, timed_out=timed_out, argv=argv)


def default_adapters() -> dict[str, Any]:
    adapters: dict[str, Any] = {"claude": ClaudeAdapter()}
    if shutil.which("codex"):
        adapters["codex"] = CodexAdapter()
    return adapters


# --------------------------------------------------------------------------- git and gates


def kit_dirty() -> set[str] | None:
    """Changed or untracked paths under the agents home's kb/, skills/ and rules/; None when it is not a git repo."""
    proc = subprocess.run(["git", "status", "--porcelain", "-uall", "--", *KIT_TOP_FOLDERS], cwd=agents_home(),
                          text=True, capture_output=True, check=False)
    return {line[3:] for line in proc.stdout.splitlines() if line} if proc.returncode == 0 else None


def git_out(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def git_baseline(repo: Path) -> dict[str, str]:
    import hashlib

    index = git_out(repo, "ls-files", "-s")
    return {"head": git_out(repo, "rev-parse", "HEAD"), "index": hashlib.sha1(index.encode()).hexdigest()}


def agentctl_json(*args: str) -> dict[str, Any]:
    script = Path(__file__).resolve().parent / "agentctl.py"
    proc = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, check=False)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": (proc.stdout + proc.stderr)[-400:]}


def tracker_task_status(task: str) -> dict[str, str | None] | None:
    """Status name and category of a Jira task, or None when the tracker cannot be read."""
    issue = agentctl_json("jira", "get", task, "--fields", "status")
    status = (issue.get("fields") or {}).get("status")
    if not isinstance(status, dict):
        return None
    return {"name": status.get("name"), "category": (status.get("statusCategory") or {}).get("key")}


def closed_task_error(task: str, cfg: dict[str, Any]) -> str | None:
    """Why a released or discarded task must not start, or None when it may (an unreadable tracker may too)."""
    tracker = tracker_settings(cfg)
    if not tracker or tracker["kind"] != "jira":
        return None
    status = tracker_task_status(task)
    if status and agentctl_config.is_closed_status(status["name"], status["category"], cfg):
        return (f"{task} is {status['name']!r} in the tracker: released or discarded tasks are never started "
                "(change the status, or remove it from [tracker.jira] closed_statuses).")
    return None


def plan_dir(task: str) -> Path:
    return agents_home() / "plans" / task


def shown(value: Any) -> str:
    """A configured command as text: an argv list is joined, a string is kept."""
    return " ".join(value) if isinstance(value, list) else str(value)


def open_tbd(task: str) -> list[str]:
    path = plan_dir(task) / "tbd.md"
    if not path.is_file():
        return []
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*[-*]\s*TBD[^:]*:\s*(.*)$", line)
        if match and match.group(1).strip().lower() not in ("none", "none.", ""):
            found.append(match.group(1).strip())
    return found


@dataclass
class GateCtx:
    task: str
    step: dict[str, Any]
    run: dict[str, Any]
    repo: Path
    report: dict[str, Any] | None
    result: WorkerResult | None
    dir: Path


Gate = tuple[str, str]  # (pass|fail|inconclusive, detail)


def gate_branch_is_task(ctx: GateCtx) -> Gate:
    if ctx.run["mode"] != "tracker":
        return "pass", "local mode"
    branch = git_out(ctx.repo, "branch", "--show-current")
    return ("pass", branch) if branch == ctx.task else ("fail", f"branch {branch!r} is not {ctx.task!r}")


def gate_tbd_empty(ctx: GateCtx) -> Gate:
    if ctx.run["mode"] != "tracker":
        return "pass", "local mode"
    open_items = open_tbd(ctx.task)
    return ("pass", "no open TBD") if not open_items else ("fail", "open TBD: " + "; ".join(open_items))


def _plan_valid(ctx: GateCtx, kind: str) -> Gate:
    data = agentctl_json("plan", "validate", str(plan_dir(ctx.task)), "--kind", kind)
    if data.get("valid"):
        return "pass", "plan valid"
    return "fail", "plan invalid: " + json.dumps(data.get("missing_sections") or data.get("error") or data)[:400]


def gate_plan_valid(ctx: GateCtx) -> Gate:
    return _plan_valid(ctx, "implementation")


def gate_plan_valid_evidence(ctx: GateCtx) -> Gate:
    return _plan_valid(ctx, "evidence")


REHEARSAL_SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "plan-data-rehearsal" / "scripts" / "rehearsal.py"


def gate_rehearsal_valid(ctx: GateCtx) -> Gate:
    proc = subprocess.run([sys.executable, str(REHEARSAL_SCRIPT), "check", ctx.task], text=True,
                          capture_output=True, check=False, timeout=120,
                          env={**os.environ, "AGENTS_HOME": str(agents_home())})
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "fail", bound((proc.stdout + proc.stderr) or "rehearsal.py printed nothing", 400)
    if data.get("status") == "ok":
        return "pass", "rehearsal valid"
    return "fail", "rehearsal invalid: " + "; ".join(data.get("errors", []))[:400]


def verdict_path(task: str) -> Path:
    return agents_home() / "prds" / f"{task}.autonomy.json"


def gate_autonomy_check(ctx: GateCtx) -> Gate:
    script = agents_home() / "skills" / "classify-ticket-autonomy" / "scripts" / "autonomy.py"
    path = verdict_path(ctx.task)
    if not path.is_file():
        return "fail", f"verdict file missing: {path}"
    proc = subprocess.run([sys.executable, str(script), "check", str(path)], text=True, capture_output=True, check=False)
    return ("pass", "verdict valid") if proc.returncode == 0 else ("fail", bound(proc.stdout, 600))


def gate_artifacts_exist(ctx: GateCtx) -> Gate:
    artifacts = (ctx.report or {}).get("artifacts") or []
    if not artifacts:
        return "fail", "report lists no artifacts"
    missing = [a for a in artifacts if not Path(a).expanduser().exists()]
    return ("pass", f"{len(artifacts)} artifacts") if not missing else ("fail", "missing artifacts: " + ", ".join(missing))


def gate_auth_state(ctx: GateCtx) -> Gate:
    evidence = plan_dir(ctx.task) / "evidence.md"
    text = evidence.read_text(encoding="utf-8") if evidence.is_file() else ""
    if re.search(r"^\*\*Auth required:\*\*\s*no\b", text, re.MULTILINE | re.IGNORECASE):
        return "pass", "evidence plan says no auth required"
    # The header's first URL is the tracker link, so the testing host is read by its label.
    match = re.search(r"^\*\*Testing base URL:\*\*\s*(https?://[^\s)\]>`'\"]+)", text, re.MULTILINE)
    host = match.group(1) if match else ""
    script = agents_home() / "skills" / "plan-task-evidence" / "scripts" / "find-auth-storage.py"
    if not script.is_file():
        return "fail", "find-auth-storage.py not found"
    argv = [sys.executable, str(script), "--json", "--cwd", str(ctx.repo)] + (["--host", host] if host else [])
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "fail", "find-auth-storage output unreadable"
    found = data if isinstance(data, list) else (data.get("host_matches" if host else "matches") or [])
    return ("pass", f"{len(found)} saved states") if found else ("fail", f"no saved auth state for {host or 'review host'}")


def gate_evidence_pass(ctx: GateCtx) -> Gate:
    data = agentctl_json("plan", "progress", ctx.task, "--kind", "evidence", "--json")
    if data.get("total", 0) > 0 and not data.get("pending") and not data.get("blocked"):
        return "pass", f"{len(data.get('done', []))} evidence steps passed"
    return "fail", f"evidence not all passed: pending={data.get('pending')} blocked={data.get('blocked')}"


def gate_evidence_folder(ctx: GateCtx) -> Gate:
    script = agents_home() / "skills" / "validate-evidence" / "scripts" / "gate-evidence-folder.py"
    if not script.is_file():
        return "inconclusive", "gate-evidence-folder.py not found"
    proc = subprocess.run([sys.executable, str(script), ctx.task], text=True, capture_output=True, check=False)
    if proc.returncode == 0:
        return "pass", "every planned shot passes the folder gate"
    return "fail", bound(proc.stdout or proc.stderr, 600)


def resolve_base_ref(repo: Path, cfg: dict[str, Any]) -> str | None:
    for ref in (cfg.get("git") or {}).get("base_branches", []):
        if subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref], cwd=repo, capture_output=True,
                          check=False).returncode == 0:
            return ref
    return None


def git_run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)


def key_reachable(repo: Path, ref: str, key: str, key_re: re.Pattern[str]) -> bool:
    """A commit whose message carries exactly `key` is reachable from `ref` (`--grep` also hits `KEY-11` for `KEY-1`)."""
    raw = git_run(repo, "log", ref, "-F", f"--grep={key}", "--format=%B%x01").stdout
    return any(key in key_re.findall(message) for message in raw.split("\x01"))


def latest_release_graph(task: str) -> dict[str, Any] | None:
    found = []
    for path in (agents_home() / "prds" / "releases").glob("*.graph.json"):
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if any(m.get("key") == task for m in graph.get("members", [])):
            found.append((path.stat().st_mtime, graph))
    return max(found, key=lambda item: item[0])[1] if found else None


def gate_release_order(ctx: GateCtx) -> Gate:
    graph = latest_release_graph(ctx.task)
    if graph is None:
        return "pass", "no release graph"
    cfg = settings()
    for edge in graph.get("edges", []):
        if edge["class"] == "contradiction" and edge["confidence"] == "high" and ctx.task in (edge["from"], edge["to"]):
            quotes = " | ".join(f"{e['left']} vs {e['right']}" for e in edge["evidence"][:2])
            return "fail", f"contradiction: {edge['from']} / {edge['to']}: {bound(quotes, 400)}"
    incoming = [e for e in graph.get("edges", []) if e["class"] == "hard" and e["to"] == ctx.task]
    base = resolve_base_ref(ctx.repo, cfg)
    key_re = agentctl_config.key_pattern(cfg)
    notes: list[str] = []
    fetched = False
    for edge in incoming:
        dep = edge["from"]
        if edge["confidence"] != "high":
            notes.append(f"{dep} ({edge['confidence']} confidence) should land first")
            continue
        if base is None:
            return "fail", "no base branch in [git] base_branches; cannot tell whether " + dep + " is finished"
        if not key_reachable(ctx.repo, base, dep, key_re):
            fetch = git_run(ctx.repo, "fetch", "origin")
            fetched = True
            base = resolve_base_ref(ctx.repo, cfg) or base
            if not key_reachable(ctx.repo, base, dep, key_re):
                first = edge["evidence"][0]
                state = "git fetch origin failed: " + bound(fetch.stderr, 160) if fetch.returncode else "after git fetch origin"
                return "fail", (f"{dep} is not on {base} ({state}). Evidence {first['signal']}: "
                                f"{first['left']} | {first['right']}")
        if not key_reachable(ctx.repo, "HEAD", dep, key_re):
            notes.append(f"{dep} is on {base} but not in this branch")
    return "pass", "; ".join(notes) or ("dependencies finished" + (" (fetched origin)" if fetched else ""))


def check_owner_keys(repo: Path, base: str, path: str, key_re: re.Pattern[str]) -> list[str]:
    message = git_run(repo, "log", "-1", "--format=%B", base, "--", path).stdout
    return [k.upper() for k in key_re.findall(message)]


def foreign_checks(repo: Path, task: str, base: str, changed: list[tuple[str, str]], cfg: dict[str, Any]) -> list[tuple[str, str]]:
    """(path, owner key) for each check file this task edits, deletes or renames that another task owns."""
    key_re = agentctl_config.key_pattern(cfg)
    found = []
    for path, status in changed:
        if status[:1] not in ("M", "D", "R", "U") or not agentctl_release.is_check_file(path):
            continue
        owners = check_owner_keys(repo, base, path, key_re)
        if owners and task not in owners:
            found.append((path, owners[0]))
    return found


def gate_foreign_checks(ctx: GateCtx) -> Gate:
    cfg = settings()
    base = resolve_base_ref(ctx.repo, cfg)
    if base is None:
        return "pass", "no base branch"
    merge_base = git_run(ctx.repo, "merge-base", base, "HEAD").stdout.strip()
    if not merge_base:
        return "pass", "no merge base"
    raw = git_run(ctx.repo, "diff", "--name-status", "--find-renames", merge_base).stdout
    changed = []
    for line in raw.splitlines():
        parts = line.split("\t")
        changed.append((parts[1], parts[0]))
    hits = foreign_checks(ctx.repo, ctx.task, base, changed, cfg)
    if hits:
        return "fail", ", ".join(f"{p} owned by {k}" for p, k in hits)
    return "pass", "no check file of another task touched"


GATES: dict[str, Callable[[GateCtx], Gate]] = {
    "branch_is_task": gate_branch_is_task, "tbd_empty": gate_tbd_empty, "plan_valid": gate_plan_valid,
    "plan_valid_evidence": gate_plan_valid_evidence, "rehearsal_valid": gate_rehearsal_valid,
    "autonomy_check": gate_autonomy_check,
    "artifacts_exist": gate_artifacts_exist, "auth_state": gate_auth_state, "evidence_pass": gate_evidence_pass,
    "evidence_folder": gate_evidence_folder, "release_order": gate_release_order,
    "foreign_checks": gate_foreign_checks,
}


# --------------------------------------------------------------------------- report contract


REPORT_STATUSES = ("ok", "failed", "blocked")


def read_report(path: Path, limit: int) -> dict[str, Any] | None:
    """Validate the worker's report.json; None means missing or malformed (fall back to exit code + gates)."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or data.get("status") not in REPORT_STATUSES:
        return None
    raw_learnings = data.get("learnings")
    learnings = [bound(x, LEARNING_CHARS) for x in raw_learnings if isinstance(x, str)][:LEARNING_LIMIT] \
        if isinstance(raw_learnings, list) else []
    return {"status": data["status"], "summary": bound(str(data.get("summary", "")), limit),
            "artifacts": [str(a) for a in data.get("artifacts", []) if isinstance(a, str)],
            "blockers": [str(b) for b in data.get("blockers", [])], "next_hint": bound(str(data.get("next_hint", "")), 400),
            "learnings": learnings}


def extract_json(text: str) -> dict[str, Any] | None:
    with contextlib.suppress(json.JSONDecodeError):
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        with contextlib.suppress(json.JSONDecodeError):
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
    return None


def operator_rules(run: dict[str, Any], step: dict[str, Any]) -> str:
    cfg = run.get("settings") or {}
    git = (cfg.get("git") or {}).get("factory", {})
    tracker = (cfg.get("tracker") or {}).get("kind")
    if git.get("worker_git_writes"):
        rules = ("Git writes stay on the task branch: never force-push, never fast-forward, never push a "
                 "protected branch.")
    else:
        rules = ("Never run git commit, add, push, reset, merge or stash; the engine owns git writes "
                 "(commit, merge of the base, push).")
    if step["id"] == "post-evidence":
        return f"{rules} Make no {tracker} write except the evidence comment, and only in this step."
    return f"{rules} Make no {tracker or 'tracker'} write at all."


def step_prompt(run: dict[str, Any], step: dict[str, Any], handoff: str, report_path: Path,
                extra: str, findings: str) -> str:
    skill_args = step.get("args", "")
    parts = [
        f"Run the skill `{step['skill']}` for task `{run['task_id']}` (called_from: factory). {skill_args}".strip(),
        (f"Operator rules for this run (factory, headless): {operator_rules(run, step)} "
         f"You are in repo {run['repo']} on branch {run['branch']}; mode is {run['mode']}."),
        "Do not ask questions; this is a headless run. Stop after the skill's own end.",
        ("Bash: one command per call. The working directory is already the repo, so no `cd`, no `git -C`, no "
         "`export`, no `$?` or `$(...)`, no `;` or `&&` chains. Run `agentctl` by name (it is on PATH). "
         "Read files with Read, not `cat`."),
    ]
    if run.get("context"):
        parts.append(f"Handoff context file: {run['context']}")
    if handoff:
        parts.append("Previous steps (summaries only):\n" + handoff)
    if findings:
        parts.append("Findings to address:\n" + findings)
    if extra:
        parts.append(extra)
    keys = ("status (ok|failed|blocked), summary (<=1200 chars), artifacts (list of paths), blockers (list), "
            "next_hint")
    if step.get("role") not in NO_LEARNINGS_ROLES and step.get("id") != "kb-harvest":
        keys += (", learnings (optional, at most 3 strings of at most 300 chars: what cost time and what would "
                 "have avoided it)")
    parts.append(f"When finished write JSON to {report_path} with keys: {keys}.")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- engine


PENDING_DEPLOY = ("created", "running", "waiting", "blocked")


def review_deploy_state(deployments: list[dict[str, Any]],
                        contains: Callable[[str], bool]) -> tuple[str, dict[str, Any] | None]:
    """("ok" | "failed" | "pending", deciding deployment) for deployments listed newest first.

    ok: the newest successful deployment contains the head. failed: the newest deployment that contains the head
    failed or was canceled, with nothing newer still going. Anything else is still pending.
    """
    for deployment in deployments:
        status, has_head = deployment["status"], contains(deployment["sha"])
        if status in PENDING_DEPLOY:
            if has_head:
                return "pending", deployment
        elif status == "success":
            return ("ok" if has_head else "pending"), deployment
        elif has_head:
            return "failed", deployment
    return "pending", deployments[0] if deployments else None


class Parked(Exception):
    def __init__(self, reason: str, action: str = "", step_id: str | None = None, detail: Any = None) -> None:
        super().__init__(reason)
        self.reason, self.action, self.step_id, self.detail = reason, action, step_id, detail


class Engine:
    def __init__(self, task: str, adapters: dict[str, Any] | None = None,
                 sleep: Callable[[float], None] = time.sleep,
                 playwright_stop: Callable[[str], None] | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 host_factory: Callable[[], Any] | None = None) -> None:
        self.task = task
        self.dir = run_dir(task)
        self.adapters = adapters if adapters is not None else default_adapters()
        self.sleep = sleep
        self.clock = clock
        self.playwright_stop = playwright_stop or self._playwright_stop
        self.host_factory = host_factory
        self.events = read_events(self.dir)
        self.run = derive(self.events)
        self.started = self.clock()
        self.stop_requested = False
        self.only_step: str | None = None
        self.cfg = self.run.get("settings") or {}
        self.limits = dict(self.run.get("limits", {}))
        self.worker_cfg = dict(self.run.get("worker", {}))
        self.worker_cfg["disallowed_tools"] = list(self.worker_cfg.get("disallowed_tools", [])) + kit_deny_rules()
        self.repo = Path(self.run["repo"]) if self.run.get("repo") else Path.cwd()

    # -- state ----------------------------------------------------------------

    def emit_event(self, kind: str, **data: Any) -> None:
        self.events.append(append_event(self.dir, kind, **data))
        self.run = derive(self.events)
        write_snapshot(self.dir, self.run)

    def step(self, step_id: str) -> dict[str, Any]:
        for step in self.run["steps"]:
            if step["id"] == step_id:
                return step
        raise FactoryError(f"unknown step id {step_id!r}")

    def spec(self, step_id: str) -> dict[str, Any]:
        for spec in self.run["step_specs"]:
            if spec["id"] == step_id:
                return spec
        raise FactoryError(f"unknown step id {step_id!r}")

    def _playwright_stop(self, task: str) -> None:
        script = agents_home() / "mcp" / "playwright.py"
        if script.is_file():
            subprocess.run([sys.executable, str(script), "stop", task], capture_output=True, text=True, check=False)

    # -- lifecycle ------------------------------------------------------------

    def reconcile(self) -> None:
        """Mark steps left `running` by a dead engine as interrupted and kill their live workers."""
        for step in self.run["steps"]:
            if step["status"] == "running":
                kill_worker(step.get("pid"), step.get("session_id"))
                self.emit_event("interrupted", id=step["id"], reason="engine_gone")

    def execute(self) -> str:
        """Run the pipeline from the first unfinished step to a terminal state."""
        previous = signal.signal(signal.SIGTERM, self._on_term)
        try:
            self.reconcile()
            self.run_steps()
            if self.run["state"] == "running":
                final = "awaiting_human_review"
                outcome = {"path": (self.run.get("route") or {}).get("path", "standard")}
                self.emit_event("run_finished", state=final, **outcome)
        except Parked as park:
            self.emit_event("park", reason=park.reason, action=park.action, id=park.step_id, detail=park.detail)
            self.auto_harvest(park)
        except _Stopped:
            self.emit_event("stopped")
        finally:
            signal.signal(signal.SIGTERM, previous)
            self.emit_event("engine_stopped", elapsed_s=self.clock() - self.started)
            self.cleanup()
        return self.run["state"]

    def _on_term(self, _signum: int, _frame: Any) -> None:
        self.stop_requested = True
        for step in self.run["steps"]:
            if step["status"] == "running":
                kill_worker(step.get("pid"), step.get("session_id"))

    def cleanup(self) -> None:
        if any(self.step(i)["status"] != "pending" for i in EVIDENCE_STEPS if self._has_step(i)):
            with contextlib.suppress(Exception):
                self.playwright_stop(self.task)

    def _has_step(self, step_id: str) -> bool:
        return any(s["id"] == step_id for s in self.run["steps"])

    def check_caps(self) -> None:
        if self.stop_requested:
            raise _Stopped
        if self.run["cost_usd"] >= self.limits["run_usd"]:
            raise Parked("cap_cost", f"Cost cap USD {self.limits['run_usd']} reached; raise it with resume or review the run.")
        elapsed = self.clock() - self.started + self.run.get("elapsed_s", 0)
        if elapsed >= self.limits["run_hours"] * 3600:
            raise Parked("cap_time", f"Wall-clock cap {self.limits['run_hours']} h reached.")

    def harvest_cursor(self) -> int:
        return harvest_cursor_of(self.events)

    def writable_roots(self) -> list[str]:
        """Codex sandbox roots for one run: the repo, the run folder, the task's plan and PRD folders, and
        [factory.worker] codex_writable_extra. The agents home's kit folders are never listed."""
        home = agents_home()
        extra = [str(p) for p in self.worker_cfg.get("codex_writable_extra", [])]
        return [str(self.repo), str(self.dir), str(home / "plans" / self.task), str(home / "prds"), *extra]

    def write_harvest_digest(self, step: dict[str, Any]) -> bool:
        """Write digest.json into the harvest step folder; False when there is nothing to harvest."""
        digest = run_digest(self.dir, self.harvest_cursor(), self.limits)
        if not digest["has_signals"]:
            return False
        folder = self.dir / "steps" / f"{step['index']:02d}-{step['id']}"
        folder.mkdir(parents=True, exist_ok=True)
        atomic_write(folder / DIGEST_NAME, json.dumps(digest, indent=2, ensure_ascii=False))
        return True

    def auto_harvest(self, park: Parked) -> None:
        """One harvest for a parked run that has signals. The run keeps its state, the tail harvest stays pending.
        Cost and time parks are the operator's limits and get none. Errors never escape: they become an event."""
        if park.reason in AUTO_HARVEST_EXEMPT or not any(s["id"] == "kb-harvest" for s in self.run["steps"]):
            return
        step = self.step("kb-harvest")
        try:
            if not self.write_harvest_digest(step):
                return
            self.run_step("kb-harvest")
            self.emit_event("reset", id="kb-harvest")
            self.emit_event("kb_harvest_done", through=len(self.events), auto=True)
        except Exception as exc:  # noqa: BLE001 - the harvest must never mask the park it follows
            self.emit_event("auto_harvest_failed", reason=bound(f"{type(exc).__name__}: {exc}", 300))

    def run_steps(self) -> None:
        index = 0
        steps = self.run["steps"]
        while index < len(steps):
            step = steps[index]
            if self.only_step and step["id"] != self.only_step:
                index += 1
                continue
            if step["status"] in ("ok", "skipped"):
                index += 1
                continue
            if step["id"] == "plan-rehearsal" and not (self.run.get("rehearsal") or {}).get("required"):
                self.emit_event("step_skipped", id=step["id"], reason="no rehearsal required")
                steps = self.run["steps"]
                index += 1
                continue
            if step["id"] == "kb-harvest" and not self.write_harvest_digest(step):
                self.emit_event("step_skipped", id=step["id"], reason="no harvest signals")
                steps = self.run["steps"]
                index += 1
                continue
            modes = self.spec(step["id"]).get("modes")
            if modes and self.run["mode"] not in modes:
                self.emit_event("step_skipped", id=step["id"], reason=f"mode {self.run['mode']}")
                steps = self.run["steps"]
                index += 1
                continue
            self.run_step(step["id"])
            step = self.step(step["id"])
            jump = self.after_step(step)
            if self.only_step:
                return
            if jump is not None:
                index = jump
            elif self.run["state"] != "running":
                return
            else:
                index += 1
            steps = self.run["steps"]

    # -- step execution -------------------------------------------------------

    def run_step(self, step_id: str) -> None:
        spec = self.spec(step_id)
        step = self.step(step_id)
        self.pre_gates(spec, step)
        if step_id == "validate-plan" and plan_dir(self.task).is_dir():
            before = self.dir / "snapshots" / "plan-before-validate"
            shutil.rmtree(before, ignore_errors=True)
            shutil.copytree(plan_dir(self.task), before)
        if spec["kind"] == "deterministic":
            self.run_deterministic(spec)
            return
        if spec["kind"] == "builtin":
            self.run_builtin(spec)
            return
        while True:
            self.check_caps()
            step = self.step(step_id)
            outcome = self.attempt(spec, step)
            if outcome == "ok":
                return

    def pre_gates(self, spec: dict[str, Any], step: dict[str, Any]) -> None:
        names = list(spec.get("pre", []))
        if self.run["mode"] == "tracker" and spec["id"] == "run-plan" and "branch_is_task" not in names:
            names.append("branch_is_task")
        for name in names:
            ctx = GateCtx(self.task, step, self.run, self.repo, None, None, self.dir)
            result, detail = GATES[name](ctx)
            self.emit_event("gate", id=spec["id"], name=name, result=result, detail=bound(detail, 600), phase="pre")
            if result == "fail":
                reason = {"auth_state": "no_auth_state", "branch_is_task": "wrong_branch",
                          "release_order": "contradiction" if detail.startswith("contradiction:")
                          else "blocked_by_dependency"}.get(name, f"gate_{name}")
                raise Parked(reason, detail, spec["id"])

    def run_deterministic(self, spec: dict[str, Any]) -> None:
        self.emit_event("step_started", id=spec["id"], model=None, vendor=None, role=spec["role"],
                        session_id=None, pid=None)
        proc = subprocess.run(spec["argv"], cwd=self.repo, text=True, capture_output=True, check=False)
        status = "ok" if proc.returncode == 0 else "failed"
        self.emit_event("step_finished", id=spec["id"], status=status, summary=bound(proc.stdout, 400),
                        cost_usd=0.0, reason=None if status == "ok" else "exit_code")
        if status != "ok":
            raise Parked("deterministic_step_failed", bound(proc.stderr or proc.stdout, 400), spec["id"])

    # -- builtin git steps: the engine owns commit, merge of the base, push --------

    def git(self, *args: str, timeout: float = 300) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=self.repo, text=True, capture_output=True, timeout=timeout, check=False)

    def git_policy(self) -> dict[str, Any]:
        return (self.cfg.get("git") or {}).get("factory", {})

    def builtin_skip_reason(self, spec: dict[str, Any]) -> str | None:
        policy = self.git_policy()
        name = spec["builtin"]
        if name == "rehearsal-gate":
            return self.rehearsal_gate_skip_reason()
        if name == "commit" and not policy.get("commit"):
            return "policy: [git.factory] commit = false"
        if name.startswith("sync-"):
            if not (self.cfg.get("sync") or {}).get("enabled"):
                return "policy: [sync] enabled = false"
            if "origin" not in self.git("remote").stdout.split():
                return "no remote named origin"
        if name in ("integrate", "push", "deploy-review"):
            install = name == "deploy-review" and (self.review_env() or {}).get("kind") == "install"
            if not install and not policy.get("push"):
                return "policy: [git.factory] push = false"
            if "origin" not in self.git("remote").stdout.split():
                return "no remote named origin"
        if name in ("deploy-review", "await-review"):
            if name == "deploy-review" and not policy.get("deploy_review"):
                return "policy: [git.factory] deploy_review = false"
            if self.review_env() is None:
                return "no [review_env] table for this repo's origin project"
        return None

    def run_builtin(self, spec: dict[str, Any]) -> None:
        reason = self.builtin_skip_reason(spec)
        if reason:
            self.emit_event("step_skipped", id=spec["id"], reason=reason)
            return
        self.emit_event("step_started", id=spec["id"], model=None, vendor=None, role=spec["role"],
                        session_id=None, pid=None)
        try:
            summary = getattr(self, "builtin_" + spec["builtin"].replace("-", "_"))(spec)
        except Parked:
            self.emit_event("step_finished", id=spec["id"], status="failed", summary=None, cost_usd=0.0,
                            reason=spec["builtin"] + "_failed")
            raise
        self.emit_event("step_finished", id=spec["id"], status="ok", summary=bound(summary, 400), cost_usd=0.0,
                        reason=None)

    def rehearsal_gate_skip_reason(self) -> str | None:
        if not (self.run.get("rehearsal") or {}).get("required"):
            return "no rehearsal required"
        try:
            raw = (plan_dir(self.task) / "rehearsal.json").read_bytes()
            gate = json.loads(raw).get("gate") or {}
        except (OSError, json.JSONDecodeError):
            return None  # unreadable: the builtin parks instead of skipping
        approved = (self.run.get("rehearsal") or {}).get("approved_sha256")
        if gate.get("argv") is None and approved == hashlib.sha256(raw).hexdigest():
            return f"gate.argv is null: {gate.get('reason_if_null') or 'no reason given'}"
        return None  # unapproved or changed: the builtin parks instead of skipping

    def builtin_rehearsal_gate(self, spec: dict[str, Any]) -> str:
        """Re-check the approved rehearsal just before the install. Runs only the approved argv, never an install."""
        step_id = spec["id"]
        approved = (self.run.get("rehearsal") or {}).get("approved_sha256")
        path = plan_dir(self.task) / "rehearsal.json"
        if not approved:
            raise Parked("rehearsal_ready", f"{plan_dir(self.task) / 'rehearsal.md'}; approve with "
                         f"`agentctl factory resume {self.task} --approve-rehearsal`", step_id)
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise Parked("rehearsal_changed", f"{path} unreadable: {exc}", step_id) from exc
        if hashlib.sha256(raw).hexdigest() != approved:
            raise Parked("rehearsal_changed", f"{path} differs from the approved version; read it and re-approve",
                         step_id)
        gate = json.loads(raw).get("gate") or {}
        backup = agents_home() / "prds" / self.task / "review-backup"
        sources = gate.get("source_hashes") or {}
        for rel, digest in sources.items():
            file = backup / rel
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                raise Parked("rehearsal_drift", f"source changed since the rehearsal: {rel}", step_id,
                             detail={"source": rel})
        timeout = int(gate.get("timeout_s") or 600)
        output = (backup / str(gate.get("output", ""))).resolve()
        if backup.resolve() not in output.parents:
            raise Parked("rehearsal_gate_failed", f"gate.output {gate.get('output')!r} is outside {backup}", step_id)
        output.unlink(missing_ok=True)
        try:
            proc = subprocess.run([sys.executable, "-I", *gate["argv"]], cwd=backup, text=True,
                                  capture_output=True, timeout=timeout, check=False, shell=False)
        except subprocess.TimeoutExpired as exc:
            raise Parked("rehearsal_gate_failed", f"gate timed out after {timeout}s", step_id) from exc
        if proc.returncode != 0:
            raise Parked("rehearsal_gate_failed", bound(proc.stderr or proc.stdout, 400), step_id)
        try:
            got = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise Parked("rehearsal_gate_failed", f"gate output {output} unreadable: {exc}", step_id) from exc
        expected = gate.get("expected") or {}
        diff = {key: [expected.get(key), got.get(key)] for key in gate.get("keys") or [] if got.get(key) != expected.get(key)}
        if diff:
            raise Parked("rehearsal_drift", "; ".join(f"{k}: expected {e}, got {g}" for k, (e, g) in diff.items()),
                         step_id, detail=diff)
        return f"rehearsal gate passed: {len(expected)} expected values match, {len(sources)} sources unchanged"

    def require_task_branch(self, spec: dict[str, Any]) -> str:
        branch = self.git("branch", "--show-current").stdout.strip()
        if self.run["mode"] == "tracker" and branch != self.task:
            raise Parked("wrong_branch", f"branch {branch!r} is not {self.task!r}", spec["id"])
        return branch

    def builtin_commit(self, spec: dict[str, Any]) -> str:
        self.require_task_branch(spec)
        if not self.git("status", "--porcelain").stdout.strip():
            return "nothing to commit"
        names = set(self.git("ls-files", "-m", "-o", "--exclude-standard").stdout.splitlines())
        names |= set(self.git("diff", "--cached", "--name-only").stdout.splitlines())
        never = self.git_policy().get("never_stage", [])
        hits = sorted(n for n in names if any(fnmatch.fnmatch(Path(n).name, pat) or fnmatch.fnmatch(n, pat)
                                              for pat in never))
        if hits:
            raise Parked("never_stage", "Files matching [git.factory] never_stage are in the change: " + ", ".join(hits),
                         spec["id"])
        artifacts = self.step("lint-commit").get("artifacts") or []
        draft = Path(artifacts[0]).expanduser() if artifacts else None
        if not draft or not draft.is_file():
            raise Parked("no_commit_message", "lint-commit left no commit message draft to commit with.", spec["id"])
        if re.search(r"co-authored-by:", draft.read_text(encoding="utf-8"), re.IGNORECASE):
            raise Parked("commit_message_trailer", f"{draft} carries a Co-authored-by trailer.", spec["id"])
        add = self.git("add", "-A")
        commit = self.commit_with(spec, draft.read_text(encoding="utf-8")) if add.returncode == 0 else add
        if commit.returncode != 0:
            raise Parked("commit_failed", bound(commit.stdout + commit.stderr, 600), spec["id"])
        self.emit_event("baseline_updated", git_baseline=git_baseline(self.repo))
        return "committed " + self.git("rev-parse", "--short", "HEAD").stdout.strip()

    def sign(self, message: str) -> str:
        return sign_message(message, self.git_policy().get("signature", ""))

    def commit_with(self, spec: dict[str, Any], message: str, *args: str) -> subprocess.CompletedProcess[str]:
        """`git commit` with the signed message in a file next to the step's other artifacts."""
        step_dir = self.dir / "steps" / f"{self.step(spec['id'])['index']:02d}-{spec['id']}"
        step_dir.mkdir(parents=True, exist_ok=True)
        path = step_dir / "commit-message.txt"
        path.write_text(self.sign(message), encoding="utf-8")
        return self.git("commit", *args, "-F", str(path))

    def base_ref(self) -> str | None:
        return resolve_base_ref(self.repo, self.cfg)

    def unmerged(self) -> list[str]:
        return self.git("diff", "--name-only", "--diff-filter=U").stdout.split()

    def builtin_integrate(self, spec: dict[str, Any]) -> str:
        self.require_task_branch(spec)
        fetch = self.git("fetch", "origin", timeout=180)
        if fetch.returncode != 0:
            raise Parked("fetch_failed", bound(fetch.stderr, 400), spec["id"])
        base = self.base_ref()
        if not base:
            raise Parked("no_base_branch", "None of [git] base_branches exists in this repo.", spec["id"])
        mid_merge = self.git("rev-parse", "-q", "--verify", "MERGE_HEAD").returncode == 0
        if not mid_merge and self.git("merge-base", "--is-ancestor", base, "HEAD").returncode == 0:
            return f"up to date with {base}"
        old_head = self.git("rev-parse", "HEAD").stdout.strip()
        resolved: list[str] = []
        if not mid_merge:
            branch = self.git("branch", "--show-current").stdout.strip()
            message = self.sign(f"Merge {base} into {branch}")
            merge = self.git("merge", "--no-ff", "-m", message, base)
            if merge.returncode != 0:
                if not self.unmerged():
                    self.git("merge", "--abort")
                    raise Parked("merge_failed", bound(merge.stdout + merge.stderr, 600), spec["id"])
                mid_merge = True
        if mid_merge:
            changed = [(path, "U") for path in self.unmerged()]
            foreign = foreign_checks(self.repo, self.task, base, changed, self.cfg)
            if foreign:
                self.git("merge", "--abort")
                raise Parked("foreign_check_touched", "Conflicts in check files of other tasks: "
                             + ", ".join(f"{p} owned by {k}" for p, k in foreign), spec["id"], detail=foreign)
            resolved = self.resolve_conflicts(spec, base)
            done = self.commit_with(spec, f"Merge {base} into {self.git('branch', '--show-current').stdout.strip()}")
            if done.returncode != 0:
                self.git("merge", "--abort")
                raise Parked("merge_failed", bound(done.stdout + done.stderr, 600), spec["id"])
        new_head = self.git("rev-parse", "HEAD").stdout.strip()
        if new_head != old_head and len(self.git("rev-list", "--parents", "-n1", "HEAD").stdout.split()) < 3:
            raise Parked("fast_forward_detected", f"HEAD moved to a non-merge commit while integrating {base}.",
                         spec["id"])
        self.emit_event("baseline_updated", git_baseline=git_baseline(self.repo))
        if resolved:
            self.emit_event("conflicts_resolved", id=spec["id"], files=resolved, base=base)
            return f"merged {base} (--no-ff), resolved conflicts in {', '.join(resolved)}"
        return f"merged {base} (--no-ff)"

    def resolve_conflicts(self, spec: dict[str, Any], base: str) -> list[str]:
        files = self.unmerged()
        vendor = self.run.get("vendor", "claude")
        adapter = self.adapters.get(vendor)
        if adapter is None:
            self.git("merge", "--abort")
            raise Parked("adapter_missing", f"No adapter for vendor {vendor} to resolve conflicts.", spec["id"])
        model, effort = resolve_role(spec["role"], vendor)
        step_dir = self.dir / "steps" / f"{self.step(spec['id'])['index']:02d}-{spec['id']}"
        for attempt in range(2):
            self.check_caps()
            files = self.unmerged() or files
            req = WorkerRequest(
                prompt=(f"Merging {base} into the task branch of task {self.task} left conflicts in: "
                        f"{', '.join(files)}. Edit those files to remove every conflict marker, keeping the intent "
                        f"of both sides and the behaviour the plan at {plan_dir(self.task)} requires. Do not run any "
                        "git command and do not touch other files. When done write a JSON object with keys "
                        f"status (ok or failed) and summary to {step_dir / 'resolver.json'}."),
                model=model, effort=effort, cwd=self.repo, step_dir=step_dir / "resolver", session_id=str(uuid.uuid4()),
                timeout_s=self.limits["step_timeout_min"] * 60,
                budget_usd=self.limits["budget_usd"].get(spec["role"], 8),
                allowed_tools=list(self.worker_cfg["allowed_tools"]),
                disallowed_tools=self.worker_cfg["disallowed_tools"],
                permission_mode=self.worker_cfg["permission_mode"], label="resolver")
            result = adapter.run(req)
            if result.cost_usd:
                self.emit_event("decision", id=spec["id"], decision="resolver_cost", source="engine",
                                reason="conflict resolver", cost_usd=result.cost_usd)
            marked = [f for f in files if (self.repo / f).is_file()
                      and re.search(r"^(<<<<<<<|>>>>>>>) ", (self.repo / f).read_text(errors="ignore"), re.MULTILINE)]
            if not marked:
                add = self.git("add", "--", *files)
                if add.returncode == 0 and not self.unmerged():
                    return files
        self.git("merge", "--abort")
        raise Parked("merge_conflict", f"Conflicts in {', '.join(files)} were not resolved after merging {base}; "
                     "the merge was aborted.", spec["id"], detail=files)

    # -- parallel-issue sync (plan factory-sync) ------------------------------------

    def sync_host(self) -> Any:
        try:
            if self.host_factory:
                return self.host_factory()
            return agentctl_githost.adapter_for(self.cfg, self.repo, agents_home() / ".auth")
        except agentctl_githost.HostError as exc:
            raise Parked("host_unavailable", f"Git host not usable: {exc}", self.run.get("current")) from exc

    def sync_scan(self, spec: dict[str, Any]) -> dict[str, Any]:
        adapter = self.sync_host()
        try:
            related = agentctl_sync.load_related(self.task, None, agents_home() / "prds")
        except agentctl_sync.SyncError as exc:
            raise Parked("sync_blocked", str(exc), spec["id"]) from exc
        classes = agentctl_sync.classes_from_summary(self.step("related-plan").get("summary") if self._has_step("related-plan") else None,
                                                     self.step("related-impl").get("summary") if self._has_step("related-impl") else None)
        used = len([e for e in self.events if e["type"] == "sync_proposal"])
        result = agentctl_sync.scan(self.task, self.repo, self.cfg, adapter, related, classes, proposals_this_run=used)
        (self.dir / "sync").mkdir(exist_ok=True)
        atomic_write(self.dir / "sync" / f"scan-{spec['id']}.json", json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        self.emit_event("sync_scan", id=spec["id"], status=result["status"],
                        inbox=[{k: r[k] for k in ("id", "state", "source_branch", "acknowledged", "factory_proposal")}
                               for r in result["inbox"]],
                        outbox=result["outbox"], unclassified=result["unclassified"])
        if result["status"] != "ok":
            raise Parked("host_unavailable", "; ".join(result["warnings"]) or "host unavailable", spec["id"])
        return result

    def builtin_sync_inbox(self, spec: dict[str, Any]) -> str:
        scan = self.sync_scan(spec)
        pending = [r for r in scan["inbox"] if r["factory_proposal"] and not r["acknowledged"]]
        if pending:
            raise Parked("sync_blocked",
                         "Open proposals into this branch need a decision (merge or close them, then resume): "
                         + "; ".join(f"!{r['id']} from {r['marker']['from']} ({r['marker']['class']}, "
                                     f"{', '.join(r['marker']['files'][:3])})" for r in pending),
                         spec["id"], detail=pending)
        return f"inbox: {len(scan['inbox'])} request(s), none pending"

    def builtin_sync_outbox(self, spec: dict[str, Any]) -> str:
        scan = self.sync_scan(spec)
        notes: list[str] = []
        unconfirmed: list[dict[str, Any]] = []
        for item in scan["outbox"]:
            action = item["action"]
            if action == "park_contradiction":
                if agentctl_sync.acknowledged(plan_dir(self.task), item["key"]):
                    notes.append(f"{item['key']}: contradiction acknowledged in the plan")
                    continue
                raise Parked("proposal_contradiction",
                             f"{item['key']} contradicts this task ({item['reason']}). Record the decision in the plan "
                             "naming the issue key, or settle it with the owners, then resume.", spec["id"], detail=item)
            if action == "confirm" and agentctl_sync.confirmed(plan_dir(self.task), item["key"]):
                action = "proposal"
            if action == "confirm":
                unconfirmed.append(item)
            elif action == "proposal":
                notes.append(self.sync_propose(spec, item))
            elif action == "append":
                notes.append(self.sync_append(spec, item))
            else:
                notes.append(f"{item['key']}: {action}")
        for key in scan["unclassified"]:
            notes.append(f"{key}: no relation class, left alone")
        if unconfirmed:
            plan = plan_dir(self.task)
            raise Parked("proposal_needs_confirmation",
                         "An earlier proposal for these related issues was closed without a merge, so no new one is "
                         "opened or reopened without a human: " + ", ".join(i["key"] for i in unconfirmed)
                         + f". To allow one, add the line `confirm-proposal: KEY` to {plan / 'sync-confirmed.md'}, then resume.",
                         spec["id"], detail=unconfirmed)
        return "; ".join(notes) or "no related issues to sync"

    def sync_append(self, spec: dict[str, Any], item: dict[str, Any]) -> str:
        adapter = self.sync_host()
        requests = adapter.list_review_requests(source=item["proposal_branch"])
        if not requests:
            return f"{item['key']}: open proposal vanished"
        request = requests[0]
        adapter.comment(request.id, sign_message(f"{self.task} was updated; the proposal still applies to {item['branch']}.",
                                                 self.git_policy().get("signature", "")))
        self.emit_event("sync_proposal", id=spec["id"], pair=item["pair"], request=request.id, appended=True)
        return f"{item['key']}: appended to !{request.id}"

    def git_in(self, cwd: Path, *args: str, timeout: float = 300) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)

    def sync_propose(self, spec: dict[str, Any], item: dict[str, Any]) -> str:
        """A signed proposal in a temporary worktree of the related branch. The task checkout is never touched."""
        if not self.git_policy().get("push"):
            return f"{item['key']}: proposals need [git.factory] push"
        sync_cfg = self.cfg["sync"]
        destination, branch, files = item["branch"], item["proposal_branch"], item["files"]
        protected = (self.cfg.get("git") or {}).get("protected_branches", [])
        if not branch.startswith("proposal/") or branch == destination or {branch, destination} & set(protected):
            raise Parked("sync_blocked", f"refusing to propose {branch!r} into {destination!r}", spec["id"])
        before = git_baseline(self.repo)
        base = (agentctl_sync.load_related(self.task, None, agents_home() / "prds").get("base") or "origin/master")
        mine = set(self.git("diff", "--name-only", f"{base}...HEAD").stdout.split())
        files = [f for f in files if f in mine] or files
        worktree = self.dir / "sync" / item["pair"]
        shutil.rmtree(worktree, ignore_errors=True)
        try:
            added = self.git("worktree", "add", "-b", branch, str(worktree), f"origin/{destination}")
            if added.returncode != 0:
                raise Parked("sync_blocked", bound(added.stderr, 400), spec["id"])
            diff = self.git("diff", f"{base}...HEAD", "--", *files).stdout
            self.sync_worker(spec, item, worktree, files, bound(diff, 6000))
            changed = [line[3:].strip() for line in self.git_in(worktree, "status", "--porcelain").stdout.splitlines()]
            outside = sorted(set(changed) - set(files))
            if outside:
                raise Parked("sync_blocked", f"the proposal worker changed files outside the marker: {', '.join(outside)}",
                             spec["id"], detail=outside)
            if not changed:
                return f"{item['key']}: nothing to propose into {destination}"
            marker = agentctl_sync.build_marker(self.task, item["key"], item["class"],
                                                self.git("rev-parse", f"origin/{destination}").stdout.strip(), changed)
            message = f"Proposal from {self.task} into {item['key']}"
            signature = self.git_policy().get("signature", "")
            self.git_in(worktree, "add", "--", *changed)
            commit = self.git_in(worktree, "commit", "-m", sign_message(message, signature))
            if commit.returncode != 0:
                raise Parked("sync_blocked", bound(commit.stdout + commit.stderr, 400), spec["id"])
            push = self.git_in(worktree, "push", "-u", "origin", branch, timeout=180)
            if push.returncode != 0:
                raise Parked("push_rejected", bound(push.stdout + push.stderr, 400), spec["id"])
            description = agentctl_sync.render_description(
                f"{self.task} proposes a {item['class']} change into {item['key']} ({', '.join(changed[:5])}).",
                marker, block=sync_cfg["marker_block"], signature=signature)
            request = self.sync_host().create(branch, destination, f"[{self.task}] Proposal into {item['key']}",
                                              description, [sync_cfg["marker_label"]])
            self.emit_event("sync_proposal", id=spec["id"], pair=item["pair"], request=request.id, files=changed,
                            appended=False)
            return f"{item['key']}: proposal !{request.id} into {destination}"
        finally:
            self.git("worktree", "remove", "--force", str(worktree))
            self.git("branch", "-D", branch)
            if git_baseline(self.repo) != before:
                raise Parked("git_baseline_violation", "the task checkout changed while a proposal was prepared", spec["id"])

    def sync_worker(self, spec: dict[str, Any], item: dict[str, Any], worktree: Path, files: list[str], diff: str) -> None:
        vendor = self.run.get("vendor", "claude")
        adapter = self.adapters.get(vendor)
        if adapter is None:
            raise Parked("adapter_missing", f"No adapter for vendor {vendor} to prepare a proposal.", spec["id"])
        model, effort = resolve_role("build", vendor)
        req = WorkerRequest(
            prompt=(f"Task {self.task} changes these files and the related issue {item['key']} ({item['class']}) "
                    f"works on the branch checked out here. Make the smallest change in this checkout that keeps "
                    f"{item['key']}'s branch compatible with {self.task}'s change. Edit only: {', '.join(files)}. "
                    f"Do not run git commands. Here is {self.task}'s change to those files:\n{diff}"),
            model=model, effort=effort, cwd=worktree, step_dir=self.dir / "sync" / f"worker-{item['pair']}",
            session_id=str(uuid.uuid4()), timeout_s=self.limits["step_timeout_min"] * 60,
            budget_usd=self.limits["budget_usd"].get("build", 8), allowed_tools=list(self.worker_cfg["allowed_tools"]),
            disallowed_tools=self.worker_cfg["disallowed_tools"], permission_mode=self.worker_cfg["permission_mode"],
            label="sync-proposal")
        result = adapter.run(req)
        if result.cost_usd:
            self.emit_event("decision", id=spec["id"], decision="proposal_cost", source="engine",
                            reason="proposal worker", cost_usd=result.cost_usd)

    def builtin_sync_notice(self, spec: dict[str, Any]) -> str:
        scan = next((e for e in reversed(self.events) if e["type"] == "sync_scan" and e["id"] == "sync-outbox"), None)
        wanted = [i for i in (scan or {}).get("outbox", []) if i["action"] == "notice_restricted"]
        if not wanted:
            return "no related issue without a branch"
        tracker = agentctl_config.tracker(self.cfg) or {}
        visibility = tracker.get("restricted_comment_visibility")
        if tracker.get("kind") != "jira" or not visibility or ":" not in visibility:
            raise Parked("restricted_comment_unavailable",
                         "No restricted-comment method is configured for this tracker; see "
                         "kb/implementation/How-to-leave-a-restricted-comment-on-the-tracker.md.", spec["id"])
        group = visibility.split(":", 1)[1]
        picked = agentctl_json("jira", "request", "GET", f"/rest/api/3/groups/picker?query={urllib.parse.quote(group)}")
        names = [g.get("name") for g in (picked.get("result") or {}).get("groups", [])]
        if group not in names:
            raise Parked("restricted_comment_unavailable", f"Jira group {group!r} was not found; nothing was posted.", spec["id"])
        notes = []
        for item in wanted:
            notes.append(self.post_restricted_notice(spec, item, visibility, group))
        return "; ".join(notes)

    def post_restricted_notice(self, spec: dict[str, Any], item: dict[str, Any], visibility: str, group: str) -> str:
        key, pair = item["key"], item["pair"]
        marker = f"[agentctl-sync notice {pair}]"
        existing = agentctl_json("jira", "request", "GET", f"/rest/api/3/issue/{key}/comment")
        if marker in json.dumps(existing):
            return f"{key}: notice already there"
        body = (f"{marker}\n\n{self.task} overlaps with this issue ({item['class']}"
                + (f", files: {', '.join(item['files'][:5])}" if item["files"] else "")
                + ") and this issue has no branch yet. Check the other branch before starting.")
        path = self.dir / "sync" / f"notice-{pair}.txt"
        path.parent.mkdir(exist_ok=True)
        path.write_text(body, encoding="utf-8")
        posted = agentctl_json("jira", "comment", key, "--body-file", str(path), "--visibility", visibility,
                               "--confirm-issue", key, "--allow-second")  # the marker lookup above is the duplicate guard
        comment_id = posted.get("id")
        if posted.get("status") != "ok" or not comment_id:
            raise Parked("restricted_comment_unavailable", f"posting the notice on {key} failed: {posted}", spec["id"])
        back = (agentctl_json("jira", "request", "GET", f"/rest/api/3/issue/{key}/comment/{comment_id}").get("result") or {})
        seen = back.get("visibility") or {}
        if seen.get("type") != "group" or seen.get("value") != group:
            raise Parked("restricted_comment_unavailable",
                         f"comment {comment_id} on {key} was posted WITHOUT visibility {visibility!r}; restrict or "
                         "remove it now.", spec["id"], detail=back)
        self.emit_event("sync_notice", id=spec["id"], pair=pair, issue=key, comment=comment_id, visibility=visibility)
        return f"{key}: restricted notice {comment_id}"

    def builtin_push(self, spec: dict[str, Any]) -> str:
        branch = self.require_task_branch(spec)
        protected = (self.cfg.get("git") or {}).get("protected_branches", [])
        if branch in protected:
            raise Parked("protected_branch", f"Refusing to push {branch!r}: it is in [git] protected_branches.",
                         spec["id"])
        push = self.git("push", "-u", "origin", branch, timeout=180)
        if push.returncode != 0:
            raise Parked("push_rejected", bound(push.stdout + push.stderr, 600) +
                         f" If the remote moved, run `agentctl factory step {self.task} integrate`, then resume.",
                         spec["id"])
        local = self.git("rev-parse", "HEAD").stdout.strip()
        remote = self.git("rev-parse", f"origin/{branch}").stdout.strip()
        if local != remote:
            raise Parked("push_unverified", f"origin/{branch} is {remote[:10]}, local HEAD is {local[:10]}.", spec["id"])
        return f"pushed {branch} to origin at {local[:10]}"

    # -- review environment: merge into the branch it deploys from, wait for the deploy ---

    def origin_project(self) -> str | None:
        """origin's `group/repo` on the configured git host, or None when there is no origin or it is not a host URL."""
        url = self.git("remote", "get-url", "origin")
        if url.returncode != 0:
            return None
        try:
            return agentctl_githost.remote_project(url.stdout.strip())[1]
        except agentctl_githost.HostError:
            return None

    def repo_tools(self) -> list[str]:
        """Extra worker tool patterns for this repo: `[factory.repo_tools."group/repo"] allowed_tools`, by origin."""
        project = self.origin_project()
        entry = ((self.cfg.get("factory") or {}).get("repo_tools") or {}).get(project) if project else None
        return list((entry or {}).get("allowed_tools", []))

    def review_env(self) -> dict[str, Any] | None:
        """The `[review_env."group/repo"]` table of origin's project, or None."""
        project = self.origin_project()
        if project is None:
            return None
        entry = (self.cfg.get("review_env") or {}).get(project)
        if not entry:
            return None
        env = {"project": project, "kind": "branch", **entry}
        if env["kind"] not in ("branch", "install"):
            raise FactoryError(f'[review_env."{project}"] kind must be "branch" or "install", not {env["kind"]!r}')
        if env["kind"] == "install":
            missing = [key for key in ("artifact", "backup", "install", "restore", "verify") if not env.get(key)]
            if missing:
                raise FactoryError(f'[review_env."{project}"] kind = "install" needs {", ".join(missing)}')
        return env

    def repo_path(self, value: str) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else self.repo / path

    def artifact_sha(self, env: dict[str, Any], step_id: str) -> str:
        """sha256 of the one built artifact the install kind names (a glob relative to the repo)."""
        matches = sorted(p for p in self.repo.glob(env["artifact"]) if p.is_file())
        if not matches:
            raise Parked("artifact_missing", f"No file matches artifact {env['artifact']!r}: build it first.", step_id)
        if len(matches) > 1:
            raise Parked("artifact_ambiguous", f"{env['artifact']!r} matches {len(matches)} files; keep one build.",
                         step_id, detail=[str(p) for p in matches])
        return hashlib.sha256(matches[0].read_bytes()).hexdigest()

    def install_verify(self, env: dict[str, Any]) -> tuple[set[str], str]:
        """Run the read-only `verify` probe. Returns the sha256 values it printed and its bounded output."""
        argv = env["verify"] if isinstance(env["verify"], list) else shlex.split(env["verify"])
        try:
            proc = subprocess.run(argv, cwd=self.repo, text=True, capture_output=True, timeout=300, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return set(), bound(f"verify could not run: {exc}", 400)
        output = proc.stdout + proc.stderr
        return set(re.findall(r"\b[0-9a-f]{64}\b", proc.stdout)), bound(output, 400)

    def rehearsal_gate_command(self) -> str | None:
        """The approved gate command the operator re-runs right before the install, or None when there is none."""
        if not (self.run.get("rehearsal") or {}).get("required"):
            return None
        try:
            gate = json.loads((plan_dir(self.task) / "rehearsal.json").read_text(encoding="utf-8")).get("gate") or {}
        except (OSError, json.JSONDecodeError):
            return None
        if gate.get("argv") is None:
            return None
        backup = agents_home() / "prds" / self.task / "review-backup"
        return f"cd {backup} && python3 -I {' '.join(gate['argv'])}"

    def deploy_install(self, spec: dict[str, Any], env: dict[str, Any]) -> str:
        """Install kind: verify the built artifact is live. The factory never installs; it parks with the commands."""
        backup = self.repo_path(env["backup"])
        if not backup.is_file():
            raise Parked("backup_missing", f"Backup {backup} is missing: take it before any install "
                         f"(rehearsal.md, Backups).", spec["id"])
        sha = self.artifact_sha(env, spec["id"])
        printed, output = self.install_verify(env)
        if sha in printed:
            return f"installed artifact verified {sha[:12]}"
        gate = self.rehearsal_gate_command()
        gate_note = f"Gate (re-run right before installing): {gate}. " if gate else ""
        raise Parked("operator_install",
                     f"Verify did not report {sha[:12]} (output: {output}). "
                     f"Backup: {backup}. {gate_note}Install: {shown(env['install'])}. "
                     f"Restore: {shown(env['restore'])}. "
                     f"Then `agentctl factory resume {self.task}`.", spec["id"], detail={"artifact_sha256": sha})

    def builtin_deploy_review(self, spec: dict[str, Any]) -> str:
        """Merge the task branch into the review branch (--no-ff) in a temporary worktree and push it."""
        env = self.review_env() or {}
        if env.get("kind") == "install":
            return self.deploy_install(spec, env)
        branch = self.require_task_branch(spec)
        target = env["branch"]
        protected = (self.cfg.get("git") or {}).get("protected_branches", [])
        if target in protected or target == branch:
            raise Parked("protected_branch", f"Refusing to merge into {target!r}: it is protected or the task branch.",
                         spec["id"])
        head = self.git("rev-parse", "HEAD").stdout.strip()
        before = git_baseline(self.repo)
        worktree = self.dir / "deploy" / target
        local = f"factory-deploy/{self.task}-into-{target}"
        rejected = ""
        for _ in range(3):  # the review branch is shared; another merge may land between fetch and push
            fetch = self.git("fetch", "origin", target, timeout=180)
            if fetch.returncode != 0:
                raise Parked("fetch_failed", bound(fetch.stderr, 400), spec["id"])
            if self.git("merge-base", "--is-ancestor", head, f"origin/{target}").returncode == 0:
                return f"{target} already contains {branch} at {head[:10]}"
            shutil.rmtree(worktree, ignore_errors=True)
            try:
                added = self.git("worktree", "add", "-B", local, str(worktree), f"origin/{target}")
                if added.returncode != 0:
                    raise Parked("review_merge_failed", bound(added.stderr, 400), spec["id"])
                merge = self.git_in(worktree, "merge", "--no-ff", "-m",
                                    self.sign(f"Merge branch '{branch}' into {target}"), branch)
                if merge.returncode != 0:
                    files = self.git_in(worktree, "diff", "--name-only", "--diff-filter=U").stdout.split()
                    self.git_in(worktree, "merge", "--abort")
                    if not files:
                        raise Parked("review_merge_failed", bound(merge.stdout + merge.stderr, 600), spec["id"])
                    raise Parked("review_merge_conflict",
                                 f"Merging {branch} into {target} conflicts in {', '.join(files)}; nothing was pushed. "
                                 f"Resolve by hand: `git checkout {target} && git pull && git merge --no-ff {branch}`, "
                                 f"fix and commit, `git push origin {target}`, then `agentctl factory resume {self.task}`.",
                                 spec["id"], detail=files)
                merged = self.git_in(worktree, "rev-parse", "HEAD").stdout.strip()
                if len(self.git_in(worktree, "rev-list", "--parents", "-n1", "HEAD").stdout.split()) < 3:
                    raise Parked("fast_forward_detected", f"merging {branch} into {target} made no merge commit",
                                 spec["id"])
                push = self.git_in(worktree, "push", "origin", f"HEAD:refs/heads/{target}", timeout=180)
                if push.returncode == 0:
                    remote = self.git("ls-remote", "origin", f"refs/heads/{target}").stdout.split()
                    if not remote or remote[0] != merged:
                        raise Parked("push_unverified", f"origin/{target} is not the merge commit {merged[:10]}.",
                                     spec["id"])
                    self.git("fetch", "origin", target, timeout=180)
                    self.emit_event("review_merged", id=spec["id"], branch=target, merge=merged, head=head)
                    return f"merged {branch} into {target} (--no-ff) and pushed {merged[:10]}"
                rejected = bound(push.stdout + push.stderr, 400)
            finally:
                self.git("worktree", "remove", "--force", str(worktree))
                self.git("branch", "-D", local)
                if git_baseline(self.repo) != before:
                    raise Parked("git_baseline_violation", f"the task checkout changed while merging into {target}",
                                 spec["id"])
        raise Parked("push_rejected", f"origin/{target} rejected the merge three times: {rejected} Resume to retry.",
                     spec["id"])

    def builtin_await_review(self, spec: dict[str, Any]) -> str:
        """Wait until the review environment's live deployment contains the task head."""
        env = self.review_env() or {}
        if env.get("kind") == "install":
            sha = self.artifact_sha(env, spec["id"])
            printed, output = self.install_verify(env)
            if sha in printed:
                return f"installed artifact verified {sha[:12]}"
            raise Parked("install_unverified", f"verify does not report {sha[:12]} (output: {output}). "
                         f"Install the artifact, then `agentctl factory resume {self.task}`.", spec["id"])
        target, name = env["branch"], env.get("environment") or env["branch"]
        timeout_min = env.get("timeout_min", 45)
        head = self.git("rev-parse", "HEAD").stdout.strip()
        deadline = self.clock() + float(timeout_min) * 60
        adapter = self.sync_host()

        def contains(sha: str) -> bool:
            check = self.git("merge-base", "--is-ancestor", head, sha)
            if check.returncode not in (0, 1):  # the deployed commit is not fetched yet
                self.git("fetch", "origin", target, timeout=180)
                check = self.git("merge-base", "--is-ancestor", head, sha)
            return check.returncode == 0

        while True:
            self.check_caps()
            try:
                deployments = adapter.deployments(name)
            except agentctl_githost.HostError as exc:
                raise Parked("host_unavailable", f"Cannot read deployments of {name!r}: {exc}", spec["id"]) from exc
            state, latest = review_deploy_state(deployments, contains)
            seen = f"deployment {latest['id']} ({latest['status']}, {latest['sha'][:10]})" if latest else "no deployment"
            if state == "ok":
                self.emit_event("review_deployed", id=spec["id"], environment=name, deployment=latest["id"],
                                sha=latest["sha"], head=head)
                return f"{name} serves {latest['sha'][:10]} (deployment {latest['id']}), which contains {head[:10]}"
            if state == "failed":
                raise Parked("review_deploy_failed", f"The {name} deployment of {target} failed: {seen}. Fix or rerun "
                             f"the pipeline, then `agentctl factory resume {self.task}`.", spec["id"], detail=latest)
            if self.clock() >= deadline:
                raise Parked("review_deploy_timeout", f"After {timeout_min} min {name} still does not serve "
                             f"{head[:10]}; latest is {seen}. Check the {target} pipeline, then "
                             f"`agentctl factory resume {self.task}`.", spec["id"], detail=latest)
            self.sleep(float(env.get("poll_s", 30)))

    def choose_model(self, spec: dict[str, Any], step: dict[str, Any]) -> tuple[str, str, str]:
        """(vendor, model, effort). Reviewer must differ from the author recorded in state."""
        vendor = self.run.get("vendor", "claude")
        level = step["escalations"]
        model, effort = resolve_role(spec["role"], vendor, level)
        author_id = spec.get("reviews")
        if author_id:
            author_model = self.step(author_id).get("model")
            if author_model and author_model == model:
                for other in self.adapters:
                    if other != vendor:
                        alt_model, alt_effort = resolve_role(spec["role"], other, 0)
                        if alt_model != author_model:
                            return other, alt_model, alt_effort
                raise Parked("reviewer_model_collision",
                             f"Reviewer {model} equals author model for {author_id} and no other vendor adapter is "
                             "available. Install the Codex CLI or pick another vendor.", spec["id"])
        return vendor, model, effort

    def attempt(self, spec: dict[str, Any], step: dict[str, Any]) -> str:
        vendor, model, effort = self.choose_model(spec, step)
        adapter = self.adapters.get(vendor)
        if adapter is None:
            raise Parked("adapter_missing", f"No adapter for vendor {vendor}.", spec["id"])
        number = len([e for e in self.events if e["type"] == "step_started" and e["id"] == spec["id"]]) + 1
        step_dir = self.dir / "steps" / f"{step['index']:02d}-{spec['id']}"
        step_dir.mkdir(parents=True, exist_ok=True)
        report_path = step_dir / "report.json"
        report_path.unlink(missing_ok=True)
        session_id = str(uuid.uuid4())
        findings = self.take_findings(spec["id"])
        extra = self.retry_extra(spec["id"])
        prompt = step_prompt(self.run, spec, self.handoff(spec.get("reviews")), report_path, extra, findings)
        (step_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        remaining = self.limits["run_usd"] - self.run["cost_usd"]
        budget = min(self.limits["budget_usd"].get(spec["role"], 8), max(remaining, 0.01))
        timeout = min(self.limits["step_timeout_min"] * 60,
                      max(self.limits["run_hours"] * 3600 - (self.clock() - self.started), 1))
        allowed = list(self.worker_cfg["allowed_tools"]) + self.repo_tools() + [
            t.replace("{task}", self.task) for t in spec.get("allowed_tools_extra", [])]
        req = WorkerRequest(
            prompt=prompt, model=model, effort=effort, cwd=self.repo, step_dir=step_dir, session_id=session_id,
            timeout_s=timeout, budget_usd=budget, allowed_tools=allowed,
            disallowed_tools=self.worker_cfg["disallowed_tools"], permission_mode=self.worker_cfg["permission_mode"],
            mcp_config=self.mcp_config(spec, step_dir), writable_roots=self.writable_roots(),
            on_pid=lambda pid: self.emit_event("worker_pid", id=spec["id"], pid=pid),
        )
        self.emit_event("step_started", id=spec["id"], model=model, vendor=vendor, role=spec["role"],
                        session_id=session_id, pid=None, attempt=number)
        kit_before = kit_dirty()
        result: WorkerResult = adapter.run(req)
        cost = result.cost_usd
        kit_after = kit_dirty() if kit_before is not None else None
        if kit_after and kit_after - kit_before:
            changed = sorted(kit_after - kit_before)
            self.emit_event("kit_changed", id=spec["id"], count=len(changed), paths=changed[:20])
        if result.denials:
            atomic_write(step_dir / "denials.json", json.dumps(result.denials, indent=2))
        if self.stop_requested:
            self.emit_event("interrupted", id=spec["id"], reason="stop", cost_usd=cost or 0.0)
            raise _Stopped
        if result.timed_out:
            if self.clock() - self.started >= self.limits["run_hours"] * 3600:
                self.emit_event("interrupted", id=spec["id"], reason="cap_time", cost_usd=cost or 0.0)
                raise Parked("cap_time", f"Wall-clock cap {self.limits['run_hours']} h reached.", spec["id"])
            return self.fail(spec, step, "transient", "timeout", result, step_dir, cost=cost)
        report = read_report(report_path, self.limits["summary_chars"])
        baseline = self.git_violation()
        if baseline:
            self.finish(spec, "failed", report, cost, "git_baseline_violation", result)
            raise Parked("git_baseline_violation", baseline, spec["id"])
        forbidden = [d for d in result.denials if forbidden_denial(d, self.cfg)]
        if result.denials and not forbidden:
            self.emit_event("denials_noted", id=spec["id"], count=len(result.denials),
                            sample=[bound(json.dumps(d.get("tool_input")), 160) for d in result.denials[:3]],
                            file=str(step_dir / "denials.json"))
        if forbidden:
            denial = forbidden[0]
            self.finish(spec, "failed", report, cost, "hook_denial", result)
            raise Parked("needs_human", "Permission or hook denied "
                         f"{denial.get('tool_name')}: {bound(json.dumps(denial.get('tool_input')), 200)}", spec["id"],
                         detail=forbidden[:3])
        classification = self.classify(result, report)
        if classification == "transient":
            return self.fail(spec, step, "transient", "transient_error", result, step_dir, cost=cost)
        if classification == "blocked":
            self.finish(spec, "failed", report, cost, "blocked", result)
            raise Parked("blocked", "; ".join((report or {}).get("blockers", [])) or "worker reported blocked",
                         spec["id"])
        gate_failure, inconclusive = self.post_gates(spec, step, report, result)
        if report is None and result.exit_code == 0 and not gate_failure and not spec.get("post"):
            inconclusive = True
        if gate_failure:
            if gate_failure.startswith(("tbd_empty", "foreign_checks")) or spec.get("park_on_fail"):
                self.finish(spec, "failed", report, cost, "gate_failed", result)
                reason = ("tbd_open" if gate_failure.startswith("tbd_empty") else
                          "foreign_check_touched" if gate_failure.startswith("foreign_checks") else "evidence_failed")
                raise Parked(reason, gate_failure + (f" Draft: {plan_dir(self.task)}" if reason == "evidence_failed" else ""),
                             spec["id"])
            return self.fail(spec, step, "gate", gate_failure, result, step_dir, cost=cost, report=report)
        if classification == "semantic":
            return self.fail(spec, step, "semantic", (report or {}).get("summary") or "worker reported failure",
                             result, step_dir, cost=cost, report=report)
        if inconclusive:
            decision = self.supervise(spec, step, report, result, "gates could not verify the step")
            return self.apply_decision(decision, spec, step, report, cost, result, step_dir)
        self.finish(spec, "ok", report, cost, None, result)
        return "ok"

    def classify(self, result: WorkerResult, report: dict[str, Any] | None) -> str:
        if result.exit_code != 0:
            return "transient" if TRANSIENT_RE.search(result.stderr + result.text) else "semantic"
        if report and report["status"] == "blocked":
            return "blocked"
        if report and report["status"] == "failed":
            return "semantic"
        return "ok"

    def post_gates(self, spec: dict[str, Any], step: dict[str, Any], report: dict[str, Any] | None,
                   result: WorkerResult) -> tuple[str | None, bool]:
        inconclusive = False
        for name in spec.get("post", []):
            ctx = GateCtx(self.task, step, self.run, self.repo, report, result, self.dir)
            outcome, detail = GATES[name](ctx)
            self.emit_event("gate", id=spec["id"], name=name, result=outcome, detail=bound(detail, 600), phase="post")
            if outcome == "fail":
                return f"{name}: {detail}", False
            inconclusive = inconclusive or outcome == "inconclusive"
        return None, inconclusive

    def git_violation(self) -> str | None:
        baseline = self.run.get("git_baseline")
        if not baseline:
            return None
        current = git_baseline(self.repo)
        if current != baseline:
            return f"HEAD or index changed during a worker step: expected {baseline}, found {current}"
        return None

    def finish(self, spec: dict[str, Any], status: str, report: dict[str, Any] | None, cost: float | None,
               reason: str | None, result: WorkerResult | None = None) -> None:
        measured = measurement(result) if result is not None else {}
        learnings = (report or {}).get("learnings", [])
        if spec["role"] in NO_LEARNINGS_ROLES or spec["id"] == "kb-harvest":
            learnings = []
        self.emit_event("step_finished", id=spec["id"], status=status, summary=(report or {}).get("summary"),
                        artifacts=(report or {}).get("artifacts", []), cost_usd=cost or 0.0, reason=reason,
                        learnings=learnings, **measured)

    # -- failures, retries, escalation ---------------------------------------

    def fail(self, spec: dict[str, Any], step: dict[str, Any], cls: str, reason: str, result: WorkerResult,
             step_dir: Path, cost: float | None = None, report: dict[str, Any] | None = None) -> str:
        self.finish(spec, "failed", report, cost, reason, result)
        step = self.step(spec["id"])
        key = {"transient": "transient_retries", "gate": "gate_retries", "semantic": "gate_retries"}[cls]
        used = step["retries"].get(cls, 0)
        if step["attempts"] < self.limits["attempts"] and used < self.limits[key]:
            self.emit_event("retry", id=spec["id"], **{"class": cls}, reason=bound(reason, 300))
            if cls == "transient":
                backoff = self.limits["backoff_s"]
                self.sleep(backoff[min(used, len(backoff) - 1)])
            else:
                self.set_retry_excerpt(spec["id"], reason, step_dir)
            return "retry"
        return self.exhausted(spec, step, reason)

    def exhausted(self, spec: dict[str, Any], step: dict[str, Any], reason: str) -> str:
        """Retries used up: raise effort one step once, then (plan stage) dual run, then park."""
        if step["escalations"] == 0 and self.can_escalate(spec):
            self.emit_event("escalate", id=spec["id"], reason=bound(reason, 300))
            self.emit_event("decision", id=spec["id"], decision="escalate", source="engine", reason="retries exhausted")
            return "retry"
        if spec["id"] in PLAN_STAGE_STEPS and (self.run.get("dual") or {}).get("stage") != "dual_decided":
            self.emit_event("dual_trigger", reason="escalation_failed", id=spec["id"])
        raise Parked("retries_exhausted", f"Step {spec['id']} failed after retries and escalation: {bound(reason, 400)}",
                     spec["id"])

    def can_escalate(self, spec: dict[str, Any]) -> bool:
        """False when escalation would rerun the same model and effort (the cell is already at xhigh or max)."""
        vendor = self.run.get("vendor", "claude")
        return resolve_role(spec["role"], vendor, 1) != resolve_role(spec["role"], vendor)

    def set_retry_excerpt(self, step_id: str, reason: str, step_dir: Path) -> None:
        excerpt = reason
        stderr = step_dir / "stderr.log"
        if stderr.is_file() and stderr.stat().st_size:
            data = agentctl_json("logs", "extract", str(stderr), "--levels", "ERROR,WARN", "--limit", "20")
            excerpt += "\n" + json.dumps(data.get("events", []))[:1500]
        (self.dir / "steps" / f"{self.step(step_id)['index']:02d}-{step_id}" / "retry.txt").write_text(
            bound(excerpt, self.limits["excerpt_bytes"]), encoding="utf-8")

    def retry_extra(self, step_id: str) -> str:
        path = self.dir / "steps" / f"{self.step(step_id)['index']:02d}-{step_id}" / "retry.txt"
        if path.is_file():
            return "Your previous attempt failed a check. Fix it:\n" + path.read_text(encoding="utf-8")
        return ""

    def take_findings(self, step_id: str) -> str:
        path = self.dir / "findings" / f"{step_id}.md"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def handoff(self, reviewed: str | None = None) -> str:
        """Earlier steps' summaries; the step a reviewer reviews keeps its artifacts but not its own account."""
        done = [s for s in self.run["steps"] if s["status"] == "ok" and s.get("summary")]
        window = done[-self.limits["handoff_summaries"]:]
        window += [s for s in self.run["steps"] if s["id"] == reviewed and s["status"] == "ok" and s not in window]
        lines = []
        for s in window:
            if s["id"] == reviewed:
                lines.append(f"- {s['id']}: summary withheld for independent review")
                lines.append("  artifacts: " + (", ".join(s.get("artifacts") or []) or "none"))
            else:
                lines.append(f"- {s['id']}: {s['summary']}")
        return bound("\n".join(lines), self.limits["handoff_bytes"])

    def instance_problem(self, data: dict[str, Any]) -> str | None:
        """Why the task's Playwright instance is not the one this task may drive, or None when it is."""
        if data.get("id") != self.task:
            return f"the bound browser instance is {data.get('id')!r}, not {self.task!r}"
        if data.get("name") != f"playwright-{self.task}":
            return f"the browser server is named {data.get('name')!r}, not 'playwright-{self.task}'"
        pid = data.get("pid")
        if not isinstance(pid, int) or not pid_alive(pid):
            return f"the browser instance process {pid} is not running"
        try:
            with socket.create_connection((str(data["host"]), int(data["port"])), timeout=2):
                pass
        except (KeyError, OSError, TypeError, ValueError):
            return f"nothing answers at {data.get('host')}:{data.get('port')}"
        return None

    def mcp_config(self, spec: dict[str, Any], step_dir: Path) -> Path | None:
        servers = self.catalog_servers(spec.get("mcp_servers", []))
        if spec["id"] in ("run-evidence",):
            instance = agents_home() / ".playwright-mcp" / "instances" / self.task / "instance.json"
            if instance.is_file():
                data = json.loads(instance.read_text(encoding="utf-8"))
                problem = self.instance_problem(data)
                if problem:
                    raise Parked("browser_instance_mismatch",
                                 f"{problem}; revive with `python3 ~/.agents/mcp/playwright.py revive {self.task}` "
                                 f"(or `spawn {self.task} --enable`) and resume", spec["id"])
                servers[f"playwright-{self.task}"] = {"type": "http", "url": data["url"]}
        if not servers:
            return None
        path = step_dir / "mcp.json"
        path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")
        return path

    @staticmethod
    def catalog_servers(names: list[str]) -> dict[str, Any]:
        """Stdio entries of `mcp/catalog.json` by name, for steps that opt in with `mcp_servers`."""
        if not names:
            return {}
        catalog = json.loads((agents_home() / "mcp" / "catalog.json").read_text(encoding="utf-8"))
        home = str(Path.home())
        out: dict[str, Any] = {}
        for name in names:
            spec = catalog["servers"][name]
            out[name] = {"type": "stdio", "command": spec["command"].replace("${HOME}", home),
                         "args": spec.get("args", []), "env": spec.get("env", {})}
        return out

    # -- supervisor -----------------------------------------------------------

    def supervise(self, spec: dict[str, Any], step: dict[str, Any], report: dict[str, Any] | None,
                  result: WorkerResult | None, why: str, allowed: tuple[str, ...] = DECISIONS) -> dict[str, Any]:
        """One short fresh headless call. Invalid or timed-out output is `park`."""
        vendor = self.run.get("vendor", "claude")
        adapter = self.adapters.get(vendor)
        role = self.run.get("supervisor_role", "follow")
        context = bound(json.dumps({"step": spec["id"], "why": why, "report": report,
                                    "exit_code": result.exit_code if result else None,
                                    "attempts": step["attempts"], "gates": [e for e in self.events
                                    if e["type"] == "gate" and e.get("id") == spec["id"]][-5:]}),
                        self.limits["supervisor_bytes"])
        schema = {"type": "object", "required": ["decision", "reason"], "properties": {
            "decision": {"type": "string", "enum": list(allowed)}, "reason": {"type": "string"}}}
        decision = {"decision": "park", "reason": "supervisor unavailable"}
        if adapter is not None:
            model, effort = resolve_role(role, vendor)
            sup_dir = self.dir / "supervisor" / f"{len(self.events):05d}"
            req = WorkerRequest(
                prompt=("You are the factory supervisor. Choose one decision for the step below from "
                        f"{list(allowed)}; answer JSON {{\"decision\",\"reason\"}} only.\n" + context),
                model=model, effort=effort, cwd=self.repo, step_dir=sup_dir, session_id=str(uuid.uuid4()),
                timeout_s=300, budget_usd=min(self.limits["budget_usd"].get(role, 2), 2),
                allowed_tools=[], disallowed_tools=self.worker_cfg["disallowed_tools"],
                permission_mode="default", json_schema=schema, label="supervisor")
            try:
                res = adapter.run(req)
                parsed = None if res.timed_out else extract_json(res.text)
                if res.cost_usd:
                    self.emit_event("decision", id=spec["id"], decision="supervisor_cost", source="supervisor",
                                    reason="cost", cost_usd=res.cost_usd)
                if parsed and parsed.get("decision") in allowed and isinstance(parsed.get("reason"), str):
                    decision = {"decision": parsed["decision"], "reason": bound(parsed["reason"], 400)}
                else:
                    decision = {"decision": "park", "reason": "supervisor output invalid or timed out"}
            except Exception as exc:  # noqa: BLE001 - any adapter failure is a park, never a crash
                decision = {"decision": "park", "reason": f"supervisor failed: {exc}"}
        if decision["decision"] == "dual_run" and spec["id"] not in PLAN_STAGE_STEPS:
            decision = {"decision": "escalate", "reason": "dual_run is plan stage only; downgraded: " + decision["reason"]}
        self.emit_event("decision", id=spec["id"], source="supervisor", **decision)
        return decision

    def apply_decision(self, decision: dict[str, Any], spec: dict[str, Any], step: dict[str, Any],
                       report: dict[str, Any] | None, cost: float | None, result: WorkerResult, step_dir: Path) -> str:
        choice = decision["decision"]
        if choice == "proceed":
            self.finish(spec, "ok", report, cost, "supervisor_proceed", result)
            return "ok"
        if choice == "park":
            self.finish(spec, "failed", report, cost, "supervisor_park", result)
            raise Parked("supervisor_park", decision["reason"], spec["id"])
        self.finish(spec, "failed", report, cost, f"supervisor_{choice}", result)
        if choice in ("escalate", "retry_other_model"):
            if self.step(spec["id"])["escalations"] == 0 and self.can_escalate(spec):
                self.emit_event("escalate", id=spec["id"], reason=decision["reason"])
                return "retry"
            raise Parked("retries_exhausted", decision["reason"], spec["id"])
        if choice == "dual_run":
            self.emit_event("dual_trigger", reason="supervisor", id=spec["id"])
            return "retry"
        self.emit_event("retry", id=spec["id"], **{"class": "gate"}, reason=decision["reason"])
        return "retry"

    # -- after each finished step: routing, review loops, dual run -----------

    def after_step(self, step: dict[str, Any]) -> int | None:
        if step["status"] != "ok":
            return None
        step_id = step["id"]
        if step_id == self.run.get("route_step", "route"):
            self.route(step)
        if step_id in REVIEW_LOOPS:
            return self.review_loop(step)
        if step_id in PLAN_STAGE_STEPS:
            self.maybe_dual(step)
        if step_id == "validate-plan" and (self.run.get("route") or {}).get("path") == "plan_only" \
                and not (self.run.get("rehearsal") or {}).get("required"):
            self.emit_event("run_finished", state="awaiting_human_review", path="plan_only")
        if step_id == "plan-rehearsal":
            self.after_rehearsal(step)
        return None

    def after_rehearsal(self, step: dict[str, Any]) -> None:
        md = plan_dir(self.task) / "rehearsal.md"
        if (self.run.get("route") or {}).get("path") == "plan_only":
            self.emit_event("run_finished", state="awaiting_human_review", path="plan_only", rehearsal=str(md))
            return
        if not (self.run.get("rehearsal") or {}).get("approved_sha256"):
            raise Parked("rehearsal_ready",
                         f"{md}; review it, then `agentctl factory resume {self.task} --approve-rehearsal`",
                         step["id"])

    def review_loop(self, step: dict[str, Any]) -> int | None:
        target = REVIEW_LOOPS[step["id"]]
        report = read_report(self.dir / "steps" / f"{step['index']:02d}-{step['id']}" / "report.json",
                             self.limits["summary_chars"])
        blockers = (report or {}).get("blockers", [])
        if not blockers:
            return None
        used = len([e for e in self.events if e["type"] == "reset" and e.get("id") == target and e.get("loop")])
        if used >= self.limits["review_loops"]:
            raise Parked("review_loop_exhausted",
                         f"{step['id']} blockers remain after the review loop limit: " + "; ".join(blockers)[:600],
                         step["id"])
        findings = self.dir / "findings"
        findings.mkdir(exist_ok=True)
        text = "\n".join(f"- {b}" for b in blockers)
        (findings / f"{target}.md").write_text(bound(text, self.limits["excerpt_bytes"]), encoding="utf-8")
        self.emit_event("reset", id=target, loop=True)
        self.emit_event("reset", id=step["id"])
        return self.step(target)["index"]

    def route(self, step: dict[str, Any]) -> None:
        path = verdict_path(self.task)
        verdict = json.loads(path.read_text(encoding="utf-8"))
        if rehearsable(verdict):
            self.emit_event("rehearsal_required", criteria=[b["criterion"] for b in verdict["blockers"]],
                            isolation=verdict["rehearsal"].get("isolation"),
                            sync_delete=bool(verdict["rehearsal"].get("sync_delete")))
        elif verdict["verdict"] == "Human-in-the-loop":
            blockers = [{"criterion": b["criterion"], "human_action": b["human_action"], "owner": b["owner"]}
                        for b in verdict.get("blockers", [])]
            self.emit_event("route", verdict="Human-in-the-loop", path="park", blockers=blockers)
            raise Parked("human_in_the_loop",
                         "; ".join(f"{b['criterion']}: {b['human_action']} ({b['owner']})" for b in blockers),
                         step["id"], detail=blockers)
        signals = self.path_signals(verdict)
        score = signals["score"]
        chosen = "standard" if score <= 1 else "plan_only" if score <= 3 else "park"
        override = None
        if self.run.get("path_flag"):
            chosen, override = self.run["path_flag"], "operator flag"
        elif score in (2, 3):
            decision = self.supervise(self.spec(step["id"]), step, None, None, f"borderline route score {score}",
                                      allowed=("proceed", "plan_only", "park"))
            if decision["decision"] in ("plan_only", "park"):
                chosen, override = decision["decision"], decision["reason"]
        self.emit_event("route", verdict=verdict["verdict"], path=chosen, signals=signals, override=override)
        if chosen == "park":
            raise Parked("route_park", "Route gate chose park" + (f": {override}" if override else ""), step["id"])
        if chosen == "skip_evidence":
            for sid in EVIDENCE_STEPS:
                if self._has_step(sid):
                    self.emit_event("step_skipped", id=sid, reason="skip_evidence")

    def path_signals(self, verdict: dict[str, Any]) -> dict[str, Any]:
        prd = agents_home() / "prds" / f"{self.task}.md"
        text = prd.read_text(encoding="utf-8", errors="ignore") if prd.is_file() else ""
        lines = len(text.splitlines())
        acs = len(re.findall(r"^\s*[-*]\s*(\[.\]|Given)", text, re.MULTILINE))
        auto = len(verdict.get("auto_resolved", []))
        score = (2 if lines > 400 else 1 if lines > 200 else 0) + (2 if acs > 12 else 1 if acs > 6 else 0) + (1 if auto >= 4 else 0)
        return {"prd_lines": lines, "ac_count": acs, "auto_resolved": auto, "score": score}

    # -- plan-stage dual run (release 1) --------------------------------------

    def maybe_dual(self, step: dict[str, Any]) -> None:
        dual = self.run.get("dual") or {}
        if dual.get("stage") == "dual_decided":
            return
        reason = None
        if self.run.get("dual_flag") == "plan" and step["id"] == "plan-implementation":
            reason = "operator_flag"
        elif dual.get("stage") == "dual_trigger":
            reason = dual.get("reason")
        elif step["id"] == "plan-implementation" and self._first_attempt_gate_failed("plan-implementation"):
            reason = "first_attempt_gate_failure"
        elif step["id"] == "validate-plan" and self.plan_rewrite_ratio() >= self.limits["dual_rewrite_ratio"]:
            reason = "plan_rewrite_ratio"
        elif step["escalations"] > 0:
            reason = "escalation"
        if reason is None:
            return
        self.emit_event("dual_trigger", reason=reason, id=step["id"])
        self.dual_plan(reason)

    def _first_attempt_gate_failed(self, step_id: str) -> bool:
        first = next((e for e in self.events if e["type"] == "step_started" and e["id"] == step_id), None)
        if not first:
            return False
        for ev in self.events[self.events.index(first):]:
            if ev["type"] == "step_finished" and ev["id"] == step_id:
                return ev["status"] != "ok"
        return False

    def plan_rewrite_ratio(self) -> float:
        before = self.dir / "snapshots" / "plan-before-validate"
        after = plan_dir(self.task)
        if not before.is_dir() or not after.is_dir():
            return 0.0
        old = self._plan_lines(before)
        new = self._plan_lines(after)
        if not old:
            return 0.0
        changed = len(set(old) ^ set(new))
        return min(changed / max(len(old), 1), 1.0)

    @staticmethod
    def _plan_lines(directory: Path) -> list[str]:
        lines: list[str] = []
        for path in sorted(directory.glob("*.md")):
            lines += path.read_text(encoding="utf-8").splitlines()
        return lines

    def dual_plan(self, reason: str) -> None:
        others = [name for name in self.adapters if name != self.run.get("vendor", "claude")]
        if not others:
            raise Parked("dual_unavailable",
                         f"A plan-stage dual run was triggered ({reason}) but only one vendor adapter is available.",
                         "plan-implementation", detail={"trigger": reason})
        author_vendor = self.run.get("vendor", "claude")
        variant_vendor = others[0]
        plan = plan_dir(self.task)
        variants = self.dir / "variants"
        a_dir, b_dir = variants / "A", variants / "B"
        for target in (a_dir, b_dir):
            shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(plan, a_dir)
        author_model = self.step("plan-implementation").get("model")
        # run B: plan-implementation on the other vendor with the author's plan removed from the canonical path
        shutil.rmtree(plan)
        variant_model, variant_effort = resolve_role("plan", variant_vendor)
        spec = self.spec("plan-implementation")
        step_dir = self.dir / "steps" / "variant-B"
        report_path = step_dir / "report.json"
        step_dir.mkdir(parents=True, exist_ok=True)
        req = WorkerRequest(
            prompt=step_prompt(self.run, spec, "", report_path, "", ""), model=variant_model, effort=variant_effort,
            cwd=self.repo, step_dir=step_dir, session_id=str(uuid.uuid4()),
            timeout_s=self.limits["step_timeout_min"] * 60, budget_usd=self.limits["budget_usd"]["plan"],
            allowed_tools=self.worker_cfg["allowed_tools"], disallowed_tools=self.worker_cfg["disallowed_tools"],
            permission_mode=self.worker_cfg["permission_mode"], label="variant")
        res = self.adapters[variant_vendor].run(req)
        if res.cost_usd:
            self.emit_event("decision", id="plan-implementation", decision="variant_cost", source="engine",
                            reason="variant", cost_usd=res.cost_usd)
        if plan.is_dir():
            shutil.copytree(plan, b_dir)
            shutil.rmtree(plan)
        else:
            b_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(a_dir, plan)
        compare = self.compare_variants(a_dir, b_dir, author_model, variant_model, author_vendor, variant_vendor)
        winner = compare["winner"]
        shutil.rmtree(plan)
        shutil.copytree(a_dir if winner == "A" else b_dir, plan)
        atomic_write(variants / "compare.json", json.dumps(compare, indent=2, ensure_ascii=False) + "\n")
        self.emit_event("dual_decided", winner=winner, reason=compare["reason"], trigger=reason,
                        compare=str(variants / "compare.json"))
        if winner == "B":
            self.emit_event("author_override", id="plan-implementation", model=variant_model)

    def deterministic_score(self, directory: Path) -> dict[str, Any]:
        text = "\n".join(self._plan_lines(directory))
        prd = agents_home() / "prds" / f"{self.task}.md"
        prd_text = prd.read_text(encoding="utf-8", errors="ignore") if prd.is_file() else ""
        ids = sorted(set(re.findall(r"\b(?:FR|US)-?\d+\b", prd_text)))
        missing = [i for i in ids if i not in text]
        valid = agentctl_json("plan", "validate", str(directory), "--kind", "implementation").get("valid", False)
        tbd = len(re.findall(r"^\s*[-*]\s*TBD[^:]*:\s*(?!none)\S", text, re.MULTILINE | re.IGNORECASE))
        return {"valid": bool(valid), "missing_ids": missing, "open_tbd": tbd, "lines": len(text.splitlines())}

    def compare_variants(self, a_dir: Path, b_dir: Path, a_model: str | None, b_model: str,
                         a_vendor: str, b_vendor: str) -> dict[str, Any]:
        scores = {"A": self.deterministic_score(a_dir), "B": self.deterministic_score(b_dir)}

        def key(label: str) -> tuple[Any, ...]:
            s = scores[label]
            return (not s["valid"], len(s["missing_ids"]), s["open_tbd"], s["lines"])

        det = "A" if key("A") <= key("B") else "B"
        result: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "inputs": {"A": str(a_dir), "B": str(b_dir)},
                                  "models": {"A": a_model, "B": b_model}, "scores": scores,
                                  "deterministic_winner": det, "winner": det, "reason": "deterministic compare",
                                  "judge": None}
        judge_vendor = a_vendor
        judge_model, judge_effort = resolve_role("plan-review", judge_vendor)
        if judge_model in (a_model, b_model):
            judge_vendor = b_vendor
            judge_model, judge_effort = resolve_role("plan-review", judge_vendor)
        if judge_model in (a_model, b_model) or judge_vendor not in self.adapters:
            result["judge"] = {"skipped": "no third distinct model available"}
            return result
        rng = random.Random(int(time.time()))
        flip = rng.random() < 0.5
        labels = {"X": "B" if flip else "A", "Y": "A" if flip else "B"}
        judge_dir = self.dir / "variants" / "judge"
        for blind, real in labels.items():
            shutil.rmtree(judge_dir / blind, ignore_errors=True)
            shutil.copytree(a_dir if real == "A" else b_dir, judge_dir / blind)
        req = WorkerRequest(
            prompt=(f"Two implementation plans for task {self.task} are in {judge_dir}/X and {judge_dir}/Y, written "
                    "from the same PRD. Pick the one that is more complete, correct and executable. Answer JSON "
                    '{"winner":"X"|"Y","reason":"..."} only.'),
            model=judge_model, effort=judge_effort, cwd=self.repo, step_dir=judge_dir, session_id=str(uuid.uuid4()),
            timeout_s=600, budget_usd=self.limits["budget_usd"]["plan-review"], allowed_tools=["Read", "Glob", "Grep"],
            disallowed_tools=self.worker_cfg["disallowed_tools"], permission_mode="default", label="judge",
            json_schema={"type": "object", "required": ["winner", "reason"], "properties": {
                "winner": {"type": "string", "enum": ["X", "Y"]}, "reason": {"type": "string"}}})
        verdict = None
        with contextlib.suppress(Exception):
            res = self.adapters[judge_vendor].run(req)
            verdict = None if res.timed_out else extract_json(res.text)
        if verdict and verdict.get("winner") in labels and isinstance(verdict.get("reason"), str):
            result["winner"] = labels[verdict["winner"]]
            result["reason"] = "blinded judge: " + bound(verdict["reason"], 400)
            result["judge"] = {"model": judge_model, "labels": labels, "winner_label": verdict["winner"]}
        else:
            result["judge"] = {"model": judge_model, "labels": labels, "invalid": True}
            result["reason"] = "judge output invalid; deterministic compare used"
        return result


class _Stopped(Exception):
    pass


# --------------------------------------------------------------------------- CLI


def detect_pipeline(task: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    tracker = tracker_settings()
    if tracker and re.match(tracker["key_regex"], task):
        return "tracker-standard"
    if (agents_home() / "prds" / f"{task}.md").is_file():
        return "brainstorm"
    raise FactoryError(f"{task!r} is not a {(tracker or {}).get('kind', 'tracker')} task id and has no local PRD "
                       f"at prds/{task}.md; pass --pipeline")


def repo_top(cwd: Path) -> Path:
    top = git_out(cwd, "rev-parse", "--show-toplevel")
    if not top:
        raise FactoryError(f"{cwd} is not inside a git repository")
    return Path(top)


def other_live_run_on_repo(task: str, repo: Path) -> str | None:
    root = factory_root()
    if not root.is_dir():
        return None
    for child in sorted(root.iterdir()):
        if child.name == task or not (child / "events.jsonl").is_file():
            continue
        snap = derive(read_events(child))
        if snap.get("repo") == str(repo) and lock_holder(child) is not None:
            return child.name
    return None


def watch_requested(args: argparse.Namespace) -> bool:
    watching = bool(getattr(args, "progress", False) or getattr(args, "verbose", False))
    if watching and getattr(args, "foreground", False):
        raise FactoryError("--progress and --verbose cannot be combined with --foreground: "
                           "the foreground engine blocks this process; start detached and use `watch`")
    return watching


def attach_watch(task: str, args: argparse.Namespace) -> int:
    import agentctl_factory_watch  # imports this module; kept out of the top to avoid a cycle

    return agentctl_factory_watch.watch_task(task, progress=args.progress, verbose=args.verbose)


def harness_repo(repo: Path) -> Path | None:
    """The harness root when the factory must refuse this repo: the agents home is inside it, or it or one
    direct child holds both kb/ and skills/ (structural, so devkit exports match too). None when it is not."""
    if not repo.is_dir():
        return None
    resolved = repo.resolve()
    home = agents_home().resolve()
    if home == resolved or resolved in home.parents:
        return home
    for candidate in [resolved, *sorted(c for c in resolved.iterdir() if c.is_dir() and not c.is_symlink())]:
        if (candidate / "kb").is_dir() and (candidate / "skills").is_dir():
            return candidate
    return None


def harness_refusal(match: Path) -> str:
    return f"the factory never runs on a harness repo: {match} holds kb/ and skills/"


def cmd_start(args: argparse.Namespace) -> int:
    watching = watch_requested(args)
    task = args.task
    directory = run_dir(task)
    pipeline_name = detect_pipeline(task, args.pipeline)
    pipeline = load_pipeline(pipeline_name)
    repo = repo_top(Path.cwd())
    if (match := harness_repo(repo)) is not None:
        raise FactoryError(harness_refusal(match))
    branch = git_out(repo, "branch", "--show-current")
    mode = pipeline["mode"]
    branch_error = (f"Tracker-mode run needs branch {task!r} checked out, found {branch!r}. "
                    "The factory never creates or switches branches.") if mode == "tracker" and branch != task else None
    if args.context and not Path(args.context).expanduser().is_file():
        raise FactoryError(f"--context file not found: {args.context}")
    closed_error = closed_task_error(task, pipeline["settings"]) if mode == "tracker" else None
    vendor = args.vendor or pipeline["settings"]["factory"]["vendor"]
    steps_view = []
    for index, spec in enumerate(pipeline["steps"]):
        entry = {"index": index, "id": spec["id"], "skill": spec["skill"], "role": spec["role"],
                 "gates": {"pre": spec["pre"], "post": spec["post"]}}
        if spec["kind"] == "model":
            entry["model"], entry["effort"] = resolve_role(spec["role"], vendor)
        elif spec["kind"] == "builtin":
            entry["builtin"] = spec["builtin"]
        steps_view.append(entry)
    if args.dry_run:
        emit({"dry_run": True, "task_id": task, "pipeline": pipeline_name, "mode": mode, "repo": str(repo),
              "branch": branch, "branch_error": branch_error, "closed_error": closed_error, "vendor": vendor,
              "limits": pipeline["limits"], "steps": steps_view})
        return 0
    if branch_error:
        raise FactoryError(branch_error)
    if closed_error:
        raise FactoryError(closed_error)
    if lock_holder(directory) is not None:
        raise FactoryError(f"run {task} is live (pid {lock_holder(directory)}); use status or stop")
    if (directory / "events.jsonl").is_file() and derive(read_events(directory)).get("state") != "new":
        raise FactoryError(f"run {task} already exists; use `agentctl factory resume {task}`")
    clash = other_live_run_on_repo(task, repo)
    if clash:
        raise FactoryError(f"run {clash} is live on repo {repo}; parallel tasks need multitask-same-repo worktrees")
    limits = dict(pipeline["limits"])
    if args.max_cost_usd is not None:
        limits["run_usd"] = args.max_cost_usd
    if args.max_hours is not None:
        limits["run_hours"] = args.max_hours
    append_event(directory, "run_started", task_id=task, pipeline=pipeline_name, mode=mode, repo=str(repo),
                 branch=branch, vendor=vendor, git_baseline=git_baseline(repo), limits=limits,
                 worker=pipeline["worker"], supervisor_role=pipeline["supervisor_role"],
                 settings=pipeline["settings"], tracker=(tracker_settings(pipeline["settings"]) or {}).get("kind"),
                 route_step=pipeline["route_step"], context=str(Path(args.context).expanduser()) if args.context else None,
                 path_flag=args.path, dual_flag=args.dual, step_specs=[dict(step) for step in pipeline["steps"]])
    write_snapshot(directory, snapshot(directory))
    code = launch(task, foreground=args.foreground)
    return attach_watch(task, args) if watching and code == 0 else code


def launch(task: str, *, foreground: bool, only_step: str | None = None) -> int:
    directory = run_dir(task)
    if foreground:
        return run_engine(task, only_step=only_step)
    script = Path(__file__).resolve().parent / "agentctl.py"
    log = (directory / "engine.log").open("a")
    argv = [sys.executable, str(script), "factory", "_engine", task] + (["--only-step", only_step] if only_step else [])
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
                            cwd=directory)
    emit({"task_id": task, "started": True, "engine_pid": proc.pid, "state_dir": str(directory),
          "status": f"agentctl factory status {task}"})
    return 0


def run_engine(task: str, only_step: str | None = None, adapters: dict[str, Any] | None = None,
               engine_kwargs: dict[str, Any] | None = None) -> int:
    directory = run_dir(task)
    if not (directory / "events.jsonl").is_file():
        raise FactoryError(f"unknown run {task!r}")
    lock = RunLock(directory)
    if not lock.acquire():
        raise FactoryError(f"run {task} is live; refusing a second engine")
    try:
        snap = derive(read_events(directory))
        clash = other_live_run_on_repo(task, Path(snap["repo"]))
        if clash:
            raise FactoryError(f"run {clash} is live on repo {snap['repo']}")
        engine = Engine(task, adapters=adapters, **(engine_kwargs or {}))
        engine.only_step = only_step
        state = engine.execute()
    finally:
        lock.release()
    emit({"task_id": task, "state": state, "cost_usd": engine.run["cost_usd"]}, as_json=True)
    return 0


def cmd_engine(args: argparse.Namespace) -> int:
    return run_engine(args.task, only_step=args.only_step)


def harvest_cursor_of(events: list[dict[str, Any]]) -> int:
    """Event number up to which a harvest already ran (kb_harvest_done.through); 0 when none did."""
    cursor = 0
    for ev in events:
        if ev.get("type") == "kb_harvest_done":
            cursor = max(cursor, int(ev.get("through") or 0))
    return cursor


def kit_activity(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Attributed worker writes to the kit (kit_writes) and unattributed changes seen by git (kit_changed)."""
    writes = [{"step": ev.get("id"), "paths": ev["kit_writes"]} for ev in events
              if ev.get("type") == "step_finished" and ev.get("kit_writes")]
    changed = [{"step": ev.get("id"), "paths": ev.get("paths") or []} for ev in events
               if ev.get("type") == "kit_changed"]
    return writes, changed


def human_action(snap: dict[str, Any], directory: Path | None = None) -> str | None:
    park = snap.get("park")
    if snap["state"] == "parked" and park:
        action = park.get("action") or park["reason"]
        if directory is not None and directory.is_dir():
            events = read_events(directory)
            if not any(ev.get("type") == "kb_harvest_done" for ev in events) and run_digest(
                    directory, harvest_cursor_of(events))["has_signals"]:
                action = f"{action}; harvest the run: agentctl factory step {directory.name} kb-harvest"
        return action
    if snap["state"] == "awaiting_human_review":
        return "Review the delivery, the evidence comment and the commit message draft."
    if snap["state"] == "failed":
        return "Inspect events.jsonl and the failed step folder."
    return None


def status_payload(task: str) -> dict[str, Any]:
    directory = run_dir(task)
    if not (directory / "events.jsonl").is_file():
        raise FactoryError(f"unknown run {task!r}")
    snap = snapshot(directory)
    state = snap["state"]
    if state == "running" and not snap["live"]:
        state = "interrupted"
    steps = [{"id": s["id"], "status": "interrupted" if s["interrupted"] else s["status"], "skill": s["skill"],
              "attempts": s["attempts"], "model": s["model"], "session_id": s["session_id"],
              "cost_usd": s["cost_usd"], "started_at": s["started_at"], "finished_at": s["finished_at"],
              "reason": s["reason"]} for s in snap["steps"]]
    rows = run_rows(directory, agents_home())
    kit_writes, kit_changed = kit_activity(read_events(directory))
    return {"task_id": task, "state": state, "schema_version": SCHEMA_VERSION, "pipeline": snap.get("pipeline"),
            "mode": snap.get("mode"), "repo": snap.get("repo"), "branch": snap.get("branch"),
            "current_step": snap.get("current"), "progress": progress_of(snap), "cost_usd": snap["cost_usd"],
            "route": snap.get("route"),
            "sync": snap.get("sync"), "sync_writes": snap.get("sync_writes", []),
            "park": snap.get("park"), "human_action": human_action(snap, directory), "engine_pid": snap["engine_pid"],
            "created_at": snap.get("created_at"), "finished_at": snap.get("finished_at"), "steps": steps,
            "kb_proposals": sorted(str(p) for p in directory.glob("steps/*/kb-proposals.md")),
            "kb_proposals_pending": sum(1 for r in rows if r["state"] == "pending"),
            "kb_proposals_invalid": sum(1 for r in rows if r["state"] == "invalid"),
            "harness_proposals": sum(1 for r in run_rows(directory, agents_home(), "harness") if r["state"] == "pending"),
            "kit_writes": kit_writes, "kit_changed": kit_changed}


def render_table(payload: dict[str, Any]) -> str:
    prog = payload["progress"]
    head = f"{payload['task_id']}  {payload['state']}  pipeline={payload['pipeline']}  "
    lines = [head + f"progress={prog['done']}/{prog['total']} {prog['percent']}%  cost=${payload['cost_usd']:.2f}"]
    for step in payload["steps"]:
        lines.append(f"  {step['id']:<24} {step['status']:<12} attempts={step['attempts']} model={step['model'] or '-'}")
    if payload.get("kb_proposals"):
        lines.append(f"  kb proposals pending: {payload.get('kb_proposals_pending', 0)} "
                     f"(agentctl kb proposals list --task {payload['task_id']})")
        if payload.get("kb_proposals_invalid"):
            lines.append(f"  kb proposals invalid: {payload['kb_proposals_invalid']} "
                         f"(agentctl kb proposals list --task {payload['task_id']} --state invalid)")
    if payload.get("harness_proposals"):
        lines.append(f"  harness proposals: {payload['harness_proposals']} (applied only by agentctl harness)")
    if payload.get("kit_writes"):
        lines.append(f"  kit writes by workers: {sum(len(w['paths']) for w in payload['kit_writes'])} "
                     "(status --json lists them)")
    if payload.get("kit_changed"):
        lines.append(f"  kit changed outside attribution: {sum(len(c['paths']) for c in payload['kit_changed'])} "
                     "(visibility only, nothing reverted)")
    if payload.get("human_action"):
        reason = payload["park"]["reason"] if payload.get("park") else payload["state"]
        lines.append(f"  -> {reason}: {payload['human_action']}")
    return "\n".join(lines)


def cmd_status(args: argparse.Namespace) -> int:
    if args.task:
        payload = status_payload(args.task)
        print(json.dumps(payload, separators=(",", ":"), ensure_ascii=False) if args.json else render_table(payload))
        return 0
    root = factory_root()
    runs = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if (child / "events.jsonl").is_file():
                runs.append(status_payload(child.name))
    if args.json:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "runs": [
            {k: r[k] for k in ("task_id", "state", "pipeline", "current_step", "cost_usd", "human_action")}
            for r in runs]}, separators=(",", ":"), ensure_ascii=False))
    else:
        print("\n".join(f"{r['task_id']:<20} {r['state']:<24} {r['pipeline'] or '-'}  {r['current_step'] or '-'}"
                        for r in runs) or "no factory runs")
    return 0


def resumable(task: str) -> bool:
    snap = snapshot(run_dir(task))
    return not snap["live"] and snap["state"] in ("running", "stopped", "parked", "failed")


def approve_rehearsal(directory: Path, task: str, snap: dict[str, Any]) -> None:
    """Record the operator's approval of rehearsal.json as it is now (the gate refuses any later change)."""
    if (snap.get("park") or {}).get("reason") != "rehearsal_ready":
        raise FactoryError(f"run {task} is not parked rehearsal_ready; --approve-rehearsal has nothing to approve")
    path = plan_dir(task) / "rehearsal.json"
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise FactoryError(f"cannot approve: {path} unreadable: {exc}") from exc
    append_event(directory, "rehearsal_approved", sha256=digest, approved_at=now())


def cmd_resume(args: argparse.Namespace) -> int:
    watching = watch_requested(args)
    if watching and args.all:
        raise FactoryError("--progress and --verbose follow one run; pass a task id instead of --all")
    if args.approve_rehearsal and args.all:
        raise FactoryError("--approve-rehearsal approves one run; pass its task id instead of --all")
    tasks = []
    if args.all:
        root = factory_root()
        tasks = [c.name for c in sorted(root.iterdir()) if (c / "events.jsonl").is_file()] if root.is_dir() else []
        tasks = [t for t in tasks if snapshot(run_dir(t))["state"] in ("running", "stopped") and resumable(t)
                 and (snapshot(run_dir(t)).get("park") or {}).get("reason") != "rehearsal_ready"]
    elif args.task:
        tasks = [args.task]
    else:
        raise FactoryError("resume needs a task id or --all")
    for task in tasks:
        directory = run_dir(task)
        if not (directory / "events.jsonl").is_file():
            raise FactoryError(f"unknown run {task!r}")
        if lock_holder(directory) is not None:
            raise FactoryError(f"run {task} is live; refusing a second engine")
        snap = snapshot(directory)
        match = harness_repo(Path(snap["repo"])) if snap.get("repo") else None
        if match is not None:
            if args.all:
                print(f"skipped {task}: {harness_refusal(match)}", file=sys.stderr)
                continue
            raise FactoryError(harness_refusal(match))
        if snap["state"] == "awaiting_human_review":
            raise FactoryError(f"run {task} already finished (awaiting_human_review)")
        if args.approve_rehearsal:
            approve_rehearsal(directory, task, snap)
        elif (snap.get("park") or {}).get("reason") == "rehearsal_ready":
            raise FactoryError(f"run {task} waits for the rehearsal approval: read {plan_dir(task) / 'rehearsal.md'}, "
                               f"then run `agentctl factory resume {task} --approve-rehearsal`")
        append_event(directory, "resume", previous_state=snap["state"])
        write_snapshot(directory, snapshot(directory))
        launch(task, foreground=args.foreground)
        if watching:
            return attach_watch(task, args)
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    directory = run_dir(args.task)
    if not (directory / "events.jsonl").is_file():
        raise FactoryError(f"unknown run {args.task!r}")
    pid = lock_holder(directory)
    if pid and pid > 0:
        os.kill(pid, signal.SIGTERM)
        for _ in range(100):
            if lock_holder(directory) is None:
                break
            time.sleep(0.1)
    snap = derive(read_events(directory))
    for step in snap["steps"]:
        if step["status"] == "running":
            kill_worker(step.get("pid"), step.get("session_id"))
            append_event(directory, "interrupted", id=step["id"], reason="stop")
    if derive(read_events(directory))["state"] not in ("stopped", "awaiting_human_review"):
        append_event(directory, "stopped")
    write_snapshot(directory, snapshot(directory))
    emit({"task_id": args.task, "state": "stopped", "resumable": True})
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    watching = watch_requested(args)
    directory = run_dir(args.task)
    if not (directory / "events.jsonl").is_file():
        raise FactoryError(f"unknown run {args.task!r}")
    snap = snapshot(directory)
    if snap["live"]:
        raise FactoryError(f"run {args.task} is live; stop it first")
    if args.step_id not in [s["id"] for s in snap["steps"]]:
        raise FactoryError(f"unknown step id {args.step_id!r}")
    if snap.get("repo") and (match := harness_repo(Path(snap["repo"]))) is not None:
        raise FactoryError(harness_refusal(match))
    append_event(directory, "reset", id=args.step_id)
    append_event(directory, "resume", previous_state=snap["state"], single_step=args.step_id)
    code = launch(args.task, foreground=args.foreground, only_step=args.step_id)
    return attach_watch(args.task, args) if watching and code == 0 else code


def cmd_watch(args: argparse.Namespace) -> int:
    import agentctl_factory_watch  # imports this module; kept out of the top to avoid a cycle

    return agentctl_factory_watch.cmd_watch(args)


def add_watch_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--progress", action="store_true", help="Show steps done (n/total, percent) while the run goes.")
    parser.add_argument("--verbose", action="store_true", help="Show engine events and the worker's actions live.")


def add_factory_parsers(group: argparse._SubParsersAction) -> None:
    start = group.add_parser("start", help="Start a pipeline run for a tracker task id or a local slug.",
                             description="Start a run in the git repo of the current directory. The tracker pipeline "
                                         "needs the task branch checked out; the factory never switches branches.")
    start.add_argument("task")
    start.add_argument("--pipeline", help="A pipeline listed in .agentctl [factory] pipelines.")
    start.add_argument("--context", help="Brainstorm handoff file passed to plan-implementation.")
    start.add_argument("--path", choices=list(PATHS), help="Force the route path (the only way to skip_evidence).")
    start.add_argument("--dual", choices=["plan"], help="Force a plan-stage dual run.")
    start.add_argument("--vendor", choices=["claude", "codex"], help="Default: .agentctl [factory] vendor.")
    start.add_argument("--max-cost-usd", type=float, dest="max_cost_usd")
    start.add_argument("--max-hours", type=float, dest="max_hours")
    start.add_argument("--dry-run", action="store_true", help="Print resolved steps, roles, models and gates only.")
    start.add_argument("--foreground", action="store_true", help="Run in this process (tests, debugging).")
    add_watch_flags(start)
    start.set_defaults(func=cmd_start)

    status = group.add_parser("status", help="Show run state from files (no model or network call).")
    status.add_argument("task", nargs="?")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    resume = group.add_parser("resume", help="Resume an interrupted, stopped or parked run.")
    resume.add_argument("task", nargs="?")
    resume.add_argument("--all", action="store_true", help="Resume every running or stopped run.")
    resume.add_argument("--foreground", action="store_true")
    resume.add_argument("--approve-rehearsal", action="store_true", dest="approve_rehearsal",
                        help="Approve the rehearsal of a run parked rehearsal_ready, then resume it.")
    add_watch_flags(resume)
    resume.set_defaults(func=cmd_resume)

    stop = group.add_parser("stop", help="Stop the engine and worker; the run stays resumable.")
    stop.add_argument("task")
    stop.set_defaults(func=cmd_stop)

    step = group.add_parser("step", help="Run one step through the same engine path.")
    step.add_argument("task")
    step.add_argument("step_id")
    step.add_argument("--foreground", action="store_true")
    add_watch_flags(step)
    step.set_defaults(func=cmd_step)

    watch = group.add_parser("watch", help="Follow a run live: progress, verbose log, or both (read-only).",
                             description="Tails the run's files. Default view is --progress. Ctrl-C detaches the "
                                         "viewer only; the engine keeps running.")
    watch.add_argument("task", nargs="?", help="Default: the one live run.")
    add_watch_flags(watch)
    watch.set_defaults(func=cmd_watch)

    engine = group.add_parser("_engine")
    engine.add_argument("task")
    engine.add_argument("--only-step")
    engine.set_defaults(func=cmd_engine)
