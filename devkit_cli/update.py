"""The update protocol: check, fetch, apply.

One direction of travel. `check` never writes and is the only command safe to
run unattended. `fetch` stages a payload from a source: a local directory or a
git URL (`--from`, else the source the installed kit recorded, else `upstream`).
`apply` is offline, installs the staged payload as a new release in the kit
home, flips `current`, re-materializes each instance, and puts the previous
release and every instance back if anything fails.

The refusal messages name the fix, because a refusal the user cannot act on is
just an outage.
"""

from __future__ import annotations

import datetime as _dt
import json
import shutil
import sys
import tempfile
from pathlib import Path

from . import instances, kithome, kitsource, manifest, migrations, privilege
from .common import REPO_ROOT, Plan, back_up, relative_to_home, timestamp, write_json
from .errors import DevkitError

STAGING_ROOT = Path.home() / ".cache" / "devkit" / "staged"

# Declared by a tree that can install itself: it has the hidden `update stage-tree`,
# `update inspect-tree` and `update apply --staged`. A parent reads this constant
# from the incoming tree's source before handing off (kitsource.incoming_support).
HANDOFF_PROTOCOL = 1


def _kit() -> dict:
    from .profiles import _kit_metadata
    return _kit_metadata()


def _git(*args: str, cwd: Path | None = None):
    return kithome._git(*args, cwd=cwd or REPO_ROOT)


def _stamp() -> str:
    """Sortable, finer than a second: two fetches in one second must order."""
    return _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _installed_instances(profile_filter: str | None) -> list[tuple[str, str, Path, dict]]:
    found = instances.discover_instances(Path.home())
    if not profile_filter:
        return found
    return [row for row in found if row[0] == profile_filter]


def _installed_root() -> Path:
    """The installed kit when there is one, else the tree that is running."""
    return kithome.current_release(Path.home()) or REPO_ROOT


def _bare(commit: str | None) -> str:
    return str(commit or "").removesuffix("-dirty")


# ------------------------------------------------------------------ check

def _source_state(source: str, ref: str, kit: dict) -> dict:
    """What the source offers, without staging it. Raises nothing on a bad source."""
    if kitsource.is_git_url(source):
        result = _git("ls-remote", source, ref)
        if result.returncode == 0 and result.stdout.split():
            return {"commit": result.stdout.split()[0]}
        return {"error": f"could not reach {source}"}
    try:
        found = _directory_state(Path(source).expanduser(), kit)
    except DevkitError as exc:
        return {"error": str(exc)}
    found["foreign"] = found["lineage_id"] != kit.get("lineage_id")
    return found


def _directory_state(path: Path, kit: dict) -> dict:
    """A directory source's state, its payload digest computed by its own code
    when it can: the installed code's file list would hide an entry it lacks."""
    found = kitsource.inspect_directory(path, kit, payload=False)
    result = kithome.run_as_incoming(
        path, ["update", "inspect-tree", "--tree", str(path)],
        supported=kitsource.incoming_support(path), what="checking")
    if result is None:
        found["payload_digest"] = kitsource.tree_payload(path)["payload_digest"]
        return found
    lines = result.stdout.splitlines()
    if result.returncode != 0 or not lines:
        raise DevkitError(f"the source tree could not describe itself ({path})")
    found["payload_digest"] = json.loads(lines[-1])["payload_digest"]
    return found


