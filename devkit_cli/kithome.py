"""The installed kit: a copy of devkit that profiles link to, not the checkout.

Layout, under `${XDG_DATA_HOME:-$HOME/.local/share}/devkit/`:

    releases/<release-id>/   immutable copy of the payload plus .devkit-install.json
    current                  symlink to one release

Every projection devkit writes points through `current`, so an upgrade installs
a new release and flips one symlink; none of the links in a profile is rewritten.
The repository, local or remote, is only the source of an upgrade.

`REPO_ROOT` resolves symlinks, so a running installed devkit sees a release
directory. Anything written for later use must name `current_link(home)`.
"""

from __future__ import annotations

import ast
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .common import EXEC_MODE, FILE_MODE, REPO_ROOT, STAMP_NAME, Plan, ensure_dir
from .errors import DevkitError

# The runtime allowlist. Bootstrap and install stay checkout-only, docs and
# tests stay in the repo, and `core/` ships whole so a release matches `export`.
PAYLOAD = ("devkit.py", "devkit", "devkit_cli", "core", "templates", "profiles", "flavors",
           "devkit.yaml", "export-allowlist.json", "path-contract.json")
SKIP_PARTS = frozenset({".git", "__pycache__"})
RETAIN = 2  # current plus the previous release

STAGED_MARKER = ".devkit-staged.json"

# Set in a child that was handed an install: a process that sees it never hands off.
HANDOFF_ENV = "DEVKIT_HANDOFF"


# ------------------------------------------------------------------ paths

def kit_home(home: Path) -> Path:
    """XDG_DATA_HOME counts only when it lies under `home`: a `--user` run or a
    test under another home must not write into the caller's data dir, and
    devkit-uninstall.sh applies the same rule."""
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg and os.path.isabs(xdg) and Path(xdg).is_relative_to(home):
        return Path(xdg) / "devkit"
    return home / ".local" / "share" / "devkit"


def releases_dir(home: Path) -> Path:
    return kit_home(home) / "releases"


def current_link(home: Path) -> Path:
    return kit_home(home) / "current"


def current_release(home: Path) -> Path | None:
    link = current_link(home)
    return link.resolve() if link.is_symlink() and link.exists() else None


def read_stamp(root: Path) -> dict | None:
    try:
        return json.loads((root / STAMP_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def is_installed_tree(root: Path) -> bool:
    return (root / STAMP_NAME).is_file()


# ---------------------------------------------------------------- payload

def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                              text=True, check=False)
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, 127, "", "git is not installed")


def _skipped(rel: str) -> bool:
    return any(part in SKIP_PARTS for part in rel.split("/"))


def payload_files(src: Path, entries: tuple[str, ...] | None = None) -> list[str]:
    """Payload files (and symlinks) under `src`, as sorted posix relative paths.

    A checkout reads the working tree through git (tracked plus untracked,
    ignored files out); a tree without `.git` is walked. Either way only the
    allowlist is considered: `PAYLOAD`, or `entries` when a release built by
    another version is being checked against its own list.
    """
    entries = entries or PAYLOAD
    found: set[str] = set()
    listed = None
    if (src / ".git").exists():
        result = _git("ls-files", "--cached", "--others", "--exclude-standard",
                      "-z", "--", *entries, cwd=src)
        if result.returncode == 0:
            listed = [p for p in result.stdout.split("\0") if p]
    if listed is not None:
        # --cached still lists a file deleted from the working tree.
        found = {rel for rel in listed
                 if os.path.lexists(src / rel) and not _skipped(rel)}
    else:
        for name in entries:
            top = src / name
            if top.is_symlink() or top.is_file():
                found.add(name)
                continue
            for base, dirs, files in os.walk(top):
                dirs[:] = [d for d in dirs if d not in SKIP_PARTS]
                base_path = Path(base)
                for entry in (*files, *(d for d in dirs
                                        if (base_path / d).is_symlink())):
                    rel = (base_path / entry).relative_to(src).as_posix()
                    if not _skipped(rel):
                        found.add(rel)
    return sorted(found)


