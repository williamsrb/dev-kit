"""Where an upgrade comes from: a local directory or a git URL.

Both are turned into a staged payload (`<staging>/<id>/` plus `.devkit-staged.json`)
after lineage is verified, so nothing foreign reaches the kit home. `update apply`
installs from the staged payload and never reads the source again.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
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

_SHA = re.compile(r"^[0-9a-f]{4,40}$")


def _ref_commit(work: Path, ref: str) -> str | None:
    head = kithome._git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", cwd=work)
    return head.stdout.strip() if head.returncode == 0 else None


def _resolve_ref(work: Path, ref: str, kind: str | None, source: str) -> str:
    """The commit `ref` names in a fresh clone, under the rules of `kind`.

    `track` is a remote branch only. `pin` is a tag or a commit SHA, never a
    branch. `None` keeps the update path: the name as given, then `origin/<name>`.
    """
    branch = _ref_commit(work, f"refs/remotes/origin/{ref}")
    tag = _ref_commit(work, f"refs/tags/{ref}")
    if kind == "track":
        if branch:
            return branch
        if tag:
            raise DevkitError(f"{ref} is not a branch in {source} (it is a tag)",
                              f"use --pin {ref} to fix the kit to that tag")
    elif kind == "pin":
        if tag:
            return tag
        sha = _ref_commit(work, ref) if _SHA.match(ref) else None
        if sha:
            return sha
        if branch:
            raise DevkitError(f"{ref} is a branch in {source}; a pin never moves",
                              f"use --track {ref} to follow the branch, or pin a tag or commit")
    else:
        found = _ref_commit(work, ref) or branch
        if found:
            return found
    raise DevkitError(f"{ref} does not exist in {source}",
                      "name a branch (--track) or a tag or commit (--pin) of that source")


@contextmanager
def checkout(source: str, ref: str, kind: str | None,
             kit: dict) -> Iterator[tuple[Path, dict]]:
    """A detached, lineage-checked clone of `source` at `ref`, removed on exit.

    `source` is a git URL or a local directory holding `.git`; a local one is
    cloned by path, so the ref is read and the working tree is not. Yields
    `(tree, facts)`. With a `kind` the tree must hold `core/skills`; a ref that
    predates `core/` is refused.
    """
    from .profiles import _kit_metadata

    if shutil.which("git") is None:
        raise DevkitError("git is not installed", "run bootstrap.sh first")
    origin = source
    if not is_git_url(source):
        path = Path(source).expanduser()
        if not (path / ".git").exists():
            raise DevkitError(f"{source} is not a git checkout, so a ref cannot be read from it",
                              "pass a git checkout or a git URL as --from")
        origin = str(path.resolve())
    work = Path(tempfile.mkdtemp(prefix="devkit-ref-"))
    try:
        result = kithome._git("clone", "--quiet", origin, str(work), cwd=work.parent)
        if result.returncode != 0:
            raise DevkitError(f"could not clone {source}: {result.stderr.strip()}",
                              "check the remote and your credentials")
        commit = _resolve_ref(work, ref, kind, source)
        kithome._git("checkout", "--quiet", "--detach", commit, cwd=work)
        lineage = clone_lineage(work, commit)
        refuse_foreign(lineage, kit, f"{ref} of {source}")
        if kind and not (work / "core" / "skills").is_dir():
            raise DevkitError(f"{ref} predates core/ in {source}: it has no core/skills",
                              "name a newer branch, tag or commit")
        yield work, {"commit": commit, "lineage_id": lineage,
                     "fork_id": _kit_metadata(work).get("fork_id"),
                     "source": source, "ref": ref, "kind": kind}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def stage_git(url: str, ref: str, kit: dict, staging_root: Path, stamp: str) -> Path:
    """Clone, verify the ref and the lineage, strip `.git`, write the marker."""
    staging_root.mkdir(parents=True, exist_ok=True)
    with checkout(url, ref, None, kit) as (work, facts):
        shutil.rmtree(work / ".git", ignore_errors=True)
        return stage_as_incoming(work, staging_root, stamp, {
            "commit": facts["commit"], "dirty": False, "lineage_id": facts["lineage_id"],
            "fork_id": facts["fork_id"], "lineage_verified": True,
            "source": url, "upstream": url, "staged_name": facts["commit"]})


def refuse_other_fork(facts: dict, kit: dict, name: str = "<name>") -> None:
    """A ref must be of the running kit's own fork: provenance records the
    running kit's `fork_id`, so a mismatch would pass `_refuse_incompatible`."""
    if facts.get("fork_id") != kit.get("fork_id"):
        raise DevkitError(
            f"{facts.get('ref')} of {facts.get('source')} is fork {facts.get('fork_id')}; "
            f"this kit is {kit.get('fork_id')}",
            f"devkit profile migrate {name} --to-fork {facts.get('fork_id')}")


