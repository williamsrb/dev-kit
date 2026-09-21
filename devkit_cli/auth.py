"""URL-redirect auth dispatcher.

Linux allows one default x-scheme-handler per scheme. Profile launchers do not
claim vendor schemes; this module installs a NoDisplay handler per scheme and
routes the callback to the profile that started login.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from . import appfork, instances
from .common import EXEC_MODE, FILE_MODE, REPO_ROOT, Plan, ensure_dir, write_json
from .errors import DevkitError

# scheme -> vendor
SCHEMES = {
    "claude": "claude",
    "claude-cli": "claude",
    "codex": "codex",
    "codex-browser-sidebar": "codex",
    "cursor": "cursor",
}

STOCK_HANDLERS = {
    "claude": "com.anthropic.Claude.desktop",
    "claude-cli": "claude-code-url-handler.desktop",
    "codex": "chatgpt.desktop",
    "codex-browser-sidebar": "chatgpt.desktop",
    "cursor": "cursor-url-handler.desktop",
}

PENDING_TTL = timedelta(minutes=30)


def desktop_id(scheme: str) -> str:
    return f"devkit-auth-{scheme}.desktop"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def write_pending(home: Path, profile: str, vendor: str,
                  now: datetime | None = None) -> Path:
    path = instances.auth_paths(home)["pending"]
    ensure_dir(path.parent)
    payload = {
        "profile": profile,
        "vendor": vendor,
        "at": (now or _now()).strftime("%Y%m%dT%H%M%SZ"),
    }
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    path.chmod(FILE_MODE)
    return path


def read_pending(home: Path, now: datetime | None = None) -> dict | None:
    path = instances.auth_paths(home)["pending"]
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    stamp = payload.get("at")
    if not stamp:
        return None
    try:
        written = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    if (now or _now()) - written > PENDING_TTL:
        return None
    return payload


def clear_pending(home: Path) -> None:
    path = instances.auth_paths(home)["pending"]
    if path.is_file():
        path.unlink()


def scheme_of(url: str) -> str:
    return urlparse(url).scheme


def running_profiles(vendor: str, home: Path,
                     proc_root: Path | None = None) -> list[str]:
    """Instance names whose GUI looks alive in /proc cmdline or environ."""
    names = sorted({n for n, v, _d, _p in instances.discover_instances(home) if v == vendor})
    if not names:
        return []
    app = instances._vendor_app_name(vendor)
    hits: list[str] = []
    root = proc_root or Path("/proc")
    if not root.is_dir():
        return []
    for proc in root.iterdir():
        if not proc.name.isdigit():
            continue
        blob = b""
        for filename in ("cmdline", "environ"):
            try:
                blob += (proc / filename).read_bytes()
            except (OSError, PermissionError):
                continue
        text = blob.replace(b"\x00", b" ").decode("utf-8", "replace")
        for name in names:
            markers = (
                str(home / ".agents-profiles" / name / vendor),
                str(home / ".config" / f"{app}-{name}"),
            )
            if name not in hits and any(m in text for m in markers):
                hits.append(name)
    return hits


def resolve_target(url: str, home: Path, now: datetime | None = None,
                   running: list[str] | None = None) -> tuple[str, str]:
    """Return (instance_name, vendor) or raise DevkitError."""
    scheme = scheme_of(url)
    vendor = SCHEMES.get(scheme)
    if not vendor:
        raise DevkitError(f"no devkit handler for scheme {scheme!r}",
                          "this dispatcher only routes vendor auth URLs")
    pending = read_pending(home, now=now)
    if pending and pending.get("vendor") == vendor and pending.get("profile"):
        name = pending["profile"]
        if any(n == name and v == vendor
               for n, v, _d, _p in instances.discover_instances(home)):
            return name, vendor
    alive = running if running is not None else running_profiles(vendor, home)
    if len(alive) == 1:
        return alive[0], vendor
    if len(alive) > 1:
        raise DevkitError(
            f"ambiguous {scheme}:// callback; running profiles: {', '.join(alive)}",
            "start login from one profile's launcher and retry before the pending marker expires")
    raise DevkitError(
        f"no profile claimed this {scheme}:// callback",
        "open the profile's desktop launcher (or CLI) and start login from there")


def _gui_bin(name: str, vendor: str) -> str | None:
    forked = appfork.gui_bin(vendor, name)
    if forked.is_file():
        return str(forked)
    return instances.first_existing(instances.VENDOR_GUI_CANDIDATES.get(vendor, []))


def launch_argv(name: str, vendor: str, home: Path, url: str) -> list[str]:
    """Command that delivers `url` to the profile's GUI or CLI wrapper."""
    layout = instances.paths_for(name, vendor, home)
    if vendor == "claude":
        gui = _gui_bin(name, vendor)
        if scheme_of(url) == "claude-cli" or not gui:
            return [str(layout["wrapper"]), url]
        return ["env", f"CLAUDE_CONFIG_DIR={layout['config_dir']}",
                gui, f"--user-data-dir={layout['user_data_dir']}", url]
    if vendor == "codex":
        gui = _gui_bin(name, vendor)
        if not gui:
            return [str(layout["wrapper"]), url]
        return ["env", f"CODEX_HOME={layout['config_dir']}",
                f"CODEX_ELECTRON_USER_DATA_PATH={layout['user_data_dir']}",
                gui, url]
    gui = _gui_bin(name, vendor)
    if not gui:
        return [str(layout["wrapper"]), url]
    return [gui, f"--user-data-dir={layout['config_dir']}",
            f"--extensions-dir={layout['data_dir']}/extensions", url]


