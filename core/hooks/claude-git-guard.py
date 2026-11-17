#!/usr/bin/env python3
"""Git policy for Claude Code and Codex (user-level PreToolUse hook on Bash).

  git push (any form)                        -> deny
  merge --ff / --ff-only, pull --ff-only     -> deny
  git commit whose text has Co-authored-by   -> deny
  git commit / reset / rebase / clean        -> ask
  anything else                              -> no decision; normal permission rules apply

Factory workers (the env var named by .agentctl [factory] env is set) follow [git.factory] instead:
commit and push are allowed when the file says so, but never a fast-forward, a force push, a push of
every branch, or a push of a [git] protected branch; commit and push are denied when the file switches
them off or when [git.factory] worker_git_writes is false (the engine owns git writes); every other
`ask` becomes `deny` because nobody can answer a prompt. A missing or unreadable .agentctl leaves a
factory worker with commit and push denied.

The fallthrough stays silent: emitting "allow" would auto-approve every Bash command.
Fails closed: a payload or command that cannot be parsed exits 2, which blocks the call.
Cursor keeps its own hooks/deny-git-push.sh over git-push-policy.sh.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

WRAPPERS = {"rtk", "env", "command", "sudo", "nohup", "time", "exec"}
OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
ASK_SUBCOMMANDS = {"commit", "reset", "rebase", "clean"}
SHELLS = {"sh", "bash", "zsh", "dash"}
# Commands that run another command given in their arguments (find -exec, xargs, timeout 10 ...).
LAUNCHERS = {"xargs", "find", "timeout", "nice", "ionice", "watch", "parallel", "flock", "setsid", "stdbuf"}
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
COAUTHOR = re.compile(r"(?i)co-authored-by:")
HEREDOC = re.compile(
    r"<<-?[ \t]*(?P<q>['\"]?)(?P<tag>\w+)(?P=q)(?P<rest>[^\n]*)\n(?P<body>.*?)\n[ \t]*(?P=tag)[ \t]*(?=\n|$)",
    re.DOTALL,
)
SHELL_STDIN = re.compile(r"(?:^|[\s;&|(])(?:ba|z|da)?sh(?:\s[^<]*)?$")
SHELL_COMMAND_FLAG = re.compile(r"^-[a-z]*c[a-z]*$")
SUBSTITUTION = re.compile(r"\$\(((?:[^()]|\([^()]*\))*)\)|`([^`]*)`")

FORCE_FLAGS = {"-f", "--force", "--force-with-lease", "--mirror", "--delete", "-d"}
ALL_BRANCH_FLAGS = {"--all", "--branches"}
FALLBACK_FACTORY_ENV = "AGENTCTL_FACTORY"  # only used when .agentctl cannot be read
MESSAGES = {
    "force": "Force pushes are not allowed, not even for the factory.",
    "protected": "That branch is in .agentctl [git] protected_branches; the factory never pushes it.",
    "all-branches": "Pushing every branch would include a protected one: push the task branch by name.",
    "engine-owned": ".agentctl [git.factory] worker_git_writes is false: the factory engine commits and pushes, "
                    "workers do not.",
    "commit-off": ".agentctl [git.factory] commit is false: the factory may not commit.",
    "push-off": ".agentctl [git.factory] push is false: the factory may not push.",
    "headless": "This git command needs an operator's go-ahead and no one can answer a prompt in a headless run.",
    "push": "git push is disabled for the agent. Push to remote yourself if needed.",
    "fast-forward": "Merges never fast-forward: use git merge --no-ff, and do not use pull --ff-only.",
    "coauthor": "Commit messages carry no Co-authored-by or tool attribution trailer.",
    "reset": "git reset runs only on an explicit reset order. Confirm it was ordered.",
    "write": "This git command is commit, rebase, or clean. Confirm it was explicitly ordered.",
}


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies: they are data (often code with stray quotes), not commands."""
    return HEREDOC.sub(lambda m: f"<<{m.group('tag')}{m.group('rest')}", command)


def segments(command: str, depth: int = 0) -> list[list[str]]:
    """Token lists of every simple command, including nested ($(...), sh -c, eval) and launched (xargs) ones."""
    if depth > 4:
        raise ValueError("nesting too deep")
    result: list[list[str]] = []
    for match in HEREDOC.finditer(command):
        preface = command[:match.start()].rsplit("\n", 1)[-1]
        if SHELL_STDIN.search(preface):
            result += segments(match.group("body"), depth + 1)
    command = strip_heredocs(command)
    for match in SUBSTITUTION.finditer(command):
        result += segments(match.group(1) or match.group(2) or "", depth + 1)
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    current: list[str] = []
    for token in lexer:
        if set(token) <= set("&|;()"):
            if current:
                result.append(current)
            current = []
        else:
            current.append(token)
    if current:
        result.append(current)
    for tokens in list(result):
        core = strip_prefix(tokens)
        flags = [i for i, t in enumerate(core) if SHELL_COMMAND_FLAG.match(t)]
        if core and core[0].rsplit("/", 1)[-1] in SHELLS and flags:
            index = flags[0]
            if index + 1 < len(core):
                result += segments(core[index + 1], depth + 1)
        elif core and core[0] == "eval":
            result += segments(" ".join(core[1:]), depth + 1)
        elif core and core[0].rsplit("/", 1)[-1] in LAUNCHERS:
            starts = [i for i, t in enumerate(core) if t.rsplit("/", 1)[-1] == "git"]
            if starts:
                result.append(core[starts[0]:])
    return result


