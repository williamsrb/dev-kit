"""Shared proposal format, validator and decision ledger for agentctl.

One format for every `kb-proposals.md` (run-plan, plan-task-evidence, the
factory harvest and chat harvest). `agentctl kb proposals` and the factory
status code both use this module. Stdlib only.

Format: one H2 per proposal whose text is the target path, then `- kind:`,
`- evidence:`, optional `- covers:` and `- keys:` lines, then one fenced body
(the full file for `new`, a unified diff for `edit`).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from agentctl_jira import agents_home
from agentctl_kb import OWNED_DEFAULT

KIT_TOP_FOLDERS = ("skills", "kb", "rules")
HARNESS_FOLDERS = ("skills", "rules", "hooks", "mcp", "skills-vendor")
KINDS = ("new", "edit", "remove")
STATES = ("pending", "applied", "rejected", "invalid")
PROPOSALS_NAME = "kb-proposals.md"
HARNESS_NAME = "harness-proposals.md"
LEDGER_NAME = "kb-decisions.jsonl"
HARNESS_LEDGER_NAME = "harness-decisions.jsonl"
SCOPES = ("kb", "harness")
FIELD_RE = re.compile(r"^- (kind|evidence|covers|keys):\s*(.*)$")
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
STEP_PREFIX_RE = re.compile(r"^\d+-")
HARNESS_REASON = "harness change: agentctl harness only"


class ProposalError(Exception):
    """User-facing proposal command failure."""


def kit_relative(path: str) -> str | None:
    """A path inside the agents home's skills/, kb/ or rules/, relative to it; else None."""
    try:
        rel = Path(path).expanduser().resolve().relative_to(agents_home().resolve())
    except (ValueError, OSError, RuntimeError):
        return None
    return rel.as_posix() if rel.parts and rel.parts[0] in KIT_TOP_FOLDERS else None


@dataclass
class Proposal:
    target: str
    kind: str | None
    evidence: str
    covers: list[str]
    keys: list[str]
    body: str
    n: int
    file: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse(path: Path) -> list[Proposal]:
    """Every proposal in a file, in order. Missing file gives []."""
    if not path.is_file():
        return []
    proposals: list[Proposal] = []
    cur: dict[str, Any] | None = None
    fence: str | None = None
    body_seen = False

    def finish() -> None:
        if cur is None:
            return
        proposals.append(
            Proposal(
                target=cur["target"],
                kind=cur["fields"].get("kind") or None,
                evidence=cur["fields"].get("evidence", ""),
                covers=_split_list(cur["fields"].get("covers", "")),
                keys=_split_list(cur["fields"].get("keys", "")),
                body="\n".join(cur["body"]).rstrip("\n"),
                n=len(proposals) + 1,
                file=str(path),
            )
        )

    for line in path.read_text(encoding="utf-8").splitlines():
        if fence is not None:
            stripped = line.strip()
            match = FENCE_RE.match(stripped)
            if match and stripped == fence:
                fence = None
            elif cur is not None:
                cur["body"].append(line)
            continue
        if line.startswith("## "):
            finish()
            cur = {"target": line[3:].strip(), "fields": {}, "body": []}
            body_seen = False
            continue
        if cur is None:
            continue
        match = FIELD_RE.match(line)
        if match and not body_seen:
            cur["fields"][match.group(1)] = match.group(2).strip()
            continue
        fence_match = FENCE_RE.match(line.strip())
        if fence_match and not body_seen:
            fence = fence_match.group(1)
            body_seen = True
    finish()
    return proposals


def effective_kind(p: Proposal, home: Path) -> str:
    """The kind a proposal acts as. Without `kind:`, a missing target is `new`, an existing one `edit`."""
    if p.kind:
        return p.kind
    return "edit" if (home / p.target).exists() else "new"


