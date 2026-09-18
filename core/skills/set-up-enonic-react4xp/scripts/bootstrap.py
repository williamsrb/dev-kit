#!/usr/bin/env python3
"""Bootstrap an Enonic React4XP project.

Ported from bootstrap.sh. Behavior is intentionally identical:

  bootstrap.py "<project-display-name>" "<project-short-name>" [<starter-sha-commit>]

Steps:
  0. Refuse to run if an `xp/` folder already exists (repo must be clean).
  1. Ensure the Enonic CLI is installed (npm install -g @enonic/cli if missing).
  2. Create the Enonic React4XP project.
  3. Patch xp/gradle.properties and xp/package.json.
  4. Copy template files, drop the starter `hello` component, replace placeholders.
  5. Append project-specific ignores to xp/.gitignore.

The project root is resolved the same way as the shell version: four levels up
from this script's directory (…/<skill>/scripts -> project root when installed at
<project>/.claude/skills/<skill>/scripts).
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# scripts -> <skill> -> skills -> .claude -> project root
ROOT_DIR = SCRIPT_DIR.parents[3]
TEMPLATE_DIR = SCRIPT_DIR.parent / "template"

PLACEHOLDER_EXCLUDE_DIRS = {".git", "node_modules", ".gradle", "build", ".claude"}

GITIGNORE_BLOCK = """
# --- Project-specific ignores ---
src/main/resources/react4xp/components/prototype/*
!src/main/resources/react4xp/components/prototype/.gitkeep
src/main/resources/react4xp/assets/scss/*
!src/main/resources/react4xp/assets/scss/.gitkeep
src/main/resources/react4xp/assets/css/*
!src/main/resources/react4xp/assets/css/.gitkeep
src/main/resources/react4xp/assets/fonts/*
!src/main/resources/react4xp/assets/fonts/.gitkeep
src/main/resources/react4xp/utils/prototype/*
!src/main/resources/react4xp/utils/prototype/.gitkeep
src/main/resources/react4xp/shared/scss/*
!src/main/resources/react4xp/shared/scss/.gitkeep
src/main/resources/react4xp/shared/css/*
!src/main/resources/react4xp/shared/css/.gitkeep
src/main/resources/react4xp/shared/fonts/*
!src/main/resources/react4xp/shared/fonts/.gitkeep
"""


def info(msg: str) -> None:
    print(f"[INFO]  {msg}")


def error(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)


def fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    error(msg)
    raise SystemExit(1)


def have_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def check_clean_repo() -> None:
    if (ROOT_DIR / "xp").is_dir():
        error(f"The 'xp' folder already exists at {ROOT_DIR / 'xp'}")
        fail("Setup can only be executed in a clean repository.")


def ensure_enonic_cli() -> None:
    info("Checking Enonic CLI...")
    if have_command("enonic"):
        version = subprocess.run(
            ["enonic", "-v"], capture_output=True, text=True
        ).stdout.strip()
        info(f"Enonic CLI is already installed: {version}")
        return

    info("Enonic CLI not found. Installing...")
    subprocess.run(["npm", "install", "-g", "@enonic/cli"])
    if not have_command("enonic"):
        fail("Failed to install Enonic CLI")
    info("Enonic CLI installed successfully!")


def create_project(display_name: str, short_name: str, commit_version: str | None) -> None:
    info(f"Creating Enonic project: {display_name}")

    cmd = [
        "enonic", "project", "create",
        "-r", "starter-react4xp",
        "-d", "xp",
        "-v", "1.0.0",
        "-n", f"com.example.{short_name}",
        "--skip-start", "-f",
    ]
    if commit_version and commit_version != "default":
        cmd += ["-c", commit_version]
        info(f"Using commit version: {commit_version}")

    info(f"Running: {shlex.join(cmd)}")
    if subprocess.run(cmd).returncode != 0:
        fail("Failed to create Enonic project")

    info(f"Project '{display_name}' created successfully!")


def sub_in_file(path: Path, pattern: str, replacement: str, *, flags: int = 0) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(pattern, replacement, text, flags=flags), encoding="utf-8")


def update_gradle_and_package(display_name: str, short_name: str) -> None:
    gradle_props = ROOT_DIR / "xp" / "gradle.properties"
    if not gradle_props.is_file():
        fail(f"gradle.properties not found at {gradle_props}")

    info("Updating gradle.properties...")
    sub_in_file(gradle_props, r"^projectName[ \t]*=.*", f"projectName = {short_name}", flags=re.M)
    sub_in_file(gradle_props, r"^appDisplayName[ \t]*=.*", f"appDisplayName = {display_name}", flags=re.M)
    sub_in_file(gradle_props, r"^vendorName[ \t]*=.*", "vendorName = Example", flags=re.M)
    sub_in_file(gradle_props, r"^vendorUrl[ \t]*=.*", "vendorUrl = https://example.com", flags=re.M)
    info("gradle.properties updated successfully!")

    package_json = ROOT_DIR / "xp" / "package.json"
    if package_json.is_file():
        info("Updating check:types script in package.json...")
        sub_in_file(
            package_json,
            r'"check:types":.*',
            '"check:types": "concurrently -g -r --timings npm:check:types:* || exit 0",',
        )
        info("check:types script updated successfully!")
    else:
        info(f"package.json not found at {package_json}, skipping check:types update.")


def copy_template() -> None:
    info(f"Copying template files from {TEMPLATE_DIR} to {ROOT_DIR}")
    try:
        shutil.copytree(TEMPLATE_DIR, ROOT_DIR, dirs_exist_ok=True)
    except OSError as exc:
        fail(f"Failed to copy template files: {exc}")
    info("Template files copied successfully!")

    hello_dir = ROOT_DIR / "xp/src/main/resources/react4xp/components/hello"
    if hello_dir.is_dir():
        info("Removing hello component from starter...")
        shutil.rmtree(hello_dir)
        info("Hello component removed successfully!")
    else:
        info(f"Hello component not found at {hello_dir}, skipping.")


def read_xp_version() -> str:
    gradle_props = ROOT_DIR / "xp" / "gradle.properties"
    if not gradle_props.is_file():
        fail(f"gradle.properties not found at {gradle_props}")
    for line in gradle_props.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^xpVersion\s*=(.*)$", line)
        if m:
            value = re.sub(r"\s+", "", m.group(1))
            if value:
                info(f"Detected Enonic XP version: {value}")
                return value
    fail(f"Could not read xpVersion from {gradle_props}")


def read_node_version() -> str:
    nvmrc = ROOT_DIR / "xp" / ".nvmrc"
    if not nvmrc.is_file():
        fail(f".nvmrc not found at {nvmrc}")
    value = re.sub(r"\s+", "", nvmrc.read_text(encoding="utf-8"))
    if not value:
        fail(f"Could not read Node version from {nvmrc}")
    info(f"Detected Node version for XP: {value}")
    return value


def replace_placeholders(display_name: str, short_name: str, xp_version: str, node_version: str) -> None:
    info(
        "Replacing placeholders: "
        f"{{ENONIC_XP_VERSION}} -> {xp_version}, {{NODE_XP_VERSION}} -> {node_version}, "
        f"{{PROJECT_SHORT_NAME}} -> {short_name}, {{PROJECT_DISPLAY_NAME}} -> {display_name}"
    )
    replacements = {
        "{ENONIC_XP_VERSION}": xp_version,
        "{NODE_XP_VERSION}": node_version,
        "{PROJECT_SHORT_NAME}": short_name,
        "{PROJECT_DISPLAY_NAME}": display_name,
    }

    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        dirnames[:] = [d for d in dirnames if d not in PLACEHOLDER_EXCLUDE_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable — skip, same as the text-only shell filter
            if not any(token in text for token in replacements):
                continue
            for token, value in replacements.items():
                text = text.replace(token, value)
            path.write_text(text, encoding="utf-8")

    info("Placeholder replacement complete!")


def append_gitignore() -> None:
    gitignore = ROOT_DIR / "xp" / ".gitignore"
    info(f"Appending project-specific entries to {gitignore}...")
    try:
        with gitignore.open("a", encoding="utf-8") as fh:
            fh.write(GITIGNORE_BLOCK)
    except OSError:
        fail(f"Failed to update {gitignore}")
    info(".gitignore updated successfully!")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap an Enonic React4XP project.")
    parser.add_argument("display_name", help="Project display name")
    parser.add_argument("short_name", help="Project short name (used in com.example.<short>)")
    parser.add_argument("commit_version", nargs="?", default=None, help="Optional starter SHA commit")
    args = parser.parse_args()

    info(f"Working directory: {ROOT_DIR}")
    if not ROOT_DIR.is_dir():
        fail(f"Failed to resolve root dir: {ROOT_DIR}")
    os.chdir(ROOT_DIR)

    check_clean_repo()
    ensure_enonic_cli()
    create_project(args.display_name, args.short_name, args.commit_version)
    update_gradle_and_package(args.display_name, args.short_name)
    copy_template()
    xp_version = read_xp_version()
    node_version = read_node_version()
    replace_placeholders(args.display_name, args.short_name, xp_version, node_version)
    append_gitignore()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
