"""`devkit profile session-sync`: copy agent sessions from one instance to another.

One direction per run; swap --source and --target for the other. `stock` names
the unprefixed installs (~/.config/Claude, ~/.claude, ~/.codex, ~/.config/Cursor).
--agent picks which of Claude, Codex and Cursor to copy; each agent's rules are
in devkit_cli/sessions/<agent>.py.

A file or row is copied when the target lacks it or the source is newer. Nothing
is deleted, and a newer target is never overwritten. Everything is a dry run
until --apply, and --apply refuses while the target's app is running.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from . import instances, privilege
from .common import Plan
from .errors import DevkitError
from .sessions import claude, codex, cursor
from .sessions.claude import STOCK, running
from .sessions.common import Side, Step, holders

AGENTS = ("claude", "codex", "cursor")
Found = list[tuple[str, str]]


def resolve_side(name: str, home: Path) -> Side:
    if name == STOCK:
        return Side(STOCK, home / ".config" / "Claude", home / ".claude",
                    home / ".codex", home / ".config" / "Cursor")
    mine = {vendor: config_dir for n, vendor, config_dir, _prov
            in instances.discover_instances(home) if n == name}
    if not mine:
        installed = sorted({n for n, *_ in instances.discover_instances(home)})
        raise DevkitError(f"no installed profile named {name!r}",
                          f"use one of: {', '.join([STOCK, *installed])}")
    layout = instances.paths_for(name, "claude", home) if "claude" in mine else None
    return Side(name,
                layout["user_data_dir"] if layout else None,
                layout["config_dir"] if layout else None,
                mine.get("codex"), mine.get("cursor"))


def _installed(side: Side) -> set[str]:
    return {agent for agent, path in (("claude", side.code), ("codex", side.codex),
                                      ("cursor", side.cursor)) if path}


def choose_agents(raw: str, src: Side, dst: Side) -> list[str]:
    names = [n.strip() for n in raw.split(",") if n.strip()]
    if names == ["all"]:
        shared = [a for a in AGENTS if a in _installed(src) & _installed(dst)]
        if not shared:
            raise DevkitError(f"{src.name} and {dst.name} have no agent in common",
                              "'devkit profile list' shows what each profile has")
        return shared
    unknown = [n for n in names if n not in AGENTS]
    if unknown or not names:
        raise DevkitError(f"unknown agent {', '.join(unknown) or raw!r}",
                          f"use a comma-separated list of: {', '.join(AGENTS)}, or 'all'")
    chosen = list(dict.fromkeys(names))
    for agent in chosen:
        for side in (src, dst):
            if agent not in _installed(side):
                raise DevkitError(f"{side.name} has no {agent} instance",
                                  f"drop {agent} from --agent, or create it with "
                                  f"'devkit profile create'")
    return chosen


def sync_sessions(home: Path, source: str, target: str, plan: Plan, *,
                  agents: str = "claude", only: str | None = None,
                  indexeddb: bool = False,
                  find_running: Callable[..., Found] = running,
                  find_holders: Callable[..., Found] = holders) -> None:
    if source == target:
        raise DevkitError("source and target are the same instance",
                          "pass two different names; 'stock' is the unprefixed install")
    src, dst = resolve_side(source, home), resolve_side(target, home)
    chosen = choose_agents(agents, src, dst)
    if (only or indexeddb) and "claude" not in chosen:
        raise DevkitError("--only and --indexeddb are Claude options",
                          "add claude to --agent, or drop them")

    steps: list[Step] = []
    blockers: Found = []
    if "claude" in chosen:
        steps += claude.plan(src, dst, only, indexeddb)
        blockers += find_running(dst, only != "code", only != "desktop")
        if indexeddb:
            blockers += find_running(src, True, False)
    if "codex" in chosen:
        steps += _guard(codex.plan, src.codex, dst.codex)
        blockers += find_holders("Codex", [dst.codex])
    if "cursor" in chosen:
        steps += _guard(cursor.plan, src.cursor, dst.cursor)
        blockers += find_holders("Cursor", [dst.cursor])
    if not steps:
        raise DevkitError(f"{source} has no {', '.join(chosen)} sessions to copy",
                          "check the name; 'devkit profile list' shows installed profiles")

    work = [step for step in steps if step.line]
    for step in work:
        plan.record(step.line)
    if blockers and work and plan.apply:
        raise DevkitError("an app is still running: " + _summary(blockers),
                          "quit it, then re-run")
    if blockers and work:
        print("note: quit these before --apply: " + _summary(blockers))
    if plan.apply:
        for step in work:
            _guard(step.run)


def _guard(call, *args):
    try:
        return call(*args)
    except sqlite3.DatabaseError as exc:
        raise DevkitError(f"a session database could not be used: {exc}",
                          "quit the app that owns it and re-run; both sides should run "
                          "the same version of the agent") from exc


def _summary(blockers: Found) -> str:
    kinds: dict[str, list[str]] = {}
    for kind, pid in blockers:
        kinds.setdefault(kind, []).append(pid)
    return "; ".join(f"{kind} (pids {', '.join(pids[:3])}{', ...' if len(pids) > 3 else ''})"
                     for kind, pids in kinds.items())


def cmd_session_sync(args) -> int:
    user = privilege.refuse_root(None)
    plan = Plan(args.apply)
    sync_sessions(Path(user.pw_dir), args.source, args.target, plan,
                  agents=args.agent, only=args.only, indexeddb=args.indexeddb)
    return plan.report(f"session-sync {args.source} -> {args.target}")