def cmd_check(args) -> int:
    """Reports; never fails the machine, never writes to an instance."""
    kit = _kit()
    home = Path.home()
    root = _installed_root()
    local_head = instances.kit_commit(root)
    stamp = kithome.read_stamp(root) or {}

    state = None
    try:
        source = kitsource.resolve_source(getattr(args, "from_source", None), home)
    except DevkitError as exc:
        source = None
        if getattr(args, "from_source", None) is None:
            print(f"note: no update source; reporting local state only ({exc.args[0]})")
    if source:
        state = _source_state(source, getattr(args, "ref", None) or "HEAD", kit)
        if "error" in state:
            print(f"note: {state['error']}; reporting local state only")
            state = None

    found = _installed_instances(getattr(args, "profile", None))
    if not found:
        print("no installed instances found.")
        return 0

    line = f"kit {kit.get('fork_id', '?')} at {local_head[:8]}"
    if stamp:
        line += f" (release {stamp.get('release_id', '?')})"
    if state:
        head = _bare(state.get("commit"))[:8] or "?"
        line += f", {source} at {head}" + (" (dirty)" if state.get("dirty") else "")
        offered = _bare(state.get("commit"))
        same_commit = offered != "unknown" and offered == _bare(
            stamp.get("commit") or local_head)
        if "payload_digest" in state:
            newer = state["payload_digest"] != stamp.get("payload_digest")
        else:
            newer = not same_commit
        if not newer:
            line += ": up to date"
        elif "payload_digest" in state and same_commit and state.get("dirty"):
            line += ": same commit, uncommitted changes in the source"
        elif "payload_digest" in state and same_commit:
            line += (": same commit, payload differs (release built by an older "
                     "devkit, or the source changed)")
        else:
            line += ": update available"
        if state.get("foreign"):
            line += " (foreign lineage; fetch will refuse it)"
        elif "lineage_verified" in state and not state["lineage_verified"]:
            line += " (lineage unverified by history)"
    print(line)
    if state and newer and same_commit and "payload_digest" in state:
        print(f"    fix: devkit update apply --from {source} --apply")
    print(f"{'INSTANCE':28s} {'INSTALLED':10s} {'SCHEMA':8s} STATE")

    tips: dict[tuple[str, str], str | None] = {}
    for name, vendor, _config_dir, prov in found:
        blockers = []
        if prov.get("lineage_id") != kit.get("lineage_id"):
            blockers.append("foreign lineage")
        elif prov.get("fork_id") != kit.get("fork_id"):
            blockers.append(f"fork {prov.get('fork_id')} != {kit.get('fork_id')}")
        if prov.get("profile_schema_version", 0) > instances.PROFILE_SCHEMA_VERSION:
            blockers.append("installer too old")
        ref = prov.get("kit_ref")
        if not blockers and ref and ref["kind"] == "pin":
            blockers.append(f"pinned {ref['ref']}")
        elif not blockers and ref:
            blockers.append(f"track {ref['ref']}: " + _track_state(ref, tips, name))
        elif not blockers:
            blockers.append("up to date" if prov.get("source_commit") == local_head
                            else "update available")
        print(f"{name + '/' + vendor:28s} {str(prov.get('source_commit'))[:8]:10s} "
              f"{prov.get('profile_schema_version', '?'):<8} {', '.join(blockers)}")

    for name, links in _legacy_by_profile(home, found).items():
        link, target = links[0]
        print(f"legacy: {name} links into {target.parent}; e.g. {relative_to_home(link)}\n"
              f"    fix: devkit profile sync {name} --apply")
    return 0


def _track_state(ref: dict, tips: dict, name: str) -> str:
    """`up to date` or `update available` for a followed branch, from ls-remote.
    An unreachable source is a note, not a failure."""
    key = (ref["source"], ref["ref"])
    if key not in tips:
        result = kithome._git("ls-remote", ref["source"], f"refs/heads/{ref['ref']}",
                              cwd=Path.home())
        found = result.stdout.split()
        tips[key] = found[0] if result.returncode == 0 and found else None
        if tips[key] is None:
            print(f"note: {name} track {ref['ref']}: could not read the branch from "
                  f"{ref['source']}")
    if tips[key] is None:
        return "unknown"
    return "up to date" if tips[key] == ref["commit"] else "update available"


def _legacy_by_profile(home: Path, found) -> dict[str, list]:
    legacy: dict[str, list] = {}
    for name, _vendor, config_dir, _prov in found:
        links = kithome.legacy_links(home, config_dir)
        if links:
            legacy.setdefault(name, []).extend(links)
    return legacy