def strip_prefix(tokens: list[str]) -> list[str]:
    tokens = list(tokens)
    while tokens and (ENV_ASSIGNMENT.match(tokens[0]) or tokens[0] in WRAPPERS):
        tokens.pop(0)
    return tokens


def git_call(tokens: list[str]) -> tuple[str, list[str]] | None:
    core = strip_prefix(tokens)
    if not core or core[0].rsplit("/", 1)[-1] != "git":
        return None
    rest = core[1:]
    index = 0
    while index < len(rest):
        token = rest[index]
        if token in OPTIONS_WITH_VALUE:
            index += 2
        elif token.startswith("-"):
            index += 1
        else:
            return token, rest[index + 1:]
    return None


def load_policy() -> dict | None:
    """The factory git policy when this process is a factory worker, else None."""
    cfg = None
    for root in (Path(__file__).resolve().parent.parent, Path.home() / ".agents"):
        if (root / "bin" / "agentctl_config.py").is_file():
            sys.path.insert(0, str(root / "bin"))
            try:
                import agentctl_config

                cfg = agentctl_config.load()
            except Exception:  # noqa: BLE001 - an unreadable config must not widen what a worker may do
                cfg = None
            break
    env_name = ((cfg or {}).get("factory") or {}).get("env", FALLBACK_FACTORY_ENV)
    if not os.environ.get(env_name):
        return None
    git = (cfg or {}).get("git") or {}
    factory = git.get("factory") or {}
    return {"commit": bool(factory.get("commit")), "push": bool(factory.get("push")),
            "worker_writes": bool(factory.get("worker_git_writes")),
            "force_push": bool(factory.get("force_push")), "protected": list(git.get("protected_branches", [])),
            "ask_to_deny": bool(((cfg or {}).get("hooks") or {}).get("ask_becomes_deny_in_factory", True))}


def current_branch(cwd: str | None) -> str:
    try:
        proc = subprocess.run(["git", "branch", "--show-current"], cwd=cwd or None, text=True,
                              capture_output=True, timeout=10, check=False)
        return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def push_verdict(args: list[str], policy: dict, cwd: str | None) -> tuple[str, str] | None:
    if not policy["push"]:
        return "deny", "push-off"
    if not policy["worker_writes"]:
        return "deny", "engine-owned"
    positional = [a for a in args if not a.startswith("-")]
    if not policy["force_push"] and (any(a in FORCE_FLAGS or a.startswith("--force-with-lease=") for a in args)
                                     or any(a.startswith("+") for a in positional)):
        return "deny", "force"
    if any(a in ALL_BRANCH_FLAGS for a in args):
        return "deny", "all-branches"
    targets = []
    for ref in positional[1:]:
        dest = ref.rsplit(":", 1)[-1].removeprefix("+").removeprefix("refs/heads/")
        targets.append(current_branch(cwd) if dest == "HEAD" else dest)
    if not targets:
        targets = [current_branch(cwd)]
    if any(t in policy["protected"] for t in targets):
        return "deny", "protected"
    return None


def decide(command: str, policy: dict | None = None, cwd: str | None = None) -> tuple[str, str] | None:
    verdicts: list[tuple[str, str]] = []
    for tokens in segments(command):
        call = git_call(tokens)
        if not call:
            continue
        sub, args = call
        if sub == "push":
            if policy is None:
                verdicts.append(("deny", "push"))
            else:
                pushed = push_verdict(args, policy, cwd)
                if pushed:
                    verdicts.append(pushed)
        elif (sub == "merge" and any(a in ("--ff", "--ff-only") for a in args)) or (
            sub == "pull" and "--ff-only" in args
        ):
            verdicts.append(("deny", "fast-forward"))
        elif sub == "commit":
            if COAUTHOR.search(command):
                verdicts.append(("deny", "coauthor"))
            if policy is None:
                verdicts.append(("ask", "write"))
            elif not policy["commit"]:
                verdicts.append(("deny", "commit-off"))
            elif not policy["worker_writes"]:
                verdicts.append(("deny", "engine-owned"))
        elif sub == "reset":
            verdicts.append(("ask", "reset"))
        elif sub in ASK_SUBCOMMANDS:
            verdicts.append(("ask", "write"))
    for kind in ("deny", "ask"):
        for verdict, key in verdicts:
            if verdict == kind:
                return verdict, key
    return None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        command = payload["tool_input"].get("command", "")
        policy = load_policy()
        verdict = decide(command, policy, payload.get("cwd"))
    except (ValueError, KeyError, AttributeError, TypeError) as exc:
        print(f"claude-git-guard: cannot parse hook input ({exc}); blocking", file=sys.stderr)
        return 2
    if verdict:
        decision, key = verdict
        if decision == "ask" and policy is not None and policy["ask_to_deny"]:
            decision, key = "deny", "headless"
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": MESSAGES[key],
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
