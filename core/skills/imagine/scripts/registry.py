#!/usr/bin/env python3
"""Context-lake registry for the imagine skill: init, merge, check, render.

Exit codes: 0 clean, 1 check findings, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

TABLES = {
    "concept": "concepts",
    "character": "characters",
    "term": "terms",
    "actor": "actors",
    "place": "places",
}
LEVEL_AXES = ("era", "tech")
REGION_AXES = ("biome", "climate", "feature")
STORY_FILES = ("story.md", "steps.md")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


class BadInput(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except BadInput as exc:
        print(f"registry: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="registry.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(required=False)

    def add(name: str, func, help_text: str) -> argparse.ArgumentParser:
        cmd = sub.add_parser(name, help=help_text, description=help_text)
        cmd.add_argument("--dir", default=".", type=Path, help="context-lake folder (default: current directory)")
        cmd.set_defaults(func=func)
        return cmd

    init = add("init", cmd_init, "Validate a canon, copy it into the lake, and create an empty registry.json.")
    init.add_argument("--canon", required=True, type=Path, help="canon JSON file")
    merge = add("merge", cmd_merge, "Merge one subagent result (entities, links) into registry.json.")
    merge.add_argument("result", type=Path, help="result JSON file")
    merge.add_argument("--origin", help="origin to stamp on new entities (default: result file stem)")
    check = add("check", cmd_check, "Report dangling links, orphans, duplicates, axis violations, story references.")
    check.add_argument("--json", action="store_true", help="print the JSON report")
    add("render", cmd_render, "Write registry.md: one table per entity type plus a links table per entity.")
    return parser


# --- commands ---------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    canon = load_json(args.canon)
    validate_canon(canon)
    lake: Path = args.dir
    lake.mkdir(parents=True, exist_ok=True)
    registry_path = lake / "registry.json"
    if registry_path.exists():
        raise BadInput(f"{registry_path} already exists")
    target = lake / "canon.json"
    if not target.exists() or target.resolve() != args.canon.resolve():
        write_json(target, canon)
    write_json(registry_path, {"version": 1, "story_root": None, **{t: [] for t in TABLES.values()}})
    print(json.dumps({"canon": str(target), "registry": str(registry_path)}))
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    lake: Path = args.dir
    registry = load_registry(lake)
    result = load_json(args.result)
    if not isinstance(result, dict):
        raise BadInput("result must be a JSON object")
    origin = args.origin or args.result.stem
    entities = result.get("entities", [])
    links = result.get("links", [])
    if not isinstance(entities, list) or not isinstance(links, list):
        raise BadInput("result 'entities' and 'links' must be lists")

    index = {e["id"]: e for e in iter_entities(registry)}
    added, updated = [], []
    for raw in entities:
        entity = normalize_entity(raw, origin)
        current = index.get(entity["id"])
        if current is None:
            registry[TABLES[entity["type"]]].append(entity)
            index[entity["id"]] = entity
            added.append(entity["id"])
            continue
        if current["type"] != entity["type"]:
            raise BadInput(f"{entity['id']}: type {entity['type']} conflicts with existing {current['type']}")
        merge_into(current, entity)
        updated.append(entity["id"])

    for link in links:
        if not isinstance(link, dict) or not all(isinstance(link.get(k), str) for k in ("from", "to", "rel")):
            raise BadInput(f"link needs string from, to, rel: {link!r}")
        source = index.get(link["from"])
        if source is None:
            raise BadInput(f"link from unknown entity {link['from']}")
        add_link(source, {"to": link["to"], "rel": link["rel"]})

    write_json(lake / "registry.json", registry)
    print(json.dumps({
        "added": added,
        "updated": updated,
        "candidates": result.get("candidates", []),
        "assumptions": result.get("assumptions", []),
    }, indent=2))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    lake: Path = args.dir
    canon = load_json(lake / "canon.json")
    validate_canon(canon)
    registry = load_registry(lake)
    findings = check_registry(canon, registry, lake)
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding["kind"]] = counts.get(finding["kind"], 0) + 1
    if args.json:
        print(json.dumps({"ok": not findings, "counts": counts, "findings": findings}, indent=2))
    elif findings:
        for finding in findings:
            print(f"{finding['kind']}\t{finding['id']}\t{finding['detail']}")
    else:
        print("registry clean")
    return 1 if findings else 0


def cmd_render(args: argparse.Namespace) -> int:
    lake: Path = args.dir
    registry = load_registry(lake)
    index = {e["id"]: e for e in iter_entities(registry)}
    lines = ["# Registry", ""]
    for table in TABLES.values():
        rows = registry[table]
        lines += [f"## {table.capitalize()}", ""]
        if not rows:
            lines += ["_None._", ""]
            continue
        lines += ["| id | name | summary | tags | origin |", "|---|---|---|---|---|"]
        for e in rows:
            lines.append(f"| `{e['id']}` | {cell(e['name'])} | {cell(e['summary'])} | {cell(format_tags(e))} | {cell(e['origin'])} |")
        lines.append("")
        for e in rows:
            if not e["links"]:
                continue
            lines += [f"### `{e['id']}` links", "", "| rel | to | type |", "|---|---|---|"]
            for link in e["links"]:
                target = index.get(link["to"])
                lines.append(f"| {cell(link['rel'])} | `{link['to']}` | {target['type'] if target else 'missing'} |")
            lines.append("")
    out = lake / "registry.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(str(out))
    return 0


# --- checks -----------------------------------------------------------------


def check_registry(canon: dict, registry: dict, lake: Path) -> list[dict]:
    entities = list(iter_entities(registry))
    ids = {e["id"] for e in entities}
    findings: list[dict] = []

    inbound: set[str] = set()
    for e in entities:
        for link in e["links"]:
            if link["to"] in ids:
                inbound.add(link["to"])
            else:
                findings.append(finding("dangling-link", e["id"], f"{link['rel']} -> {link['to']}"))

    root = registry.get("story_root")
    for e in entities:
        if e["id"] != root and not e["links"] and e["id"] not in inbound:
            findings.append(finding("orphan", e["id"], "no inbound or outbound link"))

    findings += check_duplicates(entities)
    for e in entities:
        findings += check_axes(canon, e)

    for name in STORY_FILES:
        path = lake / name
        if not path.exists():
            continue
        for ref in sorted(set(WIKILINK_RE.findall(path.read_text(encoding="utf-8")))):
            if ref.strip() not in ids:
                findings.append(finding("story-reference", ref.strip(), f"[[{ref.strip()}]] in {name} is not in the registry"))
    return findings


def check_duplicates(entities: list[dict]) -> list[dict]:
    owners: dict[str, set[str]] = {}
    seen_ids: dict[str, int] = {}
    for e in entities:
        seen_ids[e["id"]] = seen_ids.get(e["id"], 0) + 1
        for label in [e["name"], *e["aliases"]]:
            key = normalize_label(label)
            if key:
                owners.setdefault(key, set()).add(e["id"])
    findings = [finding("duplicate", i, f"id used {n} times") for i, n in seen_ids.items() if n > 1]
    for key, owner_ids in sorted(owners.items()):
        if len(owner_ids) > 1:
            findings.append(finding("duplicate", ",".join(sorted(owner_ids)), f"name or alias '{key}' shared"))
    return findings


def check_axes(canon: dict, entity: dict) -> list[dict]:
    findings = []
    tags = entity["tags"]
    region_id = entity.get("region")
    for axis in LEVEL_AXES:
        spec = canon["axes"].get(axis)
        if spec is None:
            continue
        levels, ceiling = spec["levels"], spec["ceiling"]
        for value in as_list(tags.get(axis)):
            if rule_allows(canon, axis, value, region_id):
                continue
            if value not in levels:
                findings.append(finding("axis-violation", entity["id"], f"{axis} '{value}' is not a canon level"))
            elif levels.index(value) > levels.index(ceiling):
                findings.append(finding("axis-violation", entity["id"], f"{axis} '{value}' is above the ceiling '{ceiling}'"))

    if entity["type"] == "place" and not region_id:
        return findings + [finding("axis-violation", entity["id"], "place has no region")]
    if not region_id:
        return findings
    region = next((r for r in canon["regions"] if r["id"] == region_id), None)
    if region is None:
        return findings + [finding("axis-violation", entity["id"], f"region '{region_id}' is not a canon region")]
    for axis in REGION_AXES:
        allowed = as_list(region.get("allowed", {}).get(axis))
        forbidden = as_list(region.get("forbidden", {}).get(axis))
        for value in as_list(tags.get(axis)):
            if rule_allows(canon, axis, value, region_id):
                continue
            if value in forbidden:
                findings.append(finding("axis-violation", entity["id"], f"{axis} '{value}' is forbidden in region '{region_id}'"))
            elif allowed and value not in allowed:
                findings.append(finding("axis-violation", entity["id"], f"{axis} '{value}' is not allowed in region '{region_id}'"))
    return findings


def rule_allows(canon: dict, axis: str, value: str, region_id: str | None) -> bool:
    for rule in canon.get("rules", []):
        if rule.get("axis") != axis or value not in as_list(rule.get("values")):
            continue
        if rule.get("region") in (None, region_id):
            return True
    return False


# --- shapes -----------------------------------------------------------------


def validate_canon(canon: object) -> None:
    if not isinstance(canon, dict):
        raise BadInput("canon must be a JSON object")
    axes = canon.get("axes")
    if not isinstance(axes, dict):
        raise BadInput("canon needs an 'axes' object")
    for axis in LEVEL_AXES:
        spec = axes.get(axis)
        if spec is None:
            continue
        levels = spec.get("levels") if isinstance(spec, dict) else None
        if not isinstance(levels, list) or not levels or spec.get("ceiling") not in levels:
            raise BadInput(f"canon axis '{axis}' needs non-empty 'levels' and a 'ceiling' from them")
    regions = canon.get("regions", [])
    if not isinstance(regions, list) or not all(isinstance(r, dict) and isinstance(r.get("id"), str) for r in regions):
        raise BadInput("canon 'regions' must be a list of objects with an 'id'")
    for region in regions:
        if not all(isinstance(region.get(key, {}), dict) for key in ("allowed", "forbidden")):
            raise BadInput(f"canon region '{region['id']}': 'allowed' and 'forbidden' must be objects keyed by axis")
    canon.setdefault("regions", [])
    rules = canon.setdefault("rules", [])
    if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
        raise BadInput("canon 'rules' must be a list of objects")


def normalize_entity(raw: object, origin: str) -> dict:
    if not isinstance(raw, dict):
        raise BadInput(f"entity must be an object: {raw!r}")
    entity_id = raw.get("id")
    if not isinstance(entity_id, str) or not ID_RE.match(entity_id):
        raise BadInput(f"entity id must be kebab-case: {entity_id!r}")
    if raw.get("type") not in TABLES:
        raise BadInput(f"{entity_id}: type must be one of {', '.join(TABLES)}")
    if not isinstance(raw.get("name"), str) or not raw["name"].strip():
        raise BadInput(f"{entity_id}: name is required")
    if not isinstance(raw.get("tags", {}), dict):
        raise BadInput(f"{entity_id}: tags must be an object")
    links = raw.get("links", [])
    if not isinstance(links, list) or not all(isinstance(lk, dict) and isinstance(lk.get("to"), str) for lk in links):
        raise BadInput(f"{entity_id}: links must be a list of {{to, rel}}")
    aliases = raw.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(a, str) for a in aliases):
        raise BadInput(f"{entity_id}: aliases must be a list of strings")
    entity = {
        "id": entity_id,
        "type": raw["type"],
        "name": raw["name"].strip(),
        "aliases": aliases,
        "summary": str(raw.get("summary", "")),
        "tags": raw.get("tags", {}),
        "links": [],
        "origin": str(raw.get("origin") or origin),
    }
    if raw.get("region") is not None:
        entity["region"] = str(raw["region"])
    for link in links:
        add_link(entity, {"to": link["to"], "rel": str(link.get("rel", "related"))})
    return entity


def merge_into(current: dict, incoming: dict) -> None:
    current["aliases"] += [a for a in incoming["aliases"] if a not in current["aliases"]]
    if not current["summary"]:
        current["summary"] = incoming["summary"]
    for axis, value in incoming["tags"].items():
        current["tags"].setdefault(axis, value)
    if "region" in incoming:
        current.setdefault("region", incoming["region"])
    for link in incoming["links"]:
        add_link(current, link)


def add_link(entity: dict, link: dict) -> None:
    if link not in entity["links"]:
        entity["links"].append(link)


def load_registry(lake: Path) -> dict:
    registry = load_json(lake / "registry.json")
    if not isinstance(registry, dict) or not all(isinstance(registry.get(t), list) for t in TABLES.values()):
        raise BadInput(f"{lake / 'registry.json'}: needs a list per table ({', '.join(TABLES.values())})")
    return registry


def iter_entities(registry: dict):
    for table in TABLES.values():
        yield from registry[table]


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BadInput(f"{path}: not found") from None
    except json.JSONDecodeError as exc:
        raise BadInput(f"{path}: invalid JSON ({exc})") from None


def write_json(path: Path, data: object) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


# --- helpers ----------------------------------------------------------------


def finding(kind: str, entity_id: str, detail: str) -> dict:
    return {"kind": kind, "id": entity_id, "detail": detail}


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def normalize_label(label: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", label.lower()).split())


def format_tags(entity: dict) -> str:
    parts = [f"{axis}: {', '.join(as_list(value))}" for axis, value in entity["tags"].items()]
    if entity.get("region"):
        parts.insert(0, f"region: {entity['region']}")
    return "; ".join(parts)


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    sys.exit(main())
