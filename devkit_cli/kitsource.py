"""Where an upgrade comes from: a local directory or a git URL.

Both are turned into a staged payload (`<staging>/<id>/` plus `.devkit-staged.json`)
after lineage is verified, so nothing foreign reaches the kit home. `update apply`
installs from the staged payload and never reads the source again.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from . import kithome
from .common import write_json
from .errors import DevkitError

GIT_URL = re.compile(r"^(https?://|ssh://|file://|git@[^\s:/]+:)")


def is_git_url(source: str) -> bool:
    return bool(GIT_URL.match(source))


def resolve_source(from_arg: str | None, home: Path) -> str:
    """`--from`, then the source recorded in the current stamp, then `upstream`."""
    from .profiles import _kit_metadata

    if from_arg:
        return from_arg
    current = kithome.current_release(home)
    recorded = (kithome.read_stamp(current) if current else None) or {}
    if recorded.get("source"):
        return recorded["source"]
    upstream = _kit_metadata().get("upstream")
    if upstream:
        return upstream
    raise DevkitError("no update source is known: this kit was never installed "
                      "from one and devkit.yaml has no upstream",
                      "pass --from <directory or git URL>")


# ---------------------------------------------------------------- lineage

def refuse_foreign(found: str | None, kit: dict, where: str) -> None:
    if found is None:
        raise DevkitError(f"could not resolve the lineage of {where}",
                          "use a full clone; devkit will not accept an unknown lineage")
    if found != kit.get("lineage_id"):
        raise DevkitError(
            f"lineage mismatch: {where} is {found[:8]}, this kit is "
            f"{str(kit.get('lineage_id'))[:8]}",
            "this is a different kit, not a fork of yours; there is no escape hatch")


def root_commit(work: Path, commit: str) -> str | None:
    roots = kithome._git("rev-list", "--max-parents=0", commit, cwd=work).stdout.split()
    return roots[-1] if roots else None


def _is_shallow(work: Path) -> bool:
    return kithome._git("rev-parse", "--is-shallow-repository",
                        cwd=work).stdout.strip() == "true"


def clone_lineage(work: Path, commit: str) -> str | None:
    """The root commit of a clone, unshallowing it first when needed.

    A shallow clone's oldest commit is a graft point, not the lineage root, so
    trusting it compares this fork against itself and calls it foreign. When the
    upstream is itself shallow that cannot succeed, and an unresolved lineage is
    the honest refusal.
    """
    found = root_commit(work, commit)
    if found is None or _is_shallow(work):
        kithome._git("fetch", "--unshallow", cwd=work)
        found = None if _is_shallow(work) else root_commit(work, commit)
    return found


# ------------------------------------------------------------- directories

def inspect_directory(path: Path, kit: dict, *, payload: bool = True) -> dict:
    """What a local directory would install, and whether its lineage holds.

    Returns commit, dirty, lineage_id, lineage_verified (True when it came from
    git history) and, unless `payload` is False, files and payload_digest as the
    running code computes them. Nothing is written.
    """
    from .profiles import _kit_metadata

    if not path.is_dir():
        raise DevkitError(f"update source {path} is not a directory",
                          "pass --from <directory or git URL>")
    if not (path / "devkit.py").is_file() or not (path / "devkit_cli").is_dir():
        raise DevkitError(f"{path} is not a devkit tree (no devkit.py or devkit_cli/)",
                          "pass --from <the directory holding devkit.py>")
    declared = _kit_metadata(path).get("lineage_id")
    lineage, verified = declared, False
    commit, dirty = "unknown", False
    if (path / ".git").exists():
        commit, dirty = kithome.tree_commit(path)
        if commit != "unknown" and not _is_shallow(path):
            lineage, verified = root_commit(path, commit), True
    found = {"commit": commit, "dirty": dirty, "lineage_id": lineage,
             "lineage_verified": verified,
             "fork_id": _kit_metadata(path).get("fork_id")}
    if payload:
        found["files"] = kithome.payload_files(path)
        found["payload_digest"] = kithome.payload_digest(path, found["files"])
    return found


def tree_payload(tree: Path) -> dict:
    """The payload facts of `tree`, as the code running now computes them."""
    files = kithome.payload_files(tree)
    return {"files": len(files), "payload_digest": kithome.payload_digest(tree, files)}


def write_staged(tree: Path, staging_root: Path, stamp: str, facts: dict) -> Path:
    """Copy the payload of `tree` into the staging cache and write the marker.

    `facts` are what the caller verified (commit, lineage, source ...); the
    payload list and digest are computed here, by whichever version of the code
    runs this. `staged_name` names the directory; the default is the digest.
    """
    files = kithome.payload_files(tree)
    digest = kithome.payload_digest(tree, files)
    kithome.check_links(tree, files)
    staged = staging_root / (facts.get("staged_name") or f"dir-{digest[:12]}")
    shutil.rmtree(staged, ignore_errors=True)
    kithome.copy_payload(tree, staged, files)
    marker = {key: value for key, value in facts.items() if key != "staged_name"}
    write_json(staged / kithome.STAGED_MARKER,
               {**marker, "payload_digest": digest, "fetched_at": stamp})
    return staged


def incoming_support(tree: Path) -> bool:
    """Whether `tree` declares the hand-off protocol, read from its source."""
    value = kithome.literal_from(tree / "devkit_cli" / "update.py", "HANDOFF_PROTOCOL")
    return isinstance(value, int) and value >= 1


def stage_as_incoming(tree: Path, staging_root: Path, stamp: str,
                      facts: dict) -> Path:
    """Stage `tree` with its own code when it supports that, else with this code."""
    result = kithome.run_as_incoming(
        tree, ["update", "stage-tree", "--tree", str(tree), "--out", str(staging_root),
               "--stamp", stamp, "--facts", json.dumps(facts)],
        supported=incoming_support(tree), what="staging")
    if result is None:
        return write_staged(tree, staging_root, stamp, facts)
    lines = result.stdout.splitlines()
    if result.returncode != 0 or not lines:
        raise DevkitError(f"the incoming tree could not stage itself ({tree})",
                          "the error above comes from that tree's own devkit")
    for line in lines[:-1]:
        print(line)
    return Path(lines[-1])


def stage_directory(path: Path, kit: dict, staging_root: Path, stamp: str) -> Path:
    found = inspect_directory(path, kit, payload=False)
    refuse_foreign(found["lineage_id"], kit, f"{path}")
    if not found["lineage_verified"]:
        print(f"note: {path} has no usable git history; its lineage is the one its own "
              f"devkit.yaml declares (unverified by history)")
    return stage_as_incoming(path, staging_root, stamp, {**found, "source": str(path.resolve())})


# --------------------------------------------------------------------- git

def stage_git(url: str, ref: str, kit: dict, staging_root: Path, stamp: str) -> Path:
    """Clone, verify the ref and the lineage, strip `.git`, write the marker."""
    from .profiles import _kit_metadata

    if shutil.which("git") is None:
        raise DevkitError("git is not installed", "run bootstrap.sh first")
    staging_root.mkdir(parents=True, exist_ok=True)
    work = staging_root / f"fetch-{stamp}"
    shutil.rmtree(work, ignore_errors=True)
    result = kithome._git("clone", "--quiet", url, str(work), cwd=staging_root)
    if result.returncode != 0:
        raise DevkitError(f"could not clone {url}: {result.stderr.strip()}",
                          "check the remote and your credentials")
    try:
        commit = None
        for candidate in (ref, f"origin/{ref}"):
            head = kithome._git("rev-parse", "--verify", f"{candidate}^{{commit}}",
                                cwd=work)
            if head.returncode == 0:
                commit = head.stdout.strip()
                break
        if commit is None:
            raise DevkitError(f"{ref} does not exist in {url}")
        kithome._git("checkout", "--quiet", "--detach", commit, cwd=work)
        lineage = clone_lineage(work, commit)
        refuse_foreign(lineage, kit, f"the fetched {url}")
        shutil.rmtree(work / ".git", ignore_errors=True)
        return stage_as_incoming(work, staging_root, stamp, {
            "commit": commit, "dirty": False, "lineage_id": lineage,
            "fork_id": _kit_metadata(work).get("fork_id"), "lineage_verified": True,
            "source": url, "upstream": url, "staged_name": commit})
    finally:
        shutil.rmtree(work, ignore_errors=True)


def stage(source: str, ref: str, kit: dict, staging_root: Path, stamp: str) -> Path:
    if is_git_url(source):
        return stage_git(source, ref, kit, staging_root, stamp)
    return stage_directory(Path(source).expanduser(), kit, staging_root, stamp)


def read_marker(staged: Path) -> dict:
    return json.loads((staged / kithome.STAGED_MARKER).read_text(encoding="utf-8"))
