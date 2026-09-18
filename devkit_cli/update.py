"""The update protocol: check, fetch, apply (section 4.7, D8, D9, D10).

One direction of travel. `check` never writes and is the only command safe to
run unattended. `fetch` is the only one that touches the network. `apply` is
offline and per-instance, installs from the staged payload rather than from the
local checkout, and restores from backup if it fails mid-write.

The refusal messages name the fix, because a refusal the user cannot act on is
just an outage.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import instances, manifest, privilege
from .common import Plan, REPO_ROOT, back_up, relative_to_home, timestamp, write_json
from .errors import DevkitError

STAGING_ROOT = Path.home() / ".cache" / "devkit" / "staged"


def _kit() -> dict:
    from .profiles import _kit_metadata
    return _kit_metadata()


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd or REPO_ROOT),
                          capture_output=True, text=True, check=False)


def _is_shallow(work: Path) -> bool:
    return _git("rev-parse", "--is-shallow-repository", cwd=work).stdout.strip() == "true"


def _installed_instances(profile_filter: str | None) -> list[tuple[str, str, Path, dict]]:
    home = Path.home()
    found = []
    for name in manifest.available():
        if profile_filter and name != profile_filter:
            continue
        profile = manifest.load(name)
        for instance in profile.get("instances", []):
            layout = instances.paths_for(name, instance["vendor"], home)
            prov = instances.read_provenance(layout["config_dir"])
            if prov:
                found.append((name, instance["vendor"], layout["config_dir"], prov))
    return found


# ------------------------------------------------------------------ check

def cmd_check(args) -> int:
    """Reports; never fails the machine, never writes to an instance."""
    kit = _kit()
    local_head = instances.kit_commit()
    remote_head = None
    upstream = kit.get("upstream")

    if upstream:
        result = _git("ls-remote", upstream, "HEAD")
        if result.returncode == 0 and result.stdout.split():
            remote_head = result.stdout.split()[0]
        else:
            print(f"note: could not reach {upstream}; reporting local state only")

    found = _installed_instances(getattr(args, "profile", None))
    if not found:
        print("no installed instances found.")
        return 0

    print(f"kit {kit.get('fork_id', '?')} at {local_head[:8]}"
          + (f", remote at {remote_head[:8]}" if remote_head else ""))
    print(f"{'INSTANCE':28s} {'INSTALLED':10s} {'SCHEMA':8s} STATE")

    for name, vendor, _config_dir, prov in found:
        blockers = []
        if prov.get("lineage_id") != kit.get("lineage_id"):
            blockers.append("foreign lineage")
        elif prov.get("fork_id") != kit.get("fork_id"):
            blockers.append(f"fork {prov.get('fork_id')} != {kit.get('fork_id')}")
        if prov.get("profile_schema_version", 0) > instances.PROFILE_SCHEMA_VERSION:
            blockers.append("installer too old")
        if not blockers:
            blockers.append("up to date" if prov.get("source_commit") == local_head
                            else "update available")
        print(f"{name + '/' + vendor:28s} {str(prov.get('source_commit'))[:8]:10s} "
              f"{prov.get('profile_schema_version', '?'):<8} {', '.join(blockers)}")
    return 0


# ------------------------------------------------------------------ fetch

def cmd_fetch(args) -> int:
    """Verifies what it downloaded is the commit it asked for, and resolves
    lineage_id from the fetched repository. A lineage mismatch fails here, so a
    foreign kit is rejected before anything is staged."""
    kit = _kit()
    upstream = kit.get("upstream")
    if not upstream:
        raise DevkitError("this kit has no upstream; it is the origin fork",
                          "set 'upstream' in devkit.yaml, or fetch from a fork that has one")
    if shutil.which("git") is None:
        raise DevkitError("git is not installed", "run bootstrap.sh first")

    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    work = STAGING_ROOT / f"fetch-{timestamp()}"
    result = _git("clone", "--quiet", upstream, str(work))
    if result.returncode != 0:
        raise DevkitError(f"could not clone {upstream}: {result.stderr.strip()}",
                          "check the remote and your credentials")

    head = _git("rev-parse", args.ref, cwd=work)
    if head.returncode != 0:
        shutil.rmtree(work, ignore_errors=True)
        raise DevkitError(f"{args.ref} does not exist in {upstream}")
    commit = head.stdout.strip()

    def resolve_lineage() -> str | None:
        roots = _git("rev-list", "--max-parents=0", commit, cwd=work).stdout.split()
        return roots[-1] if roots else None

    fetched_lineage = resolve_lineage()

    # A shallow clone's oldest commit is a graft point, not the lineage root, so
    # trusting it compares this fork against itself and calls it foreign.
    # Unshallow first. When the upstream is itself shallow that cannot succeed,
    # and an unresolved lineage is the honest refusal — "fetch a full clone" is
    # something the user can act on; "there is no escape hatch" is not.
    if fetched_lineage is None or _is_shallow(work):
        _git("fetch", "--unshallow", cwd=work)
        fetched_lineage = None if _is_shallow(work) else resolve_lineage()
    if fetched_lineage is None:
        shutil.rmtree(work, ignore_errors=True)
        raise DevkitError("could not resolve the fetched repository's lineage",
                          "fetch a full clone; devkit will not accept an unknown lineage")

    if fetched_lineage != kit.get("lineage_id"):
        shutil.rmtree(work, ignore_errors=True)
        raise DevkitError(
            f"lineage mismatch: fetched {fetched_lineage[:8]}, this kit is "
            f"{str(kit.get('lineage_id'))[:8]}",
            "this is a different kit, not a fork of yours; there is no escape hatch")

    staged = STAGING_ROOT / commit
    if staged.exists():
        shutil.rmtree(staged)
    shutil.move(str(work), str(staged))
    shutil.rmtree(staged / ".git", ignore_errors=True)
    write_json(staged / ".devkit-staged.json",
               {"commit": commit, "lineage_id": fetched_lineage,
                "upstream": upstream, "fetched_at": timestamp()})
    print(f"staged {commit[:8]} at {relative_to_home(staged)}")
    print("next:  devkit update apply --apply")
    return 0


# ------------------------------------------------------------------ apply

def _latest_staged() -> tuple[Path, dict] | None:
    if not STAGING_ROOT.is_dir():
        return None
    candidates = []
    for directory in STAGING_ROOT.iterdir():
        marker = directory / ".devkit-staged.json"
        if marker.is_file():
            try:
                candidates.append((directory, json.loads(marker.read_text())))
            except ValueError:
                continue
    if not candidates:
        return None
    return max(candidates, key=lambda c: c[1].get("fetched_at", ""))


def cmd_apply(args) -> int:
    privilege.refuse_root(getattr(args, "user", None))
    staged = _latest_staged()
    if staged is None:
        raise DevkitError("nothing is staged", "run 'devkit update fetch' first")
    payload, marker = staged
    kit = _kit()

    found = _installed_instances(getattr(args, "profile", None))
    if not found:
        raise DevkitError("no installed instances to update",
                          "run 'devkit profile create <name> --apply' first")

    plan = Plan(args.apply)
    for name, vendor, config_dir, prov in found:
        label = f"{name}/{vendor}"

        if prov.get("lineage_id") != marker.get("lineage_id"):
            raise DevkitError(
                f"{label}: foreign lineage — instance {str(prov.get('lineage_id'))[:8]}, "
                f"staged {str(marker.get('lineage_id'))[:8]}",
                "none; a foreign lineage has no migration path")
        if prov.get("fork_id") != kit.get("fork_id"):
            raise DevkitError(
                f"{label}: fork mismatch — instance {prov.get('fork_id')}, "
                f"kit {kit.get('fork_id')}",
                f"devkit profile migrate {name} --to-fork {kit.get('fork_id')}")
        if prov.get("profile_schema_version", 0) > instances.PROFILE_SCHEMA_VERSION:
            raise DevkitError(
                f"{label}: installed schema {prov['profile_schema_version']} is newer "
                f"than this installer's {instances.PROFILE_SCHEMA_VERSION}",
                "update this kit first; there is no override for a newer schema")

        plan.record(f"update {label} to {marker['commit'][:8]}")
        if not args.apply:
            continue

        # The provenance file is never updated before the tree it describes, so
        # a failure leaves it describing the pre-apply state. BaseException, not
        # Exception: a Ctrl-C mid-write has to restore too, and KeyboardInterrupt
        # is not an Exception.
        backup = back_up(config_dir)
        try:
            from .profiles import materialize
            inner = Plan(apply=True)
            materialize(manifest.load(name, kit_root=payload), [vendor], Path.home(),
                        inner, force=True, kit_root=payload,
                        source_commit=marker["commit"])
            updated = instances.read_provenance(config_dir) or prov
            updated["history"] = [*prov.get("history", []),
                                  {"from": prov.get("source_commit"),
                                   "to": marker["commit"], "at": timestamp()}]
            write_json(config_dir / instances.PROVENANCE_NAME, updated)
            shutil.rmtree(backup, ignore_errors=True)
        except BaseException:
            shutil.rmtree(config_dir, ignore_errors=True)
            shutil.move(str(backup), str(config_dir))
            raise DevkitError(f"{label}: apply failed and was rolled back from backup",
                              "the instance and its provenance describe the pre-apply state")
    return plan.report("update")


# ------------------------------------------------------------------ origin

def cmd_origin_show(args) -> int:
    kit = _kit()
    print(json.dumps({
        "lineage_id": kit.get("lineage_id"),
        "fork_id": kit.get("fork_id"),
        "name": kit.get("name"),
        "upstream": kit.get("upstream"),
        "local_commit": instances.kit_commit(),
    }, indent=2))
    return 0


def cmd_origin_adopt(args) -> int:
    privilege.refuse_root(getattr(args, "user", None))
    kit = _kit()
    plan = Plan(args.apply)
    for name, vendor, config_dir, prov in _installed_instances(None):
        if prov.get("lineage_id") != kit.get("lineage_id"):
            raise DevkitError(f"{name}/{vendor}: foreign lineage; adopt cannot cross lineages",
                              "none")
        plan.record(f"repoint {name}/{vendor} to fork {args.fork_id}")
        if args.apply:
            prov["fork_id"] = args.fork_id
            prov["upstream"] = args.upstream
            write_json(config_dir / instances.PROVENANCE_NAME, prov)
    return plan.report("origin adopt")


def migrate_profile(args) -> int:
    privilege.refuse_root(getattr(args, "user", None))
    kit = _kit()
    plan = Plan(args.apply)
    home = Path.home()
    profile = manifest.load(args.name)
    for instance in profile.get("instances", []):
        layout = instances.paths_for(args.name, instance["vendor"], home)
        prov = instances.read_provenance(layout["config_dir"])
        if not prov:
            continue
        if prov.get("lineage_id") != kit.get("lineage_id"):
            raise DevkitError(
                f"{args.name}/{instance['vendor']}: foreign lineage",
                "none; migrate moves between forks of one lineage, not between kits")
        plan.record(f"migrate {args.name}/{instance['vendor']} "
                    f"{prov.get('fork_id')} -> {args.to_fork}")
        if args.apply:
            prov["fork_id"] = args.to_fork
            prov["history"] = [*prov.get("history", []),
                               {"migrated_to_fork": args.to_fork, "at": timestamp()}]
            write_json(layout["config_dir"] / instances.PROVENANCE_NAME, prov)
    return plan.report(f"migrate {args.name}")
