#!/usr/bin/env python3
"""Fetch and register user-level MCP servers for the four agent vendors.

Extracted from ~/.cursor, ~/.claude, ~/.claude_personal, ~/.codex.
Secrets stay in env files / existing vendor configs — never in this tree.

  python3 ~/.agents/mcp/install.py list
  python3 ~/.agents/mcp/install.py fetch [name ...]
  python3 ~/.agents/mcp/install.py register [name ...] [--vendors cursor,claude]
  python3 ~/.agents/mcp/install.py unregister [name ...] [--vendors cursor,claude]
  python3 ~/.agents/mcp/install.py install [name ...]   # fetch + register

  --dry-run   print actions, write nothing
  --force     replace a vendor entry even if it already exists (Codex: remove+add)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "catalog.json"
HOME = Path.home()
SECRET_HINTS = ("TOKEN", "SECRET", "AUTHORIZATION", "PASSWORD", "BEARER")
VENDOR_ORDER = ("cursor", "claude", "claude_personal", "codex")
VENDOR_LABELS = {
    "cursor": "cursor",
    "claude": "claude",
    "claude_personal": "personal",
    "codex": "codex",
}


def expand(value: str) -> str:
    return os.path.expanduser(os.path.expandvars(value.replace("${HOME}", str(HOME))))


def expand_path(value: str) -> Path:
    return Path(expand(value))


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text())


def load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip("'").strip('"')
    return out


def is_secret_key(key: str) -> bool:
    upper = key.upper()
    return any(hint in upper for hint in SECRET_HINTS)


def redact(key: str, value: str) -> str:
    if not value:
        return ""
    if is_secret_key(key) or key.upper() in {"AUTHORIZATION", "CLIENT_SECRET"}:
        return "<set>"
    return value


def vendor_home(catalog: dict, vendor: str) -> Path:
    return expand_path(catalog["vendors"][vendor]["home"])


def env_file_path(catalog: dict, key: str | None) -> Path | None:
    if not key:
        return None
    raw = catalog["env_files"].get(key)
    return expand_path(raw) if raw else None


def server_env(catalog: dict, spec: dict, existing: dict | None) -> dict[str, str]:
    values: dict[str, str] = {}
    path = env_file_path(catalog, spec.get("env_file"))
    if path:
        values.update(load_env_file(path))
    old_env = (existing or {}).get("env") or {}
    for key in spec.get("env_keys") or []:
        if key not in values or not values[key]:
            if old_env.get(key):
                values[key] = str(old_env[key])
            elif key == "EXTENSION_PORT":
                values[key] = "8089"
    return {k: v for k, v in values.items() if v}


def overlay(spec: dict, vendor: str) -> dict:
    out = dict(spec)
    extra = (spec.get("vendor_overrides") or {}).get(vendor) or {}
    out.update(extra)
    return out


def build_spec(catalog: dict, name: str, vendor: str, existing: dict | None) -> dict:
    spec = overlay(catalog["servers"][name], vendor)
    env_values = server_env(catalog, spec, existing)
    transport = spec["transport"]
    if transport == "http":
        built: dict = {"type": "http", "url": expand(spec["url"])}
        if vendor == "cursor":
            built = {"url": built["url"]}
            if name == "atlassian-rovo-preview":
                built["type"] = "http"
            client_id = os.environ.get(spec.get("oauth_client_id_env") or "")
            if not client_id and existing:
                client_id = ((existing.get("auth") or {}).get("CLIENT_ID"))
            if client_id:
                built["auth"] = {"CLIENT_ID": client_id}
            return built
        token = os.environ.get(spec.get("bearer_env") or "")
        if not token and existing:
            header = (existing.get("headers") or {}).get("Authorization") or ""
            if header.lower().startswith("bearer "):
                token = header[7:].strip()
        if token:
            built["headers"] = {"Authorization": f"Bearer {token}"}
        return built

    built = {
        "command": expand(spec["command"]),
        "args": [expand(a) for a in spec.get("args") or []],
    }
    if env_values:
        built["env"] = env_values
    if vendor in ("claude", "claude_personal"):
        built = {"type": "stdio", **built}
    return built


def cursor_mcp_path() -> Path:
    return HOME / ".cursor" / "mcp.json"


def claude_mcp_map(home: Path) -> dict:
    path = home / ".claude.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text()).get("mcpServers") or {}


def codex_mcp_map() -> dict:
    path = HOME / ".codex" / "config.toml"
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text()).get("mcp_servers") or {}


def existing_spec(vendor: str, name: str, catalog: dict) -> dict | None:
    if vendor == "cursor":
        path = cursor_mcp_path()
        if not path.is_file():
            return None
        return (json.loads(path.read_text()).get("mcpServers") or {}).get(name)
    if vendor in ("claude", "claude_personal"):
        return claude_mcp_map(vendor_home(catalog, vendor)).get(name)
    if vendor == "codex":
        return codex_mcp_map().get(name)
    return None


def run(cmd: list[str], env: dict | None = None, dry_run: bool = False) -> int:
    printable = []
    skip_next = False
    for part in cmd:
        if skip_next:
            key, _, val = part.partition("=")
            printable.append(f"{key}={redact(key, val)}" if val else part)
            skip_next = False
            continue
        if part in ("--env", "-e", "--header", "-H"):
            printable.append(part)
            skip_next = True
            continue
        printable.append(part)
    if "add-json" in cmd:
        printable[-1] = "<json>"
    print("  $ " + " ".join(printable))
    if dry_run:
        return 0
    proc = subprocess.run(cmd, env=env)
    return proc.returncode


# --- fetch -----------------------------------------------------------------


def fetch_gitlab(meta: dict, dry_run: bool) -> int:
    dest = expand_path(meta["dest"])
    version = meta["version"]
    if dest.is_file():
        got = subprocess.run([str(dest), "--version"], capture_output=True, text=True)
        if version in (got.stdout or ""):
            print(f"  gitlab-mcp-server {version} already at {dest}")
            return 0
    url = meta["url"]
    print(f"  download {url} -> {dest}")
    if dry_run:
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with urllib.request.urlopen(url) as resp, tmp.open("wb") as fh:
        shutil.copyfileobj(resp, fh)
    tmp.chmod(tmp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    tmp.replace(dest)
    print(f"  wrote {dest}")
    return 0


def fetch_browser_control(meta: dict, dry_run: bool) -> int:
    dest = expand_path(meta["dest"])
    server_js = dest / "mcp-server" / "dist" / "server.js"
    if dest.is_dir() and server_js.is_file():
        print(f"  browser-control-mcp already built at {dest}")
        return 0
    if dest.is_dir():
        cmd = ["npm", "install"]
        print(f"  build in {dest}")
        if dry_run:
            return 0
        if subprocess.run(cmd, cwd=dest).returncode != 0:
            return 1
        return subprocess.run(["npm", "run", "build"], cwd=dest).returncode
    print(f"  git clone {meta['repo']} {dest}")
    if dry_run:
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["git", "clone", "--depth", "1", meta["repo"], str(dest)]).returncode:
        return 1
    if subprocess.run(["npm", "install"], cwd=dest).returncode:
        return 1
    return subprocess.run(["npm", "run", "build"], cwd=dest).returncode


def fetch_npx(package: str, dry_run: bool) -> int:
    cmd = ["npx", "--yes", package, "--help"]
    print(f"  warm npx cache: {package}")
    if dry_run:
        return 0
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.returncode


def fetch_one(catalog: dict, fetch_key: str | None, dry_run: bool) -> int:
    if not fetch_key:
        print("  nothing to fetch (http / in-tree)")
        return 0
    meta = catalog["fetch"][fetch_key]
    if fetch_key == "gitlab-mcp-server":
        return fetch_gitlab(meta, dry_run)
    if fetch_key == "browser-control-mcp":
        return fetch_browser_control(meta, dry_run)
    if "npx_package" in meta:
        return fetch_npx(meta["npx_package"], dry_run)
    raise SystemExit(f"unknown fetch recipe: {fetch_key}")


# --- register --------------------------------------------------------------


def register_cursor(name: str, spec: dict, dry_run: bool, force: bool) -> int:
    path = cursor_mcp_path()
    data = {"mcpServers": {}}
    if path.is_file():
        data = json.loads(path.read_text())
        data.setdefault("mcpServers", {})
    if name in data["mcpServers"] and not force:
        print(f"  cursor: {name} exists (use --force to replace)")
        return 0
    print(f"  cursor: upsert {name} in {path}")
    if dry_run:
        return 0
    data["mcpServers"][name] = spec
    path.write_text(json.dumps(data, indent=2) + "\n")
    return 0


def register_claude(name: str, spec: dict, config_dir: Path, dry_run: bool, force: bool) -> int:
    existing = claude_mcp_map(config_dir)
    if name in existing and not force:
        print(f"  {config_dir.name}: {name} exists (use --force to replace)")
        return 0
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    payload = json.dumps(spec, separators=(",", ":"))
    if name in existing:
        run(["claude", "mcp", "remove", "-s", "user", name], env=env, dry_run=dry_run)
    return run(
        ["claude", "mcp", "add-json", "-s", "user", name, payload],
        env=env,
        dry_run=dry_run,
    )


def register_codex(name: str, spec: dict, catalog: dict, dry_run: bool, force: bool) -> int:
    present = name in codex_mcp_map()
    if present and not force:
        print(f"  codex: {name} exists (use --force to replace)")
        return 0
    if present:
        run(["codex", "mcp", "remove", name], dry_run=dry_run)
    if spec.get("url") or spec.get("type") == "http":
        url = spec.get("url")
        cmd = ["codex", "mcp", "add", name, "--url", url]
        server = catalog.get("servers", {}).get(name) or {}
        bearer_env = server.get("bearer_env")
        if bearer_env:
            cmd += ["--bearer-token-env-var", bearer_env]
        client_env = server.get("oauth_client_id_env")
        client_id = os.environ.get(client_env or "")
        if client_id:
            cmd += ["--oauth-client-id", client_id]
        return run(cmd, dry_run=dry_run)
    cmd = ["codex", "mcp", "add", name]
    for key, val in (spec.get("env") or {}).items():
        cmd += ["--env", f"{key}={val}"]
    argv = [spec["command"], *(spec.get("args") or [])]
    cmd += ["--", *argv]
    return run(cmd, dry_run=dry_run)


def unregister_cursor(name: str, dry_run: bool) -> int:
    path = cursor_mcp_path()
    if not path.is_file():
        print(f"  cursor: no {path}")
        return 0
    data = json.loads(path.read_text())
    servers = data.setdefault("mcpServers", {})
    if name not in servers:
        print(f"  cursor: {name} absent")
        return 0
    print(f"  cursor: remove {name} from {path}")
    if dry_run:
        return 0
    del servers[name]
    path.write_text(json.dumps(data, indent=2) + "\n")
    return 0


def unregister_claude(name: str, config_dir: Path, dry_run: bool) -> int:
    existing = claude_mcp_map(config_dir)
    if name not in existing:
        print(f"  {config_dir.name}: {name} absent")
        return 0
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return run(["claude", "mcp", "remove", "-s", "user", name], env=env, dry_run=dry_run)


def unregister_codex(name: str, dry_run: bool) -> int:
    if name not in codex_mcp_map():
        print(f"  codex: {name} absent")
        return 0
    return run(["codex", "mcp", "remove", name], dry_run=dry_run)


def unregister_one(catalog: dict, name: str, vendors: list[str], dry_run: bool) -> int:
    rc = 0
    for vendor in vendors:
        print(f"[{vendor}] unregister {name}")
        if vendor == "cursor":
            rc |= unregister_cursor(name, dry_run)
        elif vendor in ("claude", "claude_personal"):
            rc |= unregister_claude(
                name,
                expand_path(catalog["vendors"][vendor]["claude_config_dir"]),
                dry_run,
            )
        elif vendor == "codex":
            rc |= unregister_codex(name, dry_run)
    return rc


def register_one(catalog: dict, name: str, vendors: list[str], dry_run: bool, force: bool) -> int:
    spec = catalog["servers"][name]
    rc = 0
    for vendor in vendors:
        if vendor not in spec["vendors"]:
            continue
        existing = existing_spec(vendor, name, catalog)
        built = build_spec(catalog, name, vendor, existing)
        print(f"[{vendor}] {name}")
        if vendor == "cursor":
            rc |= register_cursor(name, built, dry_run, force)
        elif vendor in ("claude", "claude_personal"):
            rc |= register_claude(
                name, built,
                expand_path(catalog["vendors"][vendor]["claude_config_dir"]),
                dry_run, force,
            )
        elif vendor == "codex":
            rc |= register_codex(name, built, catalog, dry_run, force)
    return rc


# --- list ------------------------------------------------------------------


def list_servers(catalog: dict, names: list[str]) -> int:
    name_w = max(len(n) for n in names)
    col_w = 10
    head = ["server".ljust(name_w)] + [
        VENDOR_LABELS[v].ljust(col_w) for v in VENDOR_ORDER
    ] + ["fetch"]
    print("  ".join(head))
    for name in names:
        spec = catalog["servers"][name]
        cells = [name.ljust(name_w)]
        for vendor in VENDOR_ORDER:
            if vendor not in spec["vendors"]:
                mark = "-"
            else:
                live = existing_spec(vendor, name, catalog)
                parked = name in (catalog.get("parked") or {})
                if live:
                    mark = "yes"
                elif parked:
                    mark = "parked"
                else:
                    mark = "MISSING"
            cells.append(mark.ljust(col_w))
        fetch = spec.get("fetch") or "n/a"
        if fetch == "gitlab-mcp-server":
            dest = expand_path(catalog["fetch"][fetch]["dest"])
            fetch = "bin ok" if dest.is_file() else "bin MISSING"
        elif fetch == "browser-control-mcp":
            dest = expand_path(catalog["fetch"][fetch]["dest"]) / "mcp-server" / "dist" / "server.js"
            fetch = "src ok" if dest.is_file() else "src MISSING"
        cells.append(fetch)
        print("  ".join(cells))
    parked = catalog.get("parked") or {}
    if parked:
        print("\nParked (not always-on; --force to register live):")
        for key, reason in parked.items():
            print(f"  {key}: {reason}")
    skipped = catalog.get("skip") or {}
    if skipped:
        print("\nSkipped (not user-installable):")
        for key, reason in skipped.items():
            print(f"  {key}: {reason}")
    plugins = catalog.get("plugins_not_user_mcp") or {}
    if plugins:
        print("\nPlugin MCPs (marketplace, not this installer):")
        for key, where in plugins.items():
            if key == "comment":
                continue
            print(f"  {key}: {', '.join(where)}")
    return 0


def selected_names(catalog: dict, requested: list[str]) -> list[str]:
    available = list(catalog["servers"])
    if not requested:
        return available
    unknown = [n for n in requested if n not in catalog["servers"]]
    if unknown:
        raise SystemExit(f"unknown server(s): {', '.join(unknown)}")
    return requested


def selected_vendors(raw: str | None) -> list[str]:
    if not raw:
        return list(VENDOR_ORDER)
    names = [p.strip() for p in raw.split(",") if p.strip()]
    bad = [n for n in names if n not in VENDOR_ORDER]
    if bad:
        raise SystemExit(f"unknown vendor(s): {', '.join(bad)}")
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=("list", "fetch", "register", "unregister", "install"))
    ap.add_argument("names", nargs="*", help="server names; default is all catalog entries")
    ap.add_argument("--vendors", help="comma-separated: cursor,claude,claude_personal,codex")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="replace existing vendor entries")
    args = ap.parse_args()

    catalog = load_catalog()
    names = selected_names(catalog, args.names)
    vendors = selected_vendors(args.vendors)

    if args.action == "list":
        return list_servers(catalog, names)

    rc = 0
    if args.action in ("fetch", "install"):
        seen: set[str] = set()
        for name in names:
            key = catalog["servers"][name].get("fetch")
            print(f"fetch {name}" + (f" ({key})" if key else ""))
            if key in seen:
                print("  already fetched this recipe")
                continue
            if key:
                seen.add(key)
            rc |= fetch_one(catalog, key, args.dry_run)
    if args.action in ("register", "install"):
        parked = catalog.get("parked") or {}
        for name in names:
            if name in parked and not args.force:
                print(f"register {name} skipped (parked: {parked[name]}). Use --force to register live.")
                continue
            print(f"register {name}")
            rc |= register_one(catalog, name, vendors, args.dry_run, args.force)
    if args.action == "unregister":
        for name in names:
            print(f"unregister {name}")
            rc |= unregister_one(catalog, name, vendors, args.dry_run)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