def _is_exec(path: Path) -> bool:
    return bool(path.lstat().st_mode & 0o111)


def payload_digest(src: Path, files: list[str]) -> str:
    """Over path, executable bit and content (or symlink target).

    Not the full mode: an install under umask 077 must digest like one under 022.
    """
    digest = hashlib.sha256()
    for rel in files:
        path = src / rel
        if path.is_symlink():
            kind, body = b"L", os.readlink(path).encode()
        else:
            kind, body = (b"X" if _is_exec(path) else b"F"), path.read_bytes()
        digest.update(rel.encode() + b"\0" + kind + b"\0"
                      + hashlib.sha256(body).digest())
    return digest.hexdigest()


def check_links(src: Path, files: list[str]) -> None:
    """A release is relocatable: refuse an absolute link, or one that leaves
    the payload (a target the release would not contain)."""
    base = os.path.normpath(src)
    for rel in files:
        path = src / rel
        if not path.is_symlink():
            continue
        target = os.readlink(path)
        if os.path.isabs(target):
            raise DevkitError(f"{rel} is an absolute symlink ({target})",
                              "replace it with a relative link inside the kit")
        resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
        inside = os.path.relpath(resolved, base).split(os.sep)
        if inside[0] == os.pardir or inside[0] not in PAYLOAD:
            raise DevkitError(f"{rel} is a symlink that leaves the kit payload ({target})",
                              "replace it with a relative link to a payload file")


def tree_commit(src: Path) -> tuple[str, bool]:
    """(commit, dirty) of the checkout at `src`; ("unknown", False) without git."""
    head = _git("rev-parse", "HEAD", cwd=src)
    if head.returncode != 0:
        return "unknown", False
    status = _git("status", "--porcelain", "--", *PAYLOAD, cwd=src)
    return head.stdout.strip(), bool(status.stdout.strip())


