"""agentctl tools update: find outdated user-wide tools and upgrade them on request.

Package-manager installs (npm, uv, pipx, skills CLI) upgrade through their own
manager. Standalone GitHub-release binaries are reported with their release URL
and never downloaded: asset naming differs per project.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tomllib
import urllib.request
from pathlib import Path
from typing import Any

import agentctl_config
from agentctl_common import emit, run

SOURCES = ("npm", "npm-local", "uv", "pipx", "uv-self", "skills", "github")
LOCAL_NPM_PREFIX = Path.home() / ".local"
GITHUB_BINARIES = {
    "lychee": ("lycheeverse/lychee", ["--version"]),
    "gitleaks": ("gitleaks/gitleaks", ["version"]),
    "osv-scanner": ("google/osv-scanner", ["--version"]),
    "trivy": ("aquasecurity/trivy", ["--version"]),
    "ast-grep": ("ast-grep/ast-grep", ["--version"]),
    "ollama": ("ollama/ollama", ["--version"]),
}
VERSION_RE = re.compile(r"\d+(?:\.\d+)+")
UV_OUTDATED_RE = re.compile(r"^(?P<name>\S+) v(?P<current>\S+) \[latest: (?P<latest>[^\]]+)\]")


def cmd_tools_update(args: argparse.Namespace) -> int:
    sources = selected_sources(args.source)
    only = {name.strip() for name in args.only.split(",") if name.strip()} if args.only else set()
    items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for source in sources:
        try:
            items.extend(COLLECTORS[source](args.timeout))
        except (OSError, ValueError) as exc:
            errors.append({"source": source, "error": str(exc)})
    if only:
        items = [item for item in items if item["name"] in only]
    for item in items:
        item["action"] = planned_action(item, args.include_major, args.include_skills)
        if args.apply and item["action"] == "upgrade":
            result = run(item["command"], timeout=args.timeout)
            item["returncode"] = result.returncode
            if result.returncode != 0:
                item["error"] = (result.stderr or result.stdout).strip()[-1000:]
    failed = [item["name"] for item in items if item.get("returncode", 0) != 0]
    emit({
        "apply": args.apply,
        "sources": list(sources),
        "outdated": len(items),
        "by_action": {action: [i["name"] for i in items if i["action"] == action]
                      for action in ("upgrade", "skipped-major", "held", "manual")},
        "items": items,
        "failed": failed,
        "errors": errors,
    })
    return 1 if failed or errors or any(item.get("error") for item in items) else 0


def selected_sources(value: str | None) -> tuple[str, ...]:
    if not value:
        return SOURCES
    names = tuple(part.strip() for part in value.split(",") if part.strip())
    unknown = [name for name in names if name not in SOURCES]
    if unknown:
        raise SystemExit(f"unknown source(s): {', '.join(unknown)}; expected {', '.join(SOURCES)}")
    return names


def planned_action(item: dict[str, Any], include_major: bool, include_skills: bool) -> str:
    if not item.get("command"):
        return "manual"
    if item.get("hold"):
        return "held"
    if item["source"] == "skills" and not include_skills:
        item["hold"] = "skills update replaces the folder and drops local edits; pass --include-skills"
        return "held"
    if item.get("major") and not include_major:
        return "skipped-major"
    return "upgrade"


def is_major(current: str | None, latest: str | None) -> bool:
    cur, new = first_version(current), first_version(latest)
    if not cur or not new:
        return False
    return cur.split(".")[0] != new.split(".")[0]


def first_version(text: str | None) -> str | None:
    match = VERSION_RE.search(text or "")
    return match.group(0) if match else None


def outdated_item(source: str, name: str, current: str | None, latest: str | None,
                  command: list[str] | None, **extra: Any) -> dict[str, Any]:
    return {"source": source, "name": name, "current": current, "latest": latest,
            "major": is_major(current, latest), "command": command, **extra}


def collect_npm_global(timeout: float) -> list[dict[str, Any]]:
    return npm_outdated(["npm", "outdated", "-g", "--json"], "npm", ["-g"], timeout)


def collect_npm_local(timeout: float) -> list[dict[str, Any]]:
    prefix = ["--prefix", str(LOCAL_NPM_PREFIX)]
    items = []
    # ~/.local holds a project install (node_modules) and a global one (lib/node_modules)
    # whose bin links sit in ~/.local/bin, ahead of the nvm globals on PATH.
    if (LOCAL_NPM_PREFIX / "package.json").is_file():
        items += npm_outdated(["npm", "outdated", *prefix, "--json"], "npm-local", prefix, timeout)
    if (LOCAL_NPM_PREFIX / "lib" / "node_modules").is_dir():
        items += npm_outdated(["npm", "outdated", "-g", *prefix, "--json"], "npm-local", ["-g", *prefix], timeout)
    return items


def npm_outdated(command: list[str], source: str, install_scope: list[str],
                 timeout: float) -> list[dict[str, Any]]:
    if not shutil.which("npm"):
        return []
    # npm outdated exits 1 whenever something is outdated; only the JSON matters.
    result = run(command, timeout=timeout)
    data = json.loads(result.stdout or "{}")
    if "error" in data:
        raise ValueError(f"{' '.join(command)}: {data['error'].get('summary', data['error'])}")
    return [
        outdated_item(source, name, info.get("current"), info.get("latest"),
                      ["npm", "install", *install_scope, f"{name}@{info.get('latest')}"])
        for name, info in sorted(data.items())
        if info.get("current") and info.get("current") != info.get("latest")
    ]


def collect_uv(timeout: float) -> list[dict[str, Any]]:
    if not shutil.which("uv"):
        return []
    result = run(["uv", "tool", "list", "--outdated"], timeout=timeout)
    tool_dir = Path(run(["uv", "tool", "dir"], timeout=timeout).stdout.strip())
    items = []
    for line in result.stdout.splitlines():
        match = UV_OUTDATED_RE.match(line)
        if match:
            items.append(outdated_item("uv", match["name"], match["current"], match["latest"],
                                       ["uv", "tool", "upgrade", match["name"]],
                                       hold=uv_hold_reason(tool_dir / match["name"] / "uv-receipt.toml", match["name"])))
    for line in result.stderr.splitlines():
        broken = re.match(r"Failed find package `([^`]+)`", line)
        if broken:
            items.append(outdated_item("uv", broken.group(1), None, None, None,
                                       error="broken tool environment; reinstall with uv tool install --force"))
    return items


def uv_hold_reason(receipt: Path, name: str) -> str | None:
    # uv tool list --outdated compares against the index even for a pinned or
    # local-source install, which uv tool upgrade keeps unchanged.
    try:
        requirements = tomllib.loads(receipt.read_text(encoding="utf-8"))["tool"]["requirements"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return None
    for requirement in requirements:
        if requirement.get("name") != name:
            continue
        for key in ("directory", "path", "git", "url"):
            if key in requirement:
                return f"installed from {key} {requirement[key]}"
        if str(requirement.get("specifier", "")).startswith("=="):
            return f"pinned {requirement['specifier']}"
    return None


def collect_pipx(timeout: float) -> list[dict[str, Any]]:
    if not shutil.which("pipx"):
        return []
    venvs = json.loads(run(["pipx", "list", "--json"], timeout=timeout).stdout or "{}").get("venvs", {})
    items = []
    for name, venv in sorted(venvs.items()):
        package = venv["metadata"]["main_package"]
        latest = pypi_latest(package["package"], timeout)
        if latest and latest != package["package_version"]:
            items.append(outdated_item("pipx", name, package["package_version"], latest,
                                       ["pipx", "upgrade", name]))
    return items


def collect_uv_self(timeout: float) -> list[dict[str, Any]]:
    uv = shutil.which("uv")
    if not uv:
        return []
    current = first_version(run([uv, "--version"], timeout=timeout).stdout)
    latest = first_version(github_json("repos/astral-sh/uv/releases/latest", timeout).get("tag_name"))
    if not latest or latest == current:
        return []
    return [outdated_item("uv-self", "uv", current, latest, ["uv", "self", "update"])]


def collect_skills(timeout: float) -> list[dict[str, Any]]:
    lock_path = skill_lock_path()
    if not lock_path.is_file():
        return []
    lock = json.loads(lock_path.read_text(encoding="utf-8")).get("skills", {})
    items = []
    for name, entry in sorted(lock.items()):
        if entry.get("sourceType") != "github":
            continue
        try:
            remote = skill_tree_sha(entry["source"], str(Path(entry["skillPath"]).parent), timeout)
        except OSError as exc:
            items.append(outdated_item("skills", name, None, None, None, error=str(exc)))
            continue
        if remote and remote != entry.get("skillFolderHash"):
            items.append(outdated_item(
                "skills", name, entry.get("skillFolderHash", "")[:12], remote[:12],
                ["skills", "update", name, "-g", "-y"] if shutil.which("skills") else None,
                upstream=entry["source"],
            ))
    return items


def release_binaries() -> dict[str, tuple[str, list[str]]]:
    """Tools whose releases live on GitHub, plus the active git host's MCP server binary from .agentctl."""
    binaries = dict(GITHUB_BINARIES)
    try:
        host = agentctl_config.git_host()
    except agentctl_config.ConfigError:
        host = None
    if host and host.get("mcp_binary") and host.get("mcp_release_repo"):
        binaries[host["mcp_binary"]] = (host["mcp_release_repo"], ["--version"])
    return binaries


