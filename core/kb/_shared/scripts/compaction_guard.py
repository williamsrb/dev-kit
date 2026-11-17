#!/usr/bin/env python3
"""Meaning-preservation guard for prose compaction.

Compares each changed Markdown file with its pre-image and fails when an exact item
(fence, inline code, URL, link target, number, path, issue key, referenced heading,
frontmatter key or value) or a negation/limiter word count is lost.

Usage:
  compaction_guard.py --baseline DIR [--root DIR] [--waivers FILE] [--json] [FILE ...]

DIR holds the pre-images at their root-relative paths plus baseline.json
(see compaction_baseline.py). Without FILE arguments every baselined file whose
content differs from its pre-image is checked.

A waiver entry is {"file", "item"} plus one of:
  "owner": a rule source under rules/ that now carries the removed text;
  "reason": "duplicate" and "kept": text that must still be in the file;
  "reason": "example" and "note": why the removed illustrative example was redundant.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

NEGATIONS = ("not", "never", "no", "only", "unless", "except", "without", "must")
# Contractions fold into "not" so "do not" -> "don't" is neutral.
_CONTRACTION = re.compile(r"\b(?:cannot|\w+n't)\b", re.IGNORECASE)
_WORD = re.compile(r"[a-z']+")

_FENCE = re.compile(r"^\s*(```+|~~~+)")
_INLINE_CODE = re.compile(r"(`+)(.+?)\1")
_URL = re.compile(r"https?://[^\s)>\]\"'`]+")
_LINK_TARGET = re.compile(r"\]\(([^)\s]+)")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_PATH = re.compile(r"(?<![\w/])~?/?[\w.*-]+(?:/[\w.*{}-]+)+/?")
_ISSUE_KEY = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
_LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

ANCHOR_SKIP_DIRS = {"offline-reference", "skills-vendor", "node_modules", ".git", "__pycache__"}


def tokens(text: str) -> int:
    return len(text) // 4


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[: end + 5], text[end + 5 :]


def parse_frontmatter(fm: str) -> dict[str, str]:
    """Top-level keys mapped to their raw value text, continuation lines included."""
    keys: dict[str, str] = {}
    current = None
    for line in fm.splitlines()[1:-1]:
        m = re.match(r"^([A-Za-z0-9_-]+):(.*)$", line)
        if m:
            current = m.group(1)
            keys[current] = m.group(2).strip()
        elif current is not None:
            keys[current] += "\n" + line
    return keys


def classify(text: str) -> dict[str, list[str]]:
    """Split a file into frontmatter, fenced blocks, table lines, headings and prose lines."""
    fm, body = split_frontmatter(text)
    parts: dict[str, list[str]] = {"frontmatter": [fm] if fm else [], "code": [], "table": [], "heading": [], "prose": []}
    fence: list[str] | None = None
    marker = ""
    for line in body.splitlines():
        m = _FENCE.match(line)
        if fence is not None:
            fence.append(line)
            if m and m.group(1)[0] == marker[0] and len(m.group(1)) >= len(marker):
                parts["code"].append("\n".join(fence))
                fence = None
            continue
        if m:
            fence, marker = [line], m.group(1)
            continue
        if line.lstrip().startswith("|"):
            parts["table"].append(line)
        elif _HEADING.match(line):
            parts["heading"].append(line)
        else:
            parts["prose"].append(line)
    if fence:
        parts["code"].append("\n".join(fence))
    return parts


def slug(heading: str) -> str:
    text = _INLINE_CODE.sub(lambda m: m.group(2), heading).lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"\s", "-", text.strip())


def token_counts(text: str) -> dict[str, int]:
    parts = classify(text)
    return {
        "frontmatter": tokens("".join(parts["frontmatter"])),
        "code": tokens("\n".join(parts["code"])),
        "table": tokens("\n".join(parts["table"])),
        "prose": tokens("\n".join(parts["heading"] + parts["prose"])),
    }


def _strip_code(line: str) -> str:
    return _INLINE_CODE.sub(" ", line)


def extract_items(text: str) -> dict[str, Counter]:
    """Exact-item multisets keyed by kind."""
    parts = classify(text)
    items: dict[str, Counter] = {k: Counter() for k in ("fence", "code", "url", "link", "number", "path", "issue", "table")}
    items["fence"].update(parts["code"])
    items["table"].update(parts["table"])
    for line in parts["heading"] + parts["prose"] + parts["table"]:
        for m in _INLINE_CODE.finditer(line):
            items["code"][m.group(2)] += 1
        bare = _LIST_MARKER.sub("", _strip_code(line))
        items["url"].update(m.group(0).rstrip(".,;:") for m in _URL.finditer(bare))
        items["link"].update(m.group(1) for m in _LINK_TARGET.finditer(line))
        plain = _LINK_TARGET.sub("](", _URL.sub(" ", bare))
        items["issue"].update(_ISSUE_KEY.findall(plain))
        items["path"].update(p for p in _PATH.findall(plain) if "/" in p.strip("/"))
        items["number"].update(_NUMBER.findall(plain))
    return items


def negation_counts(text: str) -> Counter:
    parts = classify(text)
    counts: Counter = Counter()
    for line in parts["heading"] + parts["prose"] + parts["table"]:
        bare = _strip_code(line)
        counts["not"] += len(_CONTRACTION.findall(bare))
        bare = _CONTRACTION.sub(" ", bare)
        for word in _WORD.findall(bare.lower()):
            if word in NEGATIONS:
                counts[word] += 1
    return counts


def referenced_anchors(root: Path) -> set[str]:
    anchors: set[str] = set()
    for path in root.rglob("*.md"):
        if ANCHOR_SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        anchors.update(re.findall(r"\]\([^)\s#]*#([^)\s]+)\)", text))
    return anchors


def load_waivers(path: Path | None, root: Path) -> list[dict]:
    if not path:
        return []
    waivers = json.loads(path.read_text(encoding="utf-8"))
    for w in waivers:
        reason = w.get("reason")
        if reason == "duplicate" and not w.get("kept"):
            raise SystemExit(f"duplicate waiver needs the kept text: {w}")
        if reason == "example" and not w.get("note"):
            raise SystemExit(f"example waiver needs a note: {w}")
        if reason is None and not (root / "rules" / w.get("owner", "")).is_file():
            raise SystemExit(f"waiver owner is not a rule source under rules/: {w.get('owner')}")
        if reason not in (None, "duplicate", "example"):
            raise SystemExit(f"unknown waiver reason: {reason}")
    return waivers


def apply_waivers(file: str, failures: list[dict], waivers: list[dict], after: str = "") -> tuple[list[dict], list[dict]]:
    """Each waiver entry cancels one lost occurrence of its item in its file.

    A duplicate waiver only applies while its kept text is still in the file.
    """
    pool = [w for w in waivers if w["file"] == file and (w.get("reason") != "duplicate" or w["kept"] in after)]
    remaining, waived = [], []
    for f in failures:
        hit = next((w for w in pool if w["item"] in (f["item"], f"{f['kind']}:{f['item']}")), None)
        if hit and f["kind"] != "frontmatter":
            pool.remove(hit)
            waived.append({**f, "owner": hit.get("owner") or hit["reason"]})
        else:
            remaining.append(f)
    return remaining, waived


def check_file(rel: str, before: str, after: str, untagged: bool, anchors: set[str]) -> list[dict]:
    failures: list[dict] = []

    def fail(kind: str, item: str, line: int | None = None) -> None:
        failures.append({"file": rel, "kind": kind, "item": item, "line": line})

    def line_of(needle: str) -> int | None:
        for n, text in enumerate(before.splitlines(), 1):
            if needle in text:
                return n
        return None

    b_items, a_items = extract_items(before), extract_items(after)
    for kind, counter in b_items.items():
        for item, count in (counter - a_items[kind]).items():
            first = item.splitlines()[0]
            for _ in range(count):
                fail(kind, first, line_of(first))

    for word, count in (negation_counts(before) - negation_counts(after)).items():
        for _ in range(count):
            fail("negation", word)

    b_fm, a_fm = (
        parse_frontmatter(p["frontmatter"][0]) if p["frontmatter"] else {}
        for p in (classify(before), classify(after))
    )
    for key, value in b_fm.items():
        if key not in a_fm:
            fail("frontmatter", f"removed key {key}")
        elif a_fm[key] != value:
            fail("frontmatter", f"changed key {key}")
    if not untagged:
        for key in a_fm.keys() - b_fm.keys():
            fail("frontmatter", f"added key {key}")

    b_heads = {slug(_HEADING.match(h).group(2)): h for h in classify(before)["heading"]}
    a_heads = {slug(_HEADING.match(h).group(2)) for h in classify(after)["heading"]}
    for s, h in b_heads.items():
        if s in anchors and s not in a_heads:
            fail("heading", h.strip(), line_of(h))
    return failures


def _blocked(rel: str, item: str) -> dict:
    return {"file": rel, "status": "fail", "failures": [{"file": rel, "kind": "baseline", "item": item, "line": None}]}


def run(baseline: Path, root: Path, waivers_path: Path | None, files: list[str]) -> dict:
    meta = json.loads((baseline / "baseline.json").read_text(encoding="utf-8"))
    entries = {e["path"]: e for e in meta["files"]}
    waivers = load_waivers(waivers_path, root)
    anchors = referenced_anchors(root)
    names = files or [p for p, e in entries.items() if e.get("guard", True)]
    report: dict = {"files": [], "failed": 0, "totals": {}}
    before_total: Counter = Counter()
    after_total: Counter = Counter()
    for rel in names:
        entry = entries.get(rel)
        current = root / rel
        if entry is None or not current.is_file():
            report["files"].append(_blocked(rel, "no pre-image" if entry is None else "file missing"))
            report["failed"] += 1
            continue
        before = (baseline / rel).read_text(encoding="utf-8")
        after = current.read_text(encoding="utf-8")
        if before == after:
            continue
        failures = check_file(rel, before, after, bool(entry.get("untagged_howto")), anchors)
        failures, waived = apply_waivers(rel, failures, waivers, after)
        tb, ta = token_counts(before), token_counts(after)
        before_total.update(tb)
        after_total.update(ta)
        report["files"].append({"file": rel, "status": "fail" if failures else "pass", "failures": failures, "waived": waived, "before": tb, "after": ta})
        report["failed"] += bool(failures)
    report["totals"] = {"before": dict(before_total), "after": dict(after_total)}
    return report


def print_text(report: dict) -> None:
    for f in report["files"]:
        print(f"{f['status'].upper():5} {f['file']}")
        for x in f["failures"]:
            where = f":{x['line']}" if x["line"] else ""
            print(f"    lost {x['kind']}: {x['item']!r} ({f['file']}{where})")
        for x in f.get("waived", []):
            print(f"    waived {x['kind']}: {x['item']!r} (owner {x['owner']})")
    b, a = report["totals"]["before"], report["totals"]["after"]
    for key in ("prose", "code", "table", "frontmatter"):
        print(f"{key:12} {b.get(key, 0):>8} -> {a.get(key, 0):>8}")
    print(f"{report['failed']} failing of {len(report['files'])} changed files")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--root", type=Path, default=Path.home() / ".agents")
    ap.add_argument("--waivers", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("files", nargs="*", help="root-relative paths; default every changed baselined file")
    args = ap.parse_args(argv)
    report = run(args.baseline, args.root, args.waivers, args.files)
    if args.json:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print_text(report)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