# ------------------------------------------------------------------ fetch

def cmd_fetch(args) -> int:
    """Stage the source after verifying its lineage. A foreign kit is rejected
    here, before anything is staged, let alone installed."""
    kit = _kit()
    source = kitsource.resolve_source(getattr(args, "from_source", None), Path.home())
    staged = kitsource.stage(source, args.ref, kit, STAGING_ROOT, _stamp())
    marker = kitsource.read_marker(staged)
    print(f"staged {str(marker['commit'])[:8]}"
          + (" (dirty working tree)" if marker.get("dirty") else "")
          + f" from {source} at {relative_to_home(staged)}")
    kitsource.stage_tracks(_installed_instances(None), kit, STAGING_ROOT, _stamp())
    print("next:  devkit update apply --apply")
    return 0


def cmd_stage_tree(args) -> int:
    """Hidden. Stage a tree with this code; the parent that verified the source
    passes its facts. The last line printed is the staged path."""
    staged = kitsource.write_staged(Path(args.tree), Path(args.out), args.stamp,
                                    json.loads(args.facts))
    print(staged)
    return 0


def cmd_inspect_tree(args) -> int:
    """Hidden. Print the payload facts of a tree as this code computes them."""
    print(json.dumps(kitsource.tree_payload(Path(args.tree))))
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
                data = json.loads(marker.read_text())
            except ValueError:
                continue
            if "track" not in data:  # a branch tip is never the kit itself
                candidates.append((directory, data))
    if not candidates:
        return None
    return max(candidates, key=lambda c: c[1].get("fetched_at", ""))


def _latest_track(source: str, branch: str) -> tuple[Path, dict] | None:
    """The newest staged payload of a followed (source, branch)."""
    found = []
    for directory in STAGING_ROOT.glob(f"track-{kitsource.track_key(source, branch)}-*"):
        try:
            found.append((directory, kitsource.read_marker(directory)))
        except (OSError, ValueError):
            continue
    return max(found, key=lambda c: c[1].get("fetched_at", ""), default=None)


def _refuse_incompatible(found, kit: dict, marker: dict) -> None:
    for name, vendor, _config_dir, prov in found:
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


def _hand_off_apply(payload: Path, args) -> int | None:
    """Let the staged tree install itself. None when no hand-off applies."""
    argv = ["update", "apply", "--staged", str(payload)]
    if getattr(args, "profile", None):
        argv += ["--profile", args.profile]
    if args.apply:
        argv.append("--apply")
    result = kithome.run_as_incoming(
        payload, argv, supported=kitsource.incoming_support(payload), what="installing")
    if result is None:
        return None
    sys.stdout.write(result.stdout)
    return result.returncode


def _restore(backups: list[tuple[Path, Path]]) -> None:
    for config_dir, backup in backups:
        shutil.rmtree(config_dir, ignore_errors=True)
        shutil.move(str(backup), str(config_dir))


def cmd_apply(args) -> int:
    privilege.refuse_root(getattr(args, "user", None))
    if (getattr(args, "from_source", None) or getattr(args, "ref", None)) and not args.apply:
        # A dry run stages into a throwaway directory: anything left in the
        # staging cache is what a later bare `apply --apply` installs.
        with tempfile.TemporaryDirectory(prefix="devkit-dry-run-") as tmp:
            return _apply(args, Path(tmp))
    return _apply(args, STAGING_ROOT)


