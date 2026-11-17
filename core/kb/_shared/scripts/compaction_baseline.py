#!/usr/bin/env python3
"""Build the compaction scope list and baseline (pre-images plus baseline.json).

Usage: compaction_baseline.py [--root DIR] [--out DIR] [--repo DIR ...]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compaction_guard import token_counts

VENDORED_SKILLS = {
    "archify", "debug-xp-app", "upgrade-xp-app",
    "use-enonic-cli", "humanize-text", "draw-diagram", "playwright-cli",
}
MIN_PROSE_TOKENS = 150
EXTRA_SKILL_MD = ("skills-vendor/cursor/export-canvas-html/SKILL.md",)


def tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", "*.md", "*.mdc"], capture_output=True, text=True, check=True)
    return [p for p in out.stdout.split("\0") if p]


def is_template(rel: str) -> bool:
    parts = rel.split("/")
    name = parts[-1].lower()
    return "template" in name or any(p in ("template", "templates") for p in parts[:-1])


def skill_set(rel: str) -> str | None:
    parts = rel.split("/")
    if parts[0] == "skills" and len(parts) > 2 and parts[1] not in VENDORED_SKILLS:
        if parts[-1] == "README.md" or is_template(rel):
            return None
        return "skill_md" if rel == f"skills/{parts[1]}/SKILL.md" else "reference"
    if rel in EXTRA_SKILL_MD or (parts[0] == "skills-vendor" and parts[-1] == "SKILL.md" and parts[2] == "orchestrate"):
        return "skill_md"
    return None


def rule_set(rel: str) -> str | None:
    if rel == "rules/AGENTS.md" or (rel.startswith("rules/claude/") and rel.endswith(".md")):
        return "always_on"
    if rel.startswith("rules/agents.d/") or rel == "rules/BASE.md" or (rel.startswith("rules/") and rel.count("/") == 1 and rel.endswith(".mdc") and rel != "rules/BASE.mdc"):
        return "rule_source"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.home() / ".agents")
    ap.add_argument("--out", type=Path, default=Path("/var/tmp/compaction-baseline/2026-10-21"))
    ap.add_argument("--repo", type=Path, nargs="*", default=[Path.home() / "Workspace/Projects/devkit"])
    args = ap.parse_args()
    root = args.root.resolve()

    seen: set[int] = set()
    files: list[dict] = []
    sets: dict[str, dict] = {k: {"files": 0, "tokens": 0, "prose": 0} for k in ("always_on", "skill_md", "reference", "kb")}
    skipped: list[dict] = []

    for rel in tracked(root):
        path = root / rel
        if path.is_symlink() or not path.is_file():
            continue
        ino = path.stat().st_ino
        if ino in seen:
            continue
        name = rel.split("/")[-1]
        group = rule_set(rel) or skill_set(rel)
        untagged = False
        if group is None and rel.startswith("kb/") and "offline-reference" not in rel and name != "llm-index.md" and rel.endswith(".md"):
            text = path.read_text(encoding="utf-8")
            group = "kb"
            untagged = name.startswith("How-to-") and not text.startswith("---\n")
            if not untagged:
                counts = token_counts(text)
                sets["kb"]["files"] += 1
                sets["kb"]["tokens"] += sum(counts.values())
                sets["kb"]["prose"] += counts["prose"]
                seen.add(ino)
                continue
        if group is None:
            continue
        seen.add(ino)
        text = path.read_text(encoding="utf-8")
        counts = token_counts(text)
        entry = {"path": rel, "set": group, "tokens": counts, "total": sum(counts.values()), "guard": group != "always_on"}
        if untagged:
            entry["untagged_howto"] = True
        if group in ("skill_md", "reference", "rule_source") and counts["prose"] < MIN_PROSE_TOKENS:
            entry["skip"] = f"prose {counts['prose']} < {MIN_PROSE_TOKENS}"
            skipped.append({"path": rel, "reason": entry["skip"]})
        key = group if group in sets else None
        if key:
            sets[key]["files"] += 1
            sets[key]["tokens"] += entry["total"]
            sets[key]["prose"] += counts["prose"]
        files.append(entry)

    for entry in files:
        dest = args.out / entry["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text((root / entry["path"]).read_text(encoding="utf-8"), encoding="utf-8")

    def head(repo: Path) -> str:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

    meta = {
        "metric": "len/4",
        "root": str(root),
        "heads": {str(r): head(r) for r in [root, *args.repo]},
        "sets": sets,
        "skipped": skipped,
        "files": files,
    }
    (args.out / "baseline.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sets": sets, "heads": meta["heads"], "in_scope": sum(1 for e in files if "skip" not in e and e["guard"]), "skipped": len(skipped), "untagged": sum(1 for e in files if e.get("untagged_howto"))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
