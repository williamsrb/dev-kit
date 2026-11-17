"""`agentctl release` integration side: test settings, runner, state, merge, checks, bugs, audit, review score.

Settings come from the profile `.agentctl [release]` and the project repo's own `.agentctl [release]` (project wins per
entry name). The integration branch lives in its own worktree and never moves the operator's checkout. One JSON state
file per release records merges, runs, bugs and verdicts. Nothing here pushes, posts or writes to the tracker.
"""

from __future__ import annotations

import contextlib
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import agentctl_config
import agentctl_githost
import agentctl_release as rl
from agentctl_common import agents_home
from agentctl_release import ReleaseError

BIN = Path(__file__).resolve().parent
TEST_KINDS = ("unit", "integration", "e2e", "lint", "smoke")
ENV_WORDS = ("review", "staging", "dev", "test", "qa", "sandbox", "preview")
TAIL_LINES = 40
RUN_CAP = 200
RESULT_FAIL = ("failed", "timeout")
PROOF_POINTS = {"ran": 1.0, "read": 0.5}
PARTS = {"criteria": 50, "impact": 20, "tests": 10, "evidence": 10, "quality": 10}
DIM_PART = {"fit": "criteria", "impact": "impact", "security": "impact", "tests": "tests", "quality": "quality",
            "less-code": "quality", "deslop": "quality", "performance": "quality"}
SAMPLES = {"python": ("unit", "python3 -m unittest"), "node": ("unit", "npm test"), "enonic": ("unit", "./gradlew test")}
PROVES = "This audit proves the test environment, not production."


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- tools


def git(repo: Path | str, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, errors="replace", check=False)
    if check and proc.returncode:
        raise ReleaseError(f"git {' '.join(args[:2])}: {(proc.stderr or proc.stdout).strip()[:300]}")
    return proc.stdout


def git_ok(repo: Path | str, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False).returncode == 0


def run_tool(argv: list[str], cwd: Path | None = None, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    """One external process (agentctl, playwright.py, find-auth-storage.py). Tests replace this."""
    try:
        return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(argv, 124, stdout=exc.stdout or "", stderr=f"timed out after {timeout}s")
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, stdout="", stderr=str(exc))


def agentctl_json(*args: str) -> dict[str, Any]:
    proc = run_tool([sys.executable, str(BIN / "agentctl"), *args])
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


# --------------------------------------------------------------------------- settings (FR-1)


def project_id(repo: Path) -> str:
    """`group/repo` of origin as the git host names it, else the repo folder name."""
    try:
        cfg = agentctl_config.load()
        host = agentctl_config.git_host(cfg)
        url = git(repo, "remote", "get-url", "origin").strip()
        if host is None:
            raise agentctl_githost.HostError("no git host")
        token = agentctl_githost.load_token(host, agents_home() / ".auth")
        base = os.environ.get("GITLAB_URL") or token["gitlab_url"]
        return agentctl_githost.project_from_remote(url, base)
    except (agentctl_githost.HostError, agentctl_config.ConfigError, ReleaseError, KeyError, OSError):
        return Path(repo).resolve().name


def sample_for(repo: Path) -> dict[str, Any]:
    stacks = agentctl_json("repo", "detect", "--cwd", str(repo)).get("stacks") or {}
    tests = [{"name": s, "kind": SAMPLES[s][0], "run": SAMPLES[s][1]} for s in stacks if s in SAMPLES]
    return {"tests": tests or [{"name": "unit", "kind": "unit", "run": "<your test command>"}]}


