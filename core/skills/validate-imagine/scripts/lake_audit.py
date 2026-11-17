#!/usr/bin/env python3
"""Mechanical audit of an imagine context lake: files, sections, counts, links, design, assets.

Exit codes (audit): 0 no blocker or major finding, 1 blocker or major findings, 2 bad input.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[2] / "imagine" / "scripts" / "registry.py"
TABLES = ("concepts", "characters", "terms", "actors", "places")
CORE = ("brief.md", "canon.json", "registry.json", "story.md", "findings.md")
REQUIRED = CORE + ("README.md", "persona.md", "research.md", "sources.md", "steps.md", "risks.md",
                   "registry.md", "plan.md", "run-log.md", "design.json")
SECTIONS = ("Brief and persona", "Research", "Canon", "Creation steps", "Challenges and opportunities", "Story",
            "Characters and places", "Plan around the story", "Art direction and assets", "Pros and cons",
            "Open assumptions", "Claims")
GAME_SECTIONS = ("Scenarios", "Mechanics", "Characters", "Skills", "Graphics", "Maps", "Quests")
SEVERITY = ("blocker", "major", "minor", "review", "note")
DESIGN_IMAGE_KEYS = ("medium", "projection", "palette.mode", "direction.drawing_style",
                     "direction.proportions", "direction.lighting")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
ACCESSED_RE = re.compile(r"accessed\s+(\d{4}-\d{2}-\d{2})")
UNVERIFIED_RE = re.compile(r"\(unverified\)")
URL_RE = re.compile(r"https?://[^\s)>\]]+")
PLACEHOLDER_CASE_RE = re.compile(r"\b(TODO|FIXME|TBD|XXX)\b|<[A-Z][A-Za-z0-9_ -]{2,}>")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
REVIEW_CAP = 40
SNAPSHOT_SKIP = {".validation", "raw", "sheets", "anchors"}


class BadInput(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lake_audit.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(required=True)
    audit = sub.add_parser("audit", help="Run every mechanical check and print the findings.")
    audit.add_argument("--dir", type=Path, default=Path("."), help="context-lake folder")
    audit.add_argument("--json", action="store_true")
    audit.add_argument("--today", help="YYYY-MM-DD, for the access-date check (default: today)")
    audit.set_defaults(func=cmd_audit)
    snap = sub.add_parser("snapshot", help="Copy the lake's text files to .validation/<run-id>/before/.")
    snap.add_argument("--dir", type=Path, default=Path("."))
    snap.add_argument("--run-id", help="default: UTC timestamp")
    snap.set_defaults(func=cmd_snapshot)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BadInput as exc:
        print(f"lake_audit: {exc}", file=sys.stderr)
        return 2


# --- commands ---------------------------------------------------------------


def cmd_audit(args: argparse.Namespace) -> int:
    lake: Path = args.dir
    if not (lake / "registry.json").exists() and not (lake / "findings.md").exists():
        raise BadInput(f"{lake} is not an imagine lake (no registry.json or findings.md)")
    today = parse_date(args.today) if args.today else dt.date.today()
    if today is None:
        raise BadInput("--today must be YYYY-MM-DD")
    findings = audit(lake, today)
    findings.sort(key=lambda f: (SEVERITY.index(f["severity"]), f["file"], f["kind"], f["ref"]))
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITY}
    failing = counts["blocker"] + counts["major"]
    if args.json:
        print(json.dumps({"ok": not failing, "counts": counts, "findings": findings}, indent=2))
    elif findings:
        for f in findings:
            print(f"{f['severity']}\t{f['kind']}\t{f['file']}\t{f['ref']}\t{f['detail']}")
    else:
        print("lake clean")
    return 1 if failing else 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    lake: Path = args.dir
    run_id = args.run_id or dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    target = lake / ".validation" / run_id / "before"
    if target.exists():
        raise BadInput(f"{target} already exists")
    copied = 0
    for path in sorted(lake.rglob("*")):
        rel = path.relative_to(lake)
        if SNAPSHOT_SKIP & set(rel.parts) or not path.is_file():
            continue
        if path.suffix not in {".md", ".json"}:
            continue
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target / rel)
        copied += 1
    print(json.dumps({"snapshot": str(target), "files": copied}))
    return 0


# --- audit ------------------------------------------------------------------


def audit(lake: Path, today: dt.date) -> list[dict]:
    out: list[dict] = []
    text = {name: read(lake / name) for name in REQUIRED if (lake / name).is_file()}
    out += check_files(lake, text)
    canon = load_json(lake / "canon.json")
    registry = load_json(lake / "registry.json")
    entities = [e for t in TABLES for e in (registry or {}).get(t, [])] if isinstance(registry, dict) else []
    for name, body in text.items():
        if name.endswith(".md") and name != "registry.md":
            out += check_placeholders(name, body)

    if "findings.md" in text:
        out += check_findings_sections(text, lake)
        out += check_claims(text, today)
    if "research.md" in text:
        out += check_research_marks(text["research.md"])
    out += check_wikilinks(text, entities)
    out += check_readme_counts(lake, text.get("README.md", ""), entities)
    out += check_registry_script(lake)
    if isinstance(registry, dict):
        out += check_story_root(registry, entities)
        out += check_entity_use(entities, text)
    if isinstance(canon, dict):
        out += check_canon_words(canon, entities, text)
        out += check_canon_reported(canon, text)
    out += check_design_and_assets(lake, load_json(lake / "design.json"), entities)
    out += check_expansions(lake, entities, text.get("run-log.md", ""))
    if "run-log.md" in text and not re.search(r"\bstop", text["run-log.md"], re.IGNORECASE):
        out.append(f("missing-stop-reason", "major", "run-log.md", "-", "run-log.md names no stop reason"))
    return out


def check_files(lake: Path, text: dict[str, str]) -> list[dict]:
    out = []
    for name in REQUIRED:
        path = lake / name
        if not path.is_file():
            out.append(f("missing-file", "blocker" if name in CORE else "major", name, "-", "required lake file is absent"))
        elif len(re.sub(r"\s", "", text[name])) < 40:
            out.append(f("empty-file", "major", name, "-", "file has under 40 non-space characters"))
    return out


def check_placeholders(name: str, body: str) -> list[dict]:
    out = []
    for number, line in enumerate(strip_code(body).splitlines(), 1):
        match = PLACEHOLDER_CASE_RE.search(line)
        if match:
            out.append(f("placeholder", "major", name, f"L{number}", f"unfinished marker '{match.group(0)}'"))
        elif re.search(r"lorem ipsum", line, re.IGNORECASE):
            out.append(f("placeholder", "major", name, f"L{number}", "lorem ipsum"))
    return out


def check_findings_sections(text: dict[str, str], lake: Path) -> list[dict]:
    out = []
    sections = parse_sections(text["findings.md"])
    titles = [(level, norm(title)) for level, title, _ in sections]
    h2 = [t for level, t in titles if level == 2]
    last = -1
    for want in SECTIONS:
        key = norm(want)
        index = next((i for i, t in enumerate(h2) if t.startswith(key)), None)
        if index is None:
            out.append(f("missing-section", "major", "findings.md", want, "template section is absent"))
            continue
        if index < last:
            out.append(f("section-order", "minor", "findings.md", want, "template section is out of order"))
        last = max(last, index)
        body = next(b for level, t, b in sections if level == 2 and norm(t).startswith(key))
        if len(re.sub(r"\s", "", body)) < 20:
            out.append(f("empty-section", "major", "findings.md", want, "section has no content"))
    for want in ("References", "Successes", "Failures", "Market"):
        if not any(level == 3 and t.startswith(norm(want)) for level, t in titles):
            out.append(f("missing-section", "major", "findings.md", f"Research / {want}", "research subsection is absent"))
    if is_game(text):
        for want in GAME_SECTIONS:
            if not any(heading_is(t, want) for _, t in titles):
                out.append(f("missing-section", "major", "findings.md", want, "game section set requires it"))
    return out


def check_claims(text: dict[str, str], today: dt.date) -> list[dict]:
    out = []
    findings = text["findings.md"]
    verified = len(ACCESSED_RE.findall(findings))
    unverified = len(UNVERIFIED_RE.findall(findings))
    stated = re.search(r"Verified:\s*(\d+)\.?\s*Unverified:\s*(\d+)", findings)
    loose = re.search(r"Verified:\s*(\d+).*?Unverified:\s*(\d+)", findings, re.DOTALL)
    if not stated and loose:
        out.append(f("claims-count", "note", "findings.md", "Claims", "claims line is not the template shape; counts not machine-checked"))
    elif not stated:
        out.append(f("claims-count", "major", "findings.md", "Claims", "no 'Verified: N. Unverified: N.' line"))
    elif (int(stated.group(1)), int(stated.group(2))) != (verified, unverified):
        out.append(f("claims-count", "major", "findings.md", "Claims",
                     f"states {stated.group(1)}/{stated.group(2)}, marks in the file count {verified}/{unverified}"))
    readme = re.search(r"(\d+)\s+verified\s*/\s*(\d+)\s+unverified", text.get("README.md", ""))
    if readme and stated and readme.groups() != stated.groups():
        out.append(f("claims-count", "major", "README.md", "counts",
                     f"README says {readme.group(1)}/{readme.group(2)}, findings.md says {stated.group(1)}/{stated.group(2)}"))
    listed = {u.rstrip(".,;") for u in URL_RE.findall(text.get("sources.md", ""))}
    for name in ("research.md", "findings.md"):
        body = text.get(name, "")
        for number, line in enumerate(body.splitlines(), 1):
            for date_text in ACCESSED_RE.findall(line):
                date = parse_date(date_text)
                if date is None or date > today:
                    out.append(f("bad-date", "major", name, f"L{number}", f"access date {date_text} is invalid or in the future"))
            for url in URL_RE.findall(line):
                if "sources.md" in text and url.rstrip(".,;") not in listed:
                    out.append(f("source-not-listed", "minor", name, f"L{number}", f"{url} is not in sources.md"))
    return out


def check_research_marks(body: str) -> list[dict]:
    out = []
    for start, block in list_items(body):
        if len(block) >= 60 and not ACCESSED_RE.search(block) and not UNVERIFIED_RE.search(block):
            out.append(f("claim-unmarked", "major", "research.md", f"L{start}",
                         "research item has neither a source+access date nor (unverified)"))
    return out


def check_wikilinks(text: dict[str, str], entities: list[dict]) -> list[dict]:
    ids = {e["id"] for e in entities}
    out = []
    for name, body in text.items():
        if not name.endswith(".md") or name in {"story.md", "steps.md", "registry.md"}:
            continue
        for ref in sorted({r.strip() for r in WIKILINK_RE.findall(strip_code(body))}):
            detail = "[[id]] outside story.md and steps.md" + ("" if ref in ids else f"; '{ref}' is not in the registry")
            out.append(f("wikilink-outside", "minor", name, ref, detail))
    return out


def check_readme_counts(lake: Path, readme: str, entities: list[dict]) -> list[dict]:
    if not readme:
        return []
    out = []
    manifest = manifest_entries(lake)
    actual = {
        "entities": len(entities),
        "expansion children": len([p for p in (lake / "expansions").glob("*.json") if not p.stem.startswith("P6")]) if (lake / "expansions").is_dir() else 0,
    }
    for label, value in actual.items():
        match = re.search(rf"(\d+)\s+{label}", readme)
        if match and int(match.group(1)) != value:
            out.append(f("readme-count", "major", "README.md", label, f"README says {match.group(1)}, lake has {value}"))
    links = {(e["id"], k.get("to"), k.get("rel")) for e in entities for k in e.get("links", [])}
    match = re.search(r"(\d+)\s+links", readme)
    if match and int(match.group(1)) != len(links):
        out.append(f("readme-count", "minor", "README.md", "links", f"README says {match.group(1)}, registry holds {len(links)} distinct links"))
    match = re.search(r"(\d+)\s+assets passed\s*/\s*(\d+)\s+failed", readme)
    if match and manifest is not None:
        passed = sum(1 for m in manifest if m.get("status") == "passed")
        failed = sum(1 for m in manifest if str(m.get("status", "")).startswith("failed"))
        if (int(match.group(1)), int(match.group(2))) != (passed, failed):
            out.append(f("readme-count", "major", "README.md", "assets",
                         f"README says {match.group(1)}/{match.group(2)}, manifest holds {passed}/{failed}"))
    return out


def check_registry_script(lake: Path) -> list[dict]:
    if not REGISTRY.is_file() or not (lake / "registry.json").is_file() or not (lake / "canon.json").is_file():
        return []
    proc = subprocess.run([sys.executable, str(REGISTRY), "check", "--json", "--dir", str(lake)],
                          capture_output=True, text=True, check=False)
    if proc.returncode == 2:
        return [f("registry-input", "blocker", "registry.json", "-", proc.stderr.strip() or "registry.py rejected the lake")]
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [f("registry-input", "blocker", "registry.json", "-", "registry.py check printed no JSON")]
    severity = {"axis-violation": "blocker"}
    return [f(item["kind"], severity.get(item["kind"], "major"), "registry.json", item["id"], item["detail"])
            for item in report.get("findings", [])]


def check_story_root(registry: dict, entities: list[dict]) -> list[dict]:
    root = registry.get("story_root")
    if not root:
        return [f("story-root", "blocker", "registry.json", "-", "story_root is not set")]
    if root not in {e["id"] for e in entities}:
        return [f("story-root", "blocker", "registry.json", root, "story_root is not a registry entity")]
    return []


def check_entity_use(entities: list[dict], text: dict[str, str]) -> list[dict]:
    pool = "\n".join(text.get(n, "") for n in ("story.md", "steps.md", "plan.md"))
    lowered = pool.casefold()
    out = []
    for e in entities:
        if not str(e.get("summary", "")).strip():
            out.append(f("entity-no-summary", "minor", "registry.json", e["id"], "entity has an empty summary"))
        if e["type"] not in {"character", "place", "actor"}:
            continue
        labels = [e["name"], *e.get("aliases", [])]
        if f"[[{e['id']}" in pool or any(label.casefold() in lowered for label in labels):
            continue
        out.append(f("entity-unused", "major", "registry.json", e["id"],
                     f"{e['type']} appears in none of story.md, steps.md, plan.md"))
    return out


def check_canon_words(canon: dict, entities: list[dict], text: dict[str, str]) -> list[dict]:
    """Candidates for the semantic pass: prose that names a forbidden or above-ceiling thing."""
    out: list[dict] = []
    regions = {r["id"]: r for r in canon.get("regions", []) if isinstance(r, dict) and "id" in r}
    rule_values = {(r.get("axis"), v) for r in canon.get("rules", []) if isinstance(r, dict)
                   for v in (r.get("values") if isinstance(r.get("values"), list) else [r.get("values")])}
    for e in entities:
        region = regions.get(e.get("region") or "")
        if not region:
            continue
        for axis in ("biome", "climate", "feature"):
            for value in as_list(region.get("forbidden", {}).get(axis)):
                if word_in(value, e.get("summary", "")) and (axis, value) not in rule_values:
                    out.append(f("forbidden-in-prose", "review", "registry.json", e["id"],
                                 f"summary names {axis} '{value}', forbidden in region '{region['id']}'"))
    common = None
    for region in regions.values():
        values = {v for axis in ("biome", "climate", "feature") for v in as_list(region.get("forbidden", {}).get(axis))}
        common = values if common is None else common & values
    scan = {n: text.get(n, "") for n in ("story.md", "plan.md")}
    for value in sorted(common or ()):
        for name, body in scan.items():
            for number, line in enumerate(body.splitlines(), 1):
                if word_in(value, line):
                    out.append(f("forbidden-in-prose", "review", name, f"L{number}", f"names '{value}', forbidden in every canon region"))
    for axis in ("era", "tech"):
        spec = canon.get("axes", {}).get(axis) or {}
        levels, ceiling = spec.get("levels", []), spec.get("ceiling")
        if ceiling not in levels:
            continue
        above = [v for v in levels[levels.index(ceiling) + 1:] if (axis, v) not in rule_values]
        for value in above:
            for e in entities:
                if word_in(value, f"{e['name']} {e.get('summary', '')}"):
                    out.append(f("above-ceiling-word", "review", "registry.json", e["id"], f"names {axis} level '{value}' above ceiling '{ceiling}'"))
            for name, body in scan.items():
                for number, line in enumerate(body.splitlines(), 1):
                    if word_in(value, line):
                        out.append(f("above-ceiling-word", "review", name, f"L{number}", f"names {axis} level '{value}' above ceiling '{ceiling}'"))
    if len(out) > REVIEW_CAP:
        dropped = len(out) - REVIEW_CAP
        out = out[:REVIEW_CAP] + [f("review-truncated", "note", "-", "-", f"{dropped} more word candidates not listed")]
    return out


def check_canon_reported(canon: dict, text: dict[str, str]) -> list[dict]:
    out = []
    findings = text.get("findings.md", "")
    if not findings:
        return out
    section = next((b for level, t, b in parse_sections(findings) if level == 2 and norm(t).startswith("open assumptions")), "")
    for item in canon.get("assumptions", []):
        if isinstance(item, str) and overlap(item, section) < 0.5:
            out.append(f("assumption-unlisted", "review", "findings.md", item[:40], "canon assumption is not in Open assumptions"))
    for rule in canon.get("rules", []):
        if isinstance(rule, dict) and rule.get("why") and overlap(str(rule["why"]), findings) < 0.6 and str(rule.get("id", "")) not in findings:
            out.append(f("rule-unreported", "minor", "findings.md", str(rule.get("id", "?")), "canon rule's reason is not in findings.md"))
    return out


def check_design_and_assets(lake: Path, design: object, entities: list[dict]) -> list[dict]:
    out: list[dict] = []
    if not isinstance(design, dict):
        return out
    ids = {e["id"] for e in entities}
    if isinstance(design.get("image"), dict):
        for key in DESIGN_IMAGE_KEYS:
            if not dig(design, key):
                out.append(f("design-incomplete", "major", "design.json", key, "image block needs this direction value"))
        colors = dig(design, "palette.colors") or []
        bad = [c for c in colors if not (isinstance(c, str) and HEX_RE.match(c))]
        if bad:
            out.append(f("bad-palette", "major", "design.json", "palette.colors", f"not #rrggbb: {bad[:3]}"))
        if dig(design, "palette.mode") == "exact" and not colors:
            out.append(f("bad-palette", "major", "design.json", "palette.colors", "exact palette lists no colors"))
    sizes = [list(s) for s in (dig(design, "image.sizes") or [])]
    seen: set[str] = set()
    assets = design.get("assets", [])
    for asset in assets if isinstance(assets, list) else []:
        aid = str(asset.get("id", "?"))
        if aid in seen:
            out.append(f("asset-duplicate", "major", "design.json", aid, "asset id listed twice"))
        seen.add(aid)
        if asset.get("entity") not in ids:
            out.append(f("asset-entity", "major", "design.json", aid, f"entity '{asset.get('entity')}' is not in the registry"))
        if sizes and asset.get("size") and list(asset["size"]) not in sizes:
            out.append(f("asset-size", "major", "design.json", aid, f"size {asset['size']} is not in image.sizes {sizes}"))
    manifest = manifest_entries(lake)
    if manifest is None:
        if (lake / "assets").is_dir() and any((lake / "assets").iterdir()):
            out.append(f("manifest-missing", "major", "assets/manifest.json", "-", "assets/ holds files but no manifest"))
        elif seen:
            out.append(f("assets-not-generated", "note", "design.json", "-", f"{len(seen)} listed assets, none generated"))
        return out
    by_id = {str(m.get("id")): m for m in manifest}
    for aid in sorted(seen - by_id.keys()):
        out.append(f("asset-missing", "major", "assets/manifest.json", aid, "design.json asset has no manifest entry"))
    for aid, m in sorted(by_id.items()):
        status = str(m.get("status", ""))
        if aid not in seen:
            out.append(f("asset-extra", "minor", "assets/manifest.json", aid, "manifest entry is not in design.json"))
        if status == "pending":
            out.append(f("asset-pending", "major", "assets/manifest.json", aid, "asset still waits for a provider"))
        elif status.startswith("failed"):
            out.append(f("asset-failed", "major", "assets/manifest.json", aid, status))
        elif status == "passed" and not (lake / "assets" / str(m.get("file", ""))).is_file():
            out.append(f("asset-file-missing", "major", "assets/manifest.json", aid, f"file '{m.get('file')}' is absent"))
        if m.get("entity") and m["entity"] not in ids:
            out.append(f("asset-entity", "major", "assets/manifest.json", aid, f"entity '{m['entity']}' is not in the registry"))
    return out


def check_expansions(lake: Path, entities: list[dict], run_log: str) -> list[dict]:
    out = []
    ids = {e["id"] for e in entities}
    for path in sorted((lake / "expansions").glob("*.json")) if (lake / "expansions").is_dir() else []:
        data = load_json(path)
        for raw in (data or {}).get("entities", []) if isinstance(data, dict) else []:
            eid = raw.get("id") if isinstance(raw, dict) else None
            if eid and eid not in ids and eid not in run_log:
                out.append(f("expansion-unlogged", "major", f"expansions/{path.name}", eid, "entity is neither in the registry nor in run-log.md"))
    return out


# --- helpers ----------------------------------------------------------------


def f(kind: str, severity: str, file: str, ref: str, detail: str) -> dict:
    return {"kind": kind, "severity": severity, "file": file, "ref": ref, "detail": detail}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def manifest_entries(lake: Path) -> list[dict] | None:
    data = load_json(lake / "assets" / "manifest.json")
    if isinstance(data, dict):
        data = data.get("assets")
    return [m for m in data if isinstance(m, dict)] if isinstance(data, list) else None


def parse_date(text: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def strip_code(body: str) -> str:
    return re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), body, flags=re.DOTALL)


def parse_sections(body: str) -> list[tuple[int, str, str]]:
    lines = strip_code(body).splitlines()
    heads = [(i, len(m.group(1)), m.group(2)) for i, line in enumerate(lines) if (m := HEADING_RE.match(line))]
    out = []
    for n, (i, level, title) in enumerate(heads):
        end = next((j for j, lv, _ in heads[n + 1:] if lv <= level), len(lines))
        out.append((level, title, "\n".join(lines[i + 1:end])))
    return out


def list_items(body: str) -> list[tuple[int, str]]:
    items: list[tuple[int, list[str]]] = []
    for number, line in enumerate(strip_code(body).splitlines(), 1):
        if re.match(r"^([-*]|\d+[.)])\s+", line):
            items.append((number, [line]))
        elif HEADING_RE.match(line):
            items.append((number, []))
        elif items and items[-1][1]:
            items[-1][1].append(line)
    return [(n, "\n".join(block)) for n, block in items if block]


def norm(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", title)).strip().casefold()


def heading_is(title: str, name: str) -> bool:
    key = name.casefold()
    return title.startswith(key) and not (key == "characters" and title.startswith("characters and places"))


def is_game(text: dict[str, str]) -> bool:
    head = text.get("persona.md", "")[:800] + text.get("brief.md", "")[:600]
    return bool(re.search(r"\bgames?\b", head, re.IGNORECASE))


def as_list(value: object) -> list:
    return [] if value is None else value if isinstance(value, list) else [value]


def dig(data: dict, dotted: str) -> object:
    for part in dotted.split("."):
        data = data.get(part) if isinstance(data, dict) else None
    return data


def word_in(value: str, text: str) -> bool:
    return any(re.search(rf"\b{re.escape(v)}s?\b", text, re.IGNORECASE) for v in {value, value.replace("-", " ")})


def overlap(needle: str, haystack: str) -> float:
    words = {w for w in re.findall(r"[a-z0-9]+", needle.casefold()) if len(w) > 3}
    if not words:
        return 1.0
    have = set(re.findall(r"[a-z0-9]+", haystack.casefold()))
    return len(words & have) / len(words)


if __name__ == "__main__":
    raise SystemExit(main())
