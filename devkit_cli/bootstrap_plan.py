#!/usr/bin/env python3
"""Turn a profile's deps into a flat plan bootstrap.sh can consume.

bootstrap.sh is bash because it runs before python3 is guaranteed, but parsing a
manifest in bash is how you get a fragile installer. So the moment python3 does
exist, this emits tab-separated lines and bash just dispatches them.

Output, one record per line:
    pkg<TAB><package>            distro package for the requested manager
    npm<TAB><package>
    uv<TAB><package>
    binary<TAB><name>=<repo>
    nvm<TAB><version>
    thirdparty<TAB><package>     needs a third-party repo on RHEL derivatives (D13)

With --verify it instead checks that every `provides` binary is on PATH and
reports the rung each came from, exiting 1 if a required one is missing.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from devkit_cli import manifest  # noqa: E402
from devkit_cli.errors import DevkitError  # noqa: E402

# Packages that are not in the base repositories on RHEL derivatives. D13: never
# enable a third-party repo silently; prompt, and treat a decline as "skipped",
# never as a failure.
NEEDS_THIRD_PARTY_ON_RHEL = {"ffmpeg"}


def emit_plan(profile: dict, manager: str) -> None:
    for dep in manifest.dependencies(profile):
        installer = dep.get("installer")
        if installer == "nvm":
            print(f"nvm\t{dep.get('version', 'lts')}")
        elif installer == "npm":
            print(f"npm\t{dep['package']}")
        elif installer == "uv":
            print(f"uv\t{dep['package']}")
        elif installer == "binary":
            print(f"binary\t{dep['provides'][0]}={dep['repo']}")
        elif manager in dep:
            package = dep[manager]
            print(f"pkg\t{package}")
            if manager == "dnf" and package.lower() in NEEDS_THIRD_PARTY_ON_RHEL:
                print(f"thirdparty\t{package}")


def verify(profile: dict) -> int:
    required = manifest.provided_binaries(profile, include_optional=False)
    optional = [b for b in manifest.provided_binaries(profile) if b not in required]
    rungs = _rung_by_binary(profile)

    missing = []
    for binary in required:
        found = shutil.which(binary) or _alternate(binary)
        if found:
            print(f"  ok       {binary:22s} {rungs.get(binary, '?'):8s} {found}")
        else:
            print(f"  MISSING  {binary:22s} {rungs.get(binary, '?'):8s}")
            missing.append(binary)
    for binary in optional:
        found = shutil.which(binary) or _alternate(binary)
        print(f"  {'ok      ' if found else 'skipped '} {binary:22s} "
              f"{rungs.get(binary, '?'):8s} {found or '(optional)'}")

    if missing:
        print(f"\n{len(missing)} required tool(s) missing: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


def _alternate(binary: str) -> str | None:
    """ImageMagick 7 ships `magick` and may not ship `convert` (4.8)."""
    if binary in ("convert", "identify"):
        return shutil.which("magick")
    return None


def _rung_by_binary(profile: dict) -> dict[str, str]:
    rungs: dict[str, str] = {}
    for dep in manifest.dependencies(profile):
        rung = dep.get("installer") or "distro"
        for binary in dep.get("provides", []):
            rungs[binary] = rung
    return rungs


def main() -> int:
    parser = argparse.ArgumentParser(prog="bootstrap_plan.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default="core")
    parser.add_argument("--manager", default="apt", choices=["apt", "dnf", "pacman"])
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    try:
        profile = manifest.load(args.profile)
    except DevkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.verify:
        return verify(profile)
    emit_plan(profile, args.manager)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
