"""Fill a profile instance's MCP files from the catalog.

The profile `mcp` list is the default-alive set. Catalog `parked` names
(slack, playwright stub, browser-control) stay out unless the operator
puts them on a profile list *and* registers with --force via mcp/install.py.
Spawned `playwright-<id>` instances are not profile defaults.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .common import load_json


def load_catalog(kit_root: Path) -> dict:
    return load_json(kit_root / "core" / "mcp" / "catalog.json", "mcp catalog")


def live_names(profile: dict, catalog: dict) -> list[str]:
    parked = catalog.get("parked") or {}
    servers = catalog.get("servers") or {}
    names: list[str] = []
    for name in profile.get("mcp") or []:
        if name in parked or name not in servers:
            continue
        if name not in names:
            names.append(name)
    return names


def _expand(value: str, home: Path) -> str:
    return value.replace("${HOME}", str(home))


def _overlay(spec: dict, vendor: str) -> dict:
    out = dict(spec)
    extra = (spec.get("vendor_overrides") or {}).get(vendor) or {}
    out.update(extra)
    return out


def server_entry(catalog: dict, name: str, vendor: str, home: Path) -> dict:
    spec = _overlay(catalog["servers"][name], vendor)
    if spec["transport"] == "http":
        url = _expand(spec["url"], home)
        if vendor == "cursor":
            built = {"url": url}
            if name == "atlassian-rovo-preview":
                built["type"] = "http"
            return built
        return {"type": "http", "url": url}

    built: dict = {
        "command": _expand(spec["command"], home),
        "args": [_expand(a, home) for a in spec.get("args") or []],
    }
    if vendor == "claude":
        built = {"type": "stdio", **built}
    return built


def keep_dynamic(existing: dict, desired: dict, catalog: dict) -> dict:
    """Keep spawned playwright-<id> (and other operator extras) across sync.

    Catalog `parked` names are dropped. Defaults from the profile list win.
    """
    parked = set(catalog.get("parked") or {})
    out = dict(desired)
    for name, spec in existing.items():
        if name in out or name in parked:
            continue
        out[name] = spec
    return out


def cursor_payload(profile: dict, catalog: dict, home: Path,
                   comment: list[str], existing: dict | None = None) -> dict:
    servers = {
        name: server_entry(catalog, name, "cursor", home)
        for name in live_names(profile, catalog)
        if "cursor" in catalog["servers"][name].get("vendors", [])
    }
    if existing:
        servers = keep_dynamic(existing, servers, catalog)
    return {"_comment": comment, "mcpServers": servers}


def claude_payload(profile: dict, catalog: dict, home: Path,
                   vendor: str = "claude", existing: dict | None = None) -> dict:
    servers = {
        name: server_entry(catalog, name, vendor, home)
        for name in live_names(profile, catalog)
        if vendor in catalog["servers"][name].get("vendors", [])
    }
    if existing:
        servers = keep_dynamic(existing, servers, catalog)
    return {
        "_comment": "Written by devkit. MCP servers from the profile list minus catalog parked.",
        "mcpServers": servers,
    }


def _toml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def codex_toml_sections(profile: dict, catalog: dict, home: Path,
                        existing_text: str = "") -> str:
    chunks: list[str] = []
    live: set[str] = set()
    for name in live_names(profile, catalog):
        spec = catalog["servers"][name]
        if "codex" not in spec.get("vendors", []):
            continue
        live.add(name)
        entry = server_entry(catalog, name, "codex", home)
        chunks.append(f"[mcp_servers.{name}]")
        if "url" in entry:
            chunks.append(f"url = {_toml_str(entry['url'])}")
        else:
            chunks.append(f"command = {_toml_str(entry['command'])}")
            args = entry.get("args") or []
            if args:
                rendered = ", ".join(_toml_str(a) for a in args)
                chunks.append(f"args = [{rendered}]")
        chunks.append("")
    parked = set(catalog.get("parked") or {})
    extras = extra_mcp_toml_blocks(existing_text, live | parked)
    if extras:
        chunks.append(extras.rstrip())
        chunks.append("")
    return "\n".join(chunks)


def extra_mcp_toml_blocks(text: str, drop: set[str]) -> str:
    """Keep operator MCP blocks (playwright-<id>, …) that are not defaults or parked."""
    pattern = re.compile(
        r"\[mcp_servers\.([^.\]]+)(?:\.[^\]]+)?\][^\[]*",
        re.MULTILINE,
    )
    kept: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text or ""):
        name = match.group(1)
        if name in drop or name in seen:
            continue
        seen.add(name)
        kept.append(match.group(0).rstrip())
    return "\n\n".join(kept)
