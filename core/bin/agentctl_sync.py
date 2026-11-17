"""Parallel-issue sync (plan factory-sync): marker, pair identity, tie-break, ladder, and the read-only scan.

The first half is pure (no I/O, no model call). The second half (`scan`, `agentctl sync`) reads git and
the host adapter (agentctl_githost) and writes nothing. The factory steps act on the answers. Everything
another factory or person wrote (titles, descriptions, comments) is untrusted: only the marker block is
parsed, and strictly.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import agentctl_config
import agentctl_githost as githost

SCHEMA_VERSION = 1
CLASSES = ("contradiction", "dependency", "overlap", "context", "duplicate")
MARKER_KEYS = ("schema_version", "from", "to", "class", "base_sha", "files")
FENCE_RE = re.compile(r"^```[a-z]*\n(.*?)\n```[ \t]*$", re.DOTALL | re.MULTILINE)
SHA_RE = re.compile(r"^[0-9a-f]{7,64}$")


class SyncError(Exception):
    """A marker or sync input that cannot be used."""


def sign_message(message: str, signature: str) -> str:
    """`message` with `signature` as its last line, after one blank line. Idempotent; empty signature = unchanged."""
    body = message.rstrip()
    if not signature or body.splitlines()[-1:] == [signature]:
        return body + "\n"
    return f"{body}\n\n{signature}\n"


# --------------------------------------------------------------------------- marker


def safe_path(path: str) -> bool:
    return bool(path) and not path.startswith("/") and ".." not in path.split("/") and "\n" not in path


def build_marker(src: str, dst: str, cls: str, base_sha: str, files: list[str]) -> dict[str, Any]:
    if cls not in CLASSES or cls == "contradiction":
        raise SyncError(f"class {cls!r} cannot be proposed")
    if not SHA_RE.match(base_sha):
        raise SyncError(f"base_sha {base_sha!r} is not a commit id")
    if not files or not all(isinstance(f, str) and safe_path(f) for f in files):
        raise SyncError("files must be a non-empty list of relative paths without '..'")
    if src == dst:
        raise SyncError("a proposal needs two different issues")
    return {"schema_version": SCHEMA_VERSION, "from": src, "to": dst, "class": cls, "base_sha": base_sha,
            "files": sorted(set(files))}


def render_description(summary: str, marker: dict[str, Any], *, block: str, signature: str) -> str:
    """Review request description: summary, the fenced marker block, the signature as last line."""
    payload = json.dumps(marker, separators=(",", ":"), sort_keys=False)
    return sign_message(f"{summary.rstrip()}\n\n```text\n{block}\n{payload}\n```", signature)


def parse_marker(description: str, *, block: str, key_re: re.Pattern[str] | None = None) -> dict[str, Any] | None:
    """The marker of a description, or None. Strict: exactly one block, exact keys, known class, safe paths.

    A second block with the same name (a forged or pasted one) invalidates the whole description. Text
    outside the block is never read.
    """
    blocks = [m.group(1) for m in FENCE_RE.finditer(description or "") if m.group(1).split("\n", 1)[0].strip() == block]
    if len(blocks) != 1:
        return None
    try:
        marker = json.loads(blocks[0].split("\n", 1)[1])
    except (IndexError, json.JSONDecodeError):
        return None
    if not isinstance(marker, dict) or set(marker) != set(MARKER_KEYS) or marker["schema_version"] != SCHEMA_VERSION:
        return None
    if marker["class"] not in CLASSES or marker["class"] == "contradiction":
        return None
    if not all(isinstance(marker[k], str) for k in ("from", "to", "base_sha")) or not SHA_RE.match(marker["base_sha"]):
        return None
    if key_re and not (key_re.fullmatch(marker["from"]) and key_re.fullmatch(marker["to"])):
        return None
    if marker["from"] == marker["to"]:
        return None
    files = marker["files"]
    if not isinstance(files, list) or not files or not all(isinstance(f, str) and safe_path(f) for f in files):
        return None
    return marker


# --------------------------------------------------------------------------- pair identity and tie-break


def pair_id(src: str, dst: str) -> str:
    return f"{src}-into-{dst}"


def proposal_branch(pattern: str, src: str, dst: str) -> str:
    return pattern.format(src=src, dst=dst)


@dataclass(frozen=True)
class BranchInfo:
    key: str
    first_unique_commit: datetime | None  # committer date of the oldest commit not in the base; None = no branch or no commit


def tie_break(a: BranchInfo, b: BranchInfo) -> tuple[str, str]:
    """(owner, proposer). The older first unique commit owns the pair; a missing date is the newest; keys break ties."""
    def rank(info: BranchInfo) -> tuple[int, float, str]:
        if info.first_unique_commit is None:
            return (1, 0.0, info.key)
        return (0, info.first_unique_commit.timestamp(), info.key)

    owner, proposer = sorted((a, b), key=rank)
    return owner.key, proposer.key


# --------------------------------------------------------------------------- ladder


@dataclass(frozen=True)
class Decision:
    action: str  # none | park_contradiction | notice_restricted | notice_comment | ordering | proposal | append | confirm | read_only | defer
    reason: str


def decide(cls: str, *, has_branch: bool, i_am_proposer: bool, ladder: list[str], inbound_same_files: bool,
           answering_proposal: bool, open_pair_request: bool, proposals_this_run: int, max_open_per_pair: int,
           max_proposals_per_run: int, closed_pair_request: bool = False) -> Decision:
    """The one action the factory takes for one related issue. Cheapest rung that resolves the relation."""
    if cls not in CLASSES:
        raise SyncError(f"unknown relation class {cls!r}")
    if cls == "contradiction":
        return Decision("park_contradiction", "a behavior conflict is a decision for the analyst or the owners")
    if cls == "context":
        return Decision("none", "context feeds planning, nothing to send")
    if answering_proposal:
        return Decision("read_only", "the related request is itself a factory proposal; never answer a proposal with one")
    if not has_branch:
        return Decision("notice_restricted", "the related issue has no branch to target")
    if cls == "duplicate":
        return Decision("notice_comment" if "notice" in ladder else "none", "same request as this task")
    if inbound_same_files:
        return Decision("read_only", "an inbound proposal already covers the same files")
    if not i_am_proposer:
        return Decision("read_only", "the other issue proposes (older first unique commit owns the pair)")
    if "proposal" not in ladder:
        return Decision("ordering" if "ordering" in ladder else "notice_comment", "proposals are switched off")
    if open_pair_request:
        return Decision("append" if max_open_per_pair >= 1 else "none", "one open request per pair: append to it")
    if closed_pair_request:
        return Decision("confirm", "an earlier proposal for this pair was closed unmerged; a human decides on a new one")
    if proposals_this_run >= max_proposals_per_run:
        return Decision("defer", "max_proposals_per_run reached")
    return Decision("proposal", f"{cls} with a branch on the host: propose into it")


# --------------------------------------------------------------------------- read-only scan

CLASS_LINE_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\s*\((" + "|".join(CLASSES) + r")\b")


def classes_from_summary(*summaries: str | None) -> dict[str, str]:
    """`KEY (class)` lines of the related-issue step summaries; the later mention of a key wins."""
    found: dict[str, str] = {}
    for text in summaries:
        for key, cls in CLASS_LINE_RE.findall(text or ""):
            found[key] = cls
    return found


def normalize_branch(ref: str) -> str:
    return re.sub(r"^(?:remotes/)?(?:origin/|heads/)", "", ref)


def git_text(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def first_unique_commit(repo: Path, base: str, ref: str) -> datetime | None:
    """Committer date of the oldest commit on `ref` that `base` lacks (the stand-in for "pushed first")."""
    out = git_text(repo, "log", "--reverse", "--format=%cI", f"{base}..{ref}")
    return datetime.fromisoformat(out.splitlines()[0]) if out else None


def remote_ref(repo: Path, branch: str) -> str | None:
    return f"origin/{branch}" if git_text(repo, "rev-parse", "--verify", "-q", f"origin/{branch}") else None


def acknowledged(plan_dir: Path, key: str) -> bool:
    """A contradiction is acknowledged when the plan (Constraints, Non-Goals, tbd, decisions) names the issue key."""
    return plan_dir.is_dir() and any(key in path.read_text(encoding="utf-8", errors="ignore")
                                     for path in plan_dir.glob("*.md") if path.name not in ("progress.md", "evidence.progress.md"))


def confirmed(plan_dir: Path, key: str) -> bool:
    """A new proposal after a closed one needs the operator: a line `confirm-proposal: KEY` in sync-confirmed.md."""
    path = plan_dir / "sync-confirmed.md"
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines() if path.is_file() else []
    return f"confirm-proposal: {key}" in (line.strip() for line in lines)


def inbox(adapter: githost.Adapter, cfg: dict[str, Any], own_branch: str, own_key: str,
          key_re: re.Pattern[str]) -> list[dict[str, Any]]:
    """Review requests that target my branch or carry my key in their marker. Opened ones are pending."""
    block = agentctl_config.section(cfg, "sync")["marker_block"]
    seen: dict[int, dict[str, Any]] = {}
    for request in adapter.list_review_requests(target=own_branch, state="all") \
            + adapter.list_review_requests(state="opened"):
        marker = parse_marker(request.description, block=block, key_re=key_re)
        if request.target_branch != own_branch and not (marker and marker["to"] == own_key):
            continue
        seen[request.id] = {"id": request.id, "state": request.state, "source_branch": request.source_branch,
                            "target_branch": request.target_branch, "marker": marker,
                            "factory_proposal": marker is not None,
                            "acknowledged": request.state in ("closed", "merged"), "title": request.title[:120]}
    return sorted(seen.values(), key=lambda r: r["id"])


def scan(task: str, repo: Path, cfg: dict[str, Any], adapter: githost.Adapter, related: dict[str, Any],
         classes: dict[str, str], *, proposals_this_run: int = 0) -> dict[str, Any]:
    """Inbox and outbox candidates for one task. Read only. A host failure makes the result `unverified`."""
    sync_cfg = agentctl_config.section(cfg, "sync")
    tracker = agentctl_config.tracker(cfg)
    key_re = re.compile(tracker["key_regex"].strip("^$")) if tracker else re.compile(r"(?!x)x")
    base = str(related.get("base") or "origin/master")
    own_branch = git_text(repo, "branch", "--show-current") or task
    protected = set((cfg.get("git") or {}).get("protected_branches", []))
    result: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "task_id": task, "status": "ok", "branch": own_branch,
                              "inbox": [], "outbox": [], "unclassified": [], "warnings": []}
    try:
        result["inbox"] = inbox(adapter, cfg, own_branch, task, key_re)
        pending = [r for r in result["inbox"] if not r["acknowledged"] and r["factory_proposal"]]
        mine = first_unique_commit(repo, base, remote_ref(repo, own_branch) or "HEAD")
        for cand in related.get("candidates", []):
            key = cand["key"]
            if cand.get("tier") == "history" or cand.get("relations") in (["parent"], ["child"]):
                continue
            if agentctl_config.is_closed_status(cand.get("status"), cand.get("status_category"), cfg):
                continue
            cls = classes.get(key)
            if cls is None:
                result["unclassified"].append(key)
                continue
            branch = next((b for b in map(normalize_branch, cand.get("branches", []))
                           if b not in protected and remote_ref(repo, b)), None)
            files = sorted(set(cand.get("overlap_files", [])))
            theirs = first_unique_commit(repo, base, f"origin/{branch}") if branch else None
            owner, proposer = tie_break(BranchInfo(task, mine), BranchInfo(key, theirs))
            pair_branch = proposal_branch(sync_cfg["proposal_branch"], task, key)
            open_pair = bool(adapter.list_review_requests(source=pair_branch))
            closed_pair = not open_pair and bool(adapter.list_review_requests(source=pair_branch, state="closed"))
            decision = decide(
                cls, has_branch=branch is not None, i_am_proposer=proposer == task, ladder=list(sync_cfg["ladder"]),
                inbound_same_files=any(set(r["marker"]["files"]) & set(files) for r in pending),
                answering_proposal=any(r["marker"]["from"] == key for r in pending),
                open_pair_request=open_pair, proposals_this_run=proposals_this_run,
                max_open_per_pair=sync_cfg["max_open_per_pair"], max_proposals_per_run=sync_cfg["max_proposals_per_run"],
                closed_pair_request=closed_pair)
            result["outbox"].append({
                "key": key, "class": cls, "action": decision.action, "reason": decision.reason, "owner": owner,
                "pair": pair_id(task, key), "branch": branch, "files": files,
                "proposal_branch": proposal_branch(sync_cfg["proposal_branch"], task, key)})
    except githost.HostError as exc:
        result.update(status="unverified", inbox=[], outbox=[])
        result["warnings"].append(f"host unavailable: {exc}")
    return result


def load_related(task: str, path: Path | None, prds_dir: Path) -> dict[str, Any]:
    target = path or prds_dir / f"{task}.related.json"
    if not target.is_file():
        raise SyncError(f"no related-issues scan at {target}; run find-related-issues scan first")
    return json.loads(target.read_text(encoding="utf-8"))


def cmd_scan(args: argparse.Namespace) -> int:
    from agentctl_common import agents_home, emit

    cfg = agentctl_config.load()
    classes = dict(item.split("=", 1) for item in args.cls)
    try:
        adapter = githost.adapter_for(cfg, args.repo, agents_home() / ".auth")
        related = load_related(args.task, args.related, agents_home() / "prds")
    except githost.HostError as exc:
        emit({"task_id": args.task, "status": "unverified", "warnings": [f"host unavailable: {exc}"],
              "inbox": [], "outbox": []})
        return 0
    emit(scan(args.task, args.repo, cfg, adapter, related, classes))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Sync events of a factory run, from files only (no host or model call)."""
    import agentctl_factory
    from agentctl_common import emit

    directory = agentctl_factory.run_dir(args.task)
    if not (directory / "events.jsonl").is_file():
        raise SyncError(f"unknown factory run {args.task!r}")
    events = [e for e in agentctl_factory.read_events(directory) if str(e["type"]).startswith("sync_")]
    emit({"task_id": args.task, "schema_version": SCHEMA_VERSION, "events": events})
    return 0


def add_sync_parsers(group: argparse._SubParsersAction) -> None:
    scan_parser = group.add_parser("scan", help="Read-only: inbox and outbox candidates for a task.")
    scan_parser.add_argument("task")
    scan_parser.add_argument("--repo", type=Path, default=Path.cwd())
    scan_parser.add_argument("--related", type=Path, help="related.json (default: prds/<TASK>.related.json).")
    scan_parser.add_argument("--class", dest="cls", action="append", default=[], metavar="KEY=CLASS",
                             help="Relation class per related issue (contradiction|dependency|overlap|context|duplicate).")
    scan_parser.set_defaults(func=cmd_scan)
    status_parser = group.add_parser("status", help="Sync events of a factory run (files only).")
    status_parser.add_argument("task")
    status_parser.set_defaults(func=cmd_status)
