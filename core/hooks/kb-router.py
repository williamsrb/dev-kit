#!/usr/bin/env python3
"""Match a user prompt against installed skills and KB indexes.

Vendor-neutral core. Reads {"prompt": "..."} on stdin, writes matches on stdout
as plain text for the agent to see before it answers.

Exists because routing gates that depend on the agent remembering to look do not
hold. Skill descriptions and KB llm-index.md files already carry the keywords;
this makes the lookup fire on every prompt instead of on recall.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

AGENTS = Path.home() / ".agents"
KB = AGENTS / "kb"
SKILLS = AGENTS / "skills"

MIN_HITS = 3          # distinct signal terms before a row is reported
MAX_ROWS = 4          # keep the injection small; noise defeats the purpose
MIN_TERM_LEN = 4

# Terms too common in this harness to discriminate between guides.
STOP = {
    "with", "from", "that", "this", "when", "what", "have", "into", "your",
    "them", "then", "than", "they", "will", "make", "does", "should", "would",
    "code", "file", "files", "using", "used", "user", "task", "work", "need",
    "want", "please", "check", "read", "write", "runs", "running", "just",
    "also", "only", "here", "there", "about", "which", "where", "each", "same",
    "more", "most", "some", "all", "any", "how", "why", "the", "and", "for",
    # Harness boilerplate: present in nearly every skill blurb and KB path,
    # so it carries no routing signal.
    "agents", "skill", "skills", "aliases", "recommendedrole", "prerequisites",
    "procedure", "pitfalls", "scope", "follow", "implement", "explore",
}


def normalize(text: str) -> str:
    t = text.lower()
    t = re.sub(r"\bxp\s*([578])\b", r"xp\1", t)
    t = re.sub(r"\bcs\s*([56])(?:\.x)?\b", r"cs\1", t)
    t = t.replace("5.x", "5x").replace("6.x", "6x")
    t = re.sub(r"\b2\s*d\b", "2d", t)
    t = re.sub(r"\b3\s*d\b", "3d", t)
    return t


def terms(text: str) -> set[str]:
    """Signal tokens from a blob of text.

    Length floor is MIN_TERM_LEN, except for tokens carrying a digit: "xp7",
    "xp8", "2d" and issue keys are short and discriminating, while 3-char
    words ("not", "the") are pure noise.

    Adjacent pairs are also kept as hyphen compounds ("content-studio") so a
    two-word topic can satisfy MIN_HITS against a topic facet.
    """
    # Hyphen is a separator, not part of a token: keeping it made
    # "how-to-execute-an-xp7-to-xp8-app-upgrade-locally" a single term that
    # could never match anything.
    words = re.findall(r"[a-z0-9]{2,}", normalize(text))
    base = [
        w for w in words
        if w not in STOP and (len(w) >= MIN_TERM_LEN or any(c.isdigit() for c in w))
    ]
    compounds = [f"{left}-{right}" for left, right in zip(base, base[1:])]
    return set(base) | {c for c in compounds if c not in STOP}


def index_rows() -> list[tuple[str, str, str]]:
    """(label, haystack, topic) for every KB guide listed in an llm-index.md.

    Nested folder indexes are included. Chooser rows that point at another
    llm-index.md are skipped so a testing scan does not inject every project.
    """
    rows = []
    for index in KB.rglob("llm-index.md"):
        if "scripts" in index.parts:
            continue
        rel_dir = index.parent.relative_to(KB).as_posix()
        for line in index.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("#") or "\t" not in line:
                continue
            parts = line.split("\t")
            path = parts[0].strip()
            if not path.endswith(".md"):
                continue
            if path.endswith("llm-index.md"):
                continue
            topic = parts[2].strip() if len(parts) >= 5 else ""
            skills = parts[3].strip() if len(parts) >= 5 else ""
            keywords = parts[-1] if len(parts) > 2 else ""
            label = f"~/.agents/kb/{rel_dir}/{path}"
            haystack = f"{rel_dir} {path} {topic} {skills} {keywords}"
            rows.append((label, haystack, topic))
    return rows


def skill_rows() -> list[tuple[str, str]]:
    """(label, haystack) for every installed skill's frontmatter description."""
    rows = []
    for skill in sorted(SKILLS.glob("*/SKILL.md")):
        head = skill.read_text(encoding="utf-8", errors="replace")[:1200]
        desc = ""
        match = re.search(r"^description:\s*(.+)$", head, re.MULTILINE)
        if match:
            desc = match.group(1).strip().strip('"').strip("'")
        rows.append((f"skill: {skill.parent.name}", f"{skill.parent.name} {desc}"))
    return rows