def _apply(args, staging_root: Path) -> int:
    home = Path.home()
    kit = _kit()
    from_source, ref = getattr(args, "from_source", None), getattr(args, "ref", None)
    if getattr(args, "staged", None):
        payload = Path(args.staged)
        marker = kitsource.read_marker(payload)
    elif from_source or ref:
        source = kitsource.resolve_source(from_source, home)
        payload = kitsource.stage(source, ref or "HEAD", kit, staging_root, _stamp())
        marker = kitsource.read_marker(payload)
    else:
        staged = _latest_staged()
        if staged is None:
            raise DevkitError("nothing is staged",
                              "run 'devkit update fetch' first, or pass --from")
        payload, marker = staged

    found = _installed_instances(getattr(args, "profile", None))
    if not found:
        raise DevkitError("no installed instances to update",
                          "run 'devkit profile create <name> --type TYPE --apply' first")
    _refuse_incompatible(found, kit, marker)

    handed = _hand_off_apply(payload, args)
    if handed is not None:
        return handed

    files = kithome.payload_files(payload)
    digest = kithome.payload_digest(payload, files)
    if marker.get("payload_digest") and marker["payload_digest"] != digest:
        raise DevkitError("the staged payload changed after it was staged",
                          "run 'devkit update fetch' again")
    release_id = digest[:12]
    previous = kithome.current_release(home)
    install_main = not (previous is not None and (kithome.read_stamp(previous) or {}).get(
        "payload_digest") == digest)

    plain = [row for row in found if not row[3].get("kit_ref")]
    moves = _track_moves(found)
    if not install_main and not moves:
        print(f"kit is up to date (release {release_id}); nothing to install.")
        return 0

    commit = str(marker.get("commit"))
    plan = Plan(args.apply)
    if install_main:
        plan.record(f"install release {release_id} ({commit[:8]}"
                    f"{', dirty' if marker.get('dirty') else ''}) into "
                    f"{relative_to_home(kithome.kit_home(home))}")
        for name, vendor, _config_dir, _prov in plain:
            plan.record(f"update {name}/{vendor} to {commit[:8]}")
    _print_ref_skips(found, moves, install_main)
    for (name, vendor), (row, _payload, moved) in moves.items():
        plan.record(f"move   {name}/{vendor} track {row[3]['kit_ref']['ref']} to "
                    f"{str(moved.get('commit'))[:8]}")
    if not args.apply:
        return plan.report("update")

    if install_main:
        release = kithome.install_checked(payload, home, files, digest, marker)
        kithome.flip_current(home, release)

    # The provenance file is never updated before the tree it describes, so
    # a failure leaves it describing the pre-apply state. BaseException, not
    # Exception: a Ctrl-C mid-write has to restore too, and KeyboardInterrupt
    # is not an Exception.
    backups: list[tuple[Path, Path]] = []
    flipped: list[tuple[str, Path | None]] = []
    current = kithome.current_link(home)
    try:
        from .profiles import materialize
        new_commit = instances.kit_commit(current)
        moved_refs = _move_refs(home, moves, flipped)
        refreshed = []
        work = [(row, None) for row in (plain if install_main else [])]
        work += [(row, moved_refs[row[0]]) for row, _payload, _marker in moves.values()]
        for (name, vendor, config_dir, prov), kit_ref in work:
            backups.append((config_dir, back_up(config_dir)))
            type_name = instances.instance_type(prov, name)
            link = kithome.ref_link(home, name)
            profile = instances.bind_instance(
                manifest.load(type_name, kit_root=link if kit_ref else current),
                name, type_name)
            instances.apply_provenance_color(profile, prov)
            instances.apply_headless(profile, None, home)
            extra = {"content": (link, link), "kit_ref": kit_ref,
                     "source_commit": kit_ref["commit"]} if kit_ref else {}
            materialize(profile, [vendor], home, Plan(apply=True), force=True,
                        kit_root=current, **extra)
            refreshed.append((config_dir, prov, kit_ref["commit"] if kit_ref else new_commit))
        # Provenance is written last: a failing migration rolls back before any
        # file names a state that is about to be undone.
        ran = migrations.run_needed(home, Plan(apply=True))
        for config_dir, prov, to_commit in refreshed:
            updated = instances.read_provenance(config_dir) or prov
            entry = {"from": prov.get("source_commit"), "to": to_commit,
                     "at": timestamp()}
            if ran:
                entry["migrations"] = ran
            updated["history"] = [*prov.get("history", []), entry]
            write_json(config_dir / instances.PROVENANCE_NAME, updated)
    except BaseException:  # noqa: BLE001 - roll back on Ctrl-C too, then report
        _restore(backups)
        for name, was in flipped:
            kithome.flip_ref(home, name, was) if was else kithome.drop_ref(home, name)
        # With no previous release, `current` stays on the complete new one: the
        # auth scripts were already rewritten to name it and must not dangle.
        if install_main and previous is not None:
            kithome.flip_current(home, previous)
        raise DevkitError("apply failed and was rolled back: the previous release is "
                          "current again and every instance was restored from backup",
                          "the instances and their provenance describe the pre-apply state")
    for _config_dir, backup in backups:
        shutil.rmtree(backup, ignore_errors=True)
    kithome.prune(home)
    return plan.report("update")


