#!/usr/bin/env python3
"""Find issues related to a task, and extract a status brief from one of them.

scan  TASK-ID  rank issues related through the tracker, unreleased branches and released history
brief KEY      status / context / handoff of one related issue (Jira + git + local PRD and plan)

Read only: no fetch, no tracker write. Jira goes through `agentctl jira`; git runs with the
caller's refs as they are.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

for _root in (Path(__file__).resolve().parents[3], Path.home() / ".agents"):
    if (_root / "bin" / "agentctl_config.py").is_file():
        sys.path.insert(0, str(_root / "bin"))
        break
import agentctl_config

_SETTINGS = agentctl_config.load()  # tracker key pattern and base branches live in .agentctl, not here

SEP_REC, SEP_FLD = "\x1e", "\x1f"
LOG_FORMAT = f"{SEP_REC}%H{SEP_FLD}%aI{SEP_FLD}%an{SEP_FLD}%s{SEP_FLD}%b{SEP_FLD}"
KEY_RE = agentctl_config.key_pattern(_SETTINGS)
KEY_RE_ANYCASE = re.compile(KEY_RE.pattern, re.IGNORECASE)
NOT_PROJECTS = {"UTF", "ISO", "SHA", "MD", "CVE", "RFC", "CSS", "HTML", "TLS", "SSL", "AES", "RSA", "ES", "GPT", "PEP"}
BASE_CANDIDATES = tuple(agentctl_config.section(_SETTINGS, "git")["base_branches"])
SECRET_RE = re.compile(r"(?i)\b(pass(?:word|wd)?|secret|token|api[_-]?key)\b(\s*[:=]\s*)\S+")
STALE_REFS_HOURS = 24
HISTORY_COMMIT_CAP = 400
FILE_CAP = 60
PRD_KEY_CAP = 15
ENRICH_CAP = 40
SCAN_FIELDS = ["summary", "status", "issuetype", "assignee", "parent", "subtasks", "issuelinks", "fixVersions", "updated"]
BRIEF_FIELDS = SCAN_FIELDS + ["description", "reporter", "comment"]
RELATION_SCORE = {"parent": 20, "sibling": 25, "child": 25, "mentioned-in-prd": 15, "linked": 35, "duplicate": 40, "via": 15}


class ToolError(Exception):
    pass


def agents_home() -> Path:
    return Path(os.environ.get("AGENTS_HOME") or Path.home() / ".agents")


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "--literal-pathspecs", "-C", str(repo), *args], capture_output=True, text=True, errors="replace", check=False
    )
    if check and proc.returncode:
        raise ToolError(f"git {' '.join(args[:2])}: {proc.stderr.strip()[:200]}")
    return proc.stdout


def git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False).returncode == 0


def redact(text: str) -> str:
    return SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[redacted]", text)


def keys_in(text: str, *, any_case: bool = False) -> list[str]:
    found: list[str] = []
    for match in (KEY_RE_ANYCASE if any_case else KEY_RE).finditer(text):
        key = match.group(1).upper()
        if key.split("-")[0] not in NOT_PROJECTS and key not in found:
            found.append(key)
    return found


def parse_log(raw: str) -> list[dict]:
    commits = []
    for record in raw.split(SEP_REC)[1:]:
        parts = record.split(SEP_FLD)
        if len(parts) < 6:
            continue
        sha, date, author, subject, body, tail = parts[:6]
        commits.append({
            "sha": sha, "date": date, "author": author, "subject": subject, "body": body.strip(),
            "files": [line for line in tail.splitlines() if line.strip()],
        })
    return commits


def resolve_base(repo: Path, explicit: str | None) -> str:
    for ref in ([explicit] if explicit else BASE_CANDIDATES):
        if git_ok(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            return ref
    raise ToolError("no base branch found; pass --base (tried: %s)" % (explicit or ", ".join(BASE_CANDIDATES)))


def refs_fetched_at(repo: Path) -> datetime | None:
    path = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "FETCH_HEAD", check=False).strip() or "/nonexistent")
    return datetime.fromtimestamp(path.stat().st_mtime, UTC) if path.is_file() else None


def unreleased_refs(repo: Path, base: str, head_sha: str, own_branch: str) -> list[dict]:
    """Local and remote branches with commits that are not in base, minus the task's own branch."""
    raw = git(repo, "for-each-ref", "--no-merged", base, "--format=%(refname)\t%(refname:short)\t%(objectname)\t%(committerdate:iso-strict)",
              "refs/heads", "refs/remotes")
    seen: dict[str, dict] = {}
    for line in raw.splitlines():
        refname, short, sha, date = line.split("\t")
        name = short.split("/", 1)[1] if refname.startswith("refs/remotes/") else short
        if refname.endswith("/HEAD") or sha == head_sha or name == own_branch or name == "HEAD":
            continue
        if name not in seen or date > seen[name]["date"]:
            seen[name] = {"ref": short, "name": name, "sha": sha, "date": date}
    return list(seen.values())


