"""What an instance materializes, and the provenance file that describes it.

Layout, path rendering, provenance, and icon colour.
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from . import appfork
from .common import FILE_MODE, REPO_ROOT, ensure_dir, timestamp
from .errors import DevkitError

# Unprefixed names the GUIs look up on PATH. Public wrappers stay
# ~/.local/bin/<vendor>-<profile> so they never collide with stock.
# Harness tools in profile bin/ wrap core/bin/<name> and pin AGENTS_HOME;
# PATH alone is not enough, because those tools read AGENTS_HOME.

PROFILE_SKIP_DIRS = ("core", "bin", "agents", "hooks")
PROFILE_PATH_TOOLS = ("agentctl",)
# Credential files that may be shared across profiles. Browser storage-state
# JSON in .auth stays profile-local so sessions do not leak.
SHARED_AUTH_FILES = ("jira-api-token.yaml", "nvidia-api-key.yaml")

# Instance names are one filesystem path segment. Nested names would break
# uniqueness and the ~/.agents-profiles/<name>/ layout.

PROVENANCE_NAME = ".devkit-profile.json"
PROFILE_SCHEMA_VERSION = 1

VENDOR_BINARIES = {
    "claude": ["claude"],
    "codex": ["codex"],
    "cursor": ["cursor-agent"],
}

# Where each vendor's GUI lives when it is installed. Probed, never assumed:
# an absent entry downgrades the instance to CLI-only rather than writing a
# launcher that points at nothing.
VENDOR_GUI_CANDIDATES = {
    "claude": ["/usr/bin/claude-desktop", "/opt/Claude/claude-desktop",
               "/usr/lib/claude-desktop/claude-desktop"],
    "codex": ["/usr/bin/chatgpt", "/usr/lib/chatgpt/ChatGPT"],
    "cursor": ["/usr/share/cursor/cursor", "/opt/cursor/cursor"],
}
CURSOR_CLI_CANDIDATES = ["/usr/share/cursor/bin/cursor", "/opt/cursor/bin/cursor"]
VENDOR_CLI_CANDIDATES = {
    "claude": ["/usr/bin/claude", "/usr/local/bin/claude"],
    "codex": ["/usr/bin/codex", "/usr/local/bin/codex"],
    "cursor": ["/usr/bin/cursor-agent", "/usr/local/bin/cursor-agent"],
}


def validate_instance_name(name: str) -> None:
    """Refuse names that are not a single path segment."""
    if not name or name in (".", "..") or "/" in name or "\0" in name:
        raise DevkitError(
            f"profile name {name!r} is not a single path segment",
            "use a name without slashes, for example 'dummy'")


def instance_type(provenance: dict | None, instance_name: str) -> str:
    """Type stored in provenance, or name-equals-type for older installs."""
    if provenance and provenance.get("type"):
        return str(provenance["type"])
    return instance_name


def bind_instance(profile: dict, instance_name: str, type_name: str) -> dict:
    """Overlay the instance name on a type manifest without copying the JSON."""
    bound = dict(profile)
    bound["name"] = instance_name
    bound["type"] = type_name
    return bound


def discover_instances(home: Path) -> list[tuple[str, str, Path, dict]]:
    """Installed instances on disk, not kit JSON stems.

    Returns (instance_name, vendor, config_dir, provenance) sorted by name then vendor.
    """
    root = home / ".agents-profiles"
    found: list[tuple[str, str, Path, dict]] = []
    if not root.is_dir():
        return found
    for profile_dir in sorted(root.iterdir()):
        if not profile_dir.is_dir() or profile_dir.name.startswith("."):
            continue
        for child in sorted(profile_dir.iterdir()):
            if not child.is_dir() or child.name in PROFILE_SKIP_DIRS:
                continue
            prov = read_provenance(child)
            if not prov:
                continue
            vendor = prov.get("vendor") or child.name
            found.append((profile_dir.name, vendor, child, prov))
    return found


def auth_paths(home: Path) -> dict[str, Path]:
    state = home / ".local" / "state" / "devkit"
    return {
        "launch": home / ".local" / "bin" / "devkit-auth-launch",
        "dispatch": home / ".local" / "bin" / "devkit-auth-dispatch",
        "applications": home / ".local" / "share" / "applications",
        "state": state / "auth-handlers.json",
        "pending": state / "pending-auth.json",
    }


def paths_for(profile_name: str, vendor: str, home: Path) -> dict[str, Path]:
    """The instance layout, anchored at a real home."""
    harness = home / ".agents-profiles" / profile_name
    return {
        "harness_dir": harness,
        "config_dir": harness / vendor,
        "data_dir": harness / f"{vendor}-data",
        "xdg_config_dir": harness / f"{vendor}-xdg",
        "user_data_dir": home / ".config" / f"{_vendor_app_name(vendor)}-{profile_name}",
        "bin_dir": harness / "bin",
        "agents_dir": harness / "agents",
        "wrapper": home / ".local" / "bin" / f"{vendor}-{profile_name}",
        "desktop": (home / ".local" / "share" / "applications"
                    / f"{_vendor_app_name(vendor)}-{profile_name}.desktop"),
        "icon": (home / ".local" / "share" / "icons" / "hicolor" / "512x512" / "apps"
                 / f"{_vendor_app_name(vendor).lower()}-{profile_name}.png"),
    }


def _vendor_app_name(vendor: str) -> str:
    return {"claude": "Claude", "codex": "Codex", "cursor": "Cursor"}.get(vendor, vendor)


def profile_hue(profile_name: str) -> float:
    """A stable hue per profile name, so two profiles never collide by accident."""
    digest = hashlib.sha256(profile_name.encode("utf-8")).digest()
    return (digest[0] << 8 | digest[1]) / 65535.0


def profile_colors(profile: dict) -> tuple[str, str]:
    declared = profile.get("color") or {}
    if declared.get("light") and declared.get("dark"):
        return declared["light"], declared["dark"]
    hue = profile_hue(profile["name"])
    light = colorsys.hsv_to_rgb(hue, 0.75, 0.95)
    dark = colorsys.hsv_to_rgb(hue, 0.85, 0.45)
    def to_hex(rgb) -> str:
        return "#" + "".join(f"{int(c * 255):02x}" for c in rgb)
    return to_hex(light), to_hex(dark)


def imagemagick() -> list[str] | None:
    """ImageMagick 7 ships `magick` and may not ship `convert`."""
    for candidate in ("magick", "convert"):
        found = shutil.which(candidate)
        if found:
            return [found]
    return None


def recolor_icon(source: Path, dest: Path, color: str) -> bool:
    binary = imagemagick()
    if binary is None or not source.is_file():
        return False
    ensure_dir(dest.parent)
    command = [*binary, str(source), "-fill", color, "-colorize", "60%", str(dest)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not dest.is_file():
        return False
    dest.chmod(FILE_MODE)
    return True


def first_existing(candidates: list[str]) -> str | None:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _is_devkit_wrapper(path: Path) -> bool:
    """Stock vendor shims are usually symlinks; our wrappers are small scripts."""
    if path.is_symlink():
        return False
    try:
        head = path.read_bytes()[:400]
    except OSError:
        return False
    return b"Generated by devkit" in head


def resolve_stock_cli(name: str, extra: list[str] | None = None) -> str:
    """Absolute path of the vendor CLI. Do not follow versioned symlink targets.

    `~/.local/bin/claude` is the stable entry; resolving it would pin a
    `versions/<build>` path that dies on the next vendor update.
    """
    ordered: list[str] = []
    found = shutil.which(name)
    if found:
        ordered.append(found)
    ordered.extend(extra or [])
    for candidate in ordered:
        path = Path(candidate)
        if path.name != name or not path.exists() or _is_devkit_wrapper(path):
            continue
        return str(path)
    return name


def render_tokens(profile: dict, vendor: str, home: Path) -> dict[str, str]:
    """Every ${PROFILE_*} a template may reference, resolved for this context."""
    layout = paths_for(profile["name"], vendor, home)
    auth = auth_paths(home)
    settings = profile.get("settings") or {}
    light, _dark = profile_colors(profile)
    tokens = {
        "PROFILE_NAME": profile["name"],
        "PROFILE_TYPE": profile.get("type") or profile["name"],
        "PROFILE_HARNESS_DIR": str(layout["harness_dir"]),
        "PROFILE_BIN_DIR": str(layout["bin_dir"]),
        "PROFILE_AGENTS_HOME": str(layout["agents_dir"]),
        "PROFILE_CONFIG_DIR": str(layout["config_dir"]),
        "PROFILE_DATA_DIR": str(layout["data_dir"]),
        "PROFILE_XDG_CONFIG_DIR": str(layout["xdg_config_dir"]),
        "PROFILE_USER_DATA_DIR": str(layout["user_data_dir"]),
        "PROFILE_ICON_NAME": layout["icon"].stem,
        "PROFILE_WM_CLASS": appfork.wm_class(vendor, profile["name"]),
        "PROFILE_GUI_BIN": str(appfork.gui_bin(vendor, profile["name"])),
        "PROFILE_WORKSPACE": str(home / "Workspace"),
        "PROFILE_COLOR": light,
        "PROFILE_CODEX_MODEL": settings.get("codex_model", "gpt-5.6-terra"),
        "PROFILE_CLAUDE_BIN": first_existing(VENDOR_GUI_CANDIDATES.get("claude", [])) or "claude",
        "PROFILE_CHATGPT_BIN": first_existing(VENDOR_GUI_CANDIDATES.get("codex", [])) or "chatgpt",
        "PROFILE_CURSOR_GUI": first_existing(VENDOR_GUI_CANDIDATES.get("cursor", [])) or "cursor",
        "PROFILE_CURSOR_CLI": first_existing(CURSOR_CLI_CANDIDATES) or "cursor",
        "PROFILE_CLAUDE_CLI": resolve_stock_cli("claude", VENDOR_CLI_CANDIDATES["claude"]),
        "PROFILE_CODEX_CLI": resolve_stock_cli("codex", VENDOR_CLI_CANDIDATES["codex"]),
        "PROFILE_CURSOR_AGENT": resolve_stock_cli(
            "cursor-agent", VENDOR_CLI_CANDIDATES["cursor"]),
        "PROFILE_KIT_ROOT": str(REPO_ROOT),
        "PROFILE_AUTH_LAUNCH": str(auth["launch"]),
        "PROFILE_AUTH_DISPATCH": str(auth["dispatch"]),
        "PROFILE_AUTH_SCHEME": "claude",
        "HOME": str(home),
    }
    return tokens


def render(text: str, tokens: dict[str, str]) -> str:
    """Substitute ${TOKEN}. ${HOME} is handled here too, so kit source never ships a real home."""
    for key, value in sorted(tokens.items(), key=lambda kv: -len(kv[0])):
        text = text.replace("${" + key + "}", value)
    return text


def provenance(profile: dict, vendor: str, home: Path, kit: dict,
               source_commit: str, history: list | None = None) -> dict:
    layout = paths_for(profile["name"], vendor, home)
    return {
        "_comment": "Written by devkit. Describes the tree beside it; never edit by hand.",
        "profile": profile["name"],
        "type": profile.get("type") or profile["name"],
        "lineage": profile.get("lineage", [profile["name"]]),
        "vendor": vendor,
        "profile_schema_version": PROFILE_SCHEMA_VERSION,
        "lineage_id": kit.get("lineage_id"),
        "fork_id": kit.get("fork_id"),
        "upstream": kit.get("upstream"),
        "source_commit": source_commit,
        "installed_at": timestamp(),
        "config_dir": str(layout["config_dir"]),
        "color": profile_colors(profile)[0],
        "appfork": {
            "lib": str(appfork.fork_dir(vendor, profile["name"])),
            "desktopName": appfork.desktop_name(vendor, profile["name"]),
            "wmClass": appfork.wm_class(vendor, profile["name"]),
        },
        "history": history or [],
    }


def read_provenance(config_dir: Path) -> dict | None:
    path = config_dir / PROVENANCE_NAME
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        raise DevkitError(f"{path} is not valid JSON",
                          "delete it and re-run 'devkit profile sync'") from None


def kit_commit() -> str:
    """The kit's HEAD, or "unknown" when it cannot be read.

    check=False swallows a non-zero exit, not a missing binary, and git is a
    dependency bootstrap.sh installs rather than one devkit can assume.
    """
    try:
        result = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 else "unknown"