def _notify(message: str) -> None:
    if not shutil_which("notify-send"):
        return
    subprocess.run(["notify-send", "devkit auth", message],
                   capture_output=True, check=False)


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def _xdg_env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env["XDG_DATA_HOME"] = str(home / ".local" / "share")
    return env


def query_default(scheme: str, home: Path | None = None) -> str:
    if not shutil_which("xdg-mime"):
        return ""
    env = _xdg_env(home) if home is not None else None
    result = subprocess.run(
        ["xdg-mime", "query", "default", f"x-scheme-handler/{scheme}"],
        capture_output=True, text=True, check=False, env=env)
    return result.stdout.strip() if result.returncode == 0 else ""


def set_default(desktop: str, scheme: str, home: Path | None = None) -> None:
    if not shutil_which("xdg-mime"):
        return
    env = _xdg_env(home) if home is not None else None
    subprocess.run(
        ["xdg-mime", "default", desktop, f"x-scheme-handler/{scheme}"],
        capture_output=True, check=False, env=env)


def _tokens(home: Path, kit_root: Path | None = None) -> dict[str, str]:
    dummy = {"name": "auth", "type": "auth"}
    tokens = instances.render_tokens(dummy, "claude", home)
    tokens["PROFILE_KIT_ROOT"] = str(kit_root or REPO_ROOT)
    return tokens


def _template(root: Path, name: str) -> str:
    path = root / "templates" / "auth" / name
    if not path.is_file():
        raise DevkitError(f"missing auth template {path}",
                          "the kit checkout is incomplete")
    return path.read_text(encoding="utf-8")


def install_dispatchers(plan: Plan, home: Path, kit_root: Path | None = None) -> None:
    root = kit_root or REPO_ROOT
    tokens = _tokens(home, root)
    paths = instances.auth_paths(home)
    ensure_dir(home / ".config")
    ensure_dir(paths["applications"])
    ensure_dir(paths["launch"].parent)
    ensure_dir(paths["state"].parent)
    scripts = (
        (paths["launch"], instances.render(_template(root, "launch.sh"), tokens)),
        (paths["dispatch"], instances.render(_template(root, "dispatch.sh"), tokens)),
    )
    for target, content in scripts:
        existing = target.read_text(encoding="utf-8") if target.is_file() else None
        if existing == content:
            continue
        plan.record(f"{'update' if existing else 'write '} {target}")
        if plan.apply:
            ensure_dir(target.parent)
            target.write_text(content, encoding="utf-8")
            target.chmod(EXEC_MODE)

    previous: dict[str, str] = {}
    state_path = paths["state"]
    if state_path.is_file():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8")).get("previous") or {}
        except ValueError:
            previous = {}

    snapshot = dict(previous)
    for scheme in SCHEMES:
        tokens_scheme = {**tokens, "PROFILE_AUTH_SCHEME": scheme}
        desktop_path = paths["applications"] / desktop_id(scheme)
        body = instances.render(_template(root, "handler.desktop"), tokens_scheme)
        existing = desktop_path.read_text(encoding="utf-8") if desktop_path.is_file() else None
        if existing != body:
            plan.record(f"{'update' if existing else 'write '} {desktop_path}")
            if plan.apply:
                ensure_dir(desktop_path.parent)
                desktop_path.write_text(body, encoding="utf-8")
                desktop_path.chmod(FILE_MODE)
        current = query_default(scheme, home)
        if scheme not in snapshot:
            snapshot[scheme] = (current if current and current != desktop_id(scheme)
                                else STOCK_HANDLERS[scheme])
        if current != desktop_id(scheme):
            plan.record(f"xdg-mime default {desktop_id(scheme)} x-scheme-handler/{scheme}")
            if plan.apply:
                set_default(desktop_id(scheme), scheme, home)

    if plan.apply:
        write_json(state_path, {"previous": snapshot})
        _lock_xdg_modes(home)
    elif snapshot != previous:
        plan.record(f"write  {state_path}")


