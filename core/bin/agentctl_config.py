"""Reader for the `.agentctl` settings file (TOML, standard library only).

Standalone on purpose: hooks import it without pulling in the rest of agentctl. Resolution order:
$AGENTCTL_CONFIG, then $AGENTS_HOME/.agentctl (a profile's own copy), then ~/.agents/.agentctl.
Nothing here carries defaults. The file is the defaults, so a missing or unreadable one is an error
the caller decides how to handle (the factory stops, a safety hook fails closed).
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
FILE_NAME = ".agentctl"


class ConfigError(Exception):
    """The settings file is missing, unreadable or of an unknown schema."""


def candidates() -> list[Path]:
    paths: list[Path] = []
    if os.environ.get("AGENTCTL_CONFIG"):
        paths.append(Path(os.environ["AGENTCTL_CONFIG"]).expanduser())
    if os.environ.get("AGENTS_HOME"):
        paths.append(Path(os.environ["AGENTS_HOME"]).expanduser() / FILE_NAME)
    paths.append(Path.home() / ".agents" / FILE_NAME)
    return paths


def config_path() -> Path:
    for path in candidates():
        if path.is_file():
            return path
    raise ConfigError("no .agentctl found; looked in " + ", ".join(str(p) for p in candidates())
                      + ". Write the defaults with `python3 bin/agentctl_defaults.py`.")


def load(path: Path | None = None) -> dict[str, Any]:
    path = path or config_path()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ConfigError(f"{path}: schema_version must be {SCHEMA_VERSION}")
    return data


def section(cfg: dict[str, Any], dotted: str) -> dict[str, Any]:
    """A table by dotted path; a missing table is an error, not an empty default."""
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f".agentctl has no [{dotted}] table")
        node = node[part]
    if not isinstance(node, dict):
        raise ConfigError(f".agentctl [{dotted}] is not a table")
    return node


def tracker(cfg: dict[str, Any]) -> dict[str, Any] | None:
    """The active tracker flavor's table, or None when kind is "none"."""
    kind = section(cfg, "tracker").get("kind")
    if kind in (None, "none"):
        return None
    flavor = section(cfg, f"tracker.{kind}")
    return {**flavor, "kind": kind}


def load_quiet() -> dict[str, Any] | None:
    """For hooks: the settings, or None when they cannot be read (the hook then picks its safe side)."""
    try:
        return load()
    except ConfigError:
        return None


def in_factory(cfg: dict[str, Any] | None, fallback_env: str = "AGENTCTL_FACTORY") -> bool:
    """True when this process carries the env var .agentctl [factory] env names (a headless factory worker)."""
    name = ((cfg or {}).get("factory") or {}).get("env", fallback_env)
    return bool(os.environ.get(name))


NEVER_MATCHES = re.compile(r"(?!x)x")


def key_pattern(cfg: dict[str, Any] | None = None, *, ignore_case: bool = False) -> re.Pattern[str]:
    """Regex that finds the active tracker's issue keys inside text (group 1 is the key).

    With `kind = "none"` nothing is a key, so the pattern never matches.
    """
    flavor = tracker(cfg or load())
    if flavor is None:
        return NEVER_MATCHES
    return re.compile(flavor["key_pattern"], re.IGNORECASE if ignore_case else 0)


def key_kind(task_id: str, cfg: dict[str, Any] | None = None, *, ignore_case: bool = False) -> str | None:
    """The tracker kind when `task_id` is one of its issue keys, else None (a local task)."""
    flavor = tracker(cfg or load())
    if flavor is None:
        return None
    flags = re.IGNORECASE if ignore_case else 0
    return flavor["kind"] if re.fullmatch(flavor["key_regex"], task_id, flags) else None


def is_closed_status(name: str | None, category: str | None, cfg: dict[str, Any] | None = None) -> bool:
    """True when a tracker issue is released or discarded: its status category is done, or its status name
    is in the tracker's `closed_statuses` (case-insensitive). Such issues are never factory work."""
    if category == "done":
        return True
    flavor = tracker(cfg or load())
    if flavor is None or not name:
        return False
    return name.strip().casefold() in {s.casefold() for s in flavor.get("closed_statuses", [])}


def git_host(cfg: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """The active git host flavor's table (merged with the shared vocabulary), or None for kind "none"."""
    cfg = cfg or load()
    host = section(cfg, "git_host")
    kind = host.get("kind")
    if kind in (None, "none"):
        return None
    return {**section(cfg, f"git_host.{kind}"), "kind": kind,
            "review_request_terms": list(host.get("review_request_terms", []))}


def bot_author_pattern(cfg: dict[str, Any] | None = None) -> re.Pattern[str]:
    """Authors of automated tracker comments: the tracker's generic bots plus the git host's integration."""
    cfg = cfg or load()
    parts = [t["bot_author_re"] for t in (tracker(cfg), git_host(cfg)) if t and t.get("bot_author_re")]
    return re.compile("|".join(parts), re.IGNORECASE) if parts else NEVER_MATCHES
