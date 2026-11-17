#!/usr/bin/env python3
"""Copy mcpServers from each Claude .claude.json into mcp-backup.json.

Default root: ~/.claude. Writes only the MCP server
map (env and headers included, with secret values replaced by "<redacted>"), not
the rest of the volatile config. Destination mode is 0600. Unchanged payloads are
left in place.

  python3 ~/.agents/bin/backup-claude-mcp.py --dry-run
  python3 ~/.agents/bin/backup-claude-mcp.py
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import json
import logging
import os
import sys
import tempfile
import time
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger(__name__)

HOME = Path.home()
DEFAULT_ROOTS = (
    HOME / ".claude",
)
SOURCE_NAME = ".claude.json"
DEST_NAME = "mcp-backup.json"
DEFAULT_LOCK = HOME / ".local" / "share" / "claude-mcp-backup" / "backup.lock"
DEFAULT_LOG = HOME / ".local" / "share" / "claude-mcp-backup" / "backup.log"
DEST_MODE = 0o600
SECRET_HINTS = ("TOKEN", "SECRET", "AUTHORIZATION", "PASSWORD", "BEARER", "KEY")
REDACTED = "<redacted>"


def acquire_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "w", encoding="utf-8")  # noqa: SIM115 - held open to keep the lock
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EAGAIN):
            fh.close()
            raise SystemExit("another backup is already running") from e
        raise
    fh.write(str(os.getpid()))
    fh.flush()
    return fh


def setup_logging(log_path: Path, verbose: bool) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def load_mcp_servers(source: Path) -> dict:
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{source} root is not an object")  # noqa: TRY004 - malformed input, not a programming error
    mcp = data.get("mcpServers")
    if mcp is None:
        return {}
    if not isinstance(mcp, dict):
        raise ValueError(f"{source} mcpServers is not an object")  # noqa: TRY004 - malformed input, not a programming error
    return mcp


def redact_secrets(mcp_servers: dict) -> dict:
    """Copy of the server map with secret-named env and header values replaced.

    Same hint list as mcp/install.py; the real values live in the env files and .auth.
    """
    out = {}
    for name, spec in mcp_servers.items():
        spec = dict(spec)
        for field in ("env", "headers"):
            if isinstance(spec.get(field), dict):
                spec[field] = {
                    key: REDACTED if any(hint in key.upper() for hint in SECRET_HINTS) else value
                    for key, value in spec[field].items()
                }
        out[name] = spec
    return out


def encode_backup(mcp_servers: dict) -> bytes:
    payload = {"mcpServers": redact_secrets(mcp_servers)}
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    return (text + "\n").encode("utf-8")


def atomic_write(dest: Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".mcp-backup.", suffix=".tmp", dir=dest.parent)
    tmp = Path(tmp_name)
    try:
        os.write(fd, data)
        os.fsync(fd)
        os.fchmod(fd, DEST_MODE)
    finally:
        os.close(fd)
    os.replace(tmp, dest)


def backup_one(root: Path, *, dry_run: bool) -> str:
    source = root / SOURCE_NAME
    dest = root / DEST_NAME
    if not source.is_file():
        raise FileNotFoundError(source)
    mcp = load_mcp_servers(source)
    data = encode_backup(mcp)
    names = sorted(mcp)
    if dest.is_file() and dest.read_bytes() == data:
        logger.info("unchanged %s servers=%d", dest, len(names))
        return "unchanged"
    action = "write" if dest.exists() else "create"
    logger.info(
        "%s %s -> %s servers=%d names=%s",
        "would " + action if dry_run else action,
        source,
        dest,
        len(names),
        ",".join(names),
    )
    if dry_run:
        return "would-write"
    atomic_write(dest, data)
    return "wrote"


def main(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--log", type=Path, default=DEFAULT_LOG)
    p.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    p.add_argument(
        "--root",
        action="append",
        type=Path,
        help="Claude config dir (repeatable). Default: ~/.claude",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    setup_logging(args.log, args.verbose)
    lock_fh = acquire_lock(args.lock)
    t0 = time.time()
    roots = tuple(r.expanduser() for r in (args.root or DEFAULT_ROOTS))
    wrote = unchanged = failed = 0
    try:
        logger.info("backup start roots=%s dry_run=%s", [str(r) for r in roots], args.dry_run)
        for root in roots:
            try:
                result = backup_one(root, dry_run=args.dry_run)
            except Exception:
                logger.exception("backup failed for %s", root)
                failed += 1
                continue
            if result == "unchanged":
                unchanged += 1
            else:
                wrote += 1
        logger.info(
            "backup done wrote=%d unchanged=%d failed=%d elapsed=%.2fs",
            wrote,
            unchanged,
            failed,
            time.time() - t0,
        )
        return 1 if failed else 0
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fh.close()


if __name__ == "__main__":
    raise SystemExit(main())
