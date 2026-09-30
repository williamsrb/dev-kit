#!/usr/bin/env python3
"""Apply the recorded tgrep-cursor patch series onto a disposable worktree.

Does not touch the operator clone's `main`. Does not install the Cursor
apt hook unless --install-cursor-hook is passed (root path; not run as the user).

Pass --workdir or TGREP_REPO (the tgrep git clone). No default clone path.

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
VENDOR = HOME / ".agents" / "vendor" / "tgrep-cursor"
PATCH_DIR = VENDOR / "patches"
UPSTREAM_FILE = VENDOR / "UPSTREAM"
REPLAY_TEMPLATE = VENDOR / "REPLAY.md"
BUILD_ROOT = HOME / ".cache" / "tgrep" / "build"
REPLAY_REQUEST = HOME / ".cache" / "tgrep" / "replay-request.md"
TGREP_BIN = HOME / ".local" / "bin" / "tgrep"
CARGO = Path.home() / ".cargo" / "bin" / "cargo"


def log(msg: str) -> None:
    print(msg, flush=True)


def parse_upstream(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    if "sha" not in data:
        raise SystemExit(f"UPSTREAM missing sha: {path}")
    return data


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
    )


def patch_files(patch_dir: Path) -> list[Path]:
    files = sorted(p for p in patch_dir.glob("*.patch") if p.is_file())
    if not files:
        raise SystemExit(f"no patches in {patch_dir}")
    return files


def worktree_path(sha: str) -> Path:
    return BUILD_ROOT / sha


def helper_branch(sha: str) -> str:
    return f"tgrep-cursor-build/{sha[:12]}"


def listed_worktrees(repo: Path) -> list[Path]:
    listed = git(repo, "worktree", "list", "--porcelain", check=True)
    paths: list[Path] = []
    for line in listed.stdout.splitlines():
        if line.startswith("worktree "):
            paths.append(Path(line[len("worktree ") :]))
    return paths


def matching_worktree(repo: Path, dest: Path) -> Path | None:
    try:
        dest_res = dest.resolve()
    except OSError:
        dest_res = dest
    for path in listed_worktrees(repo):
        try:
            if path.resolve() == dest_res:
                return path
        except OSError:
            if path == dest:
                return path
    return None


def worktree_at_sha(dest: Path, sha: str) -> bool:
    head = git(dest, "rev-parse", "HEAD", check=False)
    return head.returncode == 0 and head.stdout.strip() == sha


def tree_clean(dest: Path) -> bool:
    status = git(dest, "status", "--porcelain", check=False)
    return status.returncode == 0 and status.stdout.strip() == ""


def series_applied(dest: Path, patches: list[Path]) -> bool:
    if not patches:
        return False
    probe = git(
        dest, "apply", "--reverse", "--check", str(patches[-1]), check=False
    )
    return probe.returncode == 0


def prepare_worktree(
    repo: Path, sha: str, dest: Path, patches: list[Path]
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing_wt = matching_worktree(repo, dest)
    if (
        existing_wt is not None
        and dest.is_dir()
        and worktree_at_sha(dest, sha)
        and (series_applied(dest, patches) or tree_clean(dest))
    ):
        log(f"reuse worktree {dest}")
        return
    if existing_wt is not None:
        git(repo, "worktree", "remove", "--force", str(existing_wt), check=False)
    if dest.exists():
        shutil.rmtree(dest)
    branch = helper_branch(sha)
    existing = git(repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    if existing.returncode == 0:
        git(repo, "branch", "-D", branch, check=False)
    added = git(repo, "worktree", "add", "-b", branch, str(dest), sha, check=False)
    if added.returncode != 0:
        raise RuntimeError(
            f"worktree add failed:\n{added.stdout}\n{added.stderr}".strip()
        )


def apply_patches(dest: Path, patches: list[Path], check_only: bool) -> None:
    if series_applied(dest, patches):
        log("ok skip patches (already applied)")
        return
    for patch in patches:
        probe = git(dest, "apply", "--check", str(patch), check=False)
        if probe.returncode != 0:
            raise PatchReject(patch, probe.stderr)
        if check_only:
            log(f"ok check {patch.name}")
            continue
        applied = git(dest, "apply", str(patch), check=False)
        if applied.returncode != 0:
            raise PatchReject(patch, applied.stderr)
        log(f"ok apply {patch.name}")


class PatchReject(Exception):
    def __init__(self, patch: Path, stderr: str) -> None:
        self.patch = patch
        self.stderr = stderr
        super().__init__(f"{patch.name} rejected")


def write_replay_request(patches: list[Path], failed: Path, stderr: str) -> None:
    template = ""
    if REPLAY_TEMPLATE.exists():
        template = REPLAY_TEMPLATE.read_text(encoding="utf-8")
    body = template.replace("{{REJECTS}}", f"{failed.name}\n\n{stderr.strip()}\n")
    if "{{REJECTS}}" in template:
        text = body
    else:
        text = (
            template.rstrip()
            + "\n\n## REJECTS\n\n"
            + f"{failed.name}\n\n```\n{stderr.strip()}\n```\n"
        )
    REPLAY_REQUEST.parent.mkdir(parents=True, exist_ok=True)
    REPLAY_REQUEST.write_text(text, encoding="utf-8")
    log(f"wrote {REPLAY_REQUEST}")


def cargo_cmd() -> str:
    if CARGO.exists():
        return str(CARGO)
    found = shutil.which("cargo")
    if not found:
        raise SystemExit("cargo not found")
    return found


def run_tests(dest: Path) -> None:
    env = os.environ.copy()
    env["PATH"] = f"{CARGO.parent}:{env.get('PATH', '')}"
    result = subprocess.run(
        [
            cargo_cmd(),
            "test",
            "-p",
            "tgrep-cli",
            "--test",
            "cursor_hidden_argv",
        ],
        cwd=dest,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"cargo test failed in {dest}")


def build_install(dest: Path) -> None:
    env = os.environ.copy()
    env["PATH"] = f"{CARGO.parent}:{env.get('PATH', '')}"
    result = subprocess.run(
        [cargo_cmd(), "build", "--release", "-p", "tgrep-cli"],
        cwd=dest,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"cargo build failed in {dest}")
    src = dest / "target" / "release" / "tgrep"
    if not src.is_file():
        raise SystemExit(f"missing {src}")
    TGREP_BIN.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, TGREP_BIN)
    TGREP_BIN.chmod(0o755)
    log(f"installed {TGREP_BIN}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help="tgrep git clone. Or set TGREP_REPO. No default path.",
    )
    parser.add_argument("--upstream", default=None, help="override UPSTREAM.sha")
    parser.add_argument("--patch-dir", type=Path, default=PATCH_DIR)
    parser.add_argument("--dry-run", action="store_true", help="git apply --check only")
    parser.add_argument("--apply", action="store_true", help="apply, test, and install")
    parser.add_argument(
        "--no-cargo",
        action="store_true",
        help="skip cargo test/build (dummy-patch tests)",
    )
    parser.add_argument(
        "--install-cursor-hook",
        action="store_true",
        help="root-only; not implemented in the user apply path",
    )
    args = parser.parse_args(argv)
    if args.install_cursor_hook:
        print(
            "refusing: --install-cursor-hook is a root path; "
            "use /usr/local/bin/cursor-tgrep-rg-apply",
            file=sys.stderr,
        )
        return 2
    if not args.dry_run and not args.apply:
        parser.error("specify --dry-run or --apply")

    workdir_raw = args.workdir or os.environ.get("TGREP_REPO")
    if not workdir_raw:
        parser.error("pass --workdir or set TGREP_REPO")
    workdir = Path(workdir_raw).expanduser().resolve()
    if not (workdir / ".git").exists():
        print(f"not a git repo: {workdir}", file=sys.stderr)
        return 2
    if not UPSTREAM_FILE.exists() and not args.upstream:
        print(f"missing {UPSTREAM_FILE}", file=sys.stderr)
        return 2
    sha = args.upstream or parse_upstream(UPSTREAM_FILE)["sha"]
    patches = patch_files(args.patch_dir)

    fetch = git(workdir, "fetch", "origin", check=False)
    if fetch.returncode != 0:
        log(f"warning: git fetch failed: {fetch.stderr.strip()}")

    dest = worktree_path(sha)
    try:
        prepare_worktree(workdir, sha, dest, patches)
        apply_patches(dest, patches, check_only=args.dry_run)
    except PatchReject as exc:
        write_replay_request(patches, exc.patch, exc.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        write_replay_request(patches, patches[0], str(exc))
        return 2

    if args.dry_run:
        log(f"dry-run ok at {dest}")
        return 0
    if args.no_cargo:
        log(f"applied without cargo at {dest}")
        return 0
    try:
        run_tests(dest)
        build_install(dest)
    except SystemExit:
        log(f"left worktree for inspection: {dest}")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