def score(prompt_terms: set[str], haystack: str, weights: dict[str, float], topic: str = "") -> tuple[int, float]:
    """Return (distinct hits, IDF-weighted score).

    Unweighted counting lets boilerplate decide the ranking: every per-part
    evidence guide shares "capture", "evidence" and "part", so a whole family
    ties and alphabetical order picks the winner. Weighting by inverse document
    frequency makes a term that appears in one guide outrank one in forty.
    Topic overlap is boosted so a Content Studio prompt does not lose to a
    sibling project whose body once mentioned Content Studio.
    """
    matched = prompt_terms & terms(haystack)
    weight = sum(weights.get(term, 1.0) for term in matched)
    if topic:
        topic_terms = terms(topic.replace("-", " ") + " " + topic)
        if topic_terms & prompt_terms:
            weight *= 1.8
    if "offline-reference/" in haystack:
        weight *= 0.55
    return len(matched), weight


def idf(rows: list[tuple[str, str]]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for _, haystack in rows:
        for term in terms(haystack):
            counts[term] = counts.get(term, 0) + 1
    total = max(len(rows), 1)
    return {term: math.log(total / count) + 0.1 for term, count in counts.items()}


def collapse_parent(label: str) -> str:
    """Directory used for family collapse.

    Owned How-tos collapse per folder. Offline-reference collapses to the
    catalog root so a topic match does not list every page in that catalog.
    """
    marker = "/offline-reference/"
    if marker in label:
        catalog = label.split(marker, 1)[1].split("/", 1)[0]
        return f"~/.agents/kb/offline-reference/{catalog}"
    return label.rsplit("/", 1)[0] if "/" in label else label


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    prompt = payload.get("prompt", "") if isinstance(payload, dict) else ""
    if not prompt.strip():
        return 0
    stripped = prompt.lstrip()
    if stripped.startswith("/"):
        return 0
    if "<task-notification>" in prompt:
        return 0

    prompt_terms = terms(prompt)
    if not prompt_terms:
        return 0

    index = index_rows()
    rows = skill_rows() + [(label, haystack) for label, haystack, _topic in index]
    topics = {label: topic for label, _haystack, topic in index}
    weights = idf(rows)
    scored = []
    for label, haystack in rows:
        hits, weight = score(prompt_terms, haystack, weights, topics.get(label, ""))
        if hits >= MIN_HITS:
            scored.append((weight, label))
    if not scored:
        return 0

    scored.sort(key=lambda row: (-row[0], row[1]))
    # Drop rows far weaker than the best match rather than padding to MAX_ROWS.
    cutoff = scored[0][0] * 0.55
    kept = [(w, l) for w, l in scored if w >= cutoff]
    lines, seen_dirs = [], {}
    for weight, label in kept:
        parent = collapse_parent(label)
        seen_dirs[parent] = seen_dirs.get(parent, 0) + 1
    emitted = set()
    for weight, label in kept:
        parent = collapse_parent(label)
        # Three-plus siblings from one directory means the family matched, not a
        # specific guide. Point at the directory instead of listing an arbitrary
        # alphabetical slice of it. Offline catalogs collapse to the catalog root
        # so a Content Studio prompt does not dump 17 product pages.
        if seen_dirs[parent] >= 3:
            if parent in emitted:
                continue
            emitted.add(parent)
            lines.append(f"  {parent}/  ({seen_dirs[parent]} guides matched)")
        else:
            lines.append(f"  {label}")
        if len(lines) >= MAX_ROWS:
            break
    sys.stdout.write(
        "Possibly relevant (matched on keywords, not yet verified — open before "
        "hand-rolling an approach):\n" + "\n".join(lines) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