def collect_github(timeout: float) -> list[dict[str, Any]]:
    items = []
    for name, (repo, version_args) in release_binaries().items():
        path = shutil.which(name)
        if not path:
            continue
        probe = run([path, *version_args], timeout=timeout)
        current = first_version(probe.stdout + "\n" + probe.stderr)
        try:
            tag = github_json(f"repos/{repo}/releases/latest", timeout).get("tag_name")
        except OSError as exc:
            items.append(outdated_item("github", name, current, None, None, path=path, error=str(exc)))
            continue
        latest = first_version(tag)
        if latest and latest != current:
            items.append(outdated_item("github", name, current, latest, None, path=path,
                                       release=f"https://github.com/{repo}/releases/tag/{tag}"))
    return items


def skill_lock_path() -> Path:
    # Mirrors getSkillLockPath() in the skills CLI, which ignores AGENTS_HOME.
    state = os.environ.get("XDG_STATE_HOME")
    return Path(state) / "skills" / ".skill-lock.json" if state else Path.home() / ".agents" / ".skill-lock.json"


def skill_tree_sha(repo: str, folder: str, timeout: float) -> str | None:
    parent, base = str(Path(folder).parent), Path(folder).name
    entries = github_json(f"repos/{repo}/contents/{'' if parent == '.' else parent}", timeout)
    if not isinstance(entries, list):
        return None
    return next((entry["sha"] for entry in entries if entry.get("name") == base), None)