def _lock_xdg_modes(home: Path) -> None:
    """xdg-mime inherits umask; our installs must not."""
    ensure_dir(home / ".config")
    for rel in (".config/mimeapps.list",
                ".local/share/applications/mimeapps.list"):
        path = home / rel
        if path.is_file():
            path.chmod(FILE_MODE)


def restore_dispatchers(plan: Plan, home: Path) -> None:
    paths = instances.auth_paths(home)
    previous = {scheme: STOCK_HANDLERS[scheme] for scheme in SCHEMES}
    if paths["state"].is_file():
        try:
            stored = json.loads(paths["state"].read_text(encoding="utf-8")).get("previous") or {}
            previous.update(stored)
        except ValueError:
            pass
    for scheme, desktop in previous.items():
        if scheme not in SCHEMES:
            continue
        plan.record(f"xdg-mime default {desktop} x-scheme-handler/{scheme}")
        if plan.apply:
            set_default(desktop, scheme, home)


def doctor_lines(home: Path) -> list[str]:
    if not shutil_which("xdg-mime"):
        return ["auth: xdg-mime not found (skip scheme-default check)"]
    lines = []
    for scheme in SCHEMES:
        current = query_default(scheme, home) or "(none)"
        wanted = desktop_id(scheme)
        if current == wanted:
            lines.append(f"auth x-scheme-handler/{scheme} -> {current}")
        else:
            lines.append(
                f"auth x-scheme-handler/{scheme} -> {current} (want {wanted})\n"
                f"    fix: devkit profile sync <name> --apply")
    return lines


def cmd_restore(args) -> int:
    from . import privilege
    user = privilege.refuse_root(getattr(args, "user", None))
    home = Path(user.pw_dir)
    plan = Plan(args.apply)
    restore_dispatchers(plan, home)
    if not plan.actions:
        print("auth restore: nothing to do.")
        return 0
    return plan.report("auth restore")


def prepend_profile_bin(home: Path, profile: str) -> None:
    """Put this profile's unprefixed CLIs first on PATH for the GUI process."""
    bind_profile_env(home, profile)


def bind_profile_env(home: Path, profile: str) -> None:
    """Pin this process and its children to one profile's CLI and harness.

    PATH prepend is required so `agentctl` resolves to the profile bin/.
    It is not sufficient: harness tools read $AGENTS_HOME, not $HOME/.agents.
    """
    harness = home / ".agents-profiles" / profile
    os.environ["DEVKIT_PROFILE"] = profile
    os.environ["DEVKIT_PROFILE_HOME"] = str(harness)
    os.environ["AGENTS_HOME"] = str(harness / "agents")
    bin_dir = harness / "bin"
    if not bin_dir.is_dir():
        return
    current = os.environ.get("PATH", "")
    prefix = str(bin_dir)
    if current.split(os.pathsep)[0] == prefix:
        return
    os.environ["PATH"] = prefix + (os.pathsep + current if current else "")


def _launch(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="devkit-auth-launch")
    parser.add_argument("--vendor", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("devkit-auth-launch: missing command", file=sys.stderr)
        return 2
    home = Path.home()
    write_pending(home, args.profile, args.vendor)
    bind_profile_env(home, args.profile)
    os.execvp(command[0], command)
    return 1


def _dispatch(argv: list[str]) -> int:
    url = argv[0] if argv else ""
    if not url:
        print("devkit-auth-dispatch: missing URL", file=sys.stderr)
        return 2
    home = Path.home()
    try:
        name, vendor = resolve_target(url, home)
        command = launch_argv(name, vendor, home, url)
        clear_pending(home)
        bind_profile_env(home, name)
        os.execvp(command[0], command)
    except DevkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.fix:
            print(f"fix:   {exc.fix}", file=sys.stderr)
        _notify(str(exc))
        return 1
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: python3 -m devkit_cli.auth {launch,dispatch} ...")
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "launch":
        return _launch(rest)
    if cmd == "dispatch":
        return _dispatch(rest)
    print(f"unknown auth command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
