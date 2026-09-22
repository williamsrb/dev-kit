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
    thirdparty<TAB><package><TAB><repo>   needs a third-party repo here
    unavailable<TAB><binary>     no package and no fallback on this manager

With --verify it instead checks that every `provides` binary is on PATH and
reports the rung each came from, exiting 1 if a required one is missing.
A declined third-party repo is a skip for the binaries that only live there,
never a hard failure (rocky CI job).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from devkit_cli import manifest
from devkit_cli.errors import DevkitError

# Which repository a package needs is declared per dependency (`needs_repo`),
# measured rather than guessed. Never enable a third-party repo silently:
# prompt, and treat a decline as a fall-through to the dep's `fallback`, or as
# "skipped" — never as a failure.


def _emit_installer(spec: dict, provides: list[str]) -> None:
    installer = spec.get("installer")
    if installer == "nvm":
        print(f"nvm\t{spec.get('version', 'lts')}")
    elif installer == "npm":
        print(f"npm\t{spec['package']}")
    elif installer == "uv":
        print(f"uv\t{spec['package']}")
    elif installer == "binary":
        print(f"binary\t{spec.get('binary', provides[0])}={spec['repo']}")


def emit_plan(profile: dict, manager: str, family: str) -> None:
    for dep in manifest.dependencies(profile):
        provides = dep.get("provides", [])
        if dep.get("installer"):
            _emit_installer(dep, provides)
            continue

        package = dep.get(manager)
        if package is None:
            # This manager has no package for it; the dep says what to do instead.
            fallback = dep.get("fallback")
            if fallback:
                _emit_installer(fallback, provides)
            else:
                print(f"unavailable\t{provides[0] if provides else '?'}")
            continue

        print(f"pkg\t{package}")
        repo = (dep.get("needs_repo") or {}).get(family)
        if repo:
            print(f"thirdparty\t{package}\t{repo}")


def detect_family() -> str | None:
    """Map /etc/os-release to the needs_repo family key, or None."""
    path = Path("/etc/os-release")
    if not path.is_file():
        return None
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, raw = line.split("=", 1)
        values[key] = raw.strip().strip('"')
    distro_id = values.get("ID", "").lower()
    identity = f"{distro_id} {values.get('ID_LIKE', '')}".lower()
    if distro_id == "fedora":
        return "fedora"
    if "rhel" in identity or "centos" in identity or "rocky" in identity \
            or "almalinux" in identity:
        return "rhel"
    if "debian" in identity or "ubuntu" in identity:
        return "debian"
    if "arch" in identity:
        return "arch"
    return None


def third_party_binaries(profile: dict, manager: str, family: str) -> set[str]:
    """Binaries whose only distro package on this family needs a third-party repo."""
    claimed: set[str] = set()
    for dep in manifest.dependencies(profile):
        if dep.get("installer"):
            continue
        package = dep.get(manager)
        if not package:
            continue
        if not (dep.get("needs_repo") or {}).get(family):
            continue
        claimed.update(dep.get("provides", []))
    return claimed


def verify(profile: dict, *, manager: str = "apt", family: str | None = None,
           third_party_declined: bool = False) -> int:
    required = manifest.provided_binaries(profile, include_optional=False)
    optional = [b for b in manifest.provided_binaries(profile) if b not in required]
    rungs = _rung_by_binary(profile)
    family = family or detect_family()
    skippable = (
        third_party_binaries(profile, manager, family)
        if third_party_declined and family
        else set()
    )

    missing = []
    for binary in required:
        found = shutil.which(binary) or _alternate(binary)
        if found:
            print(f"  ok       {binary:22s} {rungs.get(binary, '?'):8s} {found}")
        elif binary in skippable:
            print(f"  skipped  {binary:22s} {rungs.get(binary, '?'):8s} "
                  f"(third-party declined)")
        else:
            print(f"  MISSING  {binary:22s} {rungs.get(binary, '?'):8s}")
            missing.append(binary)
    for binary in optional:
        found = shutil.which(binary) or _alternate(binary)
        print(f"  {'ok      ' if found else 'skipped '} {binary:22s} "
              f"{rungs.get(binary, '?'):8s} {found or '(optional)'}")

    if missing:
        print(f"\n{len(missing)} required tool(s) missing: {', '.join(missing)}",
              file=sys.stderr)
        return 1
    return 0


def _alternate(binary: str) -> str | None:
    """ImageMagick 7 ships `magick` and may not ship `convert`."""
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


def default_manager(family: str | None) -> str:
    return {"debian": "apt", "rhel": "dnf", "fedora": "dnf",
            "arch": "pacman"}.get(family or "", "apt")


def cmd_deps(args) -> int:
    """`devkit deps` — is every binary a profile declares on PATH?

    The same check as `bootstrap_plan.py --verify`, on the CLI the docs use
    everywhere else. The plan-emitting path stays a module entry point, because
    bootstrap.sh calls it before `devkit` is guaranteed to work.
    """
    family = args.family or detect_family()
    return verify(
        manifest.load(args.profile),
        manager=args.manager or default_manager(family),
        family=family,
        third_party_declined=args.third_party_declined,
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="bootstrap_plan.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default="core")
    parser.add_argument("--manager", default=None, choices=["apt", "dnf", "pacman"],
                        help="Package manager. Default: apt for plan emit; "
                             "with --verify, derived from --family / os-release.")
    parser.add_argument("--family", default=None,
                        help="Distribution family (debian, rhel, fedora, arch). "
                             "needs_repo keys on this, not on the manager. "
                             "With --verify, defaults to /etc/os-release.")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--third-party-declined", action="store_true",
                        help="With --verify: binaries that only live in a "
                             "needs_repo package are skipped, not missing.")
    args = parser.parse_args()

    try:
        profile = manifest.load(args.profile)
    except DevkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.verify:
        family = args.family or detect_family()
        return verify(
            profile,
            manager=args.manager or default_manager(family),
            family=family,
            third_party_declined=args.third_party_declined,
        )
    emit_plan(profile, args.manager or "apt", args.family or args.manager or "apt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
