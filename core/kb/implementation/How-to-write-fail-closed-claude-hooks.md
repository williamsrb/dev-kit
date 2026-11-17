# How to write fail-closed Claude Code hooks

## Scope

PreToolUse guard hooks in `~/.agents/hooks/` (`claude-git-guard.py`, `jira-write-guard.py`). Logging hooks (`history.py`, adapters) follow the opposite rule.

## Procedure

1. Read the stdin JSON; on any parse error print the reason to stderr and `exit 2`. Exit 2 blocks the call, any other non-zero exit is non-blocking in Claude Code.
2. Deny with exit 0 and `hookSpecificOutput.permissionDecision` JSON (`deny`, `ask`). Keep that shape: Codex runs `claude-deny-git-push.sh` through `~/.codex/hooks.json`.
3. Stay silent for everything else. Never print `allow`: it auto-approves the whole Bash tool.
4. For Bash commands, tokenize with `shlex(punctuation_chars=True)`, split on `&& || ; | ( )`, and recurse into `$(...)`, backticks and `sh -c` bodies.
5. Strip heredoc bodies before `shlex`: they are data with stray quotes, and unstripped they make the guard block legitimate commands. Keep the body only when the heredoc feeds a shell (`bash <<EOF`).
6. Test each hook as a subprocess with allowed, denied and malformed input (`tests/test_claude_git_guard.py`).

## Pitfalls

- A hook `ask` under bypass permissions mode is not documented. Do not rely on it for a hard stop; use `deny`.
- A `Bash` command that merely contains the text of a denied command inside a heredoc used to trip the old shell hook; write such files with the Write tool.
- `kb/_shared/scripts/llm_index.py` rewrites every KB index when run, even with `--help`.