def own_files(repo: Path, base: str, explicit: list[str], task_id: str) -> tuple[str, list[str]]:
    if explicit:
        return "args", explicit[:FILE_CAP]
    diff = git(repo, "diff", "--name-only", f"{base}...HEAD", check=False).split()
    if diff:
        return "diff", diff[:FILE_CAP]
    home = agents_home()
    plans = home / "plans" / task_id
    plan_docs = sorted(plans.glob("*.md")) if plans.is_dir() else [home / "plans" / f"{task_id}.md"]
    for source, docs in (("plan", plan_docs), ("prd", [home / "prds" / f"{task_id}.md"])):
        if paths := doc_paths(repo, docs):
            return source, paths
    return "none", []


def doc_paths(repo: Path, docs: list[Path]) -> list[str]:
    """Repo files a plan or PRD names in its text."""
    text = "\n".join(p.read_text(errors="ignore") for p in docs if p.is_file())
    tracked = set(git(repo, "ls-files", check=False).splitlines())
    tokens = (t.rstrip(".") for t in re.findall(r"[\w@.+-]+(?:/[\w@.+-]+)*", text))
    return list(dict.fromkeys(t for t in tokens if t in tracked))[:FILE_CAP]


def prd_keys(task_id: str) -> list[str]:
    prd = agents_home() / "prds" / f"{task_id}.md"
    if not prd.is_file():
        return []
    counts: dict[str, int] = {}
    for key in KEY_RE.findall(prd.read_text(errors="ignore")):
        if key != task_id and key.split("-")[0] not in NOT_PROJECTS:
            counts[key] = counts.get(key, 0) + 1
    return sorted(counts, key=lambda k: (-counts[k], k))[:PRD_KEY_CAP]


# ---------------------------------------------------------------- Jira (via agentctl)

def agentctl() -> list[str]:
    return [shutil.which("agentctl") or str(agents_home() / "bin" / "agentctl")]


def jira_search(jql: str, fields: list[str], limit: int = 50) -> dict[str, dict]:
    proc = subprocess.run(
        [*agentctl(), "jira", "search", jql, "--fields", ",".join(fields), "--max-results", str(limit), "--full"],
        capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL, check=False,
    )
    if proc.returncode:
        raise ToolError(f"jira search failed: {(proc.stderr or proc.stdout).strip()[:200]}")
    issues = json.loads(proc.stdout).get("issues") or []
    return {item["key"]: (item.get("issue") or {}).get("fields") or {} for item in issues}


def jira_get(key: str, fields: list[str]) -> dict:
    proc = subprocess.run(
        [*agentctl(), "jira", "get", key, "--fields", ",".join(fields)],
        capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL, check=False,
    )
    if proc.returncode:
        raise ToolError(f"jira get {key} failed: {(proc.stderr or proc.stdout).strip()[:200]}")
    return json.loads(proc.stdout).get("fields") or {}