def sha_of(p: Proposal, home: Path) -> str:
    text = f"{p.target}\n{effective_kind(p, home)}\n{p.body}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def tracked(home: Path, target: str) -> bool:
    result = subprocess.run(["git", "ls-files", "--error-unmatch", "--", target], cwd=home, capture_output=True, check=False)
    return result.returncode == 0


def _validate_harness(p: Proposal, home: Path) -> list[str]:
    """Harness scope: skills/, rules/, hooks/ and mcp/catalog.json. Edits and removals only of git-tracked files."""
    target = p.target
    rel = PurePosixPath(target) if target else PurePosixPath(".")
    if not target or rel.is_absolute() or ".." in rel.parts or len(rel.parts) < 2:
        return [f"target is not a file path: {target or '(empty)'}"]
    top = rel.parts[0]
    if top == "skills-vendor":
        return ["skills-vendor is not writable"]
    if p.kind and p.kind not in KINDS:
        return [f"unknown kind: {p.kind}"]
    is_catalog = rel.parts == ("mcp", "catalog.json")
    if top not in ("skills", "rules", "hooks") and not is_catalog:
        return [f"harness target outside skills/, rules/, hooks/, mcp/catalog.json: {target}"]
    if top == "skills":
        if len(rel.parts) < 3:
            return [f"skills target must be skills/<name>/<file>: {target}"]
        if (home / "skills" / rel.parts[1]).is_symlink():
            return ["symlinked skill directory refused"]
    kind = effective_kind(p, home)
    exists = (home / target).exists()
    reasons: list[str] = []
    if not p.evidence.strip():
        reasons.append("missing evidence")
    if kind == "new":
        if top != "skills":
            reasons.append("new is for skill files only")
        if exists or (home / target).is_symlink():
            reasons.append("new but the target exists")
        if not p.body.strip():
            reasons.append("empty body")
    elif kind == "edit":
        if not exists:
            reasons.append("edit but the target does not exist")
        elif not tracked(home, target):
            reasons.append("edit of an untracked file refused")
        elif not p.body.strip():
            reasons.append("empty diff")
        elif f"--- a/{target}" not in p.body.splitlines() or f"+++ b/{target}" not in p.body.splitlines():
            reasons.append("diff does not name the target")
        elif not _diff_touches_only(home, p.body, target):
            reasons.append("diff touches files other than the target")
        elif not _git_apply_ok(home, p.body, check_only=True):
            reasons.append("stale: git apply --check failed")
    elif kind == "remove":
        if is_catalog:
            reasons.append("mcp/catalog.json is edited, not removed")
        elif not exists:
            reasons.append("remove but the target does not exist")
        elif not tracked(home, target):
            reasons.append("remove of an untracked file refused")
    return reasons


def validate(p: Proposal, home: Path, scope: str = "kb") -> list[str]:
    """Reasons a proposal cannot be applied. Empty list means valid."""
    if scope == "harness":
        return _validate_harness(p, home)
    if scope != "kb":
        return [f"unsupported scope: {scope}"]
    target = p.target
    rel = PurePosixPath(target) if target else PurePosixPath(".")
    if not target or rel.is_absolute() or ".." in rel.parts or len(rel.parts) < 2:
        return [f"target is not a file path: {target or '(empty)'}"]
    if rel.parts[0] in HARNESS_FOLDERS:
        return [HARNESS_REASON]
    if len(rel.parts) < 3:
        return [f"target is not a file path: {target}"]
    if rel.parts[0] != "kb":
        return [f"target outside kb/: {target}"]
    bucket = rel.parts[1]
    if bucket not in OWNED_DEFAULT:
        return [f"bucket not writable: kb/{bucket}"]
    if not (home / "kb" / bucket).is_dir():
        return [f"bucket directory missing: kb/{bucket}"]
    reasons: list[str] = []
    if p.kind and p.kind not in KINDS:
        return [f"unknown kind: {p.kind}"]
    if not p.evidence.strip():
        reasons.append("missing evidence")
    kind = effective_kind(p, home)
    exists = (home / target).exists()
    if kind == "new":
        if exists:
            reasons.append("new but the target exists")
        if not p.body.strip():
            reasons.append("empty body")
    elif kind == "edit":
        if not exists:
            reasons.append("edit but the target does not exist")
        if not p.body.strip():
            reasons.append("empty diff")
        elif f"--- a/{target}" not in p.body.splitlines() or f"+++ b/{target}" not in p.body.splitlines():
            reasons.append("diff does not name the target")
        elif not _diff_touches_only(home, p.body, target):
            reasons.append("diff touches files other than the target")
        elif exists and not _git_apply_ok(home, p.body, check_only=True):
            reasons.append("stale: git apply --check failed")
    elif kind == "remove":
        if not exists:
            reasons.append("remove but the target does not exist")
    return reasons


