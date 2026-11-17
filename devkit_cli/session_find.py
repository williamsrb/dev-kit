"""`devkit profile session-find`: locate one Claude session by title.

Read-only. Looks at every installed profile and at stock. Desktop index files
are always read in full; transcripts are scanned from --since (default: the
last 30 days) because each side holds gigabytes of them.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from . import instances, privilege
from .errors import DevkitError
from .session_sync import resolve_side
from .sessions import claude
from .sessions.claude import STOCK

DEFAULT_DAYS = 30
CAP = 20


def _since(raw: str | None, now: float) -> tuple[float, bool]:
    if not raw:
        return now - DEFAULT_DAYS * 86400, False
    try:
        return datetime.strptime(raw, "%Y-%m-%d").timestamp(), True
    except ValueError:
        raise DevkitError(f"--since {raw!r} is not a date", "use YYYY-MM-DD") from None


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _side_records(side, cutoff: float, explicit: bool) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for path, data in claude.desktop_entries(side.desktop):
        sid = data.get("cliSessionId")
        if not sid:
            continue
        stamp = (data.get("lastActivityAt") or path.stat().st_mtime * 1000) / 1000
        known = records.get(sid)
        if known and known["_ts"] >= stamp:
            continue
        records[sid] = {"profile": side.name, "session_id": sid, "title": data.get("title"),
                        "cwd": data.get("cwd"), "_ts": stamp, "index": str(path),
                        "transcripts": []}
    for path in sorted((side.code / "projects").glob("*/*.jsonl")):
        sid = path.stem
        mtime = path.stat().st_mtime
        if sid not in records and mtime < cutoff:
            continue
        rec = records.setdefault(sid, {"profile": side.name, "session_id": sid, "title": None,
                                       "cwd": None, "_ts": mtime, "index": None,
                                       "transcripts": []})
        rec["transcripts"].append(str(path))
    for sid, rec in list(records.items()):
        if explicit and rec["_ts"] < cutoff:
            del records[sid]
            continue
        if not rec["transcripts"]:
            rec["transcripts"] = [str(p) for p in claude.transcripts(side.code, sid)]
        if rec["title"] is None and rec["transcripts"]:
            rec["title"] = claude.transcript_title(Path(rec["transcripts"][0]))
        if rec["cwd"] is None and rec["transcripts"]:
            rec["cwd"] = claude.transcript_cwd(Path(rec["transcripts"][0]))
        rec["surface"] = ("both" if rec["index"] and rec["transcripts"]
                          else "desktop" if rec["index"] else "code")
    return records


def _rank(title: str, wanted: str) -> int | None:
    low, want = title.lower(), wanted.lower()
    if low == want:
        return 0
    if low.startswith(want):
        return 1
    return 2 if want in low else None


def find_sessions(home: Path, title: str, since: str | None = None,
                  profile: str | None = None, now: float | None = None) -> tuple[list[dict], int]:
    now = time.time() if now is None else now
    cutoff, explicit = _since(since, now)
    if profile:
        names = [profile]
        resolve_side(profile, home)
    else:
        names = [STOCK, *sorted({n for n, vendor, *_ in instances.discover_instances(home)
                                 if vendor == "claude"})]
    matches = []
    for name in names:
        side = resolve_side(name, home)
        if side.code is None:
            continue
        for rec in _side_records(side, cutoff, explicit).values():
            rank = _rank(rec["title"] or "", title)
            if rank is not None:
                matches.append((rank, rec))
    matches.sort(key=lambda m: (m[0], -m[1]["_ts"]))
    rows = []
    for _, rec in matches[:CAP]:
        row = {k: v for k, v in rec.items() if k != "_ts"}
        row["last_activity"] = _iso(rec["_ts"])
        rows.append(row)
    return rows, len(matches)


def cmd_session_find(args) -> int:
    user = privilege.refuse_root(None)
    rows, total = find_sessions(Path(user.pw_dir), args.title, args.since, args.profile)
    if args.json:
        print(json.dumps({"total": total, "shown": len(rows), "sessions": rows}, indent=2))
        return 0
    if not rows:
        print(f"no session matched {args.title!r}")
        return 0
    for row in rows:
        print(f"{row['profile']:<12} {row['session_id']}  {row['last_activity']}  "
              f"{row['surface']:<7} {row['title']}")
        print(f"    cwd: {row['cwd'] or '-'}")
        if row["index"]:
            print(f"    index: {row['index']}")
        for path in row["transcripts"]:
            print(f"    transcript: {path}")
    if total > len(rows):
        print(f"\n{total - len(rows)} more matches; narrow with --since or --profile.")
    return 0