def _track_moves(found) -> dict[tuple[str, str], tuple]:
    """Instances on a followed branch whose staged tip differs from their commit,
    as `{(name, vendor): (row, payload, marker)}`."""
    moves = {}
    for row in found:
        ref = row[3].get("kit_ref") or {}
        if ref.get("kind") != "track":
            continue
        staged = _latest_track(ref["source"], ref["ref"])
        if staged and staged[1].get("commit") != ref.get("commit"):
            moves[(row[0], row[1])] = (row, *staged)
    return moves


def _print_ref_skips(found, moves: dict, install_main: bool) -> None:
    """Instances on a ref keep their content while `current` moves; their
    wrappers and vendor config keep the previous tooling until a sync."""
    if not install_main:
        return
    for name, vendor, _config_dir, prov in found:
        ref = prov.get("kit_ref")
        if not ref or (name, vendor) in moves:
            continue
        what = (f"pinned to {ref['ref']}" if ref["kind"] == "pin"
                else f"track {ref['ref']}, unchanged")
        print(f"skip   {name}/{vendor} ({what} @ {str(ref['commit'])[:8]})\n"
              f"    fix: devkit profile sync {name} --apply")


def _move_refs(home: Path, moves: dict, flipped: list) -> dict[str, dict]:
    """Install each moved branch tip once per profile and flip its ref link."""
    moved: dict[str, dict] = {}
    for row, payload, marker in moves.values():
        name, old = row[0], row[3]["kit_ref"]
        if name in moved:
            continue
        files = kithome.payload_files(payload)
        digest = kithome.payload_digest(payload, files)
        if marker.get("payload_digest") and marker["payload_digest"] != digest:
            raise DevkitError("a staged branch payload changed after it was staged",
                              "run 'devkit update fetch' again")
        release = kithome.install_checked(payload, home, files, digest, marker)
        before = kithome.ref_release(home, name)
        flipped.append((name, before))
        kithome.flip_ref(home, name, release)
        held = before.name if before and before != release.resolve() else old.get("previous_release")
        moved[name] = {**old, "commit": marker["commit"], "release": digest[:12],
                       "previous_release": held}
    return moved


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
    matches = [row for row in instances.discover_instances(home) if row[0] == args.name]
    if not matches:
        raise DevkitError(
            f"no installed profile named {args.name!r}",
            f"run 'devkit profile create {args.name} --type TYPE --apply' first")
    for name, vendor, config_dir, prov in matches:
        if prov.get("lineage_id") != kit.get("lineage_id"):
            raise DevkitError(
                f"{name}/{vendor}: foreign lineage",
                "none; migrate moves between forks of one lineage, not between kits")
        plan.record(f"migrate {name}/{vendor} "
                    f"{prov.get('fork_id')} -> {args.to_fork}")
        if args.apply:
            prov["fork_id"] = args.to_fork
            prov["history"] = [*prov.get("history", []),
                               {"migrated_to_fork": args.to_fork, "at": timestamp()}]
            write_json(config_dir / instances.PROVENANCE_NAME, prov)
    return plan.report(f"migrate {args.name}")
