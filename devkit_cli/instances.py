"""What an instance materializes, and the provenance file that describes it.

Sections 4.3 (layout), 4.5 (path rendering), 4.6 (provenance), 4.8 (icon colour).
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from .common import HOME_TOKEN, REPO_ROOT, timestamp
from .errors import DevkitError

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
    "cursor": ["/usr/share/cursor/cursor", "/opt/cursor/cursor"],
}
CURSOR_CLI_CANDIDATES = ["/usr/share/cursor/bin/cursor", "/opt/cursor/bin/cursor"]


def paths_for(profile_name: str, vendor: str, home: Path) -> dict[str, Path]:
    """The layout in 4.3, anchored at a real home."""
    harness = home / ".agents-profiles" / profile_name
    return {
        "harness_dir": harness,
        "config_dir": harness / vendor,
        "data_dir": harness / f"{vendor}-data",
        "xdg_config_dir": harness / f"{vendor}-xdg",
        "user_data_dir": home / ".config" / f"{_vendor_app_name(vendor)}-{profile_name}",
        "wrapper": home / ".local" / "bin" / f"{vendor}-{profile_name}",
        "desktop": (home / ".local" / "share" / "applications"
                    / f"{_vendor_app_name(vendor)}-{profile_name}.desktop"),
        "icon": (home / ".local" / "share" / "icons" / "hicolor" / "512x512" / "apps"
                 / f"{_vendor_app_name(vendor).lower()}-{profile_name}.png"),
    }


def _vendor_app_name(vendor: str) -> str:
    return {"claude": "Claude", "codex": "Codex", "cursor": "Cursor"}.get(vendor, vendor)


def profile_hue(profile_name: str) -> float:
    """A stable hue per profile name, so two profiles never collide by accident (4.2)."""
    digest = hashlib.sha256(profile_name.encode("utf-8")).digest()
    return (digest[0] << 8 | digest[1]) / 65535.0


def profile_colors(profile: dict) -> tuple[str, str]:
    declared = profile.get("color") or {}
    if declared.get("light") and declared.get("dark"):
        return declared["light"], declared["dark"]
    hue = profile_hue(profile["name"])
    light = colorsys.hsv_to_rgb(hue, 0.75, 0.95)
    dark = colorsys.hsv_to_rgb(hue, 0.85, 0.45)
    to_hex = lambda rgb: "#" + "".join(f"{int(c * 255):02x}" for c in rgb)
    return to_hex(light), to_hex(dark)


def imagemagick() -> list[str] | None:
    """IM7 ships `magick` and may not ship `convert` (4.8, R-icon)."""
    for candidate in ("magick", "convert"):
        found = shutil.which(candidate)
        if found:
            return [found] if candidate == "magick" else [found]
    return None


def recolor_icon(source: Path, dest: Path, color: str) -> bool:
    binary = imagemagick()
    if binary is None or not source.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [*binary, str(source), "-fill", color, "-colorize", "60%", str(dest)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode == 0 and dest.is_file()


def first_existing(candidates: list[str]) -> str | None:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def render_tokens(profile: dict, vendor: str, home: Path) -> dict[str, str]:
    """Every ${PROFILE_*} a template may reference, resolved for this context (4.5)."""
    layout = paths_for(profile["name"], vendor, home)
    settings = profile.get("settings") or {}
    light, _dark = profile_colors(profile)
    tokens = {
        "PROFILE_NAME": profile["name"],
        "PROFILE_HARNESS_DIR": str(layout["harness_dir"]),
        "PROFILE_CONFIG_DIR": str(layout["config_dir"]),
        "PROFILE_DATA_DIR": str(layout["data_dir"]),
        "PROFILE_XDG_CONFIG_DIR": str(layout["xdg_config_dir"]),
        "PROFILE_USER_DATA_DIR": str(layout["user_data_dir"]),
        "PROFILE_ICON_NAME": layout["icon"].stem,
        "PROFILE_WM_CLASS": f"{_vendor_app_name(vendor)}-{profile['name']}",
        "PROFILE_WORKSPACE": str(home / "Workspace"),
        "PROFILE_COLOR": light,
        "PROFILE_CODEX_MODEL": settings.get("codex_model", "gpt-5.6-terra"),
        "PROFILE_CLAUDE_BIN": first_existing(VENDOR_GUI_CANDIDATES.get("claude", [])) or "claude",
        "PROFILE_CURSOR_GUI": first_existing(VENDOR_GUI_CANDIDATES.get("cursor", [])) or "cursor",
        "PROFILE_CURSOR_CLI": first_existing(CURSOR_CLI_CANDIDATES) or "cursor",
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
        "lineage": profile.get("lineage", [profile["name"]]),
        "vendor": vendor,
        "profile_schema_version": PROFILE_SCHEMA_VERSION,
        "lineage_id": kit.get("lineage_id"),
        "fork_id": kit.get("fork_id"),
        "upstream": kit.get("upstream"),
        "source_commit": source_commit,
        "installed_at": timestamp(),
        "config_dir": str(layout["config_dir"]),
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
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "unknown"