def _entry_tests(raw: Any, source: str) -> list[dict[str, Any]]:
    out, seen = [], set()
    for item in raw or []:
        name, run = item.get("name"), item.get("run")
        if not name or not isinstance(name, str) or not run or not isinstance(run, str):
            raise ReleaseError(f"{source}: every release test needs `name` and `run`: {item}")
        if name in seen:
            raise ReleaseError(f"{source}: duplicate release test {name!r}")
        seen.add(name)
        if item.get("kind") not in TEST_KINDS:
            raise ReleaseError(f"{source}: test {name!r} kind must be one of {', '.join(TEST_KINDS)}")
        cwd = str(item.get("cwd", "."))
        if Path(cwd).is_absolute() or ".." in Path(cwd).parts:
            raise ReleaseError(f"{source}: test {name!r} cwd must stay inside the repo")
        timeout = item.get("timeout_min", 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ReleaseError(f"{source}: test {name!r} timeout_min must be a positive number")
        out.append({"name": name, "kind": item["kind"], "run": run, "cwd": cwd, "paths": list(item.get("paths", [])),
                    "timeout_min": timeout, "env": bool(item.get("env", False)), "source": source})
    return out


def is_test_environment(name: str, base_url: str) -> bool:
    host = re.sub(r"^\w+://", "", base_url).split("/")[0].split(":")[0]
    tokens = set(re.split(r"[^a-z0-9]+", name.lower())) | set(re.split(r"[^a-z0-9]+", host.lower()))
    return bool(tokens & set(ENV_WORDS))


def _entry_envs(raw: Any, source: str) -> list[dict[str, Any]]:
    out, seen = [], set()
    for item in raw or []:
        name, base = item.get("name"), item.get("base_url")
        if not name or not base or not re.match(r"^https?://", str(base)):
            raise ReleaseError(f"{source}: every release environment needs `name` and an http(s) `base_url`: {item}")
        if name in seen:
            raise ReleaseError(f"{source}: duplicate release environment {name!r}")
        seen.add(name)
        if not is_test_environment(name, base):
            raise ReleaseError(f"{source}: environment {name!r} ({base}) is not a test environment; its name or a host "
                               f"label must be one of {', '.join(ENV_WORDS)}")
        out.append({"name": name, "base_url": str(base).rstrip("/"), "deploy": item.get("deploy") or "",
                    "version_url": item.get("version_url") or "", "default": bool(item.get("default", False)),
                    "source": source})
    return out


def _merge_by_name(profile: list[dict[str, Any]], project: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {e["name"]: e for e in profile}
    merged.update({e["name"]: e for e in project})
    return list(merged.values())


def load_settings(repo: Path) -> dict[str, Any]:
    repo = Path(repo).resolve()
    project = project_id(repo)
    warnings: list[str] = []
    try:
        profile_path: Path | None = agentctl_config.config_path()
        cfg = agentctl_config.load(profile_path)
    except agentctl_config.ConfigError:
        profile_path, cfg = None, {}
    entry = ((cfg.get("release") or {}).get("repos") or {}).get(project) or {}
    psrc = f"{profile_path} [release.repos.\"{project}\"]"
    tests = _entry_tests(entry.get("tests"), psrc)
    envs = _entry_envs(entry.get("envs"), psrc)
    own = repo / agentctl_config.FILE_NAME
    if own.is_file() and not (profile_path and own.resolve() == profile_path.resolve()):
        try:
            data = tomllib.loads(own.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ReleaseError(f"cannot read {own}: {exc}") from exc
        ignored = sorted(set(data) - {"release", "schema_version"})
        if ignored:
            warnings.append(f"{own}: only [release] is read, ignored: {', '.join(ignored)}")
        rel = data.get("release") or {}
        tests = _merge_by_name(tests, _entry_tests(rel.get("tests"), f"{own} [release]"))
        envs = _merge_by_name(envs, _entry_envs(rel.get("envs"), f"{own} [release]"))
    if envs:
        defaults = [e for e in envs if e["default"]]
        if not defaults and len(envs) == 1:
            envs[0]["default"] = True
        elif len(defaults) != 1:
            raise ReleaseError("exactly one release environment must have default = true, found "
                               f"{len(defaults)}: {', '.join(e['name'] for e in envs)}")
    return {"project": project, "repo": str(repo), "tests": tests, "envs": envs, "warnings": warnings}


def require_tests(settings: dict[str, Any]) -> None:
    if settings["tests"]:
        return
    sample = sample_for(Path(settings["repo"]))["tests"]
    lines = [f'[[release.tests]]           # in {settings["repo"]}/.agentctl, or [[release.repos."{settings["project"]}".tests]] in the profile']
    for t in sample:
        lines += [f'name = "{t["name"]}"', f'kind = "{t["kind"]}"', f'run = "{t["run"]}"', ""]
    raise ReleaseError(f"no [[release.tests]] table for project {settings['project']!r}. Sample:\n" + "\n".join(lines))


def resolve_env(settings: dict[str, Any], name: str | None) -> dict[str, Any] | None:
    envs = settings["envs"]
    if name:
        for env in envs:
            if env["name"] == name:
                return env
        raise ReleaseError(f"unknown release environment {name!r}; known: {', '.join(e['name'] for e in envs) or 'none'}")
    return next((e for e in envs if e["default"]), None)


# --------------------------------------------------------------------------- runner (FR-2)


def tail_of(log: Path, lines: int = TAIL_LINES) -> str:
    try:
        return "\n".join(log.read_text(errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


def _attempt(entry: dict[str, Any], cwd: Path, log: Path, env: dict[str, str]) -> tuple[str, int | None, float]:
    start = time.monotonic()
    try:
        argv = shlex.split(entry["run"])
    except ValueError as exc:
        log.write_text(f"cannot split command: {exc}\n")
        return "failed", 127, 0.0
    with log.open("wb") as handle:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT, env={**os.environ, **env},
                                    start_new_session=True)
        except OSError as exc:
            handle.write(f"cannot start {argv[:1]}: {exc}\n".encode())
            return "failed", 127, time.monotonic() - start
        try:
            code = proc.wait(timeout=float(entry["timeout_min"]) * 60)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            return "timeout", None, time.monotonic() - start
    return ("passed" if code == 0 else "failed"), code, time.monotonic() - start


def run_command(entry: dict[str, Any], worktree: Path, log_dir: Path, extra_env: dict[str, str] | None = None) -> dict[str, Any]:
    """Run one command; a failure is re-run once, fail-then-pass is `flaky`."""
    worktree = Path(worktree)
    log_dir.mkdir(parents=True, exist_ok=True)
    commit = git(worktree, "rev-parse", "HEAD", check=False).strip()
    cwd = worktree / entry["cwd"]
    env = dict(extra_env or {})
    stem = f"{re.sub(r'[^\w.-]+', '-', entry['name'])}-{commit[:7]}-{time.time_ns()}"
    log = log_dir / f"{stem}.log"
    result, code, secs = _attempt(entry, cwd, log, env)
    out = {"name": entry["name"], "kind": entry["kind"], "result": result, "exit": code, "seconds": round(secs, 2),
           "log": str(log), "commit": commit}
    if result == "failed":
        second = log_dir / f"{stem}-rerun.log"
        r2, c2, s2 = _attempt(entry, cwd, second, env)
        out["seconds"] = round(secs + s2, 2)
        if r2 == "passed":
            out.update(result="flaky", exit=0, first_log=str(log), log=str(second))
        else:
            out.update(exit=c2, log=str(second), first_log=str(log), result=r2)
    if out["result"] in RESULT_FAIL:
        out["tail"] = tail_of(Path(out["log"]))
    return out


def run_line(run: dict[str, Any]) -> str:
    code = "-" if run.get("exit") is None else run["exit"]
    return f"{run['name']:<16} {run['kind']:<12} {run['result']:<8} exit={code} {run['seconds']}s  {run['log']}"


# --------------------------------------------------------------------------- state (FR-3)


def state_path(slug: str) -> Path:
    return rl.releases_dir() / f"{slug}.state.json"


def release_dir(slug: str) -> Path:
    return rl.releases_dir() / slug


def load_state(slug: str) -> dict[str, Any]:
    path = state_path(slug)
    if not path.is_file():
        raise ReleaseError(f"no release state at {path}; run `agentctl release open --release {slug}` first")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    state["runs"] = state.get("runs", [])[-RUN_CAP:]
    state["updated"] = now()
    path = state_path(state["release"])
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def load_graph(slug: str) -> dict[str, Any]:
    path = rl.releases_dir() / f"{slug}.graph.json"
    if not path.is_file():
        raise ReleaseError(f"no saved graph: {path}; run `agentctl release graph` first")
    return json.loads(path.read_text(encoding="utf-8"))


def version_for(slug: str) -> str:
    name = slug[3:] if slug.startswith("fv-") else slug.removeprefix("epic-")
    return re.sub(r"[^\w.-]+", "-", name).strip("-.") or "release"


def worktree_for(repo: Path, version: str) -> Path:
    return repo.parent / f"{repo.name}-release" / version


# --------------------------------------------------------------------------- merge helpers


def merged_keys(state: dict[str, Any]) -> list[str]:
    return [m["key"] for m in state["merged"] if m["key"] not in {e["key"] for e in state["excluded"]}]


def task_of_commit(state: dict[str, Any], sha: str) -> str | None:
    return next((m["key"] for m in state["merged"] if sha in m["merge_commits"]), None)


def edge_pairs(graph: dict[str, Any], cls: str | None = None) -> list[dict[str, Any]]:
    return [e for e in graph["edges"] if cls is None or e["class"] == cls]


def sharing_edge(graph: dict[str, Any], a: str, b: str) -> bool:
    return any({e["from"], e["to"]} == {a, b} for e in graph["edges"])


def evidence_plan_exists(key: str) -> bool:
    plans = agents_home() / "plans"
    return (plans / key / "evidence.md").is_file() or (plans / f"{key}-evidence-plan.md").is_file()


def merge_refusals(state: dict[str, Any], graph: dict[str, Any], key: str) -> list[str]:
    members = {m["key"]: m for m in graph["members"]}
    if key not in members:
        return [f"{key} is not a member of release {state['release']}"]
    if key in {e["key"] for e in state["excluded"]}:
        return [f"{key} is excluded (reverted); re-including it is not supported"]
    reasons = []
    excluded = {e["key"] for e in state["excluded"]}
    merged = set(merged_keys(state))
    if key not in merged:
        pending = {k: m["wave"] for k, m in members.items() if k not in merged and k not in excluded and m["wave"] is not None}
        if members[key]["wave"] is None:
            reasons.append(f"{key} has no wave (cycle or after_cycle)")
        elif pending and members[key]["wave"] != min(pending.values()):
            first = min(pending.values())
            reasons.append(f"{key} is wave {members[key]['wave']}; wave {first} still has unmerged tasks: "
                           + ", ".join(sorted(k for k, w in pending.items() if w == first)))
    for edge in edge_pairs(graph, "hard"):
        if edge["to"] == key and edge["confidence"] == "high" and edge["from"] in members and edge["from"] not in merged:
            reasons.append(f"hard dependency {edge['from']} is not merged")
    if evidence_plan_exists(key):
        prog = agentctl_json("plan", "progress", key, "--kind", "evidence", "--json")
        if not prog.get("total") or prog.get("pending") or prog.get("blocked"):
            reasons.append(f"evidence of {key} is not all passed (pending={prog.get('pending')} blocked={prog.get('blocked')})")
    return reasons


# --------------------------------------------------------------------------- environments (FR-8)


def release_env_vars(state: dict[str, Any], env: dict[str, Any] | None, sha: str) -> dict[str, str]:
    return {"RELEASE_SHA": sha, "RELEASE_BRANCH": state["branch"], "RELEASE_ENV": env["name"] if env else "",
            "RELEASE_BASE_URL": env["base_url"] if env else ""}


def confirm_deploy(state: dict[str, Any], env: dict[str, Any] | None, head: str, deployed: str | None,
                   log_dir: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"env": env["name"] if env else None, "sha": head, "deployed": False, "reason": ""}
    if env is None:
        info["reason"] = "no test environment configured"
    elif env["deploy"]:
        run = run_command({"name": f"deploy-{env['name']}", "kind": "smoke", "run": env["deploy"], "cwd": ".",
                           "timeout_min": 30}, Path(state["worktree"]), log_dir, release_env_vars(state, env, head))
        info["deploy_log"] = run["log"]
        if run["result"] in ("passed", "flaky"):
            info["deployed"] = True
        else:
            info["reason"] = f"deploy command {run['result']}; log {run['log']}"
    elif env["version_url"]:
        try:
            with urllib.request.urlopen(env["version_url"], timeout=20) as resp:
                body = resp.read(65536).decode("utf-8", "replace")
        except (OSError, ValueError) as exc:
            body, info["reason"] = "", f"version_url unreachable: {exc}"
        tokens = re.findall(r"\b[0-9a-f]{7,40}\b", body.lower())
        if any(head.startswith(t) for t in tokens):
            info["deployed"] = True
        elif not info["reason"]:
            info["reason"] = f"version_url reports {tokens[:1] or 'no commit'}, not the integration head {head[:7]}"
    elif deployed:
        if len(deployed) >= 7 and head.startswith(deployed.lower()):
            info["deployed"] = True
        else:
            info["reason"] = f"--deployed {deployed} does not match the integration head {head[:7]}"
    else:
        info["reason"] = "no deploy, version_url or --deployed to confirm the build"
    return info


# --------------------------------------------------------------------------- replay (FR-6)


def replay_paths(version: str, key: str) -> tuple[str, Path, Path]:
    copy_id = f"{version}-replay-{key}"
    return copy_id, agents_home() / "plans" / copy_id, agents_home() / "prds" / copy_id / "evidence"


def copy_evidence_plan(key: str, copy_id: str, plan_dir: Path, folder: Path, base_url: str) -> tuple[str, str | None]:
    """Write the copy; return (text, old origin). The task's own plan is only read."""
    plans = agents_home() / "plans"
    src = plans / key / "evidence.md"
    if not src.is_file():
        src = plans / f"{key}-evidence-plan.md"
    text = src.read_text(encoding="utf-8")
    old_origin = None
    match = re.search(r"^\*\*Testing base URL:\*\*[ \t]*(?P<u>https?://[^\s)\]>`'\"]+)", text, re.MULTILINE)
    if match:
        old_url = match.group("u")
        old_origin = "/".join(old_url.split("/")[:3])
        text = text.replace(old_url, base_url)
        text = text.replace(old_origin, "/".join(base_url.split("/")[:3]))
    fmatch = re.search(r"^\*\*Evidence folder:\*\*[ \t]*`?(?P<p>[^\s`]+)`?", text, re.MULTILINE)
    if fmatch:
        old = fmatch.group("p").rstrip("/")
        for form in {old, str(Path(old).expanduser()), old.replace(str(Path.home()), "~")}:
            if form:
                text = text.replace(form, str(folder))
    text = re.sub(r"^(\*\*Mode:\*\*).*$", r"\1 local", text, flags=re.MULTILINE)
    text = re.sub(r"^(\*\*Jira:\*\*).*$", r"\1 n/a", text, flags=re.MULTILINE)
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "evidence.md").write_text(text, encoding="utf-8")
    return text, old_origin


def reset_replay_state(copy_id: str, plan_dir: Path, folder: Path) -> None:
    """Only ever touches the copy's own folders (named `<version>-replay-<KEY>`)."""
    if "-replay-" not in copy_id:
        raise ReleaseError(f"refusing to reset {copy_id}")
    (plan_dir / "evidence.progress.md").unlink(missing_ok=True)
    shutil.rmtree(folder.parent, ignore_errors=True)


def auth_state(text: str, base_url: str, repo: Path) -> tuple[bool, str, str | None]:
    """(ok, reason, storage path). Same lookup as the factory's `auth_state` gate."""
    if re.search(r"^\*\*Auth required:\*\*\s*no\b", text, re.MULTILINE | re.IGNORECASE):
        return True, "", None
    script = agents_home() / "skills" / "plan-task-evidence" / "scripts" / "find-auth-storage.py"
    host = re.sub(r"^\w+://", "", base_url).split("/")[0]
    proc = run_tool([sys.executable, str(script), "--json", "--cwd", str(repo), "--host", base_url])
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False, f"find-auth-storage output unreadable for {host}", None
    found = data if isinstance(data, list) else (data.get("host_matches") or [])
    if not found:
        return False, f"no saved auth state for {host}", None
    first = found[0]
    return True, "", first if isinstance(first, str) else (first.get("path") or first.get("file"))


def replay(state: dict[str, Any], key: str, env: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"name": f"replay:{key}", "kind": "replay", "task": key, "result": "not_run", "reason": ""}
    if not evidence_plan_exists(key):
        out["reason"] = "no evidence plan"
        return out
    copy_id, plan_dir, folder = replay_paths(state["version"], key)
    out["copy"] = copy_id
    text, _ = copy_evidence_plan(key, copy_id, plan_dir, folder, env["base_url"])
    ok, reason, storage = auth_state(text, env["base_url"], Path(state["worktree"]))
    if not ok:
        out["reason"] = reason
        return out
    reset_replay_state(copy_id, plan_dir, folder)
    (plan_dir / "evidence.md").write_text(text, encoding="utf-8")
    playwright = agents_home() / "mcp" / "playwright.py"
    spawn = [sys.executable, str(playwright), "spawn", copy_id, "--enable"] + (["--storage-state", storage] if storage else [])
    try:
        proc = run_tool(spawn)
        if proc.returncode:
            out["reason"] = f"playwright spawn failed: {(proc.stderr or proc.stdout).strip()[:200]}"
            return out
        run_tool([sys.executable, str(BIN / "agentctl"), "factory", "start", copy_id, "--pipeline", "release-replay",
                  "--foreground"], cwd=Path(state["worktree"]), timeout=3600)
        prog = agentctl_json("plan", "progress", copy_id, "--kind", "evidence", "--json")
        if prog.get("total") and not prog.get("pending") and not prog.get("blocked"):
            out["result"] = "passed"
        elif prog.get("blocked") or (prog.get("done") and prog.get("pending")):
            out["result"] = "failed"
            out["reason"] = f"pending={prog.get('pending')} blocked={prog.get('blocked')}"
        else:
            park = (agentctl_json("factory", "status", copy_id, "--json").get("park") or {}).get("reason")
            out["reason"] = park or "the replay did not run"
    finally:
        run_tool([sys.executable, str(playwright), "stop", copy_id])
    return out


# --------------------------------------------------------------------------- checks (FR-5)


def rev(repo: Path | str, ref: str = "HEAD") -> str:
    return git(repo, "rev-parse", ref).strip()


def developer_for(graph: dict[str, Any], repo: Path, key: str) -> str | None:
    member = next((m for m in graph["members"] if m["key"] == key), None)
    if not member:
        return None
    if member.get("assignee"):
        return member["assignee"]
    ref = member.get("branch") or rl.branch_ref(rl.load_related(), repo, key)
    return git(repo, "log", "-1", "--format=%an", ref, check=False).strip() or None if ref else None


def new_failure(state: dict[str, Any], run: dict[str, Any]) -> bool:
    return run["result"] in RESULT_FAIL and run["name"] not in state["baseline"]


def merge_commits_since(state: dict[str, Any], since: str) -> list[str]:
    out = git(state["worktree"], "rev-list", "--first-parent", "--merges", "--reverse", f"{since}..HEAD", check=False)
    return out.split()


def changed_files(worktree: str, sha: str) -> list[str]:
    return git(worktree, "diff", "--name-only", f"{sha}^1", sha, check=False).split()


def next_bug_number(state: dict[str, Any]) -> int:
    nums = [b["number"] for b in state["bugs"]] + [b["number"] for e in state["excluded"] for b in e.get("bugs", [])]
    return max(nums, default=0) + 1


def propose_owner(state: dict[str, Any], graph: dict[str, Any], since: str, paths: list[str], area: str | None) -> list[str]:
    shas = list(reversed(merge_commits_since(state, since)))
    keys: list[str] = []
    for sha in shas:
        key = task_of_commit(state, sha)
        if key and key not in keys:
            keys.append(key)

    def rank(key: str) -> int:
        files = [f for m in state["merged"] if m["key"] == key for sha in m["merge_commits"] for f in changed_files(state["worktree"], sha)]
        by_path = any(fnmatch.fnmatch(f, p) for f in files for p in paths)
        by_edge = bool(area) and sharing_edge(graph, key, area)
        return 0 if by_path or by_edge else 1

    return sorted(keys, key=rank)


class Probe:
    """Temporary worktree on `release-probe/<version>`, moved with `checkout -B`, removed on exit."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.branch = f"release-probe/{state['version']}"
        self.path = Path(state["worktree"]).parent / f"{state['version']}-probe"
        self.made = False

    def at(self, sha: str) -> Path:
        repo = self.state["repo"]
        if not self.made:
            git(repo, "worktree", "add", "-B", self.branch, str(self.path), sha)
            self.made = True
        else:
            git(self.path, "checkout", "-q", "-B", self.branch, sha)
        return self.path

    def close(self) -> None:
        if self.made:
            git(self.state["repo"], "worktree", "remove", "--force", str(self.path), check=False)
            git(self.state["repo"], "branch", "-D", self.branch, check=False)
            self.made = False


def probe_owner(state: dict[str, Any], probe: Probe, entry: dict[str, Any], since: str, log_dir: Path) -> str | None:
    for sha in merge_commits_since(state, since):
        run = run_command(entry, probe.at(sha), log_dir)
        if run["result"] in RESULT_FAIL:
            return task_of_commit(state, sha)
    return None


def open_bug(state: dict[str, Any], graph: dict[str, Any], run: dict[str, Any], env: dict[str, Any] | None,
             owner: str | None, owner_state: str, candidates: list[str]) -> dict[str, Any]:
    number = next_bug_number(state)
    bug = {"id": f"{state['version']}-RB{number}", "number": number, "check": run["name"], "log": run.get("log", ""),
           "environment": env["name"] if env else None, "owner_task": owner,
           "owner_developer": developer_for(graph, Path(state["repo"]), owner) if owner else None,
           "owner_state": owner_state, "candidates": candidates, "status": "open", "tests": {"task": [], "e2e": []},
           "reason": "", "opened": now(), "commit": run.get("commit", "")}
    state["bugs"].append(bug)
    return bug


def layer_files(state: dict[str, Any], settings: dict[str, Any], bug_id: str) -> tuple[list[str], list[str], list[str]]:
    """(task-level files, e2e files, missing layers) found by `git grep -w -F` on the integration head."""
    def found(globs: list[str]) -> list[str]:
        if not globs:
            return []
        out = git(state["worktree"], "grep", "-l", "-w", "-F", bug_id, "HEAD", "--", *[f":(glob){g}" for g in globs],
                  check=False)
        return sorted(line.split(":", 1)[1] for line in out.splitlines() if ":" in line)

    task_paths = [p for c in settings["tests"] if c["kind"] != "e2e" for p in c["paths"]]
    e2e_paths = [p for c in settings["tests"] if c["kind"] == "e2e" for p in c["paths"]]
    task_files, e2e_files = found(task_paths), found(e2e_paths)
    missing = [name for name, files in (("task-level", task_files), ("end-to-end", e2e_files)) if not files]
    return task_files, e2e_files, missing


def clean_state(state: dict[str, Any], settings: dict[str, Any]) -> bool:
    last = state["last"]
    for cmd in settings["tests"]:
        run = last.get(cmd["name"])
        if run is None:
            return False
        if new_failure(state, run) or (cmd["kind"] == "e2e" and run["result"] != "passed"):
            return False
    return not any(new_failure(state, r) for n, r in last.items() if n.startswith("replay:"))


def close_bugs(state: dict[str, Any], settings: dict[str, Any]) -> None:
    clean = clean_state(state, settings)
    has_e2e = any(c["kind"] == "e2e" for c in settings["tests"])
    for bug in state["bugs"]:
        if bug["status"] != "open":
            continue
        task_files, e2e_files, missing = layer_files(state, settings, bug["id"])
        bug["tests"] = {"task": task_files, "e2e": e2e_files}
        if not has_e2e:
            bug["reason"] = "no end-to-end command configured"
        elif missing:
            bug["reason"] = "missing test layer: " + ", ".join(missing)
        elif not clean:
            bug["reason"] = "checks still failing"
        else:
            bug["status"], bug["reason"], bug["closed"] = "closed", "", now()


def open_bugs(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [b for b in state["bugs"] if b["status"] == "open"]


def replay_targets(state: dict[str, Any], graph: dict[str, Any], scope: str, merged: str | None) -> list[str]:
    keys = merged_keys(state)
    if scope == "audit":
        return keys
    if scope == "merge" and merged:
        order = keys.index(merged) if merged in keys else len(keys)
        return [k for k in keys[:order] if sharing_edge(graph, k, merged)]
    return []


def run_checks(state: dict[str, Any], settings: dict[str, Any], graph: dict[str, Any], *, scope: str,
               merged: str | None = None, env_name: str | None = None, deployed: str | None = None,
               run_all: bool = True) -> dict[str, Any]:
    wt = Path(state["worktree"])
    head = rev(wt)
    if state["state"] == "ready" and head != (state.get("audit") or {}).get("commit"):
        state["state"] = "open"
    log_dir = release_dir(state["release"]) / "logs"
    env = resolve_env(settings, env_name)
    last = state["last"]
    selected = settings["tests"] if run_all else [
        c for c in settings["tests"] if c["name"] not in last or last[c["name"]]["result"] in (*RESULT_FAIL, "not_run")]
    if any(c["env"] for c in selected) or (env and replay_targets(state, graph, scope, merged)):
        dep = confirm_deploy(state, env, head, deployed, log_dir)
    else:
        dep = {"env": env["name"] if env else None, "sha": head, "deployed": False,
               "reason": "no env command or replay selected"}
    state["deploy"] = {**dep, "date": now()}
    results: list[dict[str, Any]] = []
    for cmd in selected:
        if cmd["env"] and not dep["deployed"]:
            run = {"name": cmd["name"], "kind": cmd["kind"], "result": "not_run", "exit": None, "seconds": 0, "log": "",
                   "commit": head, "reason": dep["reason"]}
        else:
            run = run_command(cmd, wt, log_dir, release_env_vars(state, env, head) if cmd["env"] else {})
        results.append(run)
    if dep["deployed"] and env:
        for key in replay_targets(state, graph, scope, merged):
            run = replay(state, key, env)
            run["commit"] = head
            results.append(run)
    prior_pass = dict(state.get("passed_at", {}))
    new = []
    for run in results:
        run["date"] = now()
        last[run["name"]] = run
        state["runs"].append({k: v for k, v in run.items() if k != "tail"})
        if run["result"] == "passed":
            state.setdefault("passed_at", {})[run["name"]] = head
        if new_failure(state, run):
            new.append(run)
    probe = Probe(state)
    try:
        for run in new:
            existing = next((b for b in open_bugs(state) if b["check"] == run["name"]), None)
            if existing:
                existing.update(log=run.get("log", ""), commit=head)
                continue
            since = prior_pass.get(run["name"], state["base_sha"])
            cmd = next((c for c in settings["tests"] if c["name"] == run["name"]), None)
            if scope == "merge" and merged:
                open_bug(state, graph, run, env, merged, "assigned", [merged])
            elif cmd and not cmd["env"]:
                owner = probe_owner(state, probe, cmd, since, log_dir)
                open_bug(state, graph, run, env, owner, "assigned" if owner else "unassigned", [owner] if owner else [])
            else:
                paths = cmd["paths"] if cmd else []
                area = run.get("task")
                cands = propose_owner(state, graph, since, paths, area)
                open_bug(state, graph, run, env, cands[0] if cands else None, "proposed" if cands else "unassigned", cands)
    finally:
        probe.close()
    close_bugs(state, settings)
    if open_bugs(state):
        state["state"] = "blocked"
    elif state["state"] == "blocked":
        state["state"] = "open"
    save_state(state)
    return {"runs": results, "new_failures": [r["name"] for r in new], "deploy": dep}


def print_run_result(summary: dict[str, Any], state: dict[str, Any]) -> None:
    for run in summary["runs"]:
        line = run_line(run) if run["kind"] != "replay" else f"{run['name']:<16} replay       {run['result']:<8} {run.get('reason', '')}"
        print(line + (f"  ({run['reason']})" if run.get("reason") and run["kind"] != "replay" else ""))
        if run.get("tail") and new_failure(state, run):
            print("\n".join("    " + t for t in run["tail"].splitlines()))
    dep = summary["deploy"]
    print(f"environment: {dep['env'] or 'none'}  deployed: {'yes' if dep['deployed'] else 'no'}"
          + (f" ({dep['reason']})" if not dep["deployed"] else ""))
    for bug in open_bugs(state):
        print(f"open bug {bug['id']}: {bug['check']} owner {bug['owner_task'] or 'unassigned'} ({bug['owner_state']})"
              + (f"  {bug['reason']}" if bug["reason"] else ""))
    print(f"state: {state['state']}")


# --------------------------------------------------------------------------- commands: tests, open, merge, status, remove, check


def cmd_tests(args: Any) -> int:
    repo = Path(args.repo).resolve()
    settings = load_settings(repo)
    if args.list:
        print(f"project: {settings['project']}  repo: {repo}")
        for c in settings["tests"]:
            print(f"test {c['name']:<14} {c['kind']:<12} env={str(c['env']).lower():<5} {c['run']}  [{c['source']}]")
        for e in settings["envs"]:
            print(f"env  {e['name']:<14} {e['base_url']}{'  (default)' if e['default'] else ''}  [{e['source']}]")
        for w in settings["warnings"]:
            print(f"warning: {w}")
        return 0
    require_tests(settings)
    env = resolve_env(settings, args.env)
    if env:
        print(f"environment: {env['name']} {env['base_url']} [{env['source']}]")
    chosen = [c for c in settings["tests"] if (not args.kind or c["kind"] == args.kind) and (not args.name or c["name"] == args.name)]
    if not chosen:
        raise ReleaseError("no configured test matches --kind/--name")
    log_dir = agents_home() / "prds" / "releases" / "_tests" / re.sub(r"[^\w.-]+", "-", settings["project"])
    failed = False
    for cmd in chosen:
        if cmd["env"] and env is None:
            print(f"{cmd['name']:<16} {cmd['kind']:<12} not_run  needs a test environment (pass --env)")
            continue
        extra = {"RELEASE_ENV": env["name"], "RELEASE_BASE_URL": env["base_url"]} if cmd["env"] and env else {}
        run = run_command(cmd, repo, log_dir, extra)
        print(run_line(run))
        if run.get("tail"):
            print("\n".join("    " + t for t in run["tail"].splitlines()))
        failed = failed or run["result"] in RESULT_FAIL
    return 1 if failed else 0


def cmd_open(args: Any) -> int:
    slug = args.release
    graph = load_graph(slug)
    repo = Path(graph["repo"])
    if state_path(slug).is_file():
        raise ReleaseError(f"release {slug} is already open; see `agentctl release status --release {slug}`")
    settings = load_settings(repo)
    require_tests(settings)
    version = version_for(slug)
    branch = f"release/{version}"
    if git_ok(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"):
        raise ReleaseError(f"branch {branch} already exists; `agentctl release status --release {slug}` shows the release")
    wt = worktree_for(repo, version)
    wt.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "-b", branch, str(wt), graph["base"])
    state = {"release": slug, "version": version, "branch": branch, "worktree": str(wt), "repo": str(repo),
             "base": graph["base"], "base_sha": rev(wt), "state": "open", "baseline": [], "merged": [], "excluded": [],
             "runs": [], "bugs": [], "last": {}, "passed_at": {}, "audit": None, "opened": now()}
    log_dir = release_dir(slug) / "logs"
    for cmd in settings["tests"]:
        if cmd["env"]:
            continue
        run = run_command(cmd, wt, log_dir)
        state["last"][cmd["name"]] = {**run, "date": now()}
        state["runs"].append({k: v for k, v in run.items() if k != "tail"})
        print(run_line(run))
        if run["result"] in RESULT_FAIL:
            state["baseline"].append(cmd["name"])
        elif run["result"] == "passed":
            state["passed_at"][cmd["name"]] = state["base_sha"]
    save_state(state)
    print(f"opened {branch} at {wt}; baseline failures (pre-existing): {', '.join(state['baseline']) or 'none'}")
    return 0


def cmd_merge(args: Any) -> int:
    state = load_state(args.release)
    graph = load_graph(args.release)
    key = args.key.upper()
    if state["state"] == "delivered":
        raise ReleaseError("release is delivered; nothing can be merged")
    reasons = merge_refusals(state, graph, key)
    if reasons:
        raise ReleaseError(f"merge of {key} refused:\n  " + "\n  ".join(reasons))
    settings = load_settings(Path(state["repo"]))
    member = next(m for m in graph["members"] if m["key"] == key)
    ref = member.get("branch") or rl.branch_ref(rl.load_related(), Path(state["repo"]), key)
    if not ref:
        raise ReleaseError(f"{key} has no branch to merge")
    wt = Path(state["worktree"])
    before = rev(wt)
    proc = subprocess.run(["git", "-C", str(wt), "merge", "--no-ff", "-m", f"Merge {key} into {state['branch']}", ref],
                          capture_output=True, text=True, check=False)
    if proc.returncode:
        files = git(wt, "diff", "--name-only", "--diff-filter=U", check=False).split()
        git(wt, "merge", "--abort", check=False)
        raise ReleaseError(f"merge of {key} conflicts and was aborted; files: {', '.join(files) or '(see git)'}")
    after = rev(wt)
    record = next((m for m in state["merged"] if m["key"] == key), None)
    if record is None:
        record = {"key": key, "merge_commits": [], "date": now(),
                  "warning": "" if evidence_plan_exists(key) else "no evidence plan: merged without an evidence check"}
        state["merged"].append(record)
    if after != before:
        record["merge_commits"].append(after)
    else:
        print(f"{key}: already up to date, no merge commit")
    if record["warning"]:
        print(f"warning: {record['warning']}")
    summary = run_checks(state, settings, graph, scope="merge", merged=key, env_name=args.env)
    print_run_result(summary, state)
    return 1 if state["state"] == "blocked" else 0


def cmd_check(args: Any) -> int:
    state = load_state(args.release)
    graph = load_graph(args.release)
    settings = load_settings(Path(state["repo"]))
    summary = run_checks(state, settings, graph, scope="check", env_name=args.env, deployed=args.deployed,
                         run_all=args.all)
    print_run_result(summary, state)
    return 1 if state["state"] == "blocked" else 0


def cmd_remove(args: Any) -> int:
    state = load_state(args.release)
    graph = load_graph(args.release)
    key = args.key.upper()
    if key not in merged_keys(state):
        raise ReleaseError(f"{key} is not merged in release {args.release}")
    merged = set(merged_keys(state)) - {key}
    blockers = sorted({e["to"] for e in edge_pairs(graph, "hard") if e["from"] == key and e["to"] in merged})
    if blockers:
        raise ReleaseError(f"remove of {key} refused: merged task(s) depend on it: {', '.join(blockers)}")
    wt = Path(state["worktree"])
    record = next(m for m in state["merged"] if m["key"] == key)
    reverts = []
    for sha in reversed(record["merge_commits"]):
        proc = subprocess.run(["git", "-C", str(wt), "revert", "-m", "1", "--no-edit", sha], capture_output=True,
                              text=True, check=False)
        if proc.returncode:
            git(wt, "revert", "--abort", check=False)
            raise ReleaseError(f"revert of {sha[:7]} ({key}) failed and was aborted: {(proc.stderr or proc.stdout).strip()[:200]}")
        reverts.append(rev(wt))
    moved = [b for b in state["bugs"] if b["status"] == "open" and b["owner_task"] == key]
    for bug in moved:
        bug["status"] = "moved"
    state["bugs"] = [b for b in state["bugs"] if b not in moved]
    state["excluded"].append({"key": key, "date": now(), "revert_commits": reverts, "bugs": moved})
    state["last"].pop(f"replay:{key}", None)
    settings = load_settings(Path(state["repo"]))
    summary = run_checks(state, settings, graph, scope="check", env_name=args.env)
    print(f"{key} excluded; reverted {len(reverts)} merge commit(s)")
    print_run_result(summary, state)
    return 1 if state["state"] == "blocked" else 0


def status_data(state: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    excluded = {e["key"] for e in state["excluded"]}
    merged = set(merged_keys(state))
    waves = []
    for wave in graph["waves"]:
        waves.append({"wave": wave["wave"], "merged": [k for k in wave["keys"] if k in merged],
                      "pending": [k for k in wave["keys"] if k not in merged and k not in excluded],
                      "excluded": [k for k in wave["keys"] if k in excluded]})
    behind = git(state["worktree"], "rev-list", "--count", f"HEAD..{state['base']}", check=False).strip()
    return {"release": state["release"], "state": state["state"], "branch": state["branch"], "worktree": state["worktree"],
            "waves": waves, "bugs": open_bugs(state), "baseline": state["baseline"], "behind_base": int(behind or 0),
            "last": {n: {k: r.get(k) for k in ("kind", "result", "log", "commit")} for n, r in state["last"].items()}}


def cmd_status(args: Any) -> int:
    state = load_state(args.release)
    data = status_data(state, load_graph(args.release))
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    print(f"Release {data['release']}  state: {data['state']}  branch: {data['branch']}  behind {state['base']}: {data['behind_base']}")
    for w in data["waves"]:
        print(f"Wave {w['wave']}: merged [{', '.join(w['merged'])}] pending [{', '.join(w['pending'])}] excluded [{', '.join(w['excluded'])}]")
    for bug in data["bugs"]:
        print(f"open bug {bug['id']}: {bug['check']} owner {bug['owner_task'] or 'unassigned'} ({bug['owner_state']})"
              + (f"  {bug['reason']}" if bug["reason"] else ""))
    for name, run in data["last"].items():
        print(f"check {name:<16} {run['kind']:<12} {run['result']}" + (" (pre-existing)" if name in data["baseline"] and run["result"] in RESULT_FAIL else ""))
    return 0


# --------------------------------------------------------------------------- bugs


def find_bug(state: dict[str, Any], bug_id: str) -> dict[str, Any]:
    for bug in state["bugs"]:
        if bug["id"] == bug_id:
            return bug
    raise ReleaseError(f"no bug {bug_id} in release {state['release']}")


def bug_draft(state: dict[str, Any], bug: dict[str, Any]) -> str:
    owner = bug["owner_task"] or "unassigned"
    return (f"# {bug['id']}: {bug['check']} fails in release {state['version']}\n\n"
            f"The release build fails the check `{bug['check']}` after merging tasks into {state['branch']}. "
            f"Owner: {owner} ({bug['owner_state']}), developer {bug['owner_developer'] or 'unknown'}.\n\n"
            f"Log: {bug['log'] or 'n/a'}\nEnvironment: {bug['environment'] or 'none'}\n\n"
            f"The fix needs two tests that name `{bug['id']}`: one task-level test and one end-to-end test.\n")


def cmd_bugs(args: Any) -> int:
    state = load_state(args.release)
    if args.confirm:
        bug = find_bug(state, args.confirm)
        if not args.owner or args.owner.upper() not in merged_keys(state):
            raise ReleaseError("--owner must be a merged task of this release")
        owner = args.owner.upper()
        bug.update(owner_task=owner, owner_state="assigned", owner_developer=developer_for(load_graph(args.release), Path(state["repo"]), owner))
        save_state(state)
        print(f"{bug['id']} owner confirmed: {owner}")
    elif args.draft:
        bug = find_bug(state, args.draft)
        path = release_dir(args.release) / "bugs" / f"{bug['id']}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(bug_draft(state, bug), encoding="utf-8")
        print(f"draft written: {path}\nNothing was created. To create it:\n"
              f"  agentctl jira create --project <KEY> --type Bug --summary \"{bug['id']}: {bug['check']} fails in {state['version']}\" "
              f"--description \"$(cat {path})\"")
    else:
        for bug in state["bugs"]:
            print(f"{bug['id']}  {bug['status']:<7} {bug['check']}  owner {bug['owner_task'] or 'unassigned'} ({bug['owner_state']})  "
                  f"tests task={bug['tests']['task']} e2e={bug['tests']['e2e']}  {bug['reason']}")
    return 0


# --------------------------------------------------------------------------- review and score (FR-10)


def score(task: dict[str, Any]) -> dict[str, Any]:
    """Pure: the 0..100 score of one task from its criteria verdicts, findings and n/a flags."""
    findings = task.get("findings", [])
    criteria = task.get("criteria", [])
    parts: dict[str, dict[str, Any]] = {}

    def penalised(part: str, base: float) -> float:
        top = PARTS[part]
        mine = [f for f in findings if DIM_PART.get(f.get("dimension", "quality"), "quality") == part]
        if any(f.get("class") == "Blocker" for f in mine):
            return 0.0
        concerns = sum(1 for f in mine if f.get("class") == "Concern")
        notes = sum(1 for f in mine if f.get("class") == "Note")
        return max(0.0, base - concerns * top / 4 - min(notes * top / 20, top / 4))

    ran = 0.0
    if task.get("no_requirements"):
        parts["criteria"] = {"max": 50, "earned": 0.0, "assessed": True, "label": "no requirements source"}
    elif criteria:
        credit = sum(PROOF_POINTS.get(c.get("proof"), 0.0) if c.get("state") == "met" else 0.0 for c in criteria)
        ran = sum(1 for c in criteria if c.get("state") == "met" and c.get("proof") == "ran") / len(criteria) * 50
        parts["criteria"] = {"max": 50, "earned": penalised("criteria", credit / len(criteria) * 50), "assessed": True, "label": ""}
    else:
        parts["criteria"] = {"max": 50, "earned": 0.0, "assessed": False, "label": "no criteria in the requirements"}
    parts["impact"] = {"max": 20, "earned": penalised("impact", 20), "assessed": True, "label": ""}
    has_tests = bool(task.get("test_layer"))
    parts["tests"] = {"max": 10, "earned": penalised("tests", 10) if has_tests else 0.0, "assessed": has_tests,
                      "label": "" if has_tests else "no test layer"}
    ev = task.get("evidence")
    parts["evidence"] = {"max": 10, "earned": 10 * ev["passed"] / ev["total"] if ev and ev.get("total") else 0.0,
                         "assessed": bool(ev and ev.get("total")), "label": "" if ev and ev.get("total") else "no replayed shots"}
    parts["quality"] = {"max": 10, "earned": penalised("quality", 10), "assessed": True, "label": ""}
    assessed = sum(p["max"] for p in parts.values() if p["assessed"])
    earned = sum(p["earned"] for p in parts.values() if p["assessed"])
    blocker = any(f.get("class") == "Blocker" for f in findings)
    value = round(100 * earned / assessed) if assessed else 0
    if blocker:
        value = min(value, 50)
    return {"score": value, "assessed": assessed, "proved": round(ran, 2), "parts": parts, "blocker": blocker}


def release_score(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [t for t in tasks if t.get("score") is not None]
    if not scored:
        return {"score": None, "lowest": None, "blocker": False}
    weights = [len(t.get("criteria", [])) for t in scored]
    if not any(weights):
        weights = [1] * len(scored)
    value = round(sum(w * t["score"] for w, t in zip(weights, scored, strict=True)) / sum(weights))
    blocker = any(t.get("blocker") for t in scored)
    if blocker:
        value = min(value, 50)
    lowest = min(scored, key=lambda t: t["score"])["key"]
    return {"score": value, "lowest": lowest, "blocker": blocker}


def recompute(audit: dict[str, Any]) -> dict[str, Any]:
    """The release score again from `audit.json` alone."""
    rows = []
    for t in audit["tasks"]:
        review = t.get("review")
        if not review or not review.get("reviewed"):
            rows.append({"key": t["key"], "score": None})
            continue
        s = score(review)
        rows.append({"key": t["key"], "score": s["score"], "criteria": review["criteria"], "blocker": s["blocker"]})
    return release_score(rows)


CHECKBOX = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+(.+?)\s*$")
CRITERIA_MARK = re.compile(r"(?i)^(?:#{1,6}\s+|\*\*)?acceptance criteria")


def parse_criteria(text: str) -> list[dict[str, str]]:
    """`- [ ]` lines under an Acceptance Criteria heading or bold label, up to the next heading or label."""
    items: list[str] = []
    active = False
    for line in text.splitlines():
        if CRITERIA_MARK.match(line.strip()):
            active = True
            continue
        if active and (re.match(r"^#{1,6}\s", line) or re.match(r"^\*\*[^*]+:?\*\*:?\s*$", line.strip())):
            active = False
        if active and (m := CHECKBOX.match(line)):
            items.append(m.group(1))
    return [{"id": f"C{i}", "text": t} for i, t in enumerate(items, 1)]


def requirements_for(key: str) -> tuple[Path | None, Path | None]:
    """(prd path, delivered plan path). The plan is context only."""
    ctx = agentctl_json("plan", "context", key)
    prd = Path(ctx["prd"]) if ctx.get("prd") and Path(ctx["prd"]).is_file() else None
    plan = Path(ctx["plan"]) if ctx.get("plan") and Path(ctx["plan"]).is_file() else None
    if prd is None and agentctl_config.key_kind(key, ignore_case=False):
        run_tool([sys.executable, str(BIN / "agentctl"), "jira", "fetch", key, "--no-attachments"])
        candidate = agents_home() / "prds" / f"{key}.md"
        prd = candidate if candidate.is_file() else None
    return prd, plan


def criteria_store(slug: str) -> tuple[Path, dict[str, Any]]:
    path = release_dir(slug) / "criteria.json"
    return path, (json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {})


def criteria_for(slug: str, key: str, prd: Path | None) -> dict[str, Any]:
    """The stored criteria of a task, reused while the PRD hash is unchanged; else counted mechanically."""
    path, store = criteria_store(slug)
    if prd is None:
        return {"source": None, "sha256": None, "items": [], "needs_extraction": False}
    digest = hashlib.sha256(prd.read_bytes()).hexdigest()
    entry = store.get(key)
    if entry and entry.get("sha256") == digest and entry.get("source") == str(prd) and entry.get("items"):
        return {**entry, "needs_extraction": False}
    items = parse_criteria(prd.read_text(encoding="utf-8", errors="replace"))
    entry = {"source": str(prd), "sha256": digest, "items": items}
    if items:
        store[key] = entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {**entry, "needs_extraction": not items}


def store_extracted(slug: str, key: str, prd: Path, extracted: list[dict[str, str]]) -> list[dict[str, str]]:
    items = [{"id": f"C{i}", "text": str(e.get("text", ""))} for i, e in enumerate(extracted or [], 1) if e.get("text")]
    if items:
        path, store = criteria_store(slug)
        store[key] = {"source": str(prd), "sha256": hashlib.sha256(prd.read_bytes()).hexdigest(), "items": items}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return items


REVIEW_SCHEMA = """{"criteria": [{"id": "C1", "state": "met|unmet|unproven", "proof": "ran|read|none", "evidence": "Premise -> Path -> Verdict with file:line, or a test path plus its command"}],
 "findings": [{"class": "Blocker|Concern|Note", "dimension": "fit|impact|security|tests|quality|less-code|deslop|performance", "task": "<KEY>", "evidence": "..."}],
 "test_layer": true,
 "extracted": [{"text": "only when the criteria list is empty: the acceptance criteria you extracted"}]}"""


def write_review_context(state: dict[str, Any], key: str, out: Path, *, prd: Path | None, plan: Path | None,
                         criteria: dict[str, Any], diff_ranges: list[str], runs: list[dict[str, Any]],
                         replay_copy: str | None, evidence_out: Path) -> Path:
    path = out.parent / f"{key}.context.md"
    lines = [f"# Release review context: {key}", "", "Report only. Edit no code, no plan, no progress file.", "",
             f"Release {state['release']} on branch {state['branch']}, worktree {state['worktree']}.",
             f"Requirements (PRD): {prd or 'none: the criteria part scores 0'}",
             f"Delivered plan (context only, never lowers the criteria): {plan or 'none'}",
             "Review exactly these ranges (not the whole release):", *[f"  {r}" for r in diff_ranges], "",
             "Criteria (judge each; an empty list means extract them from the PRD into `extracted`):",
             *[f"  {c['id']}: {c['text']}" for c in criteria.get("items", [])], "",
             "Audit command results:", *[f"  {r['name']} ({r['kind']}): {r['result']}  log {r.get('log', '')}" for r in runs], "",
             f"Replay copy of the evidence plan: {replay_copy or 'none'}",
             f"Evidence JSON output path: {evidence_out}  ({{\"verdict\": \"PASS|FAIL|INCOMPLETE\", \"passed\": n, \"total\": n}})",
             f"Write the review JSON to: {out}", "List it in report.artifacts. Schema:", REVIEW_SCHEMA, ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def cross_check(state: dict[str, Any], settings: dict[str, Any], raw: dict[str, Any], replay_passed: bool) -> list[dict[str, Any]]:
    wt = state["worktree"]
    last = state["last"]

    def exists(path: str) -> bool:
        return git_ok(wt, "cat-file", "-e", f"HEAD:{path}")

    def line_exists(path: str, number: int) -> bool:
        return exists(path) and number <= len(git(wt, "show", f"HEAD:{path}", check=False).splitlines())

    def test_passed(path: str) -> bool:
        return any(fnmatch.fnmatch(path, g) and (last.get(c["name"]) or {}).get("result") == "passed"
                   for c in settings["tests"] for g in c["paths"])

    out = []
    for c in raw.get("criteria", []):
        state_, proof, ev = c.get("state"), c.get("proof"), str(c.get("evidence", ""))
        if state_ not in ("met", "unmet", "unproven"):
            state_ = "unproven"
        if state_ == "met":
            paths = re.findall(r"[\w./-]+\.\w+", ev)
            lines = [(p, int(n)) for p, n in re.findall(r"([\w./-]+):(\d+)", ev)]
            downgraded = False
            if proof == "ran" and not any(exists(p) and (test_passed(p) or replay_passed) for p in paths):
                proof, downgraded = "read", True
            if proof == "read" and not any(line_exists(p, n) for p, n in lines):
                proof, state_, downgraded = "none", "unproven", True
            if proof not in ("ran", "read"):
                proof, state_ = "none", "unproven"
            out.append({"id": c.get("id"), "state": state_, "proof": proof, "evidence": ev, "downgraded": downgraded})
        else:
            out.append({"id": c.get("id"), "state": state_, "proof": "none", "evidence": ev, "downgraded": False})
    return out


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def clean_findings(raw: dict[str, Any], default_task: str) -> list[dict[str, Any]]:
    out = []
    for f in raw.get("findings", []):
        klass = f.get("class") if f.get("class") in ("Blocker", "Concern", "Note") else "Note"
        dim = f.get("dimension") if f.get("dimension") in DIM_PART else "quality"
        out.append({"class": klass, "dimension": dim, "task": f.get("task") or default_task, "evidence": str(f.get("evidence", ""))})
    return out


def run_review_pipeline(state: dict[str, Any], run_id: str, context: Path) -> None:
    run_tool([sys.executable, str(BIN / "agentctl"), "factory", "start", run_id, "--pipeline", "release-review",
              "--context", str(context), "--foreground"], cwd=Path(state["worktree"]), timeout=3600)


def review_task(state: dict[str, Any], settings: dict[str, Any], key: str, replay_result: dict[str, Any] | None) -> dict[str, Any]:
    slug = state["release"]
    folder = release_dir(slug) / "review"
    out, evidence_out = folder / f"{key}.json", folder / f"{key}.evidence.json"
    prd, plan = requirements_for(key)
    criteria = criteria_for(slug, key, prd)
    record = next(m for m in state["merged"] if m["key"] == key)
    ranges = [f"git diff {sha}^1 {sha}" for sha in record["merge_commits"]] or ["(no merge commit: the branch was already merged)"]
    copy = replay_result.get("copy") if replay_result and replay_result.get("result") in ("passed", "failed") else None
    runs = [r for r in state["last"].values() if r["kind"] != "replay"]
    ctx = write_review_context(state, key, out, prd=prd, plan=plan, criteria=criteria, diff_ranges=ranges, runs=runs,
                               replay_copy=copy, evidence_out=evidence_out)
    for stale in (out, evidence_out):
        stale.unlink(missing_ok=True)
    run_review_pipeline(state, f"{state['version']}-review-{key}", ctx)
    raw = read_json(out)
    if raw is None:
        return {"reviewed": False, "reason": "the reviewer produced no valid JSON"}
    items = criteria["items"]
    if criteria["needs_extraction"] and prd and raw.get("extracted"):
        items = store_extracted(slug, key, prd, raw["extracted"])
    verdicts = cross_check(state, settings, raw, bool(replay_result and replay_result.get("result") == "passed"))
    known = {i["id"] for i in items}
    verdicts = [v for v in verdicts if v["id"] in known]
    seen = {v["id"] for v in verdicts}
    verdicts += [{"id": i["id"], "state": "unproven", "proof": "none", "evidence": "not judged", "downgraded": False}
                 for i in items if i["id"] not in seen]
    ev = read_json(evidence_out)
    evidence = None
    if copy and ev and str(ev.get("verdict", "")).upper() != "INCOMPLETE" and ev.get("total"):
        evidence = {"passed": int(ev.get("passed", 0)), "total": int(ev["total"]), "verdict": ev.get("verdict")}
    review = {"reviewed": True, "no_requirements": prd is None, "criteria": verdicts,
              "criteria_text": {i["id"]: i["text"] for i in items}, "findings": clean_findings(raw, key),
              "test_layer": bool(raw.get("test_layer")), "evidence": evidence, "prd": str(prd) if prd else None}
    review["score"] = score(review)
    return review


def review_seams(state: dict[str, Any], runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    folder = release_dir(state["release"]) / "review"
    out = folder / "release.json"
    ctx = folder / "release.context.md"
    folder.mkdir(parents=True, exist_ok=True)
    ctx.write_text("\n".join([
        "# Release review context: seams", "", "Report only. Edit nothing.",
        (f"Read the combined diff `git diff {state['base_sha']}..HEAD` in {state['worktree']} against the PRDs of the merged tasks "
         f"({', '.join(merged_keys(state))}) for seams between them. Each finding names the task it belongs to."),
        f"Write the review JSON (findings only) to: {out}. List it in report.artifacts. Schema:", REVIEW_SCHEMA,
        f"Evidence JSON path (write verdict INCOMPLETE, total 0): {folder / 'release.evidence.json'}", ""]), encoding="utf-8")
    out.unlink(missing_ok=True)
    run_review_pipeline(state, f"{state['version']}-review-release", ctx)
    raw = read_json(out)
    return clean_findings(raw, "release") if raw else []


# --------------------------------------------------------------------------- audit (FR-7)


def compute_verdict(state: dict[str, Any], settings: dict[str, Any]) -> tuple[str, list[str]]:
    last = state["last"]
    reasons: list[str] = []
    new = [n for n, r in last.items() if new_failure(state, r)]
    if open_bugs(state) or new:
        return "blocked", [f"open bug {b['id']}" for b in open_bugs(state)] + [f"new failure {n}" for n in new]
    e2e = [c for c in settings["tests"] if c["kind"] == "e2e"]
    if not e2e:
        return "not verified", ["no end-to-end command configured"]
    for c in e2e:
        run = last.get(c["name"]) or {}
        if run.get("result") != "passed":
            reasons.append(f"end-to-end command {c['name']} was {run.get('result', 'not run')}"
                           + (f" ({run['reason']})" if run.get("reason") else ""))
    return ("verified", []) if not reasons else ("not verified", reasons)


def task_rows(state: dict[str, Any], graph: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    members = {m["key"]: m for m in graph["members"]}
    for key in merged_keys(state):
        record = next(m for m in state["merged"] if m["key"] == key)
        files = [f for sha in record["merge_commits"] for f in changed_files(state["worktree"], sha)]
        replay_run = state["last"].get(f"replay:{key}")
        rows.append({"key": key, "summary": (members.get(key) or {}).get("summary", ""), "merge_commits": record["merge_commits"],
                     "warning": record.get("warning", ""), "replay": replay_run,
                     "no_task_check": not evidence_plan_exists(key) and not any(rl.is_check_file(f) for f in files)})
    return rows


def build_audit(state: dict[str, Any], settings: dict[str, Any], graph: dict[str, Any], verdict: str, reasons: list[str],
                review: dict[str, Any] | None) -> dict[str, Any]:
    env = resolve_env(settings, (state.get("deploy") or {}).get("env"))
    tasks = task_rows(state, graph)
    audit: dict[str, Any] = {
        "release": state["release"], "version": state["version"], "branch": state["branch"],
        "integration_commit": rev(state["worktree"]), "base_sha": state["base_sha"],
        "environment": {"name": env["name"], "base_url": env["base_url"], "source": env["source"]} if env else None,
        "deployed": state.get("deploy"), "tasks": tasks, "excluded": [e["key"] for e in state["excluded"]],
        "commands": [{k: r.get(k) for k in ("name", "kind", "result", "log", "reason")} | {"flaky": r["result"] == "flaky"}
                     for n, r in state["last"].items() if r["kind"] != "replay"],
        "pre_existing": [n for n in state["baseline"] if (state["last"].get(n) or {}).get("result") in RESULT_FAIL],
        "bugs": state["bugs"] + [b for e in state["excluded"] for b in e.get("bugs", [])],
        "verdict": verdict, "reasons": reasons, "proves": PROVES, "generated": now(), "review": None}
    if review is not None:
        by_key = {t["key"]: t for t in tasks}
        for key, r in review["tasks"].items():
            by_key[key]["review"] = r
        rows = [{"key": t["key"], "score": (t["review"] or {}).get("score", {}).get("score") if (t.get("review") or {}).get("reviewed") else None,
                 "criteria": (t.get("review") or {}).get("criteria", []), "blocker": (t.get("review") or {}).get("score", {}).get("blocker", False)}
                for t in tasks]
        audit["review"] = {"release_findings": review["release_findings"], "not_reviewed": review["not_reviewed"],
                           "release_score": release_score(rows), "note": "No end-to-end test proved this delivery; "
                           "model-judged lines are marked (model-judged)."}
    return audit


def render_audit(a: dict[str, Any]) -> str:
    lines = [f"# Release audit: {a['release']}", "", f"**Verdict: {a['verdict']}**", ""]
    env = a["environment"]
    env_line = f"{env['name']} {env['base_url']}" if env else "none"
    dep = a["deployed"] or {}
    dep_line = "yes" if dep.get("deployed") else "no: " + (dep.get("reason") or "not checked")
    for r in a["reasons"]:
        lines.append(f"- {r}")
    lines += ["", a["proves"], "",
              (f"Release `{a['version']}` on branch `{a['branch']}`, integration commit `{a['integration_commit'][:12]}` "
               f"(base `{a['base_sha'][:12]}`)."),
              (f"Environment: {env_line}. Deployed commit confirmed: {dep_line}."), ""]
    review = a.get("review")
    if review:
        rs = review["release_score"]
        lines += ["## Score", "", f"Release score: {rs['score'] if rs['score'] is not None else 'none'}"
                  + (f" (lowest task: {rs['lowest']})" if rs["lowest"] else "") + ("  (a Blocker caps it at 50)" if rs["blocker"] else ""),
                  "", review["note"], ""]
        ranked = sorted(a["tasks"], key=lambda t: ((t.get("review") or {}).get("score", {}).get("score", 101)
                                                    if (t.get("review") or {}).get("reviewed") else 101))
        for t in ranked:
            r = t.get("review") or {}
            if not r.get("reviewed"):
                lines.append(f"- {t['key']}: not scored, the review did not run ({r.get('reason', 'unknown')}) (model-judged)")
                continue
            s = r["score"]
            lines.append(f"- {t['key']}: **{s['score']}** over {s['assessed']} assessed points, {s['proved']} proved by running (model-judged)")
            for name, p in s["parts"].items():
                lines.append(f"  - {name}: {round(p['earned'], 2)} / {p['max']}" + (f" ({p['label']})" if p["label"] else "") + ("" if p["assessed"] else " n/a"))
            for c in r["criteria"]:
                lines.append(f"  - {c['id']} {c['state']} ({c['proof']}): {r['criteria_text'].get(c['id'], '')}")
            for f in r["findings"]:
                lines.append(f"  - {f['class']} {f['dimension']}: {f['evidence']}")
        for f in review["release_findings"]:
            lines.append(f"- release finding {f['class']} {f['dimension']} ({f['task']}): {f['evidence']} (model-judged)")
        lines.append("")
    lines += ["## Tasks", ""]
    for t in a["tasks"]:
        rp = t["replay"]
        lines.append(f"- {t['key']} {t['summary']}: replay {rp['result'] if rp else 'not run'}" + (f" ({rp['reason']})" if rp and rp.get("reason") else "")
                     + (f"; {t['warning']}" if t["warning"] else ""))
    if a["excluded"]:
        lines += ["", "Excluded: " + ", ".join(a["excluded"])]
    nocheck = [t["key"] for t in a["tasks"] if t["no_task_check"]]
    if nocheck:
        lines += ["", "No task-level check: " + ", ".join(nocheck)]
    lines += ["", "## Supporting results", ""]
    for c in a["commands"]:
        lines.append(f"- {c['name']} ({c['kind']}): {c['result']}" + (" (flaky)" if c["flaky"] else "") + (f"  log {c['log']}" if c["log"] else ""))
    if a["pre_existing"]:
        lines += ["", "Pre-existing failures: " + ", ".join(a["pre_existing"])]
    lines += ["", "## Release bugs", ""]
    for b in a["bugs"] or []:
        lines.append(f"- {b['id']} {b['status']} {b['check']} owner {b['owner_task'] or 'unassigned'} ({b['owner_state']}); "
                     f"task test {b['tests']['task'] or 'missing'}, end-to-end test {b['tests']['e2e'] or 'missing'}" + (f"; {b['reason']}" if b['reason'] else ""))
    if not a["bugs"]:
        lines.append("- none")
    lines += ["", "Nothing was posted."]
    return "\n".join(lines) + "\n"


def cmd_audit(args: Any) -> int:
    state = load_state(args.release)
    graph = load_graph(args.release)
    if state["state"] not in ("open", "ready"):
        raise ReleaseError(f"audit refused: the release is {state['state']}"
                           + ("; run `agentctl release check` first" if state["state"] == "blocked" else ""))
    settings = load_settings(Path(state["repo"]))
    require_tests(settings)
    summary = run_checks(state, settings, graph, scope="audit", env_name=args.env, deployed=args.deployed)
    print_run_result(summary, state)
    verdict, reasons = compute_verdict(state, settings)
    review = None
    if args.review and merged_keys(state):
        tasks, not_reviewed = {}, []
        for key in merged_keys(state):
            result = review_task(state, settings, key, state["last"].get(f"replay:{key}"))
            tasks[key] = result
            if not result["reviewed"]:
                not_reviewed.append(key)
        seams = review_seams(state, summary["runs"])
        review = {"tasks": tasks, "release_findings": seams, "not_reviewed": not_reviewed}
        blockers = any(f["class"] == "Blocker" for f in seams) or any(
            f["class"] == "Blocker" for r in tasks.values() if r.get("reviewed") for f in r["findings"])
        if verdict == "not verified" and not blockers and not not_reviewed:
            verdict = "reviewed"
            reasons = reasons + ["no end-to-end test proved the delivery; a model review found no Blocker"]
        elif verdict == "not verified" and blockers:
            reasons = reasons + ["the review found a Blocker"]
        if not_reviewed:
            reasons = reasons + [f"review did not run for {', '.join(not_reviewed)}"]
    audit = build_audit(state, settings, graph, verdict, reasons, review)
    folder = release_dir(args.release)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (folder / "audit.md").write_text(render_audit(audit), encoding="utf-8")
    state["audit"] = {"verdict": verdict, "date": now(), "commit": audit["integration_commit"]}
    if state["state"] != "blocked":
        state["state"] = "ready" if verdict == "verified" else "open"
    save_state(state)
    print(f"verdict: {verdict}\nreport: {folder / 'audit.md'}")
    return 1 if verdict == "blocked" else 0


# --------------------------------------------------------------------------- parsers


def add_integration_parsers(sub: Any) -> None:
    tests = sub.add_parser("tests", help="Run (or --list) the project's configured test commands. No release needed.")
    tests.add_argument("--repo", default=".", help="Project checkout (default: cwd).")
    tests.add_argument("--kind", choices=TEST_KINDS)
    tests.add_argument("--name")
    tests.add_argument("--env", help="Test environment name (default: the one marked default).")
    tests.add_argument("--list", action="store_true", help="Print the effective commands, environments and project id.")
    tests.set_defaults(func=cmd_tests)

    def release_arg(p: Any) -> None:
        p.add_argument("--release", required=True, help="Release slug (the graph file name without .graph.json).")

    op = sub.add_parser("open", help="Create release/<version> in its own worktree and record the baseline.")
    release_arg(op)
    op.set_defaults(func=cmd_open)
    merge = sub.add_parser("merge", help="Merge one task branch into the integration branch (--no-ff) and run the checks.")
    release_arg(merge)
    merge.add_argument("key")
    merge.add_argument("--env")
    merge.set_defaults(func=cmd_merge)
    check = sub.add_parser("check", help="Re-run the checks that failed last time (--all: everything).")
    release_arg(check)
    check.add_argument("--all", action="store_true")
    check.add_argument("--env")
    check.add_argument("--deployed", help="Commit SHA the test environment serves.")
    check.set_defaults(func=cmd_check)
    status = sub.add_parser("status", help="State, waves, open bugs, last results and distance from the base.")
    release_arg(status)
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    remove = sub.add_parser("remove", help="Revert every merge of a task and mark it excluded.")
    release_arg(remove)
    remove.add_argument("key")
    remove.add_argument("--env")
    remove.set_defaults(func=cmd_remove)
    audit = sub.add_parser("audit", help="Run everything, replay evidence, write audit.md and audit.json. Posts nothing.")
    release_arg(audit)
    audit.add_argument("--env")
    audit.add_argument("--deployed", help="Commit SHA the test environment serves.")
    audit.add_argument("--review", action="store_true", help="Also review each task against its PRD and score it (report only).")
    audit.set_defaults(func=cmd_audit)
    bugs = sub.add_parser("bugs", help="List release bugs, confirm an owner, or write a tracker draft.")
    release_arg(bugs)
    bugs.add_argument("--confirm", metavar="BUG")
    bugs.add_argument("--owner", metavar="KEY")
    bugs.add_argument("--draft", metavar="BUG")
    bugs.set_defaults(func=cmd_bugs)
