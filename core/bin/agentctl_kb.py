"""Owned-KB archive export and merge import for agentctl.

Pack/merge logic lives here. bin/agentctl only registers the group.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentctl_common import emit
from agentctl_jira import agents_home

OWNED_DEFAULT = ("_shared", "implementation", "testing", "validation", "worklog")
OWNED_INDEX = ("_shared", "calibration", "implementation", "testing", "validation", "worklog")
KNOWN_BUCKETS = frozenset((*OWNED_INDEX, "offline-reference"))
OFFLINE_BUCKET = "offline-reference"
SKIP_DIRS = frozenset({"scripts", "__pycache__", ".git"})
SKIP_FILES = frozenset({"llm-index.md"})
MANIFEST_NAME = "manifest.json"
FORMAT_VERSION = 1
DEFAULT_ARCHIVE_NAME = "kb-export.tar.zst"

_LLM_INDEX = None


class KbError(Exception):
    """User-facing kb command failure."""


def add_kb_parsers(group) -> None:
    export = group.add_parser(
        "export",
        help="Write a portable archive of owned KB How-tos.",
        description=(
            "Write a .tar.zst of selected owned-bucket How-tos (plus sibling "
            "examples.md). Default corpus omits offline-reference and calibration."
        ),
    )
    export.add_argument(
        "-o",
        "--output",
        type=Path,
        help=f"Archive path (default ./{DEFAULT_ARCHIVE_NAME}).",
    )
    export.add_argument(
        "--bucket",
        action="append",
        dest="buckets",
        metavar="NAME",
        help="Limit export to this owned bucket; repeatable.",
    )
    export.add_argument(
        "--include-offline",
        action="store_true",
        help="Also pack offline-reference. The only way to include that bucket.",
    )
    export.add_argument("--root", type=Path, help="KB root (default $AGENTS_HOME/kb).")
    export.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    export.set_defaults(func=cmd_export)

    import_parser = group.add_parser(
        "import",
        help="Merge a KB archive into a local KB root.",
        description=(
            "Merge How-tos from a .tar.zst into $AGENTS_HOME/kb or --root. "
            "Default is dry-run. Same sha256 is not a conflict."
        ),
    )
    import_parser.add_argument("archive", type=Path, help="Path to a .tar.zst export.")
    import_parser.add_argument("--root", type=Path, help="KB root (default $AGENTS_HOME/kb).")
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the merge without writing (default).",
    )
    import_parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the merge. Default is dry-run.",
    )
    import_parser.add_argument(
        "--conflict",
        choices=("fail", "skip", "replace"),
        default="fail",
        help="When a differing file already exists (default fail, exit 2).",
    )
    import_parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    import_parser.set_defaults(func=cmd_import)

    list_parser = group.add_parser(
        "list",
        help="List owned KB buckets and file counts.",
        description="Return bounded JSON for owned How-tos under $AGENTS_HOME/kb or --root.",
    )
    list_parser.add_argument(
        "--bucket",
        action="append",
        dest="buckets",
        metavar="NAME",
        help="Limit listing to this bucket; repeatable.",
    )
    list_parser.add_argument("--root", type=Path, help="KB root (default $AGENTS_HOME/kb).")
    list_parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    list_parser.set_defaults(func=cmd_list)


def cmd_export(args: argparse.Namespace) -> int:
    root = resolve_kb_root(args.root)
    selected = export_buckets(args.buckets, args.include_offline)
    entries = collect_entries(root, selected)
    dest = Path(args.output).expanduser() if args.output else Path.cwd() / DEFAULT_ARCHIVE_NAME
    dest = dest.resolve()
    manifest = build_manifest(entries, selected)
    write_archive(entries, manifest, dest)
    omitted = omitted_buckets(root, selected)
    emit({
        "status": "ok",
        "archive": str(dest),
        "files": len(entries),
        "bytes": sum(item["bytes"] for item in entries),
        "buckets": selected,
        "omitted": omitted,
    })
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    root = resolve_kb_root(args.root)
    archive = Path(args.archive).expanduser()
    if not archive.is_file():
        raise KbError(f"archive not found: {archive}")
    _manifest, files = read_archive(archive)
    plan = classify_import(root, files, args.conflict)
    write = bool(args.apply)
    if plan["conflicts"] and args.conflict == "fail":
        emit(import_payload("conflict", plan, []))
        return 2
    rebuilt: list[str] = []
    if write:
        apply_import(root, files, plan)
        rebuilt = rebuild_indexes(root)
    emit(import_payload("ok", plan, rebuilt))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = resolve_kb_root(args.root)
    selected = list_buckets(args.buckets)
    rows = []
    for name in selected:
        bucket = root / name
        if not bucket.is_dir():
            continue
        entries = collect_bucket_entries(root, name)
        missing = 0
        total = 0
        for item in entries:
            total += item["bytes"]
            if not _has_frontmatter(item["abs"]):
                missing += 1
        rows.append({
            "name": name,
            "files": len(entries),
            "bytes": total,
            "missing_frontmatter": missing,
        })
    emit({"status": "ok", "root": str(root), "buckets": rows})
    return 0


def resolve_kb_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root).expanduser()
    return agents_home() / "kb"


def export_buckets(names: list[str] | None, include_offline: bool) -> list[str]:
    if names:
        selected = []
        for name in names:
            _check_bucket(name)
            if name == OFFLINE_BUCKET and not include_offline:
                raise KbError("offline-reference requires --include-offline")
            if name not in selected:
                selected.append(name)
        if include_offline and OFFLINE_BUCKET not in selected:
            selected.append(OFFLINE_BUCKET)
        return selected
    selected = list(OWNED_DEFAULT)
    if include_offline:
        selected.append(OFFLINE_BUCKET)
    return selected


def list_buckets(names: list[str] | None) -> list[str]:
    if not names:
        return list(OWNED_DEFAULT)
    selected = []
    for name in names:
        _check_bucket(name)
        if name not in selected:
            selected.append(name)
    return selected


def _check_bucket(name: str) -> None:
    if name not in KNOWN_BUCKETS:
        raise KbError(f"unknown bucket: {name}")


def omitted_buckets(root: Path, selected: list[str]) -> list[str]:
    omitted = []
    for name in ("calibration", OFFLINE_BUCKET):
        if name not in selected and (root / name).is_dir():
            omitted.append(name)
    return omitted


def collect_entries(root: Path, selected: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for name in selected:
        entries.extend(collect_bucket_entries(root, name))
    return entries


def collect_bucket_entries(root: Path, name: str) -> list[dict[str, Any]]:
    bucket = root / name
    if not bucket.is_dir():
        return []
    if name == OFFLINE_BUCKET:
        paths = list(_iter_offline(bucket))
    else:
        paths = list(_iter_owned(bucket))
    entries = []
    for path in paths:
        digest, size = file_digest(path)
        rel = path.relative_to(root).as_posix()
        entries.append({
            "path": rel,
            "sha256": digest,
            "bytes": size,
            "abs": path,
        })
    return entries


def _iter_owned(bucket: Path) -> list[Path]:
    howtos: list[Path] = []
    for path in sorted(bucket.rglob("How-to-*.md")):
        if not path.is_file() or _excluded(path, bucket):
            continue
        howtos.append(path)
    extras: list[Path] = []
    for directory in {path.parent for path in howtos}:
        sibling = directory / "examples.md"
        if sibling.is_file() and not _excluded(sibling, bucket):
            extras.append(sibling)
    return howtos + extras


def _iter_offline(bucket: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(bucket.rglob("*.md")):
        if not path.is_file() or path.name in SKIP_FILES:
            continue
        if _excluded(path, bucket):
            continue
        paths.append(path)
    return paths


def _excluded(path: Path, root: Path) -> bool:
    if path.name in SKIP_FILES:
        return True
    return any(part in SKIP_DIRS for part in path.relative_to(root).parts)


def file_digest(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def build_manifest(entries: list[dict[str, Any]], buckets: list[str]) -> dict[str, Any]:
    return {
        "version": FORMAT_VERSION,
        "source": str(agents_home()),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "buckets": buckets,
        "files": [
            {"path": item["path"], "sha256": item["sha256"], "bytes": item["bytes"]}
            for item in entries
        ],
    }


def write_archive(entries: list[dict[str, Any]], manifest: dict[str, Any], dest: Path) -> None:
    zstd = _require_zstd()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "kb-export.tar"
        with tarfile.open(tar_path, "w") as tar:
            payload = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True).encode()
            info = tarfile.TarInfo(name=MANIFEST_NAME)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
            for item in entries:
                tar.add(item["abs"], arcname=item["path"], recursive=False)
        completed = subprocess.run(
            [zstd, "-f", "-q", "-o", str(dest), str(tar_path)],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise KbError(completed.stderr.strip() or "zstd compress failed")


def read_archive(archive: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    zstd = _require_zstd()
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "kb-export.tar"
        completed = subprocess.run(
            [zstd, "-d", "-f", "-q", "-o", str(tar_path), str(archive)],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise KbError(completed.stderr.strip() or "zstd decompress failed")
        members: dict[str, bytes] = {}
        with tarfile.open(tar_path, "r") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                rel = _safe_rel(member.name)
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                members[rel.as_posix()] = extracted.read()
    if MANIFEST_NAME not in members:
        raise KbError("archive is missing manifest.json")
    manifest = json.loads(members.pop(MANIFEST_NAME).decode())
    if not isinstance(manifest, dict):
        raise KbError("manifest.json is not an object")
    listed = {
        str(item["path"]): item
        for item in manifest.get("files", [])
        if isinstance(item, dict) and item.get("path")
    }
    files = {path: data for path, data in members.items() if path in listed}
    return manifest, files


def classify_import(
    root: Path,
    files: dict[str, bytes],
    conflict: str,
) -> dict[str, list[str]]:
    added: list[str] = []
    replaced: list[str] = []
    skipped: list[str] = []
    conflicts: list[str] = []
    for rel, data in sorted(files.items()):
        dest = root / _safe_rel(rel)
        digest = hashlib.sha256(data).hexdigest()
        if dest.is_file():
            existing = hashlib.sha256(dest.read_bytes()).hexdigest()
            if existing == digest:
                skipped.append(rel)
            elif conflict == "replace":
                replaced.append(rel)
            elif conflict == "skip":
                skipped.append(rel)
            else:
                conflicts.append(rel)
        else:
            added.append(rel)
    return {
        "added": added,
        "replaced": replaced,
        "skipped": skipped,
        "conflicts": conflicts,
    }


def apply_import(root: Path, files: dict[str, bytes], plan: dict[str, list[str]]) -> None:
    write_paths = set(plan["added"]) | set(plan["replaced"])
    for rel in sorted(write_paths):
        dest = root / _safe_rel(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(files[rel])


def rebuild_indexes(root: Path) -> list[str]:
    llm_index = load_llm_index()
    rebuilt: list[str] = []
    for name in OWNED_INDEX:
        bucket = root / name
        if bucket.is_dir():
            llm_index.write_bucket_indexes(bucket)
            rebuilt.append(name)
    return rebuilt


def import_payload(status: str, plan: dict[str, list[str]], rebuilt: list[str]) -> dict[str, Any]:
    return {
        "status": status,
        "added": plan["added"],
        "replaced": plan["replaced"],
        "skipped": plan["skipped"],
        "conflicts": plan["conflicts"],
        "index_rebuilt": rebuilt,
    }


def load_llm_index():
    global _LLM_INDEX
    if _LLM_INDEX is not None:
        return _LLM_INDEX
    path = Path(__file__).resolve().parent.parent / "kb" / "_shared" / "scripts" / "llm_index.py"
    spec = importlib.util.spec_from_file_location("agentctl_kb_llm_index", path)
    if spec is None or spec.loader is None:
        raise KbError(f"cannot load llm_index.py from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LLM_INDEX = module
    return module


def _require_zstd() -> str:
    exe = shutil.which("zstd")
    if not exe:
        raise KbError("zstd is not on PATH")
    return exe


def _safe_rel(path: str) -> Path:
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts:
        raise KbError(f"unsafe archive path: {path}")
    return rel


def _has_frontmatter(path: Path) -> bool:
    try:
        return path.read_text(encoding="utf-8").startswith("---")
    except OSError:
        return False
