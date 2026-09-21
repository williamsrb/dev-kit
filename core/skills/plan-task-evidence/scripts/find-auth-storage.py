#!/usr/bin/env python3
"""Find Playwright storage-state JSON files in standard evidence-auth locations.

Every candidate is opened and its cookie domains / origins are reported. The
filename is a guess, never a lock: a state saved as `user.json` routinely holds
the only session for the environment under test. Candidates are ranked, never
dropped - newest first, host matches ahead of the rest.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def agents_home() -> Path:
    raw = os.environ.get("AGENTS_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".agents"


def search_specs() -> tuple[tuple[str, Path], ...]:
    home = agents_home()
    return (
        (str(home / ".auth" / "*.json"), home / ".auth"),
        (str(home / ".playwright-mcp" / "*.json"), home / ".playwright-mcp"),
        (str(home / ".playwright-mcp" / "auth" / "*.json"), home / ".playwright-mcp" / "auth"),
        ("./playwright/.auth/*.json", Path("playwright") / ".auth"),
        ("./.auth/*.json", Path(".auth")),
        ("./*.json", Path(".")),
    )


def read_storage_state(path: Path) -> dict | None:
    """Parse the file, or None when it is not a Playwright storage state."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    cookies = data.get("cookies")
    origins = data.get("origins")
    if not (isinstance(cookies, list) and isinstance(origins, list)):
        return None
    return data


def state_hosts(data: dict) -> list[str]:
    """Hosts this state actually authenticates - the only reliable identity."""
    hosts: set[str] = set()
    for cookie in data.get("cookies", []):
        domain = (cookie or {}).get("domain")
        if isinstance(domain, str) and domain:
            hosts.add(domain.lstrip("."))
    for origin in data.get("origins", []):
        value = (origin or {}).get("origin")
        if isinstance(value, str) and value:
            hosts.add(value.split("://")[-1].split("/")[0])
    return sorted(hosts)


def host_of(target: str) -> str:
    """Accept a bare host, a URL, or an env token; return a comparable host."""
    return target.strip().split("://")[-1].split("/")[0].lower()


def covers(wanted: str, hosts: list[str]) -> bool:
    for host in hosts:
        host = host.lower()
        if wanted == host or wanted.endswith("." + host) or host.endswith("." + wanted):
            return True
    return False


def collect(cwd: Path) -> list[dict]:
    """Every storage state in the search paths, newest first, contents read."""
    found: list[dict] = []
    seen: set[Path] = set()
    for label, rel in search_specs():
        directory = rel.expanduser() if str(rel).startswith("~") or rel.is_absolute() else cwd / rel
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            data = read_storage_state(path)
            if data is None:
                continue
            seen.add(resolved)
            stat = path.stat()
            found.append(
                {
                    "path": str(resolved),
                    "location": label,
                    "name": path.name,
                    "hosts": state_hosts(data),
                    "cookies": len(data.get("cookies", [])),
                    "mtime": int(stat.st_mtime),
                }
            )
    # Recency is the default tiebreak: the newest state is the one most likely
    # to still authenticate.
    found.sort(key=lambda item: item["mtime"], reverse=True)
    return found


def rank(found: list[dict], host: str | None, prefer: str | None) -> list[dict]:
    """Annotate and order candidates. Nothing is ever filtered out."""
    wanted = host_of(host) if host else None
    hint = prefer.lower() if prefer else None

    for item in found:
        item["host_match"] = bool(wanted and covers(wanted, item["hosts"]))
        item["name_hint"] = bool(
            hint and (hint in item["name"].lower() or any(hint in h.lower() for h in item["hosts"]))
        )

    # Host match is evidence, the name hint is only a nudge, recency breaks ties.
    found.sort(key=lambda item: (item["host_match"], item["name_hint"], item["mtime"]), reverse=True)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Project workspace root for relative search paths (default: cwd)",
    )
    parser.add_argument(
        "--host",
        help=(
            "Testing base URL or host under test. Candidates whose cookie domains "
            "cover it rank first, whatever the file is called."
        ),
    )
    parser.add_argument(
        "--prefer",
        help=(
            "Env/realm token used only as a tiebreak hint. It never excludes a "
            "candidate - prefer --host."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    cwd = args.cwd.resolve()
    matches = rank(collect(cwd), args.host, args.prefer)

    if args.json:
        payload = {
            "cwd": str(cwd),
            "host": args.host,
            "recommended": matches[0]["path"] if matches else None,
            "host_matches": [m["path"] for m in matches if m["host_match"]],
            "matches": matches,
        }
        print(json.dumps(payload, indent=2))
        return 0 if matches else 1

    if not matches:
        print("none")
        return 1

    for index, item in enumerate(matches):
        hosts = ",".join(item["hosts"]) or "-"
        flags = []
        if item["host_match"]:
            flags.append("host-match")
        if index == 0:
            flags.append("recommended")
        print(f"{item['path']}\t{item['location']}\t{hosts}\t{','.join(flags) or '-'}")

    if args.host and not any(m["host_match"] for m in matches):
        print(
            f"# no candidate carries cookies for {host_of(args.host)} - "
            "read the list above before asking the operator for a login",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
