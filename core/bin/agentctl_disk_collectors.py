"""Live collectors for `agentctl disk`: docker, apt/deb, flatpak, snap and system.

Parsing is separate from subprocess calls so tests feed captured output from
tests/fixtures/disk/. Every collector only reads state; the commands it emits
are strings for the operator to run.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from agentctl_disk_scan import human, mount_for_path

SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([kKMGTP]?)(i?)[bB]?\s*$")
DOCKER_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([kKMGTP]?)B")
UNITS = {"": 0, "K": 1, "M": 2, "G": 3, "T": 4, "P": 5}
VOLUMES_DIR = Path("/home/volumes")


class Unavailable(Exception):
    """A collector could not run; the message becomes the `unavailable` reason."""


def parse_size(text: str, *, binary: bool = False) -> int:
    """`500M`, `2GB`, `2GiB`, `462.3 MB`. SI by default; `iB` or binary=True means 1024."""
    match = SIZE_RE.match(text)
    if not match:
        raise ValueError(f"not a size: {text!r}")
    number, unit, ib = match.groups()
    base = 1024 if (ib or binary) else 1000
    return int(float(number) * base ** UNITS[unit.upper()])


def finding_id(category: str, key: str) -> str:
    return "dk_" + hashlib.sha1(f"{category}\0{key}".encode("utf-8", "surrogateescape")).hexdigest()[:10]


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def make_finding(category: str, key: str, title: str, path: str, nbytes: int, *, risk: str,
                 reversible: bool = False, regenerable: bool = False, confidence: str = "high",
                 needs_sudo: bool = False, command: str | None = None, last_used: float | None = None,
                 last_used_source: str = "mtime", evidence: str = "", mount: str | None = None,
                 covers: tuple[str, ...] = (), verify_command: str | None = None,
                 protected: bool = False, floor: bool = True) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "id": finding_id(category, key), "category": category, "title": title, "path": path,
        "bytes": nbytes, "human": human(nbytes),
        "last_used": {"at": iso(last_used), "source": last_used_source} if last_used else None,
        "risk": risk, "reversible": reversible, "regenerable": regenerable, "confidence": confidence,
        "needs_sudo": needs_sudo, "suggested_command": command,
    }
    if protected:
        finding["protected"] = True
    if verify_command:
        finding["verify_command"] = verify_command
    if evidence:
        finding["evidence"] = evidence
    finding["_ts"] = last_used
    finding["_mount"] = mount
    finding["_covers"] = covers
    finding["_floor"] = floor
    return finding


@dataclass
class Ctx:
    target: dict[str, str]
    mounts: list[dict[str, str]]
    timeout: float = 20.0
    live_min_bytes: int = 10_000_000
    volumes_dir: Path = VOLUMES_DIR
    home: str = field(default_factory=lambda: os.path.expanduser("~"))
    kernel: str = field(default_factory=lambda: os.uname().release)
    apt_archives: Path = Path("/var/cache/apt/archives")
    crash_dir: Path = Path("/var/crash")
    coredump_dir: Path = Path("/var/lib/systemd/coredump")
    stale_days: int = 180
    runner: Callable[..., str] | None = None
    deadline: float = 0.0

    def run(self, cmd: list[str], *, stdin: str | None = None, ok_codes: tuple[int, ...] = (0,)) -> str:
        if self.runner:
            return self.runner(cmd, stdin)
        remaining = max(1.0, self.deadline - time.monotonic()) if self.deadline else self.timeout
        try:
            proc = subprocess.run(
                cmd, check=False, input=stdin, capture_output=True, text=True, timeout=remaining,
                env={**os.environ, "LC_ALL": "C"}, stdin=None if stdin else subprocess.DEVNULL,
            )
        except FileNotFoundError:
            raise Unavailable(f"{cmd[0]} not installed") from None
        except subprocess.TimeoutExpired:
            raise Unavailable("timeout") from None
        if proc.returncode not in ok_codes:
            line = (proc.stderr.strip().splitlines() or [""])[0][:160]
            raise Unavailable(f"{' '.join(cmd[:2])} exited {proc.returncode}: {line}".strip())
        return proc.stdout

    def on_target(self, path: str) -> bool:
        mount = mount_for_path(path, self.mounts)
        return bool(mount) and mount["mount"] == self.target["mount"]

    def mount_of(self, path: str) -> str:
        mount = mount_for_path(path, self.mounts)
        return mount["mount"] if mount else "/"


def _quote(*parts: str) -> str:
    return " ".join(shlex.quote(p) for p in parts)


def _docker_bytes(text: str | None) -> int:
    match = DOCKER_SIZE_RE.match(text or "")
    if not match:
        return 0
    number, unit = match.groups()
    return int(float(number) * 1000 ** UNITS[unit.upper()])


def _docker_time(text: str | None) -> float | None:
    try:
        return datetime.strptime((text or "")[:25], "%Y-%m-%d %H:%M:%S %z").timestamp()
    except ValueError:
        return None


def protected_volume_names(volumes_dir: Path) -> set[str]:
    try:
        return {p.name for p in volumes_dir.iterdir() if p.is_dir()}
    except OSError:
        return set()


def docker_findings(df: dict[str, Any], protected: set[str], mount: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for image in df.get("Images") or []:
        if str(image.get("Containers", "0")) != "0":
            continue
        name = f"{image.get('Repository')}:{image.get('Tag')}"
        dangling = image.get("Repository") in ("<none>", None)
        size = _docker_bytes(image.get("UniqueSize")) or _docker_bytes(image.get("Size"))
        out.append(make_finding(
            "docker", image["ID"], f"Unused image {name}", image["ID"], size,
            risk="safe" if dangling else "review", reversible=True, regenerable=True,
            command=_quote("docker", "rmi", image["ID"]), mount=mount,
            last_used=_docker_time(image.get("CreatedAt")), last_used_source="created",
            evidence="no container references this image" + (" (dangling)" if dangling else ""),
        ))
    for box in df.get("Containers") or []:
        if box.get("State") == "running":
            continue
        mounted = {m for m in (box.get("Mounts") or "").split(",") if m}
        guarded = sorted(mounted & protected)
        name = box.get("Names") or box["ID"][:12]
        out.append(make_finding(
            "docker", box["ID"], f"Stopped container {name}", name, _docker_bytes(box.get("Size")),
            risk="danger" if guarded else "review", reversible=False,
            command=None if guarded else _quote("docker", "rm", name), mount=mount,
            last_used=_docker_time(box.get("CreatedAt")), last_used_source="created",
            protected=bool(guarded),
            evidence=(f"mounts protected volume {guarded[0]}" if guarded else f"{box.get('Status', 'stopped')}"),
        ))
    for volume in df.get("Volumes") or []:
        if str(volume.get("Links", "0")) != "0":
            continue
        name = volume["Name"]
        guarded = name in protected
        out.append(make_finding(
            "docker", f"volume:{name}", f"Unused volume {name}", name, _docker_bytes(volume.get("Size")),
            risk="danger" if guarded else "review", reversible=False,
            command=None if guarded else _quote("docker", "volume", "rm", name), mount=mount,
            protected=guarded,
            evidence=("listed under /home/volumes, protected" if guarded
                      else "no container uses it; removing is permanent"),
        ))
    cache = [c for c in df.get("BuildCache") or []
             if str(c.get("InUse", "")).lower() == "false" and str(c.get("Shared", "")).lower() != "true"]
    if cache:
        out.append(make_finding(
            "docker", "buildcache", "Docker build cache", "docker builder cache",
            sum(_docker_bytes(c.get("Size")) for c in cache), risk="safe", reversible=True,
            regenerable=True, command="docker builder prune -f", mount=mount,
            evidence=f"{len(cache)} unused, unshared build cache entries",
        ))
    return out


def collect_docker(ctx: Ctx) -> dict[str, Any]:
    try:
        root = ctx.run(["docker", "info", "--format", "{{.DockerRootDir}}"]).strip() or "/var/lib/docker"
        mount = ctx.mount_of(root)
        if mount != ctx.target["mount"]:
            return {"collector": "docker", "mount": mount, "findings": []}
        df = json.loads(ctx.run(["docker", "system", "df", "-v", "--format", "json"]))
    except Unavailable as exc:
        return {"collector": "docker", "mount": "/", "unavailable": str(exc), "findings": []}
    except ValueError as exc:
        return {"collector": "docker", "mount": "/", "unavailable": f"unparsable docker output: {exc}",
                "findings": []}
    return {"collector": "docker", "mount": mount,
            "findings": docker_findings(df, protected_volume_names(ctx.volumes_dir), mount)}


# --- apt / deb -----------------------------------------------------------

def parse_dpkg_query(text: str) -> list[dict[str, Any]]:
    """Lines: status<TAB>package<TAB>version<TAB>installed-size-KiB."""
    rows = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        size = int(parts[3]) * 1024 if parts[3].strip().isdigit() else 0
        rows.append({"status": parts[0].strip(), "package": parts[1], "version": parts[2], "bytes": size})
    return rows


def parse_autoremove(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^Remv (\S+)", text, re.MULTILINE)]


KERNEL_RE = re.compile(r"^linux-(image|modules|modules-extra|headers)-(?:unsigned-)?(\d+\.\d+\.\d+-\d+-\S+)$")


def extra_kernels(rows: list[dict[str, Any]], running: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        match = KERNEL_RE.match(row["package"])
        if match and row["status"] == "ii" and match.group(2) != running:
            groups.setdefault(match.group(2), []).append(row)
    return {v: rows_ for v, rows_ in groups.items() if any(r["package"].startswith("linux-image-") for r in rows_)}


def collect_apt(ctx: Ctx) -> dict[str, Any]:
    if not ctx.on_target("/var/lib/dpkg"):
        return {"collector": "apt", "mount": ctx.mount_of("/var/lib/dpkg"), "findings": []}
    mount = ctx.mount_of("/var/lib/dpkg")
    findings: list[dict[str, Any]] = []
    try:
        rows = parse_dpkg_query(ctx.run(
            ["dpkg-query", "-W", "-f", "${db:Status-Abbrev}\t${Package}\t${Version}\t${Installed-Size}\n"]))
    except Unavailable as exc:
        return {"collector": "apt", "mount": "/", "unavailable": str(exc), "findings": []}
    sizes = {r["package"]: r["bytes"] for r in rows}
    try:
        removable = parse_autoremove(ctx.run(["apt-get", "-s", "autoremove"]))
    except Unavailable as exc:
        removable = []
        findings_unavailable = str(exc)
    else:
        findings_unavailable = None
    if removable:
        findings.append(make_finding(
            "apps", "apt-autoremove", f"{len(removable)} autoremovable packages", "apt autoremove",
            sum(sizes.get(p, 0) for p in removable), risk="review", reversible=True, needs_sudo=True,
            command="sudo apt-get autoremove --purge", mount=mount, floor=False,
            evidence=", ".join(removable[:8]),
        ))
    for version, packages in extra_kernels(rows, ctx.kernel).items():
        names = [p["package"] for p in packages]
        findings.append(make_finding(
            "apps", f"kernel:{version}", f"Old kernel {version}", f"linux {version}",
            sum(p["bytes"] for p in packages), risk="review", reversible=True, needs_sudo=True,
            command="sudo apt-get remove --purge " + _quote(*names), mount=mount, floor=False,
            evidence=f"running kernel is {ctx.kernel}",
        ))
    residual = [r for r in rows if r["status"] == "rc"]
    if residual:
        names = [r["package"] for r in residual]
        findings.append(make_finding(
            "apps", "apt-residual-config", f"{len(residual)} packages with leftover config", "dpkg rc",
            0, risk="safe", reversible=False, needs_sudo=True,
            command="sudo dpkg --purge " + _quote(*names), mount=mount, floor=False, confidence="medium",
            evidence="config files only, size negligible: " + ", ".join(names[:8]),
        ))
    cached = _deb_cache(ctx.apt_archives)
    if cached[0]:
        findings.append(make_finding(
            "apps", "apt-cache", "apt package cache", str(ctx.apt_archives), cached[0], risk="safe",
            reversible=True, regenerable=True, needs_sudo=True, command="sudo apt-get clean", mount=mount,
            last_used=cached[1], covers=("/var/cache/apt",), evidence=f"{cached[2]} cached .deb files",
        ))
    out = {"collector": "apt", "mount": mount, "findings": findings}
    if findings_unavailable and not findings:
        out["unavailable"] = findings_unavailable
    return out


def _deb_cache(archives: Path) -> tuple[int, float | None, int]:
    total, newest, count = 0, None, 0
    try:
        for entry in os.scandir(archives):
            if entry.name.endswith(".deb") and entry.is_file(follow_symlinks=False):
                st = entry.stat(follow_symlinks=False)
                total += st.st_size
                count += 1
                newest = max(newest or 0.0, st.st_mtime)
    except OSError:
        pass
    return total, newest, count


# --- flatpak -------------------------------------------------------------

def parse_flatpak_list(text: str) -> dict[tuple[str, str, str], int]:
    """`application<TAB>branch<TAB>size<TAB>installation` -> {(app, branch, installation): bytes}."""
    sizes: dict[tuple[str, str, str], int] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        try:
            sizes[(parts[0], parts[1], parts[3].strip())] = parse_size(parts[2].replace("\xa0", " "))
        except ValueError:
            sizes[(parts[0], parts[1], parts[3].strip())] = 0
    return sizes


def parse_flatpak_unused(text: str) -> list[tuple[str, str]]:
    return re.findall(r"^\s*\d+\.\s+(\S+)\s+(\S+)\s+\w\s*$", text, re.MULTILINE)


def flatpak_findings(sizes: dict[tuple[str, str, str], int], unused: dict[str, list[tuple[str, str]]],
                     ctx: Ctx) -> list[dict[str, Any]]:
    out = []
    for installation, refs in unused.items():
        where = "/var/lib/flatpak" if installation == "system" else f"{ctx.home}/.local/share/flatpak"
        mount = ctx.mount_of(where)
        for app, branch in refs:
            out.append(make_finding(
                "apps", f"flatpak:{installation}:{app}/{branch}", f"Unused flatpak runtime {app} {branch}",
                f"{app}//{branch}", sizes.get((app, branch, installation), 0), risk="review",
                reversible=True, regenerable=True, needs_sudo=installation == "system",
                command=f"flatpak uninstall --unused --{installation}", mount=mount, covers=(where,),
                evidence=f"flatpak lists it under 'uninstall --unused' ({installation} installation)",
            ))
    return out


def _flatpak_unused_output(ctx: Ctx, installation: str) -> str:
    # Answering "n" makes flatpak print the unused list and abort (exit 1); nothing is removed.
    text = ctx.run(["flatpak", "uninstall", "--unused", f"--{installation}"], stdin="n\n", ok_codes=(0, 1))
    if "Proceed" not in text and "Nothing unused" not in text:
        raise Unavailable("flatpak uninstall --unused printed no list")
    return text


def collect_flatpak(ctx: Ctx) -> dict[str, Any]:
    try:
        sizes = parse_flatpak_list(ctx.run(["flatpak", "list", "--columns=application,branch,size,installation"]))
        unused: dict[str, list[tuple[str, str]]] = {}
        for installation in sorted({key[2] for key in sizes}):
            unused[installation] = parse_flatpak_unused(
                _flatpak_unused_output(ctx, installation))
    except Unavailable as exc:
        return {"collector": "flatpak", "mount": "/", "unavailable": str(exc), "findings": []}
    findings = [f for f in flatpak_findings(sizes, unused, ctx) if f["_mount"] == ctx.target["mount"]]
    return {"collector": "flatpak", "mount": ctx.target["mount"], "findings": findings}


# --- snap ----------------------------------------------------------------

def parse_snap_disabled(text: str) -> list[tuple[str, str]]:
    out = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 3 and "disabled" in parts[-1]:
            out.append((parts[0], parts[2]))
    return out


def collect_snap(ctx: Ctx) -> dict[str, Any]:
    try:
        disabled = parse_snap_disabled(ctx.run(["snap", "list", "--all"]))
    except Unavailable as exc:
        return {"collector": "snap", "mount": "/", "unavailable": str(exc), "findings": []}
    mount = ctx.mount_of("/var/lib/snapd")
    findings = []
    for name, revision in disabled:
        snap_file = Path(f"/var/lib/snapd/snaps/{name}_{revision}.snap")
        try:
            size = snap_file.stat().st_size
        except OSError:
            size = 0
        findings.append(make_finding(
            "apps", f"snap:{name}:{revision}", f"Disabled snap revision {name} {revision}", str(snap_file),
            size, risk="safe", reversible=True, regenerable=True, needs_sudo=True,
            command=f"sudo snap remove {shlex.quote(name)} --revision={shlex.quote(revision)}",
            mount=mount, evidence="old revision kept by snapd",
        ))
    return {"collector": "snap", "mount": mount,
            "findings": [f for f in findings if f["_mount"] == ctx.target["mount"]]}


# --- system --------------------------------------------------------------

def parse_journal_usage(text: str) -> int:
    match = re.search(r"take up ([\d.]+\s*[KMGT]?)\s", text)
    if not match:
        raise ValueError("no size in journalctl --disk-usage output")
    return parse_size(match.group(1), binary=True)


def reserved_blocks(st: os.statvfs_result) -> tuple[int, int]:
    """(reserved bytes, disk bytes) from statvfs."""
    return (st.f_bfree - st.f_bavail) * st.f_frsize, st.f_blocks * st.f_frsize


def _dir_total(path: Path) -> tuple[int, float | None]:
    total, newest = 0, None
    try:
        for entry in os.scandir(path):
            st = entry.stat(follow_symlinks=False)
            total += st.st_blocks * 512
            newest = max(newest or 0.0, st.st_mtime)
    except OSError:
        return 0, None
    return total, newest


def collect_system(ctx: Ctx, statvfs: Callable[[str], os.statvfs_result] = os.statvfs) -> dict[str, Any]:
    mount = ctx.target["mount"]
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    st = statvfs(mount)
    reserved, disk = reserved_blocks(st)
    fstype = ctx.target.get("fstype", "")
    if reserved >= 1_000_000_000 and reserved * 100 // disk > 1 and fstype.startswith("ext") and ctx.target.get("device"):
        freeable = max(0, reserved - disk // 100)
        findings.append(make_finding(
            "system", f"reserved:{mount}", f"Reserved blocks: {human(reserved)} reserved, "
            f"tune2fs -m 1 frees about {human(freeable)}", mount, reserved, risk="review", reversible=True,
            needs_sudo=True, command="sudo tune2fs -m 1 " + shlex.quote(ctx.target["device"]), mount=mount,
            confidence="medium", floor=False,
            evidence=f"statvfs: {human(reserved)} of {human(disk)} is reserved for root",
        ))
    if ctx.on_target("/var/log/journal"):
        try:
            size = parse_journal_usage(ctx.run(["journalctl", "--disk-usage"]))
            findings.append(make_finding(
                "system", "journald", "systemd journal", "/var/log/journal", size, risk="review",
                reversible=False, needs_sudo=True, command="sudo journalctl --vacuum-size=100M",
                mount=mount, covers=("/var/log/journal",), evidence="archived and active journals",
            ))
        except (Unavailable, ValueError) as exc:
            notes.append(f"journald: {exc}")
    for key, title, path in (("crash", "Crash reports", ctx.crash_dir), ("coredump", "Core dumps", ctx.coredump_dir)):
        if not ctx.on_target(str(path)):
            continue
        size, newest = _dir_total(path)
        if size:
            findings.append(make_finding(
                "system", key, title, str(path), size, risk="review", needs_sudo=True,
                command="sudo find " + shlex.quote(str(path)) + " -type f -delete", mount=mount,
                last_used=newest, covers=(str(path),), evidence="files in the crash directory",
            ))
    out: dict[str, Any] = {"collector": "system", "mount": mount, "findings": findings}
    if notes and not findings:
        out["unavailable"] = "; ".join(notes)
    return out


COLLECTORS: dict[str, tuple[str, Callable[[Ctx], dict[str, Any]]]] = {
    "docker": ("docker", collect_docker),
    "apt": ("apps", collect_apt),
    "flatpak": ("apps", collect_flatpak),
    "snap": ("apps", collect_snap),
    "system": ("system", collect_system),
}


def run_collectors(ctx: Ctx, categories: set[str] | None,
                   collectors: dict[str, tuple[str, Callable[[Ctx], dict[str, Any]]]] | None = None,
                   grace: float = 2.0
                   ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Run the selected collectors in threads. Returns (findings, unavailable list)."""
    table = collectors or COLLECTORS
    chosen = {name: fn for name, (cat, fn) in table.items() if categories is None or cat in categories}
    ctx.deadline = time.monotonic() + ctx.timeout
    findings: list[dict[str, Any]] = []
    unavailable: list[dict[str, str]] = []
    if not chosen:
        return findings, unavailable
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=len(chosen))
    futures = {pool.submit(fn, ctx): name for name, fn in chosen.items()}
    done, pending = concurrent.futures.wait(futures, timeout=ctx.timeout + grace)
    for future in done:
        name = futures[future]
        try:
            result = future.result()
        except Exception as exc:  # noqa: BLE001 - a collector failure must not fail the report
            unavailable.append({"collector": name, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        if result["mount"] != ctx.target["mount"]:
            continue
        if result.get("unavailable"):
            unavailable.append({"collector": name, "reason": result["unavailable"]})
        for item in result["findings"]:
            if item["_floor"] and item["bytes"] < ctx.live_min_bytes:
                continue
            findings.append(item)
    for future in pending:
        unavailable.append({"collector": futures[future], "reason": "timeout"})
    pool.shutdown(wait=False, cancel_futures=True)
    return findings, unavailable