def _diff_touches_only(home: Path, diff: str, target: str) -> bool:
    """True when the diff changes no file but the target. A multi-file diff would pass the target's header
    check and still write elsewhere, including skills/ and hooks/."""
    text = diff if diff.endswith("\n") else diff + "\n"
    result = subprocess.run(["git", "apply", "--numstat", "-z", "-"], input=text.encode("utf-8"), cwd=home,
                            capture_output=True, check=False)
    if result.returncode != 0:
        return False
    paths = {entry.split("\t", 2)[-1] for entry in result.stdout.decode("utf-8", "replace").split("\0") if entry}
    return paths == {target}


def _git_apply_ok(home: Path, diff: str, *, check_only: bool) -> bool:
    args = ["git", "apply", "--check", "-"] if check_only else ["git", "apply", "-"]
    text = diff if diff.endswith("\n") else diff + "\n"
    result = subprocess.run(args, input=text.encode("utf-8"), cwd=home, capture_output=True, check=False)
    return result.returncode == 0


def ledger_path(root: Path) -> Path:
    return root / LEDGER_NAME


def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _append_ledger(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _decided_state(ref: str, sha: str, decisions: list[dict[str, Any]]) -> dict[str, Any] | None:
    last = None
    for row in decisions:
        if row.get("ref") == ref and row.get("sha") == sha and row.get("state") in ("applied", "rejected"):
            last = row
    return last


def _sources(home: Path, scope: str = "kb") -> list[tuple[str, Path, Path, str, str]]:
    """(source, proposals file, ledger, owner, step id) for every collectable file of one scope."""
    name = PROPOSALS_NAME if scope == "kb" else HARNESS_NAME
    ledger_name = LEDGER_NAME if scope == "kb" else HARNESS_LEDGER_NAME
    found: list[tuple[str, Path, Path, str, str]] = []
    for path in sorted((home / "factory").glob(f"*/steps/*/{name}")):
        owner = path.parents[2].name
        found.append(("factory", path, path.parents[2] / ledger_name, owner, STEP_PREFIX_RE.sub("", path.parent.name)))
    for path in sorted((home / "kb-inbox").glob(f"*/{name}")):
        found.append(("chat", path, path.parent / ledger_name, path.parent.name, "chat"))
    if scope == "harness":
        for path in sorted((home / "harness" / "proposals").glob(f"*/{name}")):
            found.append(("review", path, path.parent / ledger_name, "review", path.parent.name))
    return found


def _rows_for(path: Path, ledger: Path, owner: str, step: str, source: str, home: Path,
              scope: str = "kb") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    decisions = read_ledger(ledger)
    for p in parse(path):
        ref = f"{owner}:{step}:{p.n}"
        sha = sha_of(p, home)
        decided = _decided_state(ref, sha, decisions)
        reasons = validate(p, home, scope) if decided is None else []
        if decided is not None:
            state = decided["state"]
        elif reasons:
            state = "invalid"
        else:
            state = "pending"
        rows.append(
            {
                "ref": ref,
                "scope": scope,
                "source": source,
                "owner": owner,
                "step": step,
                "n": p.n,
                "target": p.target,
                "kind": effective_kind(p, home),
                "state": state,
                "sha": sha,
                "covers": p.covers,
                "keys": p.keys,
                "evidence": p.evidence,
                "reasons": reasons,
                "reason": (decided or {}).get("reason"),
                "applied_at": (decided or {}).get("ts") if state == "applied" else None,
                "file": str(path),
                "ledger": str(ledger),
            }
        )
    return rows


def run_rows(directory: Path, home: Path, scope: str = "kb") -> list[dict[str, Any]]:
    """Proposal rows of one factory run folder (steps/*/<file>, decisions in the run folder)."""
    name = PROPOSALS_NAME if scope == "kb" else HARNESS_NAME
    ledger = directory / (LEDGER_NAME if scope == "kb" else HARNESS_LEDGER_NAME)
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob(f"steps/*/{name}")):
        step = STEP_PREFIX_RE.sub("", path.parent.name)
        rows.extend(_rows_for(path, ledger, directory.name, step, "factory", home, scope))
    return rows