def refuse_layout(tree: Path) -> None:
    """A ref a profile can use must match this devkit's schema and release layout.

    Both facts are read from the ref's source without importing it. A newer
    profile schema needs a newer installer; a different `PAYLOAD` would make
    `install_checked` fail later, because a release is stamped with the running
    `PAYLOAD` and verified against its own.
    """
    from . import instances

    schema = kithome.literal_from(tree / "devkit_cli" / "instances.py",
                                  "PROFILE_SCHEMA_VERSION")
    if isinstance(schema, int) and schema > instances.PROFILE_SCHEMA_VERSION:
        raise DevkitError(
            f"the ref uses profile schema {schema}; this installer knows "
            f"{instances.PROFILE_SCHEMA_VERSION}",
            "update the kit first: devkit update fetch, then devkit update apply --apply")
    if kithome.literal_from(tree / "devkit_cli" / "kithome.py", "PAYLOAD") != kithome.PAYLOAD:
        raise DevkitError(
            "the ref has a different release layout (its PAYLOAD is not this devkit's)",
            "name a newer ref, one cut after the layout this devkit installs")


def track_key(source: str, branch: str) -> str:
    return hashlib.sha256(f"{source}\0{branch}".encode()).hexdigest()[:12]


def stage_tracks(rows: list, kit: dict, staging_root: Path, stamp: str) -> None:
    """Stage the tip of every branch an installed instance follows.

    One payload per distinct (source, branch), named `track-<key>-<commit>`, with
    a `track` marker key so `update apply` never mistakes it for the kit itself.
    A branch that is gone, foreign, of another fork or of another layout is
    reported per instance and not staged: the instance stays on its release.
    """
    pairs: dict[tuple[str, str], list] = {}
    for name, _vendor, _config_dir, prov in rows:
        ref = prov.get("kit_ref") or {}
        if ref.get("kind") == "track":
            pairs.setdefault((ref["source"], ref["ref"]), []).append((name, ref))
    for (source, branch), owners in pairs.items():
        key = track_key(source, branch)
        try:
            with checkout(source, branch, "track", kit) as (tree, facts):
                refuse_other_fork(facts, kit, owners[0][0])
                refuse_layout(tree)
                staged = staging_root / f"track-{key}-{facts['commit']}"
                if not staged.is_dir():
                    shutil.rmtree(tree / ".git", ignore_errors=True)
                    stage_as_incoming(tree, staging_root, stamp, {
                        "commit": facts["commit"], "dirty": False,
                        "lineage_id": facts["lineage_id"], "fork_id": facts["fork_id"],
                        "lineage_verified": True, "source": source,
                        "track": {"source": source, "branch": branch},
                        "staged_name": staged.name})
            for old in staging_root.glob(f"track-{key}-*"):
                if old != staged:
                    shutil.rmtree(old, ignore_errors=True)
        except DevkitError as exc:
            for name, commit in dict.fromkeys((n, r["commit"]) for n, r in owners):
                print(f"note: {name} track {branch}: {exc.args[0]}; "
                      f"staying on {str(commit)[:8]}")


def stage(source: str, ref: str, kit: dict, staging_root: Path, stamp: str) -> Path:
    if is_git_url(source):
        return stage_git(source, ref, kit, staging_root, stamp)
    return stage_directory(Path(source).expanduser(), kit, staging_root, stamp)


def read_marker(staged: Path) -> dict:
    return json.loads((staged / kithome.STAGED_MARKER).read_text(encoding="utf-8"))
