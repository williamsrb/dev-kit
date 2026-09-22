#!/usr/bin/env python3
"""On-demand Playwright MCP instances (HTTP, one process per id).

A single user-level stdio `playwright` server is shared by every agent on a
vendor. Parallel evidence runs collide on the browser and on `--output-dir`.
This launcher starts an isolated HTTP server per task id, writes a config with
that id's output-dir, and optionally registers `playwright-<id>` on a vendor.

  python3 ~/.agents/mcp/playwright.py spawn JOT-101 JOT-102 --enable
    python3 ~/.agents/mcp/playwright.py spawn JOT-101 --storage-state ~/.agents/.auth/user.json
    python3 ~/.agents/mcp/playwright.py revive
    python3 ~/.agents/mcp/playwright.py revive --default
    python3 ~/.agents/mcp/playwright.py list
    python3 ~/.agents/mcp/playwright.py stop JOT-101
    python3 ~/.agents/mcp/playwright.py stop --all
    python3 ~/.agents/mcp/playwright.py disable JOT-101

Headless is the default. `--headed` and `--extension` exist as flags; there are
no named headed/extension catalog servers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HOME = Path.home()


def agents_home() -> Path:
    """Harness root: $AGENTS_HOME when a profile wrapper set it, else ~/.agents."""
    raw = os.environ.get("AGENTS_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".agents"


ROOT = agents_home() / ".playwright-mcp"
INSTANCES = ROOT / "instances"
DEFAULT_PACKAGE = "@playwright/mcp@latest"
# Playwright MCP's HTTP Host allowlist treats `127.0.0.1` and `localhost` as
# different names. A URL of http://127.0.0.1:<port>/mcp is answered 403
# ("Access is only allowed at localhost:<port>"), which vendors render as
# "Needs authentication". Bind and register `localhost`. Do not add
# `allowedHosts: ["127.0.0.1"]` — that 403s every Host, including localhost.
DEFAULT_HOST = "localhost"
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "0.0.0.0", "[::]"}
DEFAULT_PORT_BASE = 8931
DEFAULT_CAPS = ["vision", "pdf", "devtools", "network", "storage", "testing"]
VENDORS = ("cursor", "claude", "codex")
ID_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")


def emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def load_install():
    import importlib.util

    spec = importlib.util.spec_from_file_location("mcp_install", HERE / "install.py")
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load mcp/install.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sanitize_id(raw: str) -> str:
    value = raw.strip()
    if not value or value.startswith("-") or any(c not in ID_CHARS for c in value):
        raise SystemExit(f"invalid instance id: {raw!r}")
    return value


def server_name(instance_id: str) -> str:
    return f"playwright-{instance_id}"


def instance_dir(instance_id: str) -> Path:
    return INSTANCES / instance_id


def output_dir_for(instance_id: str, override: str | None) -> Path:
    if override:
        return Path(os.path.expanduser(override)).resolve()
    return (ROOT / instance_id).resolve()


def instance_state_path(instance_id: str) -> Path:
    return instance_dir(instance_id) / "instance.json"


def load_state(instance_id: str) -> dict[str, Any] | None:
    path = instance_state_path(instance_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def save_state(instance_id: str, state: dict[str, Any]) -> None:
    path = instance_state_path(instance_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    path.chmod(0o600)


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def public_host(host: str) -> str:
    if host in LOOPBACK_HOSTS:
        return "localhost"
    return host


def mcp_url(host: str, port: int) -> str:
    return f"http://{public_host(host)}:{port}/mcp"


def loopback_url_needs_fix(state: dict[str, Any]) -> bool:
    host = str(state.get("host") or "")
    url = str(state.get("url") or "")
    return host in LOOPBACK_HOSTS or "://127.0.0.1:" in url or "://[::1]:" in url


def live_ports() -> set[int]:
    ports: set[int] = set()
    if not INSTANCES.is_dir():
        return ports
    for path in INSTANCES.glob("*/instance.json"):
        try:
            state = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if pid_alive(state.get("pid")) and state.get("port"):
            ports.add(int(state["port"]))
    return ports


def allocate_port(host: str, requested: int | None) -> int:
    taken = live_ports()
    if requested is not None:
        if requested in taken or not port_free(host, requested):
            raise SystemExit(f"port {requested} is not free")
        return requested
    port = DEFAULT_PORT_BASE
    while port < DEFAULT_PORT_BASE + 200:
        if port not in taken and port_free(host, port):
            return port
        port += 1
    raise SystemExit("no free Playwright MCP port in 8931-9130")


def wait_for_port(host: str, port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def copy_storage_state(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "storage-state.json"
    shutil.copy2(src, dest)
    dest.chmod(0o600)
    return dest


def pick_storage_state(
    requested: str | None,
    existing: dict[str, Any] | None,
    out_dir: Path,
) -> Path | None:
    if requested:
        src = Path(os.path.expanduser(requested)).resolve()
        if not src.is_file():
            raise SystemExit(f"storage-state not found: {src}")
        return copy_storage_state(src, out_dir)
    if existing and existing.get("storage_state"):
        prev = Path(str(existing["storage_state"]))
        if prev.is_file():
            return prev
    return None


def build_config(
    *,
    output_dir: Path,
    headless: bool = True,
    isolated: bool = True,
    no_sandbox: bool = True,
    storage_state: Path | None = None,
    extension: bool = False,
    viewport_size: str | None = None,
    caps: list[str] | None = None,
    host: str = DEFAULT_HOST,
    port: int | None = None,
) -> dict[str, Any]:
    launch: dict[str, Any] = {"headless": headless}
    if no_sandbox:
        launch["chromiumSandbox"] = False
    browser: dict[str, Any] = {"isolated": isolated, "launchOptions": launch}
    if storage_state is not None:
        browser["contextOptions"] = {"storageState": str(storage_state)}
    if viewport_size:
        width, _, height = viewport_size.partition("x")
        browser.setdefault("contextOptions", {})["viewport"] = {
            "width": int(width),
            "height": int(height),
        }
    server: dict[str, Any] = {
        "host": host,
        "capabilities": list(caps if caps is not None else DEFAULT_CAPS),
        "outputDir": str(output_dir),
    }
    if port is not None:
        server["port"] = port
    config: dict[str, Any] = {"browser": browser, "server": server}
    if extension:
        config["extension"] = True
    return config


def merge_overlay(config: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(config)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def http_spec(url: str, vendor: str) -> dict[str, Any]:
    if vendor == "cursor":
        return {"url": url}
    return {"type": "http", "url": url}


def iter_instance_ids(requested: list[str], all_flag: bool) -> list[str]:
    if all_flag:
        if not INSTANCES.is_dir():
            return []
        return sorted(p.parent.name for p in INSTANCES.glob("*/instance.json"))
    if not requested:
        raise SystemExit("instance id required (or --all)")
    return [sanitize_id(item) for item in requested]


def dead_instance_ids() -> list[str]:
    ids: list[str] = []
    if not INSTANCES.is_dir():
        return ids
    for path in sorted(INSTANCES.glob("*/instance.json")):
        try:
            state = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        instance_id = str(state.get("id") or path.parent.name)
        if not pid_alive(state.get("pid")):
            ids.append(instance_id)
    return ids


def cmd_list(_args: argparse.Namespace) -> int:
    rows = []
    if INSTANCES.is_dir():
        for path in sorted(INSTANCES.glob("*/instance.json")):
            state = json.loads(path.read_text())
            state["alive"] = pid_alive(state.get("pid"))
            rows.append(state)
    emit({"instances": rows, "root": str(ROOT)})
    return 0


def start_instance(args: argparse.Namespace, instance_id: str) -> dict[str, Any]:
    existing = load_state(instance_id)
    if existing and pid_alive(existing.get("pid")):
        if not loopback_url_needs_fix(existing):
            return {**existing, "alive": True, "reused": True}
        stop_pid(int(existing["pid"]))
        existing = {**existing, "pid": None, "alive": False}

    host = args.host
    port = allocate_port(host, args.port if len(args.ids) == 1 else None)
    out_dir = output_dir_for(instance_id, args.output_dir if len(args.ids) == 1 else None)
    out_dir.mkdir(parents=True, exist_ok=True)
    inst = instance_dir(instance_id)
    inst.mkdir(parents=True, exist_ok=True)

    storage = pick_storage_state(args.storage_state, existing, out_dir)

    config = build_config(
        output_dir=out_dir,
        headless=not args.headed,
        isolated=not args.no_isolated,
        no_sandbox=not args.sandbox,
        storage_state=storage,
        extension=args.extension,
        viewport_size=args.viewport_size,
        caps=[c.strip() for c in args.caps.split(",") if c.strip()] if args.caps else None,
        host=host,
        port=port,
    )
    if args.config_overlay:
        overlay = json.loads(Path(args.config_overlay).read_text())
        config = merge_overlay(config, overlay)
    config_path = inst / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")

    url = mcp_url(host, port)
    name = server_name(instance_id)
    cmd = [
        "npx",
        "--yes",
        args.package,
        "--config",
        str(config_path),
        "--port",
        str(port),
        "--host",
        host,
    ]
    if args.npx_arg:
        cmd.extend(args.npx_arg)

    state = {
        "id": instance_id,
        "name": name,
        "url": url,
        "host": host,
        "port": port,
        "pid": None,
        "output_dir": str(out_dir),
        "config": str(config_path),
        "storage_state": str(storage) if storage else None,
        "headed": bool(args.headed),
        "extension": bool(args.extension),
        "command": cmd,
    }
    if args.dry_run:
        return {**state, "dry_run": True, "alive": False}

    log_path = inst / "server.log"
    log_fh = log_path.open("ab")
    proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log_fh.close()
    state["pid"] = proc.pid
    save_state(instance_id, state)
    if not wait_for_port(host, port, args.timeout):
        stop_pid(proc.pid)
        raise SystemExit(
            f"{instance_id}: MCP did not bind {host}:{port} within {args.timeout}s; see {log_path}"
        )
    save_state(instance_id, state)
    return {**state, "alive": True, "reused": False}


def stop_pid(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return
    deadline = time.time() + 5
    while time.time() < deadline and pid_alive(pid):
        time.sleep(0.1)
    if pid_alive(pid):
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


def disable_vendors(name: str, vendors: list[str], dry_run: bool) -> list[str]:
    install = load_install()
    catalog = install.load_catalog()
    touched = []
    # Inside a profile, do not touch stock ~/.cursor ~/.claude ~/.codex.
    if not os.environ.get("DEVKIT_PROFILE", "").strip():
        for vendor in vendors:
            print(f"[{vendor}] disable {name}", file=sys.stderr)
            rc = install.unregister_one(catalog, name, [vendor], dry_run)
            if rc == 0:
                touched.append(vendor)
    touched.extend(disable_on_profiles(Path.home(), name, vendors, dry_run))
    return touched


def enable_vendors(name: str, url: str, vendors: list[str], dry_run: bool) -> list[str]:
    install = load_install()
    catalog = install.load_catalog()
    touched = []
    if not os.environ.get("DEVKIT_PROFILE", "").strip():
        for vendor in vendors:
            spec = http_spec(url, vendor)
            print(f"[{vendor}] enable {name} -> {url}", file=sys.stderr)
            if vendor == "cursor":
                rc = install.register_cursor(name, spec, dry_run, force=True)
            elif vendor == "claude":
                rc = install.register_claude(
                    name,
                    spec,
                    install.expand_path(catalog["vendors"][vendor]["claude_config_dir"]),
                    dry_run,
                    force=True,
                )
            elif vendor == "codex":
                rc = install.register_codex(name, spec, catalog, dry_run, force=True)
            else:
                rc = 1
            if rc == 0:
                touched.append(vendor)
    touched.extend(enable_on_profiles(Path.home(), name, url, vendors, dry_run))
    return touched


def profile_mcp_targets(home: Path, vendors: list[str],
                        profile: str | None = None) -> list[tuple[str, Path, str]]:
    """(vendor, path, kind) for each provenance-marked profile instance.

    When DEVKIT_PROFILE is set (or `profile` is passed), only that instance is
    returned: a tool running inside dummy must not write php's MCP files.
    """
    root = home / ".agents-profiles"
    if not root.is_dir():
        return []
    wanted = set(vendors)
    current = profile if profile is not None else os.environ.get("DEVKIT_PROFILE", "").strip()
    found: list[tuple[str, Path, str]] = []
    for profile_dir in sorted(root.iterdir()):
        if not profile_dir.is_dir() or profile_dir.name.startswith("."):
            continue
        if current and profile_dir.name != current:
            continue
        for vendor in ("cursor", "claude", "codex"):
            if vendor not in wanted:
                continue
            config = profile_dir / vendor
            if not (config / ".devkit-profile.json").is_file():
                continue
            if vendor == "cursor":
                found.append((vendor, config / "mcp.json", "json"))
            elif vendor == "claude":
                found.append((vendor, config / ".claude.json", "json"))
            else:
                found.append((vendor, config / "config.toml", "toml"))
    return found


def upsert_json_mcp(path: Path, name: str, spec: dict[str, Any], dry_run: bool) -> None:
    data: dict[str, Any] = {"mcpServers": {}}
    if path.is_file():
        try:
            data = json.loads(path.read_text())
            data.setdefault("mcpServers", {})
        except json.JSONDecodeError:
            data = {"mcpServers": {}}
    data["mcpServers"][name] = spec
    print(f"  profile: upsert {name} in {path}", file=sys.stderr)
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def remove_json_mcp(path: Path, name: str, dry_run: bool) -> None:
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return
    servers = data.get("mcpServers") or {}
    if name not in servers:
        return
    print(f"  profile: remove {name} from {path}", file=sys.stderr)
    if dry_run:
        return
    del servers[name]
    data["mcpServers"] = servers
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def upsert_toml_url(path: Path, name: str, url: str, dry_run: bool) -> None:
    text = path.read_text() if path.is_file() else ""
    header = f"[mcp_servers.{name}]"
    url_line = f"url = {json.dumps(url)}"
    pattern = re.compile(
        rf"(\[mcp_servers\.{re.escape(name)}\]\n)(.*?)(?=\n\[|\Z)",
        re.DOTALL,
    )
    if pattern.search(text):
        def repl(match: re.Match[str]) -> str:
            body = match.group(2)
            if re.search(r"^url\s*=", body, re.MULTILINE):
                body = re.sub(r"^url\s*=.*$", url_line, body, count=1, flags=re.MULTILINE)
            else:
                body = url_line + "\n" + body
            return match.group(1) + body
        text = pattern.sub(repl, text, count=1)
    else:
        text = text.rstrip() + f"\n\n{header}\n{url_line}\n"
    print(f"  profile: upsert {name} in {path}", file=sys.stderr)
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n")


def remove_toml_section(path: Path, name: str, dry_run: bool) -> None:
    if not path.is_file():
        return
    text = path.read_text()
    pattern = re.compile(
        rf"\n*\[mcp_servers\.{re.escape(name)}(?:\.[^\]]+)?\][^\[]*",
        re.DOTALL,
    )
    if not pattern.search(text):
        return
    print(f"  profile: remove {name} from {path}", file=sys.stderr)
    if dry_run:
        return
    updated = pattern.sub("\n", text).rstrip() + "\n"
    path.write_text(updated)


def enable_on_profiles(home: Path, name: str, url: str, vendors: list[str],
                       dry_run: bool) -> list[str]:
    touched = []
    for vendor, path, kind in profile_mcp_targets(home, vendors):
        spec = http_spec(url, vendor)
        if kind == "toml":
            upsert_toml_url(path, name, url, dry_run)
        else:
            upsert_json_mcp(path, name, spec, dry_run)
        touched.append(f"profile:{vendor}")
    return touched


def disable_on_profiles(home: Path, name: str, vendors: list[str],
                        dry_run: bool) -> list[str]:
    touched = []
    for vendor, path, kind in profile_mcp_targets(home, vendors):
        if kind == "toml":
            remove_toml_section(path, name, dry_run)
        else:
            remove_json_mcp(path, name, dry_run)
        touched.append(f"profile:{vendor}")
    return touched


def selected_vendors(raw: str | None) -> list[str]:
    if not raw:
        return list(VENDORS)
    names = [p.strip() for p in raw.split(",") if p.strip()]
    bad = [n for n in names if n not in VENDORS]
    if bad:
        raise SystemExit(f"unknown vendor(s): {', '.join(bad)}")
    return names


def cmd_spawn(args: argparse.Namespace) -> int:
    ids = [sanitize_id(item) for item in args.ids]
    if args.port is not None and len(ids) != 1:
        raise SystemExit("--port requires a single id")
    if args.output_dir and len(ids) != 1:
        raise SystemExit("--output-dir requires a single id")
    vendors = selected_vendors(args.vendors) if args.enable else []
    results = []
    for instance_id in ids:
        state = start_instance(args, instance_id)
        if args.enable and not args.dry_run:
            state["vendors"] = enable_vendors(state["name"], state["url"], vendors, False)
        elif args.enable and args.dry_run:
            state["vendors"] = vendors
        results.append(state)
    emit({"spawned": results, "reload": "new vendor MCP names need a vendor restart or a new chat"})
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    ids = iter_instance_ids(args.ids, args.all)
    vendors = selected_vendors(args.vendors)
    stopped = []
    for instance_id in ids:
        state = load_state(instance_id) or {"id": instance_id, "name": server_name(instance_id)}
        pid = state.get("pid")
        if pid_alive(pid):
            stop_pid(int(pid))
        if not args.keep_mcp:
            disable_vendors(state.get("name") or server_name(instance_id), vendors, args.dry_run)
        if state_path := instance_state_path(instance_id):
            if state_path.is_file() and not args.dry_run:
                state["alive"] = False
                state["pid"] = None
                save_state(instance_id, state)
        stopped.append(
            {
                "id": instance_id,
                "name": state.get("name"),
                "output_dir": state.get("output_dir"),
                "alive": pid_alive(state.get("pid")),
            }
        )
    emit({"stopped": stopped})
    return 0


def cmd_enable(args: argparse.Namespace) -> int:
    ids = iter_instance_ids(args.ids, False)
    vendors = selected_vendors(args.vendors)
    enabled = []
    for instance_id in ids:
        state = load_state(instance_id)
        if not state:
            raise SystemExit(f"no instance {instance_id}; spawn it first")
        if not pid_alive(state.get("pid")):
            raise SystemExit(f"{instance_id} is not running")
        vendors_ok = enable_vendors(state["name"], state["url"], vendors, args.dry_run)
        enabled.append({**state, "vendors": vendors_ok, "alive": True})
    emit({"enabled": enabled, "reload": "new vendor MCP names need a vendor restart or a new chat"})
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    ids = iter_instance_ids(args.ids, args.all)
    vendors = selected_vendors(args.vendors)
    disabled = []
    for instance_id in ids:
        state = load_state(instance_id) or {"id": instance_id, "name": server_name(instance_id)}
        vendors_ok = disable_vendors(state.get("name") or server_name(instance_id), vendors, args.dry_run)
        disabled.append({"id": instance_id, "name": state.get("name"), "vendors": vendors_ok})
    emit({"disabled": disabled})
    return 0


def cmd_revive(args: argparse.Namespace) -> int:
    ids = dead_instance_ids()
    if not ids and args.default:
        ids = ["default"]
    if not ids:
        emit(
            {
                "revived": [],
                "hint": "no dead instances; python3 ~/.agents/mcp/playwright.py spawn default --enable",
            }
        )
        return 0
    args.ids = ids
    args.port = None
    args.output_dir = None
    args.enable = True
    return cmd_spawn(args)


def add_spawn_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-dir", help="Override output-dir (single id only).")
    parser.add_argument("--storage-state", help="Playwright storageState JSON to copy into the instance.")
    parser.add_argument("--viewport-size", help='Viewport, e.g. "1440x900".')
    parser.add_argument("--caps", help="Comma-separated capabilities (default: vision,pdf,devtools,network,storage,testing).")
    parser.add_argument("--headed", action="store_true", help="Visible browser instead of headless.")
    parser.add_argument("--extension", action="store_true", help="Attach via Playwright Chrome extension.")
    parser.add_argument("--no-isolated", action="store_true", help="Persist a user-data dir instead of in-memory profile.")
    parser.add_argument("--sandbox", action="store_true", help="Leave the Chromium sandbox on.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, help="Fixed port (single id only).")
    parser.add_argument("--package", default=DEFAULT_PACKAGE)
    parser.add_argument("--config-overlay", help="JSON object merged onto the generated config.")
    parser.add_argument("--npx-arg", action="append", default=[], help="Extra arg passed through to npx @playwright/mcp.")
    parser.add_argument("--timeout", type=float, default=45.0, help="Seconds to wait for the HTTP port.")
    parser.add_argument("--vendors", help="Comma-separated vendors for --enable (default: all four).")
    parser.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="action", required=True)

    spawn = sub.add_parser("spawn", help="Start one HTTP Playwright MCP per id.")
    spawn.add_argument("ids", nargs="+", help="Instance ids, e.g. JOT-101")
    add_spawn_flags(spawn)
    spawn.add_argument("--enable", action="store_true", help="Register playwright-<id> on vendor MCP configs.")
    spawn.set_defaults(func=cmd_spawn)

    revive = sub.add_parser(
        "revive",
        help="Re-spawn every dead instance from the registry (post-reboot). Enables vendor URLs.",
    )
    add_spawn_flags(revive)
    revive.add_argument(
        "--default",
        action="store_true",
        help="If the registry is empty or all dead slots are gone, spawn id 'default'.",
    )
    revive.set_defaults(func=cmd_revive)

    stop = sub.add_parser("stop", help="Kill instance processes and remove vendor MCP entries.")
    stop.add_argument("ids", nargs="*")
    stop.add_argument("--all", action="store_true")
    stop.add_argument("--keep-mcp", action="store_true", help="Leave vendor MCP URLs in place.")
    stop.add_argument("--vendors", help="Vendors to unregister (default: all four).")
    stop.add_argument("--dry-run", action="store_true")
    stop.set_defaults(func=cmd_stop)

    listing = sub.add_parser("list", help="Show instance registry.")
    listing.set_defaults(func=cmd_list)

    enable = sub.add_parser("enable", help="Register a running instance on vendor MCP configs.")
    enable.add_argument("ids", nargs="+")
    enable.add_argument("--vendors")
    enable.add_argument("--dry-run", action="store_true")
    enable.set_defaults(func=cmd_enable)

    disable = sub.add_parser("disable", help="Remove playwright-<id> from vendor MCP configs.")
    disable.add_argument("ids", nargs="*")
    disable.add_argument("--all", action="store_true")
    disable.add_argument("--vendors")
    disable.add_argument("--dry-run", action="store_true")
    disable.set_defaults(func=cmd_disable)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
