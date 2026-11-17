"""`agentctl release`: dependency graph of one release's tasks and notification drafts.

graph   infer hard / overlap / contradiction edges between the tasks of a release, print waves,
        the critical path and a Mermaid diagram. Read only: it writes one JSON under prds/releases/.
notify  write deduplicated drafts for the edges of a saved graph. It sends and posts nothing.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import agentctl_config
import agentctl_githost
import agentctl_jira
from agentctl_common import agents_home, markdown_sections


class ReleaseError(Exception):
    """User-facing failure of the release group."""


CONFIDENCE = {"low": 0, "medium": 1, "high": 2}
CLASS_RANK = {"overlap": 0, "hard": 1, "contradiction": 2}
SEARCH_FIELDS = ["summary", "status", "assignee", "issuelinks", "description"]
HARD_CUE = re.compile(r"(?i)\b(after|once|depends on|requires|blocked by|builds on)\b")
CREATE_VERB = re.compile(r"(?i)\b(create|add|new)\b")
PATH_TOKEN = re.compile(r"[\w@.+-]+(?:/[\w@.+-]+)+")
ASSESSMENT_CLASS = re.compile(r"(?i)\b(contradiction|dependency|overlap|context|duplicate|unrelated)\b")
CHECK_DIRS = ("tests/", "test/", "__tests__/")
CHECK_GLOBS = ("test_*.py", "*_test.py", "*.test.*", "*.spec.*")
MASS_MIN_MEMBERS = 4
MASS_SHARE = 0.30
EVIDENCE_CAP = 5
EXTERNAL_REF_CAP = 40
LABEL_CAP = 40


def is_check_file(path: str) -> bool:
    """A test or evidence file by location or name: `tests/`, `test_*.py`, `*.spec.*` and the like."""
    if path.startswith(CHECK_DIRS) or any(f"/{d}" in f"/{path}" for d in CHECK_DIRS):
        return True
    return any(fnmatch.fnmatch(path.rsplit("/", 1)[-1], pattern) for pattern in CHECK_GLOBS)


def load_related() -> Any:
    path = agents_home() / "skills" / "find-related-issues" / "scripts" / "related.py"
    if not path.is_file():
        path = Path(__file__).resolve().parents[1] / "skills" / "find-related-issues" / "scripts" / "related.py"
    spec = importlib.util.spec_from_file_location("agentctl_release_related", path)
    if spec is None or spec.loader is None:
        raise ReleaseError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def releases_dir() -> Path:
    return agents_home() / "prds" / "releases"


# --------------------------------------------------------------------------- members


def tracker_search(jql: str, token: str | None) -> dict[str, Any]:
    client = agentctl_jira.JiraClient(agentctl_jira.load_credentials())
    return client.search(jql, fields=SEARCH_FIELDS, max_results=100, next_page_token=token)


def release_slug(args: argparse.Namespace, keys: list[str]) -> str:
    if args.fix_version:
        return "fv-" + re.sub(r"[^\w.-]+", "-", args.fix_version).strip("-")
    if args.epic:
        return f"epic-{args.epic.upper()}"
    return "keys-" + hashlib.sha1(",".join(sorted(keys)).encode()).hexdigest()[:8]


def member_row(issue: dict[str, Any]) -> dict[str, Any]:
    fields = issue.get("fields") or {}
    markdown = (agentctl_jira.issue_bodies_as_markdown(issue).get("fields") or {}).get("description") or ""
    return {
        "key": issue["key"], "summary": fields.get("summary") or "",
        "status": (fields.get("status") or {}).get("name") or "",
        "status_category": ((fields.get("status") or {}).get("statusCategory") or {}).get("key"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "links": hard_links(fields), "description": markdown if isinstance(markdown, str) else "",
    }


def hard_links(fields: dict[str, Any]) -> list[tuple[str, str]]:
    """(from, to) pairs of `Blocks` links on this issue, as keys; the issue itself is filled in by the caller."""
    out = []
    for link in fields.get("issuelinks") or []:
        kind = link.get("type") or {}
        if (kind.get("name") or "").lower() != "blocks" and not (kind.get("outward") or "").lower().startswith("blocks"):
            continue
        if link.get("outwardIssue"):
            out.append(("self", link["outwardIssue"]["key"]))
        if link.get("inwardIssue"):
            out.append((link["inwardIssue"]["key"], "self"))
    return out


def resolve_members(args: argparse.Namespace, search: Callable[[str, str | None], dict[str, Any]],
                    warnings: list[str]) -> tuple[list[dict[str, Any]], str]:
    if args.keys:
        keys = [k.strip().upper() for k in args.keys.split(",") if k.strip()]
        jql = f"key in ({','.join(keys)})"
    elif args.fix_version:
        jql = 'fixVersion = "{}"'.format(args.fix_version.replace('"', '\\"'))
    else:
        key = args.epic.upper()
        jql = f'parent = {key} OR "Epic Link" = {key}'
    members: list[dict[str, Any]] = []
    token: str | None = None
    try:
        while True:
            page = search(jql, token)
            members += [member_row(i) for i in page.get("issues") or []]
            token = page.get("nextPageToken")
            if not token:
                break
    except (agentctl_jira.JiraError, OSError, ValueError) as exc:
        if not args.keys:
            raise ReleaseError(f"tracker unavailable, cannot resolve the release: {exc}") from exc
        warnings.append(f"tracker unavailable: {exc}; the tracker half of the graph is unverified")
        return [{"key": k, "summary": "", "status": "", "assignee": None, "links": [], "description": ""}
                for k in keys], "unavailable"
    if not token and (page.get("isLast") is False or len(page.get("issues") or []) >= 100):
        warnings.append("tracker result may be truncated; the tracker half of the graph is unverified")
    if args.keys:
        found = {m["key"] for m in members}
        members += [{"key": k, "summary": "", "status": "", "assignee": None, "links": [], "description": ""}
                    for k in keys if k not in found]
    cfg = agentctl_config.load()
    closed = [] if getattr(args, "include_closed", False) else [
        m["key"] for m in members if agentctl_config.is_closed_status(m["status"], m.get("status_category"), cfg)]
    if closed:
        warnings.append("left out, released or discarded: " + ", ".join(closed))
        members = [m for m in members if m["key"] not in closed]
    if not members:
        raise ReleaseError("the tracker returned no open member for this release")
    for member in members:
        member["links"] = [(member["key"] if a == "self" else a, member["key"] if b == "self" else b)
                           for a, b in member["links"]]
    return members, "ok"


# --------------------------------------------------------------------------- inputs


def read_text(path: Path) -> str:
    return path.read_text(errors="ignore") if path.is_file() else ""


def prd_slice(key: str, fallback: str) -> str:
    path = agents_home() / "prds" / f"{key}.md"
    if not path.is_file():
        return fallback
    wanted = [s["text"] for s in markdown_sections(path) if s["slug"] in ("description", "acceptance-criteria")]
    return "\n".join(wanted) or read_text(path)


def plan_docs(key: str) -> list[Path]:
    root = agents_home() / "plans"
    if (root / key).is_dir():
        return sorted((root / key).glob("*.md"))
    return [root / f"{key}.md"] if (root / f"{key}.md").is_file() else []


def plan_text(key: str) -> str:
    folder = agents_home() / "plans" / key
    impl = folder / "implementation.md"
    if impl.is_file():
        return read_text(impl)
    return "\n".join(read_text(p) for p in plan_docs(key))


def brief_classes(key: str) -> dict[str, tuple[str, float]]:
    """OTHER -> (class, file mtime): the class a brief under `<key>/related/` assigns to OTHER."""
    out: dict[str, tuple[str, float]] = {}
    folder = agents_home() / "prds" / key / "related"
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        text = read_text(path)
        _, _, tail = text.partition("## Assessment")
        if not tail or "_Not assessed" in tail:
            continue
        match = ASSESSMENT_CLASS.search(tail)
        if match:
            out[path.stem.upper()] = (match.group(1).lower(), path.stat().st_mtime)
    return out


def branch_ref(rel: Any, repo: Path, key: str) -> str | None:
    for ref in (key, f"origin/{key}"):
        if rel.git_ok(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            return ref
    return None


def member_files(rel: Any, repo: Path, base: str, member: dict[str, Any]) -> list[str]:
    key = member["key"]
    if member["branch"]:
        diff = rel.git(repo, "diff", "--name-only", f"{base}...{member['branch']}", check=False).split()
        if diff:
            return diff[: rel.FILE_CAP]
    for docs in (plan_docs(key), [agents_home() / "prds" / f"{key}.md"]):
        if paths := rel.doc_paths(repo, docs):
            return paths
    return []


def open_request(host: Any, branch: str | None, warnings: list[str], seen: set[str]) -> dict[str, Any] | None:
    if host is None or not branch:
        return None
    try:
        found = host.list_review_requests(source=branch.removeprefix("origin/"))
    except agentctl_githost.HostError as exc:
        if "git host unavailable" not in seen:
            seen.add("git host unavailable")
            warnings.append(f"git host unavailable: {exc}")
        return None
    return {"id": found[0].id, "url": found[0].web_url, "title": found[0].title} if found else None


# --------------------------------------------------------------------------- edges


class Edges:
    def __init__(self) -> None:
        self.rows: dict[tuple, dict[str, Any]] = {}

    def add(self, cls: str, a: str, b: str, confidence: str, signal: str, left: str, right: str, source: str) -> None:
        if cls == "hard":
            ident = (cls, a, b)
        else:
            ident = (cls, *sorted((a, b)))
        row = self.rows.setdefault(ident, {"from": a, "to": b, "class": cls, "confidence": confidence,
                                           "evidence": [], "source": source})
        if CONFIDENCE[confidence] > CONFIDENCE[row["confidence"]]:
            row["confidence"] = confidence
        if row["source"] != source and source not in row["source"].split("+"):
            row["source"] += f"+{source}"
        item = {"signal": signal, "left": left[:200], "right": right[:200]}
        if item not in row["evidence"] and len(row["evidence"]) < EVIDENCE_CAP:
            row["evidence"].append(item)

    def hard_between(self, a: str, b: str) -> list[dict[str, Any]]:
        return [r for r in self.rows.values() if r["class"] == "hard" and {r["from"], r["to"]} == {a, b}]


def collect_edges(rel: Any, repo: Path, base: str, members: list[dict[str, Any]], inputs: dict[str, dict[str, Any]],
                  warnings: list[str]) -> tuple[Edges, list[dict[str, Any]]]:
    edges = Edges()
    keys = [m["key"] for m in members]
    keyset = set(keys)
    # tracker links
    for member in members:
        for a, b in member["links"]:
            edges.add("hard", a, b, "high", "tracker-link", f"{a} blocks {b}", f"{b} is blocked by {a}", "tracker")
    # plan create/use
    tracked = set(rel.git(repo, "ls-files", check=False).splitlines())
    named: dict[str, dict[str, tuple[bool, str]]] = {}
    for key in keys:
        for line in inputs[key]["plan_text"].splitlines():
            if "http" in line:
                continue
            for token in PATH_TOKEN.findall(line):
                token = token.rstrip(".")
                if token in tracked or "." not in token.rsplit("/", 1)[-1]:
                    continue
                creator, text = named.setdefault(token, {}).get(key, (False, line.strip()))
                named[token][key] = (creator or bool(CREATE_VERB.search(line)), text)
    for path, owners in sorted(named.items()):
        ordered = sorted(owners)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                (ca, ta), (cb, tb) = owners[a], owners[b]
                if ca and not cb:
                    edges.add("hard", a, b, "high", "plan-create-use", f"{a}: {ta}", f"{b}: {tb}", "plan")
                elif cb and not ca:
                    edges.add("hard", b, a, "high", "plan-create-use", f"{b}: {tb}", f"{a}: {ta}", "plan")
                else:
                    edges.add("overlap", a, b, "high", "plan-path", f"{a}: {ta}", f"{b}: {tb}", "plan")
    # PRD cues
    for key in keys:
        text = inputs[key]["prd"]
        for match in rel.KEY_RE.finditer(text):
            other = match.group(1).upper()
            if other == key or other not in keyset:
                continue
            window = text[max(0, match.start() - 80): match.end() + 80]
            if HARD_CUE.search(window):
                edges.add("hard", other, key, "medium", "prd-cue", f"{key} PRD: {window.strip()}", other, "prd")
    # shared files, with the mass-change filter
    touched: dict[str, list[str]] = {}
    for key in keys:
        for path in inputs[key]["files"]:
            touched.setdefault(path, []).append(key)
    mass = {p for p, owners in touched.items() if len(owners) >= MASS_MIN_MEMBERS and len(owners) / len(keys) > MASS_SHARE}
    for path, owners in sorted(touched.items()):
        if path in mass:
            continue
        for i, a in enumerate(owners):
            for b in owners[i + 1:]:
                edges.add("overlap", a, b, "high", "shared-file", path, path, "files")
    # briefs
    newest = {k: inputs[k]["newest_commit"] for k in keys}
    for key in keys:
        for other, (cls, mtime) in inputs[key]["briefs"].items():
            if other not in keyset or other == key:
                continue
            stale = mtime < max(newest[key], newest[other])
            quote = f"brief {key}/related/{other}: {cls}"
            if cls == "contradiction":
                shared = set(inputs[key]["files"]) & set(inputs[other]["files"])
                edges.add("contradiction", key, other, ("low" if stale else "high" if shared else "medium"), "brief-assessment",
                          quote, f"{other} vs {key}", "brief")
            elif cls == "dependency":
                existing = edges.hard_between(key, other)
                if existing and not stale:
                    for row in existing:
                        row["confidence"] = "high"
                        if len(row["evidence"]) < EVIDENCE_CAP:
                            row["evidence"].append({"signal": "brief-assessment", "left": quote, "right": other})
                elif not existing:
                    note = f"dependency without direction: {', '.join(sorted((key, other)))}"
                    if note not in warnings:
                        warnings.append(note)
    # non-member unreleased branches on member files
    head = rel.git(repo, "rev-parse", "HEAD", check=False).strip()
    for ref in rel.unreleased_refs(repo, base, head, "")[:EXTERNAL_REF_CAP]:
        name = ref["name"]
        if name.upper() in keyset or any(k in keyset for k in rel.keys_in(name)):
            continue
        files = set(rel.git(repo, "diff", "--name-only", f"{base}...{ref['ref']}", check=False).split()) - mass
        for key in keys:
            shared = sorted(files & set(inputs[key]["files"]))
            if shared:
                edges.add("overlap", key, f"branch:{name}", "medium", "external-branch", shared[0], shared[0], "branch")
    conflicts = split_conflicts(edges)
    return edges, conflicts


def split_conflicts(edges: Edges) -> list[dict[str, Any]]:
    """Inferred hard edges that point against a tracker link are reported, not used."""
    conflicts = []
    for ident, row in list(edges.rows.items()):
        if row["class"] != "hard" or row["source"] == "tracker" or row["source"].startswith("tracker+"):
            continue
        reverse = edges.rows.get(("hard", row["to"], row["from"]))
        if reverse and reverse["source"].split("+")[0] == "tracker":
            conflicts.append({"inferred": row, "tracker": reverse})
            del edges.rows[ident]
    return conflicts


# --------------------------------------------------------------------------- waves


def schedule(keys: list[str], edges: list[dict[str, Any]]) -> dict[str, Any]:
    members = set(keys)
    succ: dict[str, set[str]] = {k: set() for k in keys}
    indeg = dict.fromkeys(keys, 0)
    for edge in edges:
        a, b = edge["from"], edge["to"]
        if edge["class"] == "hard" and a in members and b in members and b not in succ[a]:
            succ[a].add(b)
            indeg[b] += 1
    wave_of: dict[str, int] = {}
    current = sorted(k for k in keys if indeg[k] == 0)
    number = 0
    while current:
        number += 1
        nxt = []
        for k in current:
            wave_of[k] = number
            for s in succ[k]:
                indeg[s] -= 1
                if indeg[s] == 0:
                    nxt.append(s)
        current = sorted(nxt)
    left = [k for k in keys if k not in wave_of]
    cycles = tarjan(left, succ)
    in_cycle = {k for c in cycles for k in c}
    after = [k for k in left if k not in in_cycle]
    waves = [{"wave": n, "keys": sorted(k for k, w in wave_of.items() if w == n)} for n in range(1, number + 1)]
    best: dict[str, list[str]] = {}
    for k in sorted(wave_of, key=lambda x: (wave_of[x], x)):
        preds = [best[p] for p in wave_of if k in succ[p] and p in best]
        best[k] = max(preds, key=lambda p: (len(p), [-ord(c) for c in "".join(p)]), default=[]) + [k]
    path = max(best.values(), key=lambda p: (len(p), [-ord(c) for c in "".join(p)]), default=[])
    return {"wave_of": wave_of, "waves": waves, "cycles": cycles, "after_cycle": after,
            "critical_path": {"keys": path, "length": len(path)}}


def tarjan(nodes: list[str], succ: dict[str, set[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on: set[str] = set()
    out: list[list[str]] = []
    counter = [0]
    pool = set(nodes)

    def visit(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on.add(v)
        for w in sorted(succ[v] & pool):
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or v in succ[v]:
                out.append(sorted(comp))

    for v in sorted(nodes):
        if v not in index:
            visit(v)
    return sorted(out)


# --------------------------------------------------------------------------- build


def build_graph(args: argparse.Namespace, search: Callable[[str, str | None], dict[str, Any]] | None = None,
                host: Any = None) -> dict[str, Any]:
    rel = load_related()
    repo = Path(args.repo).resolve()
    warnings: list[str] = []
    try:
        base = rel.resolve_base(repo, None)
    except rel.ToolError as exc:
        raise ReleaseError(str(exc)) from exc
    members, tracker = resolve_members(args, search or tracker_search, warnings)
    if host is None:
        try:
            host = agentctl_githost.adapter_for(agentctl_config.load(), repo, agents_home() / ".auth")
        except (agentctl_githost.HostError, agentctl_config.ConfigError) as exc:
            warnings.append(f"git host unavailable: {exc}")
    seen: set[str] = {"git host unavailable"} if host is None else set()
    fetched = rel.refs_fetched_at(repo)
    if fetched is None:
        warnings.append("remote refs were never fetched; parallel branches may be missing")
    elif (datetime.now(UTC) - fetched).total_seconds() > rel.STALE_REFS_HOURS * 3600:
        warnings.append(f"remote refs last fetched {fetched.isoformat(timespec='seconds')}; parallel branches may be missing")
    inputs: dict[str, dict[str, Any]] = {}
    analysed_without_plan, no_check = [], []
    for member in members:
        key = member["key"]
        member["branch"] = branch_ref(rel, repo, key)
        member["open_request"] = open_request(host, member["branch"], warnings, seen)
        files = member_files(rel, repo, base, member)
        ptext = plan_text(key)
        stamp = rel.git(repo, "log", "-1", "--format=%ct", member["branch"], check=False).strip() if member["branch"] else ""
        inputs[key] = {"prd": prd_slice(key, member["description"]), "plan_text": ptext, "files": files,
                       "briefs": brief_classes(key), "newest_commit": float(stamp or 0)}
        has_prd = (agents_home() / "prds" / f"{key}.md").is_file() or bool(member["description"])
        if not plan_docs(key) and (has_prd or inputs[key]["briefs"]):
            analysed_without_plan.append(key)
        evidence = (agents_home() / "plans" / key / "evidence.md").is_file()
        named_checks = any(is_check_file(t) for t in PATH_TOKEN.findall(ptext)) or any(map(is_check_file, files))
        if not evidence and not named_checks:
            no_check.append(key)
    edges, conflicts = collect_edges(rel, repo, base, members, inputs, warnings)
    rows = sorted(edges.rows.values(), key=lambda r: (CLASS_RANK[r["class"]] * -1, r["from"], r["to"]))
    plan = schedule([m["key"] for m in members], rows)
    for k in plan["after_cycle"]:
        warnings.append(f"after_cycle: {k}")
    for m in members:
        m["wave"] = plan["wave_of"].get(m["key"])
    return {
        "release": release_slug(args, [m["key"] for m in members]),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "repo": str(repo), "base": base, "tracker": tracker,
        "members": [{k: m[k] for k in ("key", "summary", "status", "assignee", "branch", "open_request", "wave")}
                    for m in members],
        "waves": plan["waves"], "critical_path": plan["critical_path"], "edges": rows, "cycles": plan["cycles"],
        "conflicts": conflicts, "analysed_without_plan": analysed_without_plan, "no_replayable_check": no_check,
        "warnings": warnings,
    }


def save_graph(graph: dict[str, Any]) -> Path:
    folder = releases_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{graph['release']}.graph.json"
    path.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- output


def render_text(graph: dict[str, Any]) -> str:
    by_key = {m["key"]: m for m in graph["members"]}
    lines = [f"Release {graph['release']} ({len(graph['members'])} tasks, base {graph['base']}, tracker {graph['tracker']})", ""]
    for wave in graph["waves"]:
        lines.append(f"Wave {wave['wave']}")
        lines += [f"  {k}  {by_key[k]['summary']}  [{by_key[k]['status']}]" for k in wave["keys"]]
    nowave = [m["key"] for m in graph["members"] if m["wave"] is None]
    if nowave:
        lines += ["No wave", *[f"  {k}  {by_key[k]['summary']}" for k in nowave]]
    path = graph["critical_path"]
    lines += ["", f"Critical path ({path['length']} waves): " + " -> ".join(path["keys"]) if path["keys"]
              else "Critical path: none"]
    for cycle in graph["cycles"]:
        lines.append("Cycle: " + ", ".join(cycle))
    for cls in ("hard", "overlap", "contradiction"):
        group = [e for e in graph["edges"] if e["class"] == cls]
        if not group:
            continue
        lines += ["", f"{cls} edges"]
        for e in group:
            first = e["evidence"][0]
            lines.append(f"  {e['from']} -> {e['to']}  {e['confidence']}  {first['signal']}: {first['left']} | {first['right']}")
    for title, rows in (("Conflicts", [f"{c['inferred']['from']} -> {c['inferred']['to']} against tracker link "
                                        f"{c['tracker']['from']} -> {c['tracker']['to']}" for c in graph["conflicts"]]),
                        ("Analysed without plan", graph["analysed_without_plan"]),
                        ("No replayable check", graph["no_replayable_check"]), ("Warnings", graph["warnings"])):
        if rows:
            lines += ["", title, *[f"  {r}" for r in rows]]
    return "\n".join(lines)


def node_id(name: str) -> str:
    return re.sub(r"\W", "_", name)


def label(text: str) -> str:
    text = text if len(text) <= LABEL_CAP else text[: LABEL_CAP - 1] + "…"
    return text.replace('"', "#quot;").replace("<", "#lt;").replace(">", "#gt;").replace("[", "(").replace("]", ")")


def render_mermaid(graph: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    by_key = {m["key"]: m for m in graph["members"]}

    def node(key: str) -> str:
        summary = by_key[key]["summary"]
        return f'    {node_id(key)}["{label(f"{key}: {summary}" if summary else key)}"]'

    for wave in graph["waves"]:
        lines += [f'  subgraph W{wave["wave"]}["Wave {wave["wave"]}"]', *[node(k) for k in wave["keys"]], "  end"]
    nowave = [m["key"] for m in graph["members"] if m["wave"] is None]
    if nowave:
        lines += ['  subgraph WNONE["No wave"]', *[node(k) for k in nowave], "  end"]
    externals = sorted({n for e in graph["edges"] for n in (e["from"], e["to"]) if n not in by_key})
    lines += [f'  {node_id(x)}["{label(x)}"]' for x in externals]
    red = []
    for index, e in enumerate(graph["edges"]):
        a, b = node_id(e["from"]), node_id(e["to"])
        lines.append(f"  {a} {({'hard': '-->', 'overlap': '-.-', 'contradiction': '---'})[e['class']]} {b}")
        if e["class"] == "contradiction":
            red.append(index)
    lines += [f"  linkStyle {i} stroke:#d00,stroke-width:2px" for i in red]
    return "\n".join(lines)


def cmd_graph(args: argparse.Namespace) -> int:
    graph = build_graph(args)
    save_graph(graph)
    if args.json:
        print(json.dumps(graph, indent=2, ensure_ascii=False))
    elif args.format == "mermaid":
        print(render_mermaid(graph))
    else:
        print(render_text(graph))
    return 0


# --------------------------------------------------------------------------- notify


def edge_files(edge: dict[str, Any]) -> list[str]:
    return sorted({e["left"] for e in edge["evidence"] if e["signal"] in ("shared-file", "external-branch")})


def draft_text(edge: dict[str, Any], channel: str, recipient: str) -> str:
    a, b = edge["from"], edge["to"]
    quotes = "\n".join(f"- {e['signal']}: {e['left']} | {e['right']}" for e in edge["evidence"])
    cls = edge["class"]
    if cls == "hard":
        body = (f"Draft for {recipient}.\n\n{b} needs the work of {a} to land first. Proposed link: {a} blocks {b}.\n\n"
                f"Tracker comment (product language):\n\n{a} has to be delivered before {b} can build on it. "
                f"Please confirm the order or tell us what is missing.\n\nEvidence:\n{quotes}\n\n"
                f"Operator commands (nothing was sent):\n\n"
                f"    agentctl jira comment {b} --body-file <this file> --confirm-issue {b}\n"
                f"    agentctl jira link {a} --type Blocks --to {b}\n")
    elif cls == "contradiction":
        body = (f"Draft for {recipient}. Run `write-analyst-message` on this stub for the options before posting.\n\n"
                f"{a} and {b} ask for behaviour that cannot both hold.\n\nBoth sides:\n{quotes}\n\n"
                f"Operator commands (nothing was sent):\n\n"
                f"    agentctl jira comment {a} --body-file <this file> --confirm-issue {a}\n"
                f"    agentctl jira comment {b} --body-file <this file> --confirm-issue {b}\n")
    else:
        files = ", ".join(edge_files(edge)) or "the same area"
        medium = "review-request note" if channel == "review-request" else "Slack direct message"
        body = (f"{medium} for {recipient}.\n\n{a} and {b} both change {files}. The intent looks compatible, "
                f"so this is a heads-up about merge-conflict risk. Who lands first?\n\nEvidence:\n{quotes}\n")
    return f"# {cls}: {a} / {b}\n\n{body}"


def cmd_notify(args: argparse.Namespace) -> int:
    graph_path = releases_dir() / f"{args.release}.graph.json"
    if not graph_path.is_file():
        raise ReleaseError(f"no saved graph: {graph_path}")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    state_path = releases_dir() / f"{args.release}.notify.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {"records": []}
    records = {tuple(r["pair"]): r for r in state["records"]}
    out = Path(args.out) if args.out else releases_dir() / args.release / "notify"
    members = {m["key"]: m for m in graph["members"]}
    rel = load_related()
    repo = Path(graph["repo"])
    written = []
    for edge in graph["edges"]:
        if args.task and args.task.upper() not in (edge["from"], edge["to"]):
            continue
        pair = tuple(sorted((edge["from"], edge["to"])))
        files = edge_files(edge)
        old = records.get(pair)
        if old and CLASS_RANK[edge["class"]] <= CLASS_RANK[old["class"]] and files == old["files"]:
            continue
        sides = [edge["to"] if args.task.upper() == edge["from"] else edge["from"]] if args.task else list(pair)
        recipient = " and ".join(
            f"{k}: " + ((members.get(k) or {}).get("assignee") or last_author(rel, repo, (members.get(k) or {}).get("branch"))
                        or "the owner") for k in sides)
        requested = any((members.get(k) or {}).get("open_request") for k in pair)
        channel = "review-request" if edge["class"] == "overlap" and requested else (
            "slack" if edge["class"] == "overlap" else "tracker")
        out.mkdir(parents=True, exist_ok=True)
        draft = out / f"{pair[0]}__{pair[1]}__{edge['class']}.md"
        draft.write_text(draft_text(edge, channel, recipient), encoding="utf-8")
        record = {"pair": list(pair), "class": edge["class"], "files": files, "channel": channel,
                  "draft": str(draft), "date": datetime.now(UTC).date().isoformat(), "status": "drafted"}
        records[pair] = record
        written.append(record)
    state_path.write_text(json.dumps({"records": list(records.values())}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"release": args.release, "drafts": written}, indent=2))
    return 0


def last_author(rel: Any, repo: Path, branch: str | None) -> str | None:
    if not branch:
        return None
    return rel.git(repo, "log", "-1", "--format=%an", branch, check=False).strip() or None


# --------------------------------------------------------------------------- parser


def add_release_parsers(sub: Any) -> None:
    import agentctl_release_integration  # late: it imports this module

    agentctl_release_integration.add_integration_parsers(sub)
    graph = sub.add_parser("graph", help="Infer the dependency graph of a release and print waves, critical path, Mermaid.")
    exclusive = graph.add_mutually_exclusive_group(required=True)
    exclusive.add_argument("--fix-version", help="Tracker fixVersion name.")
    exclusive.add_argument("--epic", help="Epic key.")
    exclusive.add_argument("--keys", help="Comma separated issue keys.")
    graph.add_argument("--repo", default=".", help="Git repo of the release (default: cwd).")
    graph.add_argument("--include-closed", action="store_true",
                       help="Keep released or discarded members (default: leave them out).")
    graph.add_argument("--format", choices=("text", "mermaid"), default="text")
    graph.add_argument("--json", action="store_true", help="Print the saved JSON.")
    graph.set_defaults(func=cmd_graph)
    notify = sub.add_parser("notify", help="Write deduplicated notification drafts for a saved graph. Sends nothing.")
    notify.add_argument("--release", required=True, help="Release slug (the graph file name without .graph.json).")
    notify.add_argument("--task", help="Only edges of this task.")
    notify.add_argument("--out", help="Draft folder (default: prds/releases/<slug>/notify).")
    notify.set_defaults(func=cmd_notify)
