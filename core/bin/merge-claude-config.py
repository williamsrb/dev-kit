#!/usr/bin/env python3
"""Merge ~/.claude.json (Desktop's config) into ~/.claude/.claude.json.

Takes the richer Desktop config as the base and carries over the entries that
only exist in the ~/.claude/ copy: MCP servers, project entries, onboarding
state and the counters that would otherwise regress.

Dry-run by default. Pass --apply to write, which backs up the destination first.

  python3 ~/.agents/bin/merge-claude-config.py            # show the plan
  python3 ~/.agents/bin/merge-claude-config.py --apply    # do it

Quit Claude Desktop and any `claude` CLI first: a running process rewrites its
config on exit and will undo this.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

INCOMING = Path.home() / ".claude.json"          # base (Desktop, richer)
DEST = Path.home() / ".claude" / ".claude.json"  # target (CLAUDE_CONFIG_DIR)

# Counters where the higher/newer value is the correct one to keep.
KEEP_MAX = ("numStartups", "routineFiredWatermark", "lastReleaseNotesSeen",
            "lastOnboardingVersion", "changelogLastFetched", "closedIssuesLastChecked")
# Dict-valued keys that should be unioned rather than replaced.
UNION_DICTS = ("announcementImpressions", "tipLifetimeShownCounts", "githubRepoPaths",
               "pluginUsage")


def load(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"missing: {path}")
    return json.loads(path.read_bytes())


def merge(base: dict, other: dict, notes: list[str]) -> dict:
    """Merge `other` (the ~/.claude/ copy) into `base` (Desktop's copy)."""
    out = json.loads(json.dumps(base))  # deep copy

    # MCP servers present only in the ~/.claude/ copy.
    dst_mcp = out.setdefault("mcpServers", {})
    for name, spec in (other.get("mcpServers") or {}).items():
        if name not in dst_mcp:
            dst_mcp[name] = spec
            notes.append(f"carry over MCP server: {name}")
        elif dst_mcp[name] != spec:
            notes.append(
                f"CONFLICT (kept Desktop's): MCP server {name} differs — "
                f"review by hand if the other definition was the right one"
            )

    # Project entries present only in the ~/.claude/ copy.
    dst_proj = out.setdefault("projects", {})
    for path, entry in (other.get("projects") or {}).items():
        if path not in dst_proj:
            dst_proj[path] = entry
            notes.append(f"carry over project entry: {path}")
        else:
            # Keep sticky per-project flags that only the other copy has.
            for flag in ("hasTrustDialogAccepted", "disabledMcpServers",
                         "enabledMcpjsonServers", "disabledMcpjsonServers",
                         "allowedTools", "hasCompletedProjectOnboarding"):
                if flag in entry and flag not in dst_proj[path]:
                    dst_proj[path][flag] = entry[flag]
                    notes.append(f"carry over {path} -> {flag}")

    # Onboarding: true wins, so the flow does not re-run.
    if other.get("hasCompletedOnboarding") and not out.get("hasCompletedOnboarding"):
        out["hasCompletedOnboarding"] = True
        notes.append("set hasCompletedOnboarding = true")

    # Counters: keep whichever side is further ahead.
    for key in KEEP_MAX:
        a, b = out.get(key), other.get(key)
        if b is not None and (a is None or (type(a) is type(b) and b > a)):
            out[key] = b
            notes.append(f"advance {key}: {a!r} -> {b!r}")

    # Impression/usage maps: union, keeping the larger count per entry.
    for key in UNION_DICTS:
        a, b = out.get(key), other.get(key)
        if not isinstance(b, dict):
            continue
        merged = dict(a) if isinstance(a, dict) else {}
        for k, v in b.items():
            if k not in merged:
                merged[k] = v
                notes.append(f"union {key}: +{k}")
            elif isinstance(v, int) and isinstance(merged[k], int) and v > merged[k]:
                merged[k] = v
        out[key] = merged

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the merged config")
    args = ap.parse_args()

    incoming, dest = load(INCOMING), load(DEST)
    notes: list[str] = []
    merged = merge(incoming, dest, notes)

    print(f"base (kept):   {INCOMING}  "
          f"{len(incoming.get('projects') or {})} projects, "
          f"{len(incoming.get('mcpServers') or {})} MCP servers")
    print(f"merged in:     {DEST}  "
          f"{len(dest.get('projects') or {})} projects, "
          f"{len(dest.get('mcpServers') or {})} MCP servers")
    print(f"result:        {len(merged.get('projects') or {})} projects, "
          f"{len(merged.get('mcpServers') or {})} MCP servers\n")

    if not notes:
        print("nothing to carry over — the base is already a superset.")
    for note in notes:
        print(f"  {'!! ' if note.startswith('CONFLICT') else '+ '}{note}")

    if not args.apply:
        print("\ndry run — nothing written. Re-run with --apply.")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for path in (DEST, INCOMING):
        backup = path.with_suffix(path.suffix + f".bak-{stamp}")
        shutil.copy2(path, backup)
        print(f"\nbacked up {path} -> {backup}")

    tmp = DEST.with_suffix(DEST.suffix + ".tmp")
    tmp.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(DEST)
    DEST.chmod(0o600)
    print(f"wrote {DEST}")
    print(f"\n{INCOMING} is now unused — delete it once you have confirmed "
          f"Claude Desktop starts correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
