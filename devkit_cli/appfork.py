"""Per-profile Electron app forks, same shape as Claude Personal.

Stock packages own /usr/lib/claude-desktop, /usr/lib/chatgpt and
/usr/share/cursor. Apt/dpkg overwrite those trees. A profile fork is a
dpkg-unowned rsync copy under /usr/lib/devkit/<vendor>-<profile>/ with a
patched identity (asar desktopName, Cursor nameShort) so WM_CLASS / Wayland
app_id is unique.

This module is copied to /usr/local/bin/sync-devkit-profile-apps.py for the
apt/dpkg hooks. It must stay stdlib-only. Never write the stock trees or
Claude Personal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import shutil
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


FORK_ROOT = Path("/usr/lib/devkit")
WORKER = Path("/usr/local/bin/sync-devkit-profile-apps.py")
APT_CONF = Path("/etc/apt/apt.conf.d/99-devkit-profile-apps")
DPKG_CONF = Path("/etc/dpkg/dpkg.cfg.d/60devkit-profile-apps")
APPARMOR_DIR = Path("/etc/apparmor.d")
LOG_PATH = Path("/var/log/devkit-profile-apps.log")
HOME_ROOT = Path("/home")
PROVENANCE_NAME = ".devkit-profile.json"

PERSONAL_LIB = Path("/usr/lib/claude-desktop-personal")

APP_NAME = {"claude": "Claude", "codex": "Codex", "cursor": "Cursor"}


@dataclass(frozen=True)
class Vendor:
    name: str
    package: str
    stock_lib: Path
    binary: str
    stock_desktop_name: str
    asar_rel: str | None = None
    package_json_rel: str | None = None
    product_json_rel: str | None = None
    version_rel: str | None = "version"
    icon_globs: tuple[str, ...] = ()


VENDORS = {
    "claude": Vendor(
        name="claude",
        package="claude-desktop",
        stock_lib=Path("/usr/lib/claude-desktop"),
        binary="claude-desktop",
        stock_desktop_name="com.anthropic.Claude.desktop",
        asar_rel="resources/app.asar",
        icon_globs=("resources/icon.png", "resources/TrayIcon*.png"),
    ),
    "codex": Vendor(
        name="codex",
        package="chatgpt",
        stock_lib=Path("/usr/lib/chatgpt"),
        binary="codex-launcher",
        stock_desktop_name="chatgpt.desktop",
        asar_rel="resources/app.asar",
        icon_globs=("resources/icon-chatgpt.png",),
    ),
    "cursor": Vendor(
        name="cursor",
        package="cursor",
        stock_lib=Path("/usr/share/cursor"),
        binary="cursor",
        stock_desktop_name="cursor.desktop",
        package_json_rel="resources/app/package.json",
        product_json_rel="resources/app/product.json",
        version_rel=None,
        icon_globs=(
            "resources/app/resources/linux/code.png",
            "resources/app/resources/linux/trayTemplate.png",
            "resources/app/resources/linux/trayTemplate-*.png",
            "resources/app/resources/linux/trayTemplateDark*.png",
            "resources/app/resources/linux/trayNotifyWhite*.png",
        ),
    ),
}


@dataclass
class Env:
    fork_root: Path = FORK_ROOT
    worker: Path = WORKER
    apt_conf: Path = APT_CONF
    dpkg_conf: Path = DPKG_CONF
    apparmor_dir: Path = APPARMOR_DIR
    home_root: Path = HOME_ROOT
    log_path: Path = LOG_PATH
    vendors: dict[str, Vendor] = field(default_factory=lambda: dict(VENDORS))


class Skip(Exception):
    """Cheap gate: nothing to do."""


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    print(f"{ts} {msg}", flush=True)


def wm_class(vendor: str, profile: str) -> str:
    return f"{APP_NAME[vendor]}-{profile}"


def desktop_name(vendor: str, profile: str) -> str:
    return f"{wm_class(vendor, profile)}.desktop"


def fork_dir(vendor: str, profile: str, env: Env | None = None) -> Path:
    root = (env or Env()).fork_root
    return root / f"{vendor}-{profile}"


def gui_bin(vendor: str, profile: str, env: Env | None = None) -> Path:
    spec = (env or Env()).vendors[vendor]
    return fork_dir(vendor, profile, env) / spec.binary


# ---------------------------------------------------------------- asar (Personal)

def pickle_uint32(n: int) -> bytes:
    return struct.pack("<I", 4) + struct.pack("<I", n)


def pickle_string(payload: bytes) -> bytes:
    body = struct.pack("<I", len(payload)) + payload
    pad = (4 - (len(body) % 4)) % 4
    body += b"\x00" * pad
    return struct.pack("<I", len(body)) + body


def read_asar(path: Path) -> tuple[dict, bytes, int]:
    with path.open("rb") as f:
        size_buf = f.read(8)
        if len(size_buf) < 8:
            raise ValueError(f"asar too small: {path}")
        header_buf_len = struct.unpack_from("<I", size_buf, 4)[0]
        header_buf = f.read(header_buf_len)
        if len(header_buf) != header_buf_len:
            raise ValueError(f"asar header truncated: {path}")
        json_len = struct.unpack_from("<I", header_buf, 4)[0]
        header = json.loads(header_buf[8 : 8 + json_len])
        data = f.read()
    return header, data, 8 + header_buf_len


def write_asar(path: Path, header: dict, data: bytes, mode: int) -> None:
    header_json = json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode()
    header_buf = pickle_string(header_json)
    size_buf = pickle_uint32(len(header_buf))
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("wb") as f:
            f.write(size_buf)
            f.write(header_buf)
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def integrity_for(blob: bytes, block_size: int) -> dict:
    digest = hashlib.sha256(blob).hexdigest()
    if not blob:
        blocks = [hashlib.sha256(b"").hexdigest()]
    else:
        blocks = [
            hashlib.sha256(blob[i : i + block_size]).hexdigest()
            for i in range(0, len(blob), block_size)
        ]
    return {
        "algorithm": "SHA256",
        "hash": digest,
        "blockSize": block_size,
        "blocks": blocks,
    }


def asar_desktop_name(path: Path) -> str:
    if not path.is_file():
        return ""
    header, data, _ = read_asar(path)
    meta = header.get("files", {}).get("package.json")
    if not isinstance(meta, dict) or "offset" not in meta:
        return ""
    offset = int(meta["offset"])
    size = int(meta["size"])
    pkg = json.loads(data[offset : offset + size])
    return str(pkg.get("desktopName") or "")


def _replace_json_string(blob: bytes, key: str, new_value: str) -> bytes:
    """Replace "key": "<anything>" with "key": "new_value" (first match)."""
    prefix = f'"{key}": "'.encode()
    start = blob.find(prefix)
    if start < 0:
        pkg = json.loads(blob)
        pkg[key] = new_value
        return (json.dumps(pkg, indent=2) + "\n").encode()
    i = start + len(prefix)
    end = blob.find(b'"', i)
    if end < 0:
        raise ValueError(f"unterminated {key} in package.json")
    return blob[:start] + prefix + new_value.encode() + blob[end:]


def patch_asar_desktop_name(path: Path, wanted: str, *, dry_run: bool) -> str:
    st = path.stat()
    header, data, _header_end = read_asar(path)
    files = header.get("files")
    if not isinstance(files, dict) or "package.json" not in files:
        raise RuntimeError(f"no root package.json in {path}")
    meta = files["package.json"]
    if meta.get("unpacked"):
        unpacked = path.parent / "app.asar.unpacked" / "package.json"
        action = f"patch unpacked {unpacked} desktopName -> {wanted}"
        if dry_run:
            return action
        unpacked.write_bytes(_replace_json_string(unpacked.read_bytes(),
                                                  "desktopName", wanted))
        return action
    offset = int(meta["offset"])
    size = int(meta["size"])
    blob = data[offset : offset + size]
    current = json.loads(blob).get("desktopName")
    new_blob = _replace_json_string(blob, "desktopName", wanted)
    if new_blob == blob and current == wanted:
        return f"asar already has desktopName={wanted}"
    if "asarIntegrity" in json.loads(blob):
        log("warning: package.json has asarIntegrity; Electron may refuse a patched asar")
    block_size = int((meta.get("integrity") or {}).get("blockSize") or 4194304)
    integ = integrity_for(new_blob, block_size)
    if len(new_blob) == size:
        how = "in-place"
        new_data = data[:offset] + new_blob + data[offset + size :]
        new_offset = offset
    else:
        how = "append"
        new_offset = len(data)
        new_data = data + new_blob
    meta["size"] = len(new_blob)
    meta["offset"] = str(new_offset)
    meta["integrity"] = integ
    action = (
        f"patch {path} desktopName {current} -> {wanted} "
        f"({how}, size {size} -> {len(new_blob)}, integrity {integ['hash']})"
    )
    if dry_run:
        return action
    write_asar(path, header, new_data, st.st_mode & 0o777)
    return action


# ---------------------------------------------------------------- identity / version

def read_version(tree: Path) -> str:
    path = tree / "version"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def stock_version(spec: Vendor) -> str:
    if spec.version_rel:
        return read_version(spec.stock_lib)
    if spec.package_json_rel:
        path = spec.stock_lib / spec.package_json_rel
        try:
            return str(json.loads(path.read_text(encoding="utf-8")).get("version") or "")
        except (OSError, ValueError):
            return ""
    return ""


def fork_version(spec: Vendor, dest: Path) -> str:
    if spec.version_rel:
        return read_version(dest)
    if spec.package_json_rel:
        path = dest / spec.package_json_rel
        try:
            return str(json.loads(path.read_text(encoding="utf-8")).get("version") or "")
        except (OSError, ValueError):
            return ""
    return ""


def fork_desktop_name(spec: Vendor, dest: Path) -> str:
    if spec.asar_rel:
        try:
            return asar_desktop_name(dest / spec.asar_rel)
        except (OSError, ValueError, json.JSONDecodeError):
            return ""
    if spec.package_json_rel:
        path = dest / spec.package_json_rel
        try:
            return str(json.loads(path.read_text(encoding="utf-8")).get("desktopName") or "")
        except (OSError, ValueError):
            return ""
    return ""


def dpkg_installed(name: str) -> bool:
    r = subprocess.run(["dpkg", "-s", name], capture_output=True, text=True)
    if r.returncode != 0:
        return False
    return "Status: install ok installed" in r.stdout


def _forbidden(dest: Path, spec: Vendor) -> str | None:
    resolved = dest.resolve() if dest.exists() else dest
    stock = spec.stock_lib.resolve() if spec.stock_lib.exists() else spec.stock_lib
    personal = PERSONAL_LIB.resolve() if PERSONAL_LIB.exists() else PERSONAL_LIB
    if resolved == stock:
        return f"refusing to rsync onto stock {stock}"
    if resolved == personal:
        return f"refusing to rsync onto Claude Personal {personal}"
    if stock in resolved.parents:
        return f"refusing to nest a fork under stock {stock}"
    if personal in resolved.parents:
        return f"refusing to nest a fork under Claude Personal {personal}"
    return None


# ---------------------------------------------------------------- rsync / patch / icons

def rsync_stock(spec: Vendor, dest: Path, *, dry_run: bool) -> str:
    reason = _forbidden(dest, spec)
    if reason:
        raise RuntimeError(reason)
    src = str(spec.stock_lib) + "/"
    dst = str(dest) + "/"
    cmd = ["rsync", "-aH", "--delete", src, dst]
    action = " ".join(cmd)
    if dry_run:
        return action
    dest.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    r = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.monotonic() - t0
    if r.returncode != 0:
        raise RuntimeError(
            f"rsync failed ({r.returncode}) in {dt:.1f}s: "
            f"{r.stderr.strip() or r.stdout.strip()}"
        )
    sandbox = dest / "chrome-sandbox"
    if sandbox.is_file():
        mode = sandbox.stat().st_mode & 0o7777
        if mode != 0o4755 and os.geteuid() == 0:
            os.chmod(sandbox, 0o4755)
            log(f"chrome-sandbox mode {mode:04o} -> 4755")
    log(f"rsync done in {dt:.1f}s")
    return action


def patch_identity(spec: Vendor, dest: Path, profile: str, *, dry_run: bool) -> list[str]:
    wanted = desktop_name(spec.name, profile)
    actions: list[str] = []
    if spec.asar_rel:
        actions.append(patch_asar_desktop_name(dest / spec.asar_rel, wanted, dry_run=dry_run))
    if spec.package_json_rel:
        path = dest / spec.package_json_rel
        actions.append(_patch_json_file(path, {"desktopName": wanted}, dry_run=dry_run))
    if spec.product_json_rel:
        path = dest / spec.product_json_rel
        short = wm_class(spec.name, profile)
        actions.append(_patch_json_file(
            path,
            {"nameShort": short, "linuxIconName": f"{spec.name}-{profile}"},
            dry_run=dry_run,
        ))
    return actions


def _patch_json_file(path: Path, updates: dict[str, str], *, dry_run: bool) -> str:
    blob = path.read_bytes()
    pkg = json.loads(blob)
    already = all(pkg.get(k) == v for k, v in updates.items())
    summary = ", ".join(f"{k}={v}" for k, v in updates.items())
    if already:
        return f"{path} already {summary}"
    action = f"patch {path} {summary}"
    if dry_run:
        return action
    new = blob
    for key, value in updates.items():
        new = _replace_json_string(new, key, value)
    path.write_bytes(new)
    return action


def _imagemagick() -> list[str] | None:
    for candidate in ("magick", "convert"):
        found = shutil.which(candidate)
        if found:
            return [found]
    return None


def profile_color(profile: str, provenance: dict | None = None) -> str:
    declared = (provenance or {}).get("color")
    if isinstance(declared, str) and declared.startswith("#"):
        return declared
    digest = hashlib.sha256(profile.encode("utf-8")).digest()
    hue = (digest[0] << 8 | digest[1]) / 65535.0
    import colorsys
    rgb = colorsys.hsv_to_rgb(hue, 0.75, 0.95)
    return "#" + "".join(f"{int(c * 255):02x}" for c in rgb)


def recolor_tree_icons(spec: Vendor, dest: Path, color: str, *, dry_run: bool) -> list[str]:
    binary = _imagemagick()
    if binary is None:
        return ["skip icons: ImageMagick missing"]
    actions: list[str] = []
    seen: set[Path] = set()
    for pattern in spec.icon_globs:
        for src in spec.stock_lib.glob(pattern):
            if not src.is_file() or src in seen:
                continue
            seen.add(src)
            rel = src.relative_to(spec.stock_lib)
            target = dest / rel
            action = f"recolor {src} -> {target} ({color})"
            actions.append(action)
            if dry_run:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                [*binary, str(src), "-fill", color, "-colorize", "60%", str(target)],
                capture_output=True, text=True, check=False,
            )
            if result.returncode != 0 or not target.is_file():
                actions[-1] = f"skip {rel}: {result.stderr.strip() or result.returncode}"
    return actions


def write_apparmor(spec: Vendor, dest: Path, profile: str, env: Env,
                   *, dry_run: bool) -> str:
    abi = Path("/etc/apparmor.d/abi/4.0")
    if not abi.is_file() and env.apparmor_dir == APPARMOR_DIR:
        return "skip apparmor: abi/4.0 missing"
    name = f"devkit-{spec.name}-{profile}"
    path = env.apparmor_dir / name
    binary = dest / spec.binary
    body = (
        "abi <abi/4.0>,\n"
        "include <tunables/global>\n"
        "\n"
        f"profile {name} {binary} flags=(unconfined) {{\n"
        "  userns,\n"
        "\n"
        f"  include if exists <local/{name}>\n"
        "}\n"
    )
    action = f"write {path}"
    if dry_run:
        return action
    env.apparmor_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    os.chmod(path, 0o644)
    if shutil.which("apparmor_parser") and shutil.which("aa-enabled"):
        enabled = subprocess.run(["aa-enabled", "--quiet"], capture_output=True)
        if enabled.returncode == 0:
            r = subprocess.run(
                ["apparmor_parser", "-r", "-W", "-T", str(path)],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                log(f"apparmor_parser failed (ignored): {r.stderr.strip() or r.returncode}")
    return action


def fork_pids(dest: Path) -> list[int]:
    found: list[int] = []
    needle = str(dest).encode()
    self_pid = os.getpid()
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return found
    for proc in proc_root.iterdir():
        if not proc.name.isdigit():
            continue
        pid = int(proc.name)
        if pid == self_pid:
            continue
        try:
            cmdline = (proc / "cmdline").read_bytes()
        except OSError:
            continue
        if needle in cmdline:
            found.append(pid)
            continue
        try:
            exe = os.readlink(proc / "exe")
        except OSError:
            continue
        if str(dest) in exe:
            found.append(pid)
    return found


# ---------------------------------------------------------------- discover / sync

def iter_homes(env: Env | None = None) -> list[Path]:
    root = (env or Env()).home_root
    if not root.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(root.iterdir()):
        if (child / ".agents-profiles").is_dir():
            found.append(child)
    return found


def discover_desktop_instances(home: Path) -> list[tuple[str, str, dict]]:
    """(profile, vendor, provenance) for instances that have a desktop kind."""
    root = home / ".agents-profiles"
    rows: list[tuple[str, str, dict]] = []
    if not root.is_dir():
        return rows
    for profile_dir in sorted(root.iterdir()):
        if not profile_dir.is_dir() or profile_dir.name.startswith("."):
            continue
        for child in sorted(profile_dir.iterdir()):
            if not child.is_dir() or child.name in ("core", "bin"):
                continue
            path = child / PROVENANCE_NAME
            if not path.is_file():
                continue
            try:
                prov = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            vendor = str(prov.get("vendor") or child.name)
            if vendor not in VENDORS:
                continue
            rows.append((profile_dir.name, vendor, prov))
    return rows


def cheap_gates(spec: Vendor, dest: Path, profile: str) -> None:
    production = VENDORS.get(spec.name)
    if (
        spec.package
        and shutil.which("dpkg")
        and production is not None
        and spec.stock_lib == production.stock_lib
        and not dpkg_installed(spec.package)
    ):
        raise Skip(f"{spec.package} not installed")
    if not spec.stock_lib.is_dir():
        raise Skip(f"stock tree missing: {spec.stock_lib}")
    wanted = desktop_name(spec.name, profile)
    stock_ver = stock_version(spec)
    dest_ver = fork_version(spec, dest)
    name = fork_desktop_name(spec, dest)
    extra_ok = True
    if spec.product_json_rel:
        product = dest / spec.product_json_rel
        try:
            short = json.loads(product.read_text(encoding="utf-8")).get("nameShort")
        except (OSError, ValueError):
            short = ""
        extra_ok = short == wm_class(spec.name, profile)
    if stock_ver and stock_ver == dest_ver and name == wanted and extra_ok:
        raise Skip(
            f"{spec.name}-{profile} already at {dest_ver} with desktopName={wanted}"
        )


def sync_one(vendor: str, profile: str, home: Path, env: Env, *,
             dry_run: bool, icons_only: bool = False) -> None:
    spec = env.vendors[vendor]
    dest = fork_dir(vendor, profile, env)
    color = profile_color(profile, _read_provenance(home, profile, vendor))

    if icons_only:
        if not spec.stock_lib.is_dir():
            log(f"skip: stock tree missing: {spec.stock_lib}")
            return
        log(f"icons-only: recolor {vendor}-{profile} from stock")
        for line in recolor_tree_icons(spec, dest, color, dry_run=dry_run):
            log(line)
        return

    try:
        cheap_gates(spec, dest, profile)
    except Skip as e:
        log(f"skip: {e}")
        return

    stock_ver = stock_version(spec)
    dest_ver = fork_version(spec, dest) or "(missing)"
    log(f"plan: sync {vendor}-{profile} {dest_ver} <- stock {stock_ver}")
    if dry_run:
        log("dry-run: no writes (including not writing stock trees)")

    pids = fork_pids(dest)
    if pids:
        log(
            f"{vendor}-{profile} is running (pids: {', '.join(str(p) for p in pids)}); "
            "rebuild continues; restart that desktop to load the new version"
        )

    log(rsync_stock(spec, dest, dry_run=dry_run))
    patch_root = dest if not dry_run else spec.stock_lib
    if dry_run:
        log(f"would patch copied identity (preview against stock {spec.stock_lib})")
        for line in patch_identity(spec, patch_root, profile, dry_run=True):
            log(line)
    else:
        for line in patch_identity(spec, dest, profile, dry_run=False):
            log(line)
    for line in recolor_tree_icons(spec, dest, color, dry_run=dry_run):
        log(line)
    log(write_apparmor(spec, dest, profile, env, dry_run=dry_run))


def _read_provenance(home: Path, profile: str, vendor: str) -> dict | None:
    path = home / ".agents-profiles" / profile / vendor / PROVENANCE_NAME
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def sync_homes(homes: list[Path], env: Env, *, dry_run: bool,
               profile: str | None = None, vendor: str | None = None,
               icons_only: bool = False) -> int:
    errors = 0
    seen = False
    for home in homes:
        for name, inst_vendor, _prov in discover_desktop_instances(home):
            if profile and name != profile:
                continue
            if vendor and inst_vendor != vendor:
                continue
            seen = True
            try:
                sync_one(inst_vendor, name, home, env, dry_run=dry_run,
                         icons_only=icons_only)
            except Exception as e:
                log(f"error: {name}/{inst_vendor}: {e}")
                errors += 1
    if not seen:
        log("skip: no desktop profile instances found")
    return 1 if errors else 0


def doctor_lines(home: Path, env: Env | None = None) -> list[str]:
    env = env or Env()
    lines: list[str] = []
    user = home.name
    for name, vendor, _prov in discover_desktop_instances(home):
        spec = env.vendors[vendor]
        dest = fork_dir(vendor, name, env)
        label = f"{name}/{vendor}"
        if not spec.stock_lib.is_dir():
            continue
        if not dest.is_dir():
            lines.append(
                f"{label}: app fork missing at {dest}\n"
                f"    fix: devkit profile apps-sync --user {user} --apply"
            )
            continue
        wanted = desktop_name(vendor, name)
        try:
            cheap_gates(spec, dest, name)
        except Skip:
            continue
        except Exception as e:
            lines.append(f"{label}: app fork unreadable ({e})")
            continue
        have = fork_desktop_name(spec, dest)
        lines.append(
            f"{label}: app fork stale (desktopName={have or 'missing'}, want {wanted})\n"
            f"    fix: devkit profile apps-sync --user {user} --apply"
        )
    hook_ok = env.apt_conf.is_file() and env.dpkg_conf.is_file() and env.worker.is_file()
    if not hook_ok and any(discover_desktop_instances(home)):
        lines.append(
            "profile app-fork apt/dpkg hooks are not installed\n"
            f"    fix: devkit profile apps-sync --user {user} --install-hook --apply"
        )
    return lines


# ---------------------------------------------------------------- apt/dpkg hooks

APT_BODY = """\
// Rebuild per-profile Claude/Codex/Cursor forks after any apt/dpkg run.
// Forks are not .debs; vendor postinst cannot hold this logic.
DPkg::Post-Invoke {"/usr/local/bin/sync-devkit-profile-apps.py >>/var/log/devkit-profile-apps.log 2>&1 || true";};
"""

DPKG_BODY = """\
# Rebuild profile app forks after dpkg -i / unpack (apt's DPkg::Post-Invoke
# does not run for bare dpkg). Second run in the same apt transaction is a no-op.
post-invoke "/usr/local/bin/sync-devkit-profile-apps.py >>/var/log/devkit-profile-apps.log 2>&1 || true"
"""


def install_hook(env: Env, *, dry_run: bool) -> list[str]:
    actions: list[str] = []
    src = Path(__file__).resolve()
    actions.append(f"copy {src} -> {env.worker}")
    actions.append(f"write {env.apt_conf}")
    actions.append(f"write {env.dpkg_conf}")
    if dry_run:
        return actions
    env.worker.parent.mkdir(parents=True, exist_ok=True)
    if src != env.worker.resolve():
        shutil.copy2(src, env.worker)
    os.chmod(env.worker, 0o755)
    env.apt_conf.parent.mkdir(parents=True, exist_ok=True)
    env.apt_conf.write_text(APT_BODY, encoding="utf-8")
    os.chmod(env.apt_conf, 0o644)
    env.dpkg_conf.parent.mkdir(parents=True, exist_ok=True)
    env.dpkg_conf.write_text(DPKG_BODY, encoding="utf-8")
    os.chmod(env.dpkg_conf, 0o644)
    env.log_path.parent.mkdir(parents=True, exist_ok=True)
    if not env.log_path.exists():
        env.log_path.write_text("", encoding="utf-8")
        os.chmod(env.log_path, 0o644)
    return actions


def resolve_homes(user: str | None, env: Env) -> list[Path]:
    if user:
        try:
            return [Path(pwd.getpwnam(user).pw_dir)]
        except KeyError as e:
            raise RuntimeError(f"no such user: {user}") from e
    if os.geteuid() != 0:
        return [Path.home()]
    sudo_user = os.environ.get("SUDO_USER") or os.environ.get("DOAS_USER")
    if sudo_user and sudo_user != "root":
        try:
            return [Path(pwd.getpwnam(sudo_user).pw_dir)]
        except KeyError:
            pass
    return iter_homes(env)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Rebuild per-profile desktop app forks from stock packages."
    )
    p.add_argument("--dry-run", action="store_true", help="print actions; change nothing")
    p.add_argument("--icons-only", action="store_true",
                   help="recolor fork icons from stock; skip rsync/asar")
    p.add_argument("--install-hook", action="store_true",
                   help="install apt + dpkg post-invoke hooks and copy this worker")
    p.add_argument("--user", metavar="NAME", help="only this account's ~/.agents-profiles")
    p.add_argument("--profile", metavar="NAME", help="only this profile")
    p.add_argument("--vendor", metavar="VENDOR", help="only this vendor")
    p.add_argument("--log", metavar="PATH", help="also append stdout copy to PATH")
    args = p.parse_args(argv)

    log_fp = None
    if args.log:
        log_path = Path(args.log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fp = log_path.open("a", encoding="utf-8")
        os.dup2(log_fp.fileno(), sys.stdout.fileno())
        os.dup2(log_fp.fileno(), sys.stderr.fileno())

    env = Env()
    try:
        if args.install_hook:
            if not args.dry_run and os.geteuid() != 0:
                log("must run as root (try: sudo)")
                return 1
            for line in install_hook(env, dry_run=args.dry_run):
                log(line)
            if args.dry_run:
                return 0
        if not args.dry_run and os.geteuid() != 0:
            log("must run as root (try: sudo)")
            return 1
        homes = resolve_homes(args.user, env)
        return sync_homes(
            homes, env, dry_run=args.dry_run, profile=args.profile,
            vendor=args.vendor, icons_only=args.icons_only,
        )
    except Exception as e:
        log(f"error: {e}")
        return 1
    finally:
        if log_fp is not None:
            log_fp.close()


if __name__ == "__main__":
    sys.exit(main())
