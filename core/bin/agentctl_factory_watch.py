"""`agentctl factory watch`: a read-only live view of a run, built from its files.

The engine runs detached and writes `events.jsonl` plus `steps/<nn>-<id>/raw.jsonl`. The viewer tails
those files; it never talks to the engine, so Ctrl-C leaves the run untouched. Progress shows how many
steps are done, verbose shows engine events and the running worker's actions. Tool results, prompts
and step summaries are never printed. Liveness is read from the lock file's pid, never by taking the
lock: `lock_holder()` flocks and unlinks, which could make a starting engine lose its lock.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

import agentctl_factory as factory
from agentctl_factory import FactoryError, bound

TERMINAL_STATES = ("awaiting_human_review", "failed", "parked", "stopped")
HIDDEN_RAW = ("user", "system", "rate_limit_event", "stream_event")
SKIPPED_EVENTS = ("worker_pid", "baseline_updated")
SKIPPED_FIELDS = ("ts", "type", "summary", "id", "settings", "step_specs")
ARG_KEYS = ("command", "file_path", "path", "pattern", "query", "skill", "url", "description")
BAR_WIDTH = 10
DEFAULT_WIDTH = 80
NOT_LIVE_GRACE_S = 10.0


def parse_ts(value: str | None) -> datetime | None:
    try:
        return datetime.strptime(value or "", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def duration(seconds: float) -> str:
    total = max(int(seconds), 0)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}h{minutes:02d}m" if hours else f"{minutes}m{secs:02d}s"


def engine_live(directory: Path) -> bool:
    try:
        raw = (directory / "lock").read_text().strip()
        cmdline = Path(f"/proc/{raw}/cmdline").read_bytes().split(b"\0") if raw.isdigit() else []
    except OSError:
        return False
    return b"_engine" in cmdline and directory.name.encode() in cmdline


def render_event(ev: dict[str, Any]) -> str | None:
    kind = ev.get("type", "?")
    if kind in SKIPPED_EVENTS:
        return None
    stamp = (ev.get("ts") or "")[11:19] or "--:--:--"
    head = f"{ev['id']} " if ev.get("id") else ""
    if kind == "run_started":
        body = f"run_started pipeline={ev.get('pipeline')} steps={len(ev.get('step_specs', []))}"
    elif kind == "step_started":
        body = f"> {head}model={ev.get('model') or '-'}"
    elif kind == "step_finished":
        body = f"< {head}{ev.get('status')}" + (f" ({ev['reason']})" if ev.get("reason") else "")
    else:
        fields = " ".join(f"{k}={bound(str(v), 80)}" for k, v in ev.items()
                          if k not in SKIPPED_FIELDS and isinstance(v, str | int | float | bool))
        body = f"{kind} {head}{fields}".rstrip()
    return f"{stamp} {body}"


def tool_args(payload: dict[str, Any]) -> str:
    for key in ARG_KEYS:
        if isinstance(payload.get(key), str):
            return bound(" ".join(payload[key].split()), 80)
    return ""


def render_raw(line: str) -> list[str]:
    """Lines for one worker stream line. Claude stream-json is parsed; anything else falls back to type and text."""
    line = line.strip()
    if not line:
        return []
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return [f"  | {bound(line, 120)}"]
    if not isinstance(event, dict):
        return []
    kind = event.get("type")
    if kind in HIDDEN_RAW:
        return []
    if kind == "assistant":
        out = []
        for block in (event.get("message") or {}).get("content") or []:
            if block.get("type") == "text" and block.get("text", "").strip():
                out.append(f"  | {bound(' '.join(block['text'].split()), 160)}")
            elif block.get("type") == "tool_use":
                out.append(f"  $ {block.get('name', '?')} {tool_args(block.get('input') or {})}".rstrip())
        return out
    if kind == "result":
        cost = event.get("total_cost_usd")
        denied = [f"  ! denied {d.get('tool_name', '?')}" for d in event.get("permission_denials") or []
                  if isinstance(d, dict)]
        return denied + [f"  = worker {event.get('subtype', 'done')}" + (f" cost=${cost:.2f}" if isinstance(cost, int | float) else "")]
    item = event.get("item") if isinstance(event.get("item"), dict) else event
    text = next((item[k] for k in ("text", "message") if isinstance(item.get(k), str)), "")
    return [f"  | {kind or '?'} {bound(' '.join(text.split()), 100)}".rstrip()]


def run_elapsed(snap: dict[str, Any], events: list[dict[str, Any]], now: datetime) -> float:
    last = next((parse_ts(e["ts"]) for e in reversed(events) if e["type"] in ("run_started", "resume")), None)
    live = (now - last).total_seconds() if last and snap.get("live") else 0.0
    return snap.get("elapsed_s", 0.0) + live


def progress_line(snap: dict[str, Any], events: list[dict[str, Any]], now: datetime, *, timed: bool) -> str:
    prog = factory.progress_of(snap)
    filled = round(BAR_WIDTH * prog["done"] / prog["total"]) if prog["total"] else 0
    parts = [f"[{prog['done']}/{prog['total']} {prog['percent']}%] [{'#' * filled}{'-' * (BAR_WIDTH - filled)}]"]
    if snap["state"] != "running":
        parts.append(snap["state"])
    if prog["current"]:
        step = next(s for s in snap["steps"] if s["id"] == prog["current"])
        started = parse_ts(step.get("started_at"))
        limit = snap.get("limits", {}).get("step_timeout_min")
        if timed and started and step["status"] == "running":
            parts.append(f"{prog['current']} {duration((now - started).total_seconds())}" + (f"/{limit}m" if limit else ""))
        else:
            parts.append(prog["current"])
    cap = snap.get("limits", {}).get("run_usd")
    parts.append(f"${snap['cost_usd']:.2f}" + (f"/${cap:g}" if cap else ""))
    hours = snap.get("limits", {}).get("run_hours")
    if timed and snap.get("live"):
        parts.append(f"run {duration(run_elapsed(snap, events, now))}" + (f"/{hours:g}h" if hours else ""))
    if prog["loop"]:
        parts.append(f"loop {prog['loop']}")
    return " ".join(parts)


class Tail:
    """Complete new lines of one file since the last read, by byte offset."""

    def __init__(self, path: Path | None = None, offset: int = 0) -> None:
        self.path = path
        self.offset = offset

    def read(self) -> list[str]:
        if not self.path or not self.path.is_file():
            return []
        with self.path.open("rb") as handle:
            handle.seek(self.offset)
            data = handle.read()
        cut = data.rfind(b"\n") + 1
        self.offset += cut
        return data[:cut].decode("utf-8", errors="replace").splitlines()


def running_raw(directory: Path, snap: dict[str, Any]) -> Path | None:
    step = next((s for s in snap["steps"] if s["status"] == "running"), None)
    return directory / "steps" / f"{step['index']:02d}-{step['id']}" / "raw.jsonl" if step else None


def follow(directory: Path, *, progress: bool, verbose: bool, out: TextIO, is_tty: bool,
           clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
           wall: Callable[[], datetime] = lambda: datetime.now(UTC), interval: float = 0.5,
           grace: float = NOT_LIVE_GRACE_S, width: int | None = None) -> int:
    """Print the run's progress and/or log until it reaches a terminal state. Exit 0 only for awaiting_human_review."""
    width = width or (shutil.get_terminal_size((DEFAULT_WIDTH, 24)).columns if is_tty else DEFAULT_WIDTH)

    def fit(text: str) -> str:
        return bound(text, width - 1)

    events: list[dict[str, Any]] = []
    tail_events = Tail(directory / "events.jsonl")
    tail_raw = Tail()
    first_pass = True
    drawn = False
    last_key: tuple[Any, ...] | None = None
    dead_since: float | None = None

    def write_logs(lines: list[str]) -> None:
        nonlocal drawn
        if not lines:
            return
        if drawn:
            out.write("\r\x1b[2K")
            drawn = False
        out.write("".join(fit(line) + "\n" for line in lines))

    def draw(snap: dict[str, Any], *, final: bool) -> None:
        nonlocal drawn, last_key
        line = fit(progress_line(snap, events, wall(), timed=is_tty))
        if is_tty:
            out.write("\r\x1b[2K" + line + ("\n" if final else ""))
            drawn = not final
            return
        prog = factory.progress_of(snap)
        key = (prog["done"], prog["current"], snap["state"], prog["loop"])
        if key != last_key or final:
            out.write(line + "\n")
            last_key = key

    try:
        while True:
            for raw_line in tail_events.read():
                with contextlib.suppress(json.JSONDecodeError):
                    events.append(json.loads(raw_line))
                    if verbose and (text := render_event(events[-1])):
                        write_logs([text])
            snap = factory.derive(events)
            snap["live"] = engine_live(directory)
            if verbose:
                raw_lines = tail_raw.read()
                raw_path = running_raw(directory, snap)
                if raw_path != tail_raw.path:  # the old step's last lines were drained above
                    start = raw_path.stat().st_size if first_pass and raw_path and raw_path.is_file() else 0
                    tail_raw = Tail(raw_path, start)
                    raw_lines += tail_raw.read()
                write_logs([text for raw_line in raw_lines for text in render_raw(raw_line)])
            first_pass = False
            now = clock()
            if snap["live"] or snap["state"] != "running":
                dead_since = None
            elif dead_since is None:
                dead_since = now
            state = snap["state"]
            if snap["state"] == "running" and dead_since is not None and now - dead_since >= grace:
                state = "interrupted"
            if state in TERMINAL_STATES or state == "interrupted":
                for raw_line in tail_events.read():
                    with contextlib.suppress(json.JSONDecodeError):
                        events.append(json.loads(raw_line))
                        if verbose and (text := render_event(events[-1])):
                            write_logs([text])
                snap = factory.derive(events)
                snap["live"] = False
                if state == "interrupted":
                    snap["state"] = state
                if progress or not verbose:
                    draw(snap, final=True)
                if action := factory.human_action(snap):
                    out.write(fit(f"-> {action}") + "\n")
                out.flush()
                return 0 if snap["state"] == "awaiting_human_review" else 1
            if progress or not verbose:
                draw(snap, final=False)
            out.flush()
            sleep(interval)
    except KeyboardInterrupt:
        out.write(("\n" if drawn else "") + f"detached; the run continues. reattach: agentctl factory watch {directory.name}\n")
        out.flush()
        return 130


def watch_task(task: str, *, progress: bool, verbose: bool) -> int:
    directory = factory.run_dir(task)
    if not (directory / "events.jsonl").is_file():
        raise FactoryError(f"unknown run {task!r}")
    return follow(directory, progress=progress or not verbose, verbose=verbose, out=sys.stdout,
                  is_tty=sys.stdout.isatty())


def cmd_watch(args: Any) -> int:
    task = args.task
    if not task:
        root = factory.factory_root()
        children = sorted(root.iterdir()) if root.is_dir() else []
        live = [c.name for c in children if (c / "events.jsonl").is_file() and engine_live(c)]
        if len(live) != 1:
            raise FactoryError("pass a task id; live runs: " + (", ".join(live) or "none"))
        task = live[0]
    return watch_task(task, progress=args.progress, verbose=args.verbose)