def describe_tree(src: Path) -> dict:
    """Where a tree came from: a staged marker, an install stamp, or a checkout."""
    from .profiles import _kit_metadata

    for name in (STAGED_MARKER, STAMP_NAME):
        try:
            data = json.loads((src / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        return {key: data.get(key) for key in
                ("commit", "dirty", "lineage_id", "fork_id", "source")}
    kit = _kit_metadata(src)
    commit, dirty = tree_commit(src) if (src / ".git").exists() else ("unknown", False)
    return {"commit": commit, "dirty": dirty, "lineage_id": kit.get("lineage_id"),
            "fork_id": kit.get("fork_id"), "source": str(src.resolve())}


# ---------------------------------------------------------------- install

def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="microseconds")


def copy_payload(src: Path, dest_root: Path, files: list[str]) -> None:
    """Copy payload files with exec bits and relative symlinks preserved."""
    ensure_dir(dest_root)
    for rel in files:
        origin, dest = src / rel, dest_root / rel
        ensure_dir(dest.parent)
        if origin.is_symlink():
            os.symlink(os.readlink(origin), dest)
            continue
        shutil.copyfile(origin, dest)
        dest.chmod(EXEC_MODE if _is_exec(origin) else FILE_MODE)


def install_release(src: Path, home: Path, files: list[str], digest: str,
                    meta: dict) -> Path:
    """Copy the payload into releases/<id> via a temp dir and a rename."""
    check_links(src, files)
    release_id = digest[:12]
    releases = releases_dir(home)
    ensure_dir(releases)
    final = releases / release_id
    temp = releases / f".tmp-{release_id}-{os.getpid()}"
    shutil.rmtree(temp, ignore_errors=True)
    try:
        copy_payload(src, temp, files)
        stamp = {"release_id": release_id, "commit": meta.get("commit") or "unknown",
                 "dirty": bool(meta.get("dirty")), "lineage_id": meta.get("lineage_id"),
                 "fork_id": meta.get("fork_id"), "source": meta.get("source"),
                 "installed_at": _now(), "payload_digest": digest,
                 "payload_entries": list(PAYLOAD)}
        (temp / STAMP_NAME).write_text(json.dumps(stamp, indent=2) + "\n",
                                       encoding="utf-8")
        (temp / STAMP_NAME).chmod(FILE_MODE)
        if final.exists():  # an identical release won the race
            shutil.rmtree(temp)
        else:
            temp.rename(final)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return final


def literal_from(source_file: Path, name: str):
    """A module-level literal from a Python file, read with `ast`: the file is
    never imported or run. None when the file or the assignment is missing, or
    the value is not a literal."""
    try:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                return None
    return None


def verify_release(release: Path) -> list[str]:
    """Problems with a release, judged by facts the release itself carries.

    "Its own PAYLOAD" is the tuple in the release's `kithome.py`, not the running
    module's, which is the checkout's when doctor runs from one.
    """
    entries = literal_from(release / "devkit_cli" / "kithome.py", "PAYLOAD")
    if not isinstance(entries, tuple) or not all(isinstance(e, str) for e in entries):
        return ["the release's own PAYLOAD could not be read from devkit_cli/kithome.py"]
    problems = []
    missing = [name for name in entries if not os.path.lexists(release / name)]
    if missing:
        problems.append(f"missing from the release: {', '.join(missing)}")
    stamp = read_stamp(release) or {}
    expected = stamp.get("payload_digest")
    if expected and payload_digest(release, payload_files(release, entries)) != expected:
        problems.append("the stamped payload digest does not match the release's files")
    if "payload_entries" in stamp and tuple(stamp["payload_entries"]) != entries:
        problems.append("the stamp's payload_entries differ from the release's own PAYLOAD")
    return problems


def install_checked(src: Path, home: Path, files: list[str], digest: str,
                    meta: dict) -> Path:
    """`install_release`, then `verify_release`, before anything can flip to it.

    A release this call built and then rejected is removed; one that already
    existed is left alone. Raises with the problems and the flip never happens.
    """
    release = releases_dir(home) / digest[:12]
    built = not release.is_dir()
    if built:
        install_release(src, home, files, digest, meta)
    problems = verify_release(release)
    if problems:
        if built:
            shutil.rmtree(release, ignore_errors=True)
        raise DevkitError(f"release {release.name} is incomplete: " + "; ".join(problems),
                          "nothing was changed; fix the source tree and run it again")
    return release


def run_as_incoming(tree: Path, argv: list[str], *, supported: bool,
                    what: str) -> subprocess.CompletedProcess | None:
    """Run `devkit.py <argv>` of `tree` so the incoming code decides what it installs.

    None when no hand-off applies: the guard is set, `tree` is the running tree,
    or it predates the hand-off (`supported` False, said in a note). stdout is
    returned for the caller to forward or parse; stderr goes straight through.
    """
    if os.environ.get(HANDOFF_ENV) or tree.resolve() == REPO_ROOT:
        return None
    if not supported:
        print(f"note: {tree} predates the hand-off; {what} with the installed "
              f"devkit's code")
        return None
    print(f"note: {what} with the incoming tree's own code ({tree})")
    # No bytecode: running the tree must not leave __pycache__ in a source checkout.
    env = {**os.environ, HANDOFF_ENV: "1", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        result = subprocess.run([sys.executable, str(tree / "devkit.py"), *argv],
                                env=env, stdout=subprocess.PIPE, text=True, check=False)
    except OSError as exc:
        raise DevkitError(f"could not start the incoming tree's devkit.py: {exc}",
                          "run it directly from that tree")
    return result


def flip_current(home: Path, release: Path) -> None:
    """Point `current` at a release. The temp link is renamed over it, so a
    reader sees the old release or the new one, never a missing link."""
    kit = kit_home(home)
    ensure_dir(kit)
    temp = kit / f".current-{os.getpid()}"
    temp.unlink(missing_ok=True)
    temp.symlink_to(Path("releases") / release.name)
    os.replace(temp, current_link(home))


def _installed_at(release: Path) -> str:
    return (read_stamp(release) or {}).get("installed_at") or ""


def previous_release(home: Path) -> Path | None:
    """The newest installed release that is not current."""
    current = current_release(home)
    others = [r for r in _release_dirs(home) if r != current]
    return max(others, key=_installed_at, default=None)


def _release_dirs(home: Path) -> list[Path]:
    releases = releases_dir(home)
    if not releases.is_dir():
        return []
    return [r.resolve() for r in releases.iterdir()
            if r.is_dir() and not r.name.startswith(".")]


def prune(home: Path, keep: int = RETAIN) -> list[str]:
    """Remove every release except current and the newest others, up to `keep`."""
    current = current_release(home)
    others = sorted((r for r in _release_dirs(home) if r != current),
                    key=_installed_at, reverse=True)
    spare = max(keep - (1 if current else 0), 0)
    removed = []
    for release in others[spare:]:
        shutil.rmtree(release, ignore_errors=True)
        removed.append(release.name)
    return removed


def ensure_installed(src: Path, home: Path, plan: Plan,
                     meta: dict | None = None) -> Path:
    """Make `src` the current release and return the tree to read from.

    Apply: installs when the payload is new, flips `current`, and returns
    `current`, so reads and links name the same tree. Dry run: nothing is
    written, and the source tree is returned because `current` may not exist.
    The running tree being `current` already copies nothing.
    """
    current = current_link(home)
    if current.is_symlink() and src.resolve() == current.resolve():
        return current

    files = payload_files(src)
    digest = payload_digest(src, files)
    release = releases_dir(home) / digest[:12]
    if current.is_symlink() and current.resolve() == release.resolve():
        return current  # identical payload is already what current holds

    if release.is_dir():
        plan.record(f"kit    switch current -> release {digest[:12]}")
    else:
        plan.record(f"kit    install release {digest[:12]} into "
                    f"{kit_home(home)}/releases")
        plan.record(f"kit    point current at release {digest[:12]}")
    if not plan.apply:
        return src
    install_checked(src, home, files, digest, meta or describe_tree(src))
    flip_current(home, release)
    prune(home)
    return current


# ----------------------------------------------------------------- legacy

# Where a profile holds links into the kit. Data and session dirs are never
# walked: they are large and hold nothing the kit wrote as a projection.
_PROJECTION_DIRS = ("skills", "rules", "kb", "hooks", "bin", "bin-vendor", "mcp",
                    "share", "config", "benchmarks")


def _outside_kit(link: Path, home: Path) -> Path | None:
    """The link's target when it names a kit tree (a `core` path) that is neither
    in the kit home nor another profile (a profile may itself be called `core`)."""
    try:
        target = Path(os.readlink(link))
    except OSError:
        return None
    if not target.is_absolute() or "core" not in target.parts:
        return None
    if target.is_relative_to(kit_home(home)) or \
            target.is_relative_to(home / ".agents-profiles"):
        return None
    return target


def legacy_links(home: Path, config_dir: Path) -> list[tuple[Path, Path]]:
    """Projections of one instance that still point outside the kit home."""
    harness = config_dir.parent
    roots = [harness / "hooks"]
    for base in (config_dir, harness / "agents"):
        roots += [base / name for name in _PROJECTION_DIRS]
    found: list[tuple[Path, Path]] = []
    for root in roots:
        # agents/bin|bin-vendor|benchmarks|mcp|share|config are links themselves; skills/rules/kb/hooks
        # are directories of per-entry links.
        entries = [root] if root.is_symlink() else (
            sorted(root.iterdir()) if root.is_dir() else [])
        for entry in entries:
            if entry.is_symlink() and (target := _outside_kit(entry, home)):
                found.append((entry, target))
    return found


def legacy_cli_link(home: Path) -> Path | None:
    """`~/.local/bin/devkit` when it points at a devkit.py outside the kit home."""
    link = home / ".local" / "bin" / "devkit"
    if not link.is_symlink():
        return None
    target = Path(os.readlink(link))
    if target.name != "devkit.py" or target.is_relative_to(kit_home(home)):
        return None
    return target