def github_json(path: str, timeout: float) -> Any:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "agentctl"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"https://api.github.com/{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (OSError, ValueError) as exc:
        raise OSError(f"GitHub {path}: {exc}") from exc


def pypi_latest(package: str, timeout: float) -> str | None:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{package}/json", timeout=timeout) as response:
            return json.load(response)["info"]["version"]
    except (OSError, ValueError, KeyError):
        return None


COLLECTORS = {
    "npm": collect_npm_global,
    "npm-local": collect_npm_local,
    "uv": collect_uv,
    "pipx": collect_pipx,
    "uv-self": collect_uv_self,
    "skills": collect_skills,
    "github": collect_github,
}


def add_tools_update_parser(tools) -> None:
    update = tools.add_parser(
        "update",
        help="Report outdated user-wide tools; upgrade them with --apply.",
        description=(
            "Check npm globals (active Node), ~/.local npm (project and global prefix), uv tools, pipx, uv itself, "
            "GitHub-sourced skills in .skill-lock.json, and standalone GitHub-release "
            "binaries. Without --apply nothing changes. Major-version bumps are skipped "
            "unless --include-major, skills unless --include-skills, and pinned or local-source uv tools are held. "
            "GitHub-release binaries are reported only."
        ),
    )
    update.add_argument("--apply", action="store_true", help="Run the upgrade commands.")
    update.add_argument("--include-major", action="store_true", help="Also upgrade major-version bumps.")
    update.add_argument("--include-skills", action="store_true",
                        help="Also run skills update; it drops local edits in the skill folder.")
    update.add_argument("--source", help="Comma-separated sources: " + ", ".join(SOURCES) + ".")
    update.add_argument("--only", help="Comma-separated tool or skill names.")
    update.add_argument("--timeout", type=float, default=300.0, help="Per-command timeout in seconds.")
    update.set_defaults(func=cmd_tools_update)