def meta(fields: dict) -> dict:
    status = fields.get("status") or {}
    return {
        "summary": fields.get("summary"),
        "status": status.get("name"),
        "status_category": (status.get("statusCategory") or {}).get("key"),
        "done": (status.get("statusCategory") or {}).get("key") == "done",
        "type": (fields.get("issuetype") or {}).get("name"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "updated": fields.get("updated"),
        "fix_versions": [v.get("name") for v in fields.get("fixVersions") or []],
        "parent": (fields.get("parent") or {}).get("key"),
    }


def links_of(fields: dict) -> list[tuple[str, str]]:
    out = []
    for link in fields.get("issuelinks") or []:
        kind = link.get("type") or {}
        if link.get("outwardIssue"):
            out.append((link["outwardIssue"]["key"], kind.get("outward") or kind.get("name") or "relates to"))
        if link.get("inwardIssue"):
            out.append((link["inwardIssue"]["key"], kind.get("inward") or kind.get("name") or "relates to"))
    return out


class Candidate:
    def __init__(self, key: str):
        self.key = key
        self.relations: list[str] = []
        self.overlap: set[str] = set()
        self.branches: list[str] = []
        self.unreleased: list[dict] = []
        self.released: list[dict] = []
        self.fields: dict | None = None

    def relate(self, relation: str) -> None:
        if relation not in self.relations:
            self.relations.append(relation)

    @property
    def tracker_relations(self) -> list[str]:
        return [r for r in self.relations if r.split(":")[0] in {"parent", "sibling", "child", "linked", "duplicate", "via", "mentioned-in-prd"}]

    @property
    def tier(self) -> str:
        if self.unreleased and self.overlap:
            return "parallel"
        return "tracker" if self.tracker_relations else "history"

    @property
    def last_activity(self) -> str | None:
        dates = [c["date"] for c in self.unreleased + self.released]
        return max(dates) if dates else None

    def score(self) -> int:
        total = 0
        if self.unreleased and self.overlap:
            total += 50 + 5 * min(len(self.overlap), 6)
        elif self.released:
            total += 10 + 3 * min(len(self.overlap), 5)
        for relation in self.tracker_relations:
            head = "duplicate" if "duplicate" in relation else relation.split(":")[0]
            total += RELATION_SCORE.get(head, 0)
        if self.fields and not meta(self.fields)["done"]:
            total += 5
        return total


def commit_view(commit: dict, ref: str | None = None) -> dict:
    view = {"sha": commit["sha"][:9], "date": commit["date"], "author": commit["author"], "subject": commit["subject"][:140]}
    return {**view, "ref": ref} if ref else view


# ---------------------------------------------------------------- scan

def scan(args: argparse.Namespace, search=jira_search) -> dict:
    repo = Path(args.repo).expanduser().resolve()
    task_id = args.task_id
    warnings: list[str] = []
    base = resolve_base(repo, args.base)
    head_sha = git(repo, "rev-parse", "HEAD").strip()
    own_branch = git(repo, "branch", "--show-current").strip() or "HEAD"
    source, files = own_files(repo, base, args.files or [], task_id)
    if source == "none":
        warnings.append("no task files (no diff against base, no plan paths, no --files): git signals are skipped, tracker signals only")
    fetched = refs_fetched_at(repo)
    if fetched is None or (datetime.now(UTC) - fetched).total_seconds() > STALE_REFS_HOURS * 3600:
        warnings.append(f"remote refs older than {STALE_REFS_HOURS}h or never fetched: parallel branches may be missing (run `git fetch`, a remote read)")

    cands: dict[str, Candidate] = {}

    def cand(key: str) -> Candidate:
        return cands.setdefault(key, Candidate(key))

    unkeyed: list[dict] = []
    refs = unreleased_refs(repo, base, head_sha, own_branch)
    if files:
        for ref in refs:
            mb = git(repo, "merge-base", base, ref["ref"], check=False).strip()
            if not mb:
                continue
            commits = parse_log(git(repo, "log", f"{mb}..{ref['ref']}", "--no-merges", "--name-only", f"--format={LOG_FORMAT}", "--", *files))
            if not commits:
                continue
            branch_keys = [k for k in keys_in(ref["name"], any_case=True) if k != task_id]
            touched = {f for c in commits for f in c["files"]}
            found = False
            for commit in commits:
                for key in [k for k in keys_in(commit["subject"] + "\n" + commit["body"]) if k != task_id] or branch_keys:
                    found = True
                    c = cand(key)
                    c.relate("parallel-unreleased")
                    c.overlap |= set(commit["files"])
                    c.unreleased.append(commit_view(commit, ref["ref"]))
                    if ref["name"] not in c.branches:
                        c.branches.append(ref["name"])
            if not found:
                unkeyed.append({"ref": ref["ref"], "files": sorted(touched)[:10], "commits": [commit_view(c) for c in commits[:5]]})
        history = parse_log(git(repo, "log", base, "--no-merges", f"--since={args.since}", "-n", str(HISTORY_COMMIT_CAP), "--name-only",
                                f"--format={LOG_FORMAT}", "--", *files))
        for commit in history:
            for key in keys_in(commit["subject"] + "\n" + commit["body"]):
                if key == task_id:
                    continue
                c = cand(key)
                c.relate("history-released")
                c.overlap |= set(commit["files"])
                c.released.append(commit_view(commit))

    tracker = enrich_from_tracker(task_id, cands, refs, args, search, warnings)

    if tracker["status"] == "ok":  # Jira drops what is not an issue (a branch called step-2), so unknown keys go away
        cands = {k: c for k, c in cands.items() if c.fields is not None}
    ranked = sorted(cands.values(), key=lambda c: (-c.score(), c.key))
    return report(task_id, repo, base, own_branch, head_sha, source, files, fetched, tracker, ranked, unkeyed, warnings)


def enrich_from_tracker(task_id, cands, refs, args, search, warnings) -> dict:
    if args.no_jira:
        return {"status": "skipped", "reason": "--no-jira"}
    if not KEY_RE.fullmatch(task_id):
        return {"status": "skipped", "reason": "local task id (not a tracker key)"}
    fields = SCAN_FIELDS

    def safe(jql: str, limit: int = 50) -> dict[str, dict]:
        try:
            return search(jql, fields, limit)
        except (ToolError, OSError, ValueError, subprocess.SubprocessError) as exc:
            warnings.append(f"tracker query failed ({jql[:60]}): {exc}")
            return {}

    own = safe(f"key = {task_id}", 1).get(task_id)
    if own is None:
        return {"status": "unavailable", "reason": f"{task_id} not readable (no token, no network or unknown key)"}

    def add(key: str, relation: str, fields_: dict | None = None) -> None:
        if key == task_id:
            return
        c = cands.setdefault(key, Candidate(key))
        c.relate(relation)
        if fields_ is not None:
            c.fields = fields_

    own_meta, own_parent = meta(own), meta(own)["parent"]
    anchors = {own_parent} if own_parent else set()
    if own_parent:
        add(own_parent, "parent")
    for key, fields_ in safe(f"parent = {task_id}").items():
        add(key, "child", fields_)
    if own_parent:
        for key, fields_ in safe(f"parent = {own_parent} AND key != {task_id}").items():
            add(key, "sibling", fields_)
    for key, label in links_of(own):
        anchors.add(key)
        add(key, f"duplicate:{label}" if "duplicate" in label.lower() else f"linked:{label}")
    for key in prd_keys(task_id):
        add(key, "mentioned-in-prd")
    for ref in refs:
        for key in keys_in(ref["name"], any_case=True):
            if key in cands and ref["name"] not in cands[key].branches:
                cands[key].branches.append(ref["name"])

    pending = [k for k, c in cands.items() if c.fields is None]
    pending.sort(key=lambda k: (-cands[k].score(), k))
    for start in range(0, min(len(pending), ENRICH_CAP * 2), ENRICH_CAP):
        chunk = pending[start:start + ENRICH_CAP]
        for key, fields_ in safe(f"key in ({', '.join(chunk)})", ENRICH_CAP).items():
            if key in cands:
                cands[key].fields = fields_
    for key, c in cands.items():
        if not c.fields:
            continue
        info = meta(c.fields)
        if info["parent"] == task_id:
            c.relate("child")
        elif info["parent"] and info["parent"] == own_parent:
            c.relate("sibling")
        for linked, label in links_of(c.fields):
            if linked == task_id:
                c.relate(f"linked:{label}")
            elif linked in anchors:
                c.relate(f"via:{linked}")
        if info["parent"] in anchors and info["parent"] != own_parent:
            c.relate(f"via:{info['parent']}")
    return {"status": "ok", "own": {"key": task_id, **{k: own_meta[k] for k in ("summary", "status", "type", "parent")}}}


def report(task_id, repo, base, branch, head_sha, source, files, fetched, tracker, ranked, unkeyed, warnings) -> dict:
    def view(c: Candidate, *, commits: int) -> dict:
        info = meta(c.fields) if c.fields else {}
        state = "unreleased" if c.unreleased else "released" if c.released else "none"
        return {
            "key": c.key, "tier": c.tier, "score": c.score(), "confirmed": c.fields is not None,
            "summary": info.get("summary"), "status": info.get("status"),
            "status_category": info.get("status_category"), "type": info.get("type"),
            "assignee": info.get("assignee"), "relations": c.relations, "code_state": state,
            "overlap_files": sorted(c.overlap)[:12], "branches": c.branches,
            "commit_counts": {"unreleased": len(c.unreleased), "released": len(c.released)},
            "last_activity": c.last_activity,
            "recent": sorted(c.unreleased + c.released, key=lambda x: x["date"], reverse=True)[:commits],
        }

    full = [view(c, commits=15) for c in ranked]
    return {
        "task_id": task_id,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "repo": str(repo), "base": base, "head": {"branch": branch, "sha": head_sha[:9]},
        "files": {"source": source, "count": len(files), "list": files[:20]},
        "refs_fetched_at": fetched.isoformat(timespec="seconds") if fetched else None,
        "tracker": tracker,
        "counts": {
            "candidates": len(ranked),
            "parallel": sum(c.tier == "parallel" for c in ranked),
            "tracker": sum(c.tier == "tracker" for c in ranked),
            "history": sum(c.tier == "history" for c in ranked),
            "unkeyed_branches": len(unkeyed),
        },
        "warnings": warnings,
        "candidates": full,
        "unkeyed_branches": unkeyed,
    }


def cmd_scan(args: argparse.Namespace) -> int:
    result = scan(args)
    out = Path(args.output).expanduser() if args.output else agents_home() / "prds" / f"{args.task_id}.related.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shown = dict(result)
    shown["candidates"] = [{**c, "recent": c["recent"][:2]} for c in result["candidates"][: args.max]]
    shown["file"] = str(out)
    if len(result["candidates"]) > args.max:
        shown["more"] = len(result["candidates"]) - args.max
    print(json.dumps(shown, indent=2, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------- brief

def section(text: str, heading: str, cap: int) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    return match.group(1).strip()[:cap] if match else ""


def mentions(commits: list[dict], key: str) -> list[dict]:
    """--grep matches PROJ-1 inside PROJ-11, so keep only commits that name the key whole."""
    return [c for c in commits if key in keys_in(c["subject"] + "\n" + c["body"])]


def git_footprint(repo: Path, base: str, key: str, files: list[str], hunks: bool, own_branch: str, head_sha: str) -> dict:
    refs = unreleased_refs(repo, base, head_sha, own_branch)
    footprint = {"branches": [], "unreleased_commits": [], "released_commits": [], "files": [], "overlap_files": [], "hunks": ""}
    touched: set[str] = set()
    for ref in refs:
        named = key in keys_in(ref["name"], any_case=True)
        mb = git(repo, "merge-base", base, ref["ref"], check=False).strip()
        if not mb:
            continue
        args = ["log", f"{mb}..{ref['ref']}", "--no-merges", "--name-only", f"--format={LOG_FORMAT}", "-n", "40"]
        commits = parse_log(git(repo, *args, *([] if named else ["--fixed-strings", f"--grep={key}"])))
        commits = commits if named else mentions(commits, key)
        if not commits:
            continue
        stat = git(repo, "diff", "--shortstat", mb, ref["ref"]).strip()
        footprint["branches"].append({"ref": ref["ref"], "tip": ref["sha"][:9], "last_commit": ref["date"], "diffstat": stat})
        for commit in commits:
            touched |= set(commit["files"])
            footprint["unreleased_commits"].append(commit_view(commit, ref["ref"]))
        overlap = sorted(touched & set(files)) if files else []
        if hunks and overlap:
            diff = git(repo, "diff", "-U2", mb, ref["ref"], "--", *overlap, check=False).splitlines()
            footprint["hunks"] += f"# {ref['ref']}\n" + "\n".join(diff[:300]) + ("\n[truncated]\n" if len(diff) > 300 else "\n")
    released = mentions(parse_log(git(repo, "log", base, "--no-merges", "-n", "20", "--fixed-strings", f"--grep={key}", "--name-only", f"--format={LOG_FORMAT}")), key)
    for commit in released:
        touched |= set(commit["files"])
        footprint["released_commits"].append(commit_view(commit))
    footprint["files"] = sorted(touched)[:80]
    footprint["overlap_files"] = sorted(touched & set(files))
    footprint["hunks"] = redact(footprint["hunks"])
    return footprint


def brief(args: argparse.Namespace, get=jira_get) -> dict:
    repo = Path(args.repo).expanduser().resolve()
    key = args.key.upper()
    base = resolve_base(repo, args.base)
    head_sha = git(repo, "rev-parse", "HEAD").strip()
    own_branch = git(repo, "branch", "--show-current").strip() or "HEAD"
    files = list(args.files or [])
    if args.task and not files:
        _, files = own_files(repo, base, [], args.task)
    warnings: list[str] = []
    code = git_footprint(repo, base, key, files, args.hunks, own_branch, head_sha)

    tracker: dict = {"status": "skipped"}
    if not args.no_jira:
        try:
            fields = get(key, BRIEF_FIELDS)
            comments = [c for c in (fields.get("comment") or {}).get("comments") or []]
            tracker = {
                "status": "ok", **meta(fields),
                "links": [{"key": k, "relation": r} for k, r in links_of(fields)],
                "description": redact(str(fields.get("description") or ""))[: args.excerpt_chars],
                "recent_comments": [
                    {"author": (c.get("author") or {}).get("displayName"), "created": c.get("created"),
                     "body": redact(str(c.get("body") or ""))[:600]}
                    for c in comments[-args.max_comments:]
                ],
            }
        except (ToolError, OSError, ValueError, subprocess.SubprocessError) as exc:
            tracker = {"status": "unavailable", "reason": str(exc)}
            warnings.append("tracker half unverified: " + str(exc))

    local: dict = {}
    prd = agents_home() / "prds" / f"{key}.md"
    plan = agents_home() / "plans" / key
    if prd.is_file():
        local["prd"] = str(prd)
        local["requirement_changes"] = redact(section(prd.read_text(errors="ignore"), "Requirement Changes", 1500))
    if plan.is_dir():
        local["plan"] = {"dir": str(plan), "files": sorted(p.name for p in plan.iterdir())[:20]}

    if code["unreleased_commits"]:
        state = "in-progress-unreleased"
    elif code["released_commits"]:
        state = "released"
    else:
        state = "no-code-found"
    return {
        "key": key, "for_task": args.task, "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "repo": str(repo), "base": base, "code_state": state, "tracker": tracker, "code": code, "local": local, "warnings": warnings,
    }


def brief_markdown(data: dict) -> str:
    t, code, local = data["tracker"], data["code"], data["local"]
    title = t.get("summary") or f"(tracker {t.get('status')})"
    lines = [
        f"# Related issue status: {data['key']} {title}", "",
        "**Format:** Related issue brief (mechanical facts; assessment is written by the skill)",
        f"**Date:** {data['generated_at'][:10]}",
        f"**For task:** {data['for_task'] or 'none'}",
        f"**Base:** {data['base']}",
        "", "## Status", "",
        f"- Tracker: {t.get('status')}" + (f", {t.get('type')}, assignee {t.get('assignee') or 'none'}, updated {t.get('updated')}" if t.get("status") == "ok" else ""),
        f"- Code: {data['code_state']} ({len(code['unreleased_commits'])} unreleased, {len(code['released_commits'])} released commits found)",
    ]
    if t.get("fix_versions"):
        lines.append(f"- Fix versions: {', '.join(t['fix_versions'])}")
    if t.get("links"):
        lines.append("- Links: " + ", ".join(f"{x['relation']} {x['key']}" for x in t["links"]))
    lines += ["", "## Scope", "", t.get("description") or "No description available.", ""]
    if local.get("requirement_changes"):
        lines += ["## Requirement changes", "", local["requirement_changes"], ""]
    if t.get("recent_comments"):
        lines += ["## Recent discussion", ""]
        lines += [f"- {c['created'][:10] if c.get('created') else ''} {c['author']}: {c['body']}" for c in t["recent_comments"]]
        lines.append("")
    lines += ["## Code footprint", ""]
    for b in code["branches"]:
        lines.append(f"- Branch `{b['ref']}` tip {b['tip']}, last commit {b['last_commit'][:10]}: {b['diffstat'] or 'no diff'}")
    for c in code["unreleased_commits"][:10]:
        lines.append(f"- Unreleased {c['sha']} {c['date'][:10]} {c['author']}: {c['subject']}")
    for c in code["released_commits"][:5]:
        lines.append(f"- Released {c['sha']} {c['date'][:10]} {c['author']}: {c['subject']}")
    if code["files"]:
        lines.append("- Files: " + ", ".join(f"`{f}`" for f in code["files"][:25]))
    lines += ["", "## Overlap with this task", ""]
    lines.append(", ".join(f"`{f}`" for f in code["overlap_files"]) if code["overlap_files"] else "No shared files found.")
    if code["hunks"]:
        lines += ["", "```diff", code["hunks"].rstrip(), "```"]
    lines += ["", "## Artifacts", ""]
    lines.append(f"- PRD: {local['prd']}" if local.get("prd") else "- PRD: none cached")
    lines.append(f"- Plan: {local['plan']['dir']}" if local.get("plan") else "- Plan: none")
    lines += ["", "## Assessment", "", "_Not assessed. Read the sections above, then state: contradiction, dependency or context only, and the action for this task._", ""]
    return "\n".join(lines)


def cmd_brief(args: argparse.Namespace) -> int:
    data = brief(args)
    markdown = brief_markdown(data)
    if args.write:
        if not args.task:
            raise ToolError("--write needs --task (the file lands under prds/<TASK-ID>/related/)")
        out = agents_home() / "prds" / args.task / "related" / f"{data['key']}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        data["file"] = str(out)
    print(markdown if args.format == "md" else json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--repo", default=".", help="Git repo of the task (default: cwd).")
        p.add_argument("--base", help="Released branch (default: origin/master, origin/main, master, main).")
        p.add_argument("--files", nargs="+", help="Task files; default: diff against base, else paths named in the plan.")
        p.add_argument("--no-jira", action="store_true", help="Git signals only.")

    s = sub.add_parser("scan", help="Rank issues related to a task as bounded JSON.")
    s.add_argument("task_id")
    common(s)
    s.add_argument("--since", default="24 months ago", help="Released-history window (default: 24 months ago).")
    s.add_argument("--max", type=int, default=25, help="Candidates printed (the file keeps all).")
    s.add_argument("--output", help="Default: ~/.agents/prds/<TASK-ID>.related.json")
    s.set_defaults(func=cmd_scan)

    b = sub.add_parser("brief", help="Status, context and handoff of one related issue.")
    b.add_argument("key")
    common(b)
    b.add_argument("--task", help="The task this is for: used for file overlap and the output folder.")
    b.add_argument("--hunks", action="store_true", help="Include the other branch's diff on shared files (bounded).")
    b.add_argument("--format", choices=("json", "md"), default="md")
    b.add_argument("--write", action="store_true", help="Write ~/.agents/prds/<TASK-ID>/related/<KEY>.md")
    b.add_argument("--max-comments", type=int, default=5)
    b.add_argument("--excerpt-chars", type=int, default=1500)
    b.set_defaults(func=cmd_brief)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except ToolError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