def collect(home: Path, scope: str = "kb") -> list[dict[str, Any]]:
    """Every proposal of one scope under the factory, the chat inbox (and review folders for harness)."""
    rows: list[dict[str, Any]] = []
    for source, path, ledger, owner, step in _sources(home, scope):
        rows.extend(_rows_for(path, ledger, owner, step, source, home, scope))
    return rows


def find(home: Path, ref: str, scope: str = "kb") -> dict[str, Any]:
    for row in collect(home, scope):
        if row["ref"] == ref:
            return row
    raise ProposalError(f"unknown ref: {ref}")


def load_proposal(row: dict[str, Any]) -> Proposal:
    for p in parse(Path(row["file"])):
        if p.n == row["n"]:
            return p
    raise ProposalError(f"proposal {row['ref']} is gone from {row['file']}")


def scope_of_file(path: Path) -> str:
    return "harness" if path.name == HARNESS_NAME else "kb"


def check(path: Path, home: Path) -> list[dict[str, Any]]:
    """Validate every proposal in one file, with the scope its file name gives. Writes no decision."""
    scope = scope_of_file(path)
    out = []
    for p in parse(path):
        reasons = validate(p, home, scope)
        out.append({"n": p.n, "target": p.target, "valid": not reasons, "reasons": reasons})
    return out


