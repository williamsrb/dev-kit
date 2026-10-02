#!/usr/bin/env python3
"""Launch the Serena MCP server after choosing its language servers from the project's code.

Serena reads `language_servers` from `<project>/.serena/project.yml` and has no
flag or global setting for it. Left alone it enables the single most common
language and never Markdown. This wrapper asks `agentctl code languages` for the
top source languages, adds any that are missing to `project.yml` (creating the
project first when it does not exist), then execs `serena start-mcp-server` with
the arguments it was given.

First-run onboarding: Serena's `onboarding` is an agent task (explore the project,
write memories), so the wrapper cannot do it itself and an in-session agent would
use whatever model the session runs. When a project has no memories and no
earlier attempt, the wrapper starts one detached `claude -p` run pinned to a
cheaper model with a spend cap, restricted to Serena plus read-only built-ins.
The attempt is recorded in ~/.serena/onboarding/<id>.json (status, log path), so
a failure is not retried on every start; delete that file to retry. Languages
already listed are never removed.

Orphans: a client that dies without closing stdio can leave Serena or its language
servers running. Before each server start the wrapper runs `agentctl code orphans
--kill --fix-state`, and it execs Serena with SERENA_MCP_SERVER=1 so every process
Serena starts carries an ownership marker the detector can trust.

Set SERENA_MCP_AUTO_LANGUAGES=0 to skip detection, SERENA_MCP_AUTO_ONBOARD=0 to skip
onboarding and SERENA_MCP_REAP_ORPHANS=0 to skip orphan cleanup. SERENA_MCP_ONBOARD_MODEL
and SERENA_MCP_ONBOARD_BUDGET_USD override the model and cap. Any failure falls through
to a plain Serena start.

Python 3.12, standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SERENA = Path.home() / ".local" / "bin" / "serena"
AGENTCTL = Path(__file__).resolve().parent / "agentctl"
ONBOARD_MODE = Path(__file__).resolve().parent.parent / "mcp" / "serena" / "auto-onboard.yml"
ONBOARD_DIR = Path.home() / ".serena" / "onboarding"
ONBOARD_MODEL = "claude-sonnet-5-5"
ONBOARD_BUDGET_USD = "1.00"
ONBOARD_TIMEOUT = 1800
ONBOARD_PROMPT = (
    "Call the Serena `onboarding` tool and follow its instructions to write all the project "
    "memories with `write_memory`. Nobody is available to answer questions: if information is "
    "missing, leave it out. Do not modify any project file; write memories only. When done, "
    "reply with the names of the memories you wrote."
)
LS_ID_RE = re.compile(r"^[a-z0-9_]+$")
BLOCK_RE = re.compile(r"^language_servers:[^\n]*(?:\n|$)(?:[ \t]*-[^\n]*(?:\n|$))*", re.MULTILINE)


def project_root(cwd: Path) -> tuple[Path, bool]:
    """Return (root, has_project_yml). Mirrors --project-from-cwd: nearest .serena, else git root."""
    for folder in (cwd, *cwd.parents):
        if (folder / ".serena" / "project.yml").is_file():
            return folder, True
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=cwd, text=True, capture_output=True, check=False
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()), False
    return cwd, False


def detect(root: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, str(AGENTCTL), "code", "languages", "--cwd", str(root), "--serena"],
        text=True, capture_output=True, check=False, timeout=30,
    )
    if result.returncode != 0:
        return []
    return [token for token in result.stdout.split() if LS_ID_RE.match(token)]


def listed(text: str) -> list[str]:
    match = BLOCK_RE.search(text)
    if not match:
        return []
    block = match.group(0)
    inline = block.split(":", 1)[1].split("\n", 1)[0].split("#", 1)[0].strip()
    if inline.startswith("["):
        return [item.strip().strip("'\"") for item in inline.strip("[]").split(",") if item.strip()]
    return [
        line.split("#", 1)[0].strip().lstrip("-").strip().strip("'\"")
        for line in block.splitlines()[1:]
        if line.split("#", 1)[0].strip()
    ]


def markdown_last(names: list[str]) -> list[str]:
    if "markdown" not in names:
        return names
    return [name for name in names if name != "markdown"] + ["markdown"]


def update_project(project_yml: Path, detected: list[str]) -> None:
    text = project_yml.read_text(encoding="utf-8")
    current = listed(text)
    merged = markdown_last(current + [name for name in detected if name not in current])
    if merged == current or not BLOCK_RE.search(text):
        return
    block = "language_servers:\n" + "".join(f"- {name}\n" for name in merged)
    updated = BLOCK_RE.sub(lambda _: block, text, count=1)
    with tempfile.NamedTemporaryFile("w", dir=project_yml.parent, delete=False, encoding="utf-8") as tmp:
        tmp.write(updated)
    shutil.copymode(project_yml, tmp.name)
    os.replace(tmp.name, project_yml)
    print(f"serena-mcp: language_servers -> {', '.join(merged)}", file=sys.stderr)


def choose_languages(cwd: Path) -> None:
    root, exists = project_root(cwd)
    detected = detect(root)
    if not detected:
        return
    if exists:
        update_project(root / ".serena" / "project.yml", detected)
    elif (root / ".git").exists():
        command = [str(SERENA), "project", "create", str(root)]
        for name in markdown_last(detected):
            command += ["--language", name]
        subprocess.run(command, capture_output=True, check=False, timeout=120)


def reap_orphans() -> None:
    result = subprocess.run(
        [sys.executable, str(AGENTCTL), "code", "orphans", "--kill", "--fix-state"],
        text=True, capture_output=True, check=False, timeout=15,
    )
    if result.returncode != 0:
        return
    report = json.loads(result.stdout)
    if report.get("killed") or report.get("fixed"):
        print(
            f"serena-mcp: stopped {len(report['killed'])} orphaned Serena processes, "
            f"closed {len(report['fixed'])} stale onboarding states",
            file=sys.stderr,
        )


def onboarding_enabled() -> bool:
    return os.environ.get("SERENA_MCP_AUTO_ONBOARD") != "0"


def launch_args(args: list[str]) -> list[str]:
    if not onboarding_enabled() or not ONBOARD_MODE.is_file():
        return args
    if any(arg == "--add-mode" or arg.startswith("--add-mode=") for arg in args):
        return args
    return [*args, "--add-mode", str(ONBOARD_MODE)]


def has_memories(root: Path) -> bool:
    return any((root / ".serena" / "memories").rglob("*.md"))


def onboarding_state(root: Path) -> Path:
    return ONBOARD_DIR / f"{hashlib.sha1(str(root).encode()).hexdigest()[:12]}.json"


def write_state(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def maybe_start_onboarding(root: Path) -> None:
    claude = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")
    state = onboarding_state(root)
    if has_memories(root) or not Path(claude).exists():
        return
    log = state.with_suffix(".log")
    state.parent.mkdir(parents=True, exist_ok=True)
    try:
        with state.open("x", encoding="utf-8") as claim:
            json.dump({"root": str(root), "status": "starting", "started": int(time.time()), "log": str(log)}, claim)
    except FileExistsError:
        return
    with log.open("w", encoding="utf-8") as out:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--run-onboarding", str(root), claude],
            stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True,
        )
    print(f"serena-mcp: onboarding {root} in the background ({log})", file=sys.stderr)


def run_onboarding(root: Path, claude: str) -> int:
    """Detached worker: one capped claude -p run, then record the outcome."""
    state = onboarding_state(root)
    ONBOARD_DIR.mkdir(parents=True, exist_ok=True)
    mcp_config = state.with_suffix(".mcp.json")
    mcp_config.write_text(json.dumps({"mcpServers": {"serena": {
        "command": str(Path(__file__).resolve()),
        "args": ["start-mcp-server", "--project-from-cwd", "--context=claude-code"],
    }}}), encoding="utf-8")
    model = os.environ.get("SERENA_MCP_ONBOARD_MODEL", ONBOARD_MODEL)
    budget = os.environ.get("SERENA_MCP_ONBOARD_BUDGET_USD", ONBOARD_BUDGET_USD)
    command = [
        claude, "-p", ONBOARD_PROMPT, "--model", model, "--max-budget-usd", budget,
        "--strict-mcp-config", "--mcp-config", str(mcp_config),
        "--tools", "Read,Glob,Grep", "--allowedTools", "mcp__serena", "Read", "Glob", "Grep",
        "--permission-mode", "dontAsk", "--no-session-persistence",
    ]
    data = {"root": str(root), "model": model, "budget_usd": budget, "log": str(state.with_suffix(".log"))}
    write_state(state, {**data, "status": "running", "pid": os.getpid(), "started": int(time.time())})
    env = {**os.environ, "SERENA_MCP_AUTO_ONBOARD": "0"}
    try:
        result = subprocess.run(command, cwd=root, env=env, text=True, timeout=ONBOARD_TIMEOUT, check=False)
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = 124
    status = "done" if code == 0 and has_memories(root) else "failed"
    write_state(state, {**data, "status": status, "exit": code, "finished": int(time.time())})
    return 0 if status == "done" else 1


def main() -> None:
    args = sys.argv[1:]
    if args[:1] == ["--run-onboarding"]:
        raise SystemExit(run_onboarding(Path(args[1]), args[2]))
    if "--project-from-cwd" in args and os.environ.get("SERENA_MCP_AUTO_LANGUAGES") != "0":
        try:
            choose_languages(Path.cwd())
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"serena-mcp: language detection skipped ({exc})", file=sys.stderr)
    if args[:1] == ["start-mcp-server"]:
        if os.environ.get("SERENA_MCP_REAP_ORPHANS") != "0":
            try:
                reap_orphans()
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                print(f"serena-mcp: orphan cleanup skipped ({exc})", file=sys.stderr)
        if "--project-from-cwd" in args and onboarding_enabled():
            try:
                root, exists = project_root(Path.cwd())
                if exists:
                    maybe_start_onboarding(root)
            except (OSError, subprocess.SubprocessError) as exc:
                print(f"serena-mcp: onboarding skipped ({exc})", file=sys.stderr)
        args = launch_args(args)
    os.execve(str(SERENA), [str(SERENA), *args], {**os.environ, "SERENA_MCP_SERVER": "1"})


if __name__ == "__main__":
    main()