def _default_index_writer(home: Path, bucket_dir: Path) -> str:
    script = home / "kb" / "_shared" / "scripts" / "llm_index.py"
    spec = importlib.util.spec_from_file_location("llm_index_for_proposals", script)
    if spec is None or spec.loader is None:
        raise ProposalError(f"cannot load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.write_bucket_indexes(bucket_dir, module.skill_map())
    return "drop refused" if module.DROPPED else "written"


IndexWriter = Callable[[Path, Path], str]
Check = tuple[str, list[str]]


def _write_change(p: Proposal, home: Path, kind: str, ref: str) -> None:
    target = home / p.target
    if kind == "new":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(p.body.rstrip("\n") + "\n", encoding="utf-8")
    elif kind == "edit":
        if not _git_apply_ok(home, p.body, check_only=True):
            raise ProposalError(f"{ref} is stale: git apply --check failed")
        if not _git_apply_ok(home, p.body, check_only=False):
            raise ProposalError(f"{ref} failed to apply")
    elif kind == "remove":
        target.unlink()


def running_factory_runs(home: Path) -> list[str]:
    """Factory runs whose live state is running. Harness apply refuses while any exists."""
    import agentctl_factory as factory

    root = factory.factory_root()
    names: list[str] = []
    for directory in sorted(root.glob("*")) if root.is_dir() else []:
        if not (directory / "events.jsonl").is_file():
            continue
        snap = factory.snapshot(directory)
        # a run folder left "running" by a killed engine is not live: status shows it as interrupted
        if snap["state"] == "running" and snap["live"]:
            names.append(directory.name)
    return names


def harness_checks(home: Path, target: str) -> list[dict[str, Any]]:
    """Checks for the folder a harness change touched. Reports only; never reverts."""
    import subprocess as sp

    top = PurePosixPath(target).parts[0]
    if top == "skills":
        proc = sp.run(["agentctl", "skills", "audit", "--root", str(home / "skills")], capture_output=True, text=True, check=False)
        return [{"check": "agentctl skills audit", "exit": proc.returncode, "tail": (proc.stdout + proc.stderr)[-400:]}]
    if top == "rules":
        script = home / "bin" / "generate-agents-md.py"
        if not script.is_file():
            return [{"check": "generate-agents-md --check", "exit": None, "tail": "script missing"}]
        proc = sp.run(["python3", str(script), "--check"], capture_output=True, text=True, cwd=home, check=False)
        return [{"check": "generate-agents-md --check", "exit": proc.returncode, "tail": (proc.stdout + proc.stderr)[-400:]}]
    if target == "mcp/catalog.json":
        try:
            json.loads((home / target).read_text(encoding="utf-8"))
            return [{"check": "json parse mcp/catalog.json", "exit": 0, "tail": ""}]
        except (OSError, json.JSONDecodeError) as exc:
            return [{"check": "json parse mcp/catalog.json", "exit": 1, "tail": str(exc)[:400]}]
    return []


def apply(ref: str, home: Path, *, index_writer: IndexWriter | None = None, scope: str = "kb",
          checks: Callable[[Path, str], list[dict[str, Any]]] | None = None,
          running: Callable[[Path], list[str]] | None = None) -> dict[str, Any]:
    """Write one pending proposal, record `applied`. Never stages. KB apply refreshes the bucket index; harness
    apply refuses while a factory run is running and reports the checks for the touched folder."""
    row = find(home, ref, scope)
    if row["state"] != "pending":
        raise ProposalError(f"{ref} is {row['state']}, only pending proposals apply")
    if scope == "harness":
        live = (running or running_factory_runs)(home)
        if live:
            raise ProposalError(f"{ref} refused: factory run {', '.join(live)} is running")
    p = load_proposal(row)
    reasons = validate(p, home, scope)
    if reasons:
        raise ProposalError(f"{ref} is invalid: {'; '.join(reasons)}")
    kind = effective_kind(p, home)
    _write_change(p, home, kind, ref)
    result: dict[str, Any] = {"ref": ref, "target": p.target, "kind": kind, "state": "applied"}
    if scope == "kb":
        bucket = PurePosixPath(p.target).parts[1]
        writer = index_writer or _default_index_writer
        try:
            result["index"] = writer(home, home / "kb" / bucket)
        except Exception as exc:  # noqa: BLE001 - the KB change already happened; report the index, keep the decision
            result["index"] = f"index failed: {type(exc).__name__}: {exc}"
    else:
        result["checks"] = (checks or harness_checks)(home, p.target)
    applied = {"ts": _now(), "ref": ref, "state": "applied", "target": p.target, "sha": row["sha"], "keys": p.keys}
    _append_ledger(Path(row["ledger"]), applied)
    result["applied_at"] = applied["ts"]
    return result


def reject(ref: str, home: Path, *, reason: str, scope: str = "kb") -> dict[str, Any]:
    if not reason.strip():
        raise ProposalError("reject needs --reason")
    row = find(home, ref, scope)
    if row["state"] not in ("pending", "invalid"):
        raise ProposalError(f"{ref} is {row['state']}, only pending or invalid proposals reject")
    line = {
        "ts": _now(),
        "ref": ref,
        "state": "rejected",
        "target": row["target"],
        "sha": row["sha"],
        "reason": reason.strip(),
    }
    _append_ledger(Path(row["ledger"]), line)
    return {"ref": ref, "state": "rejected", "reason": line["reason"]}
