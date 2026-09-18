#!/usr/bin/env bash
# Git policy for Claude Code and Codex (user-level PreToolUse hook on Bash).
# Filename is claude-deny-git-push.sh on purpose: this does not block git reads.
# Mirrors deny-git-push.sh's policy for Cursor via the shared git-push-policy.sh, but
# speaks Claude Code's hookSpecificOutput/permissionDecision schema instead of
# Cursor's permission/user_message schema.
#
#   git push                              -> deny
#   git commit / reset / rebase / clean   -> ask
#   anything else                         -> no decision; normal permission rules apply
#
# The fallthrough must stay silent. Emitting "allow" here would auto-approve
# every Bash command in the session, which is how unordered commits got through.
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/git-push-policy.sh"

input=$(cat)
command=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" <<<"$input")

if is_git_push_command "$command"; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"git push is disabled for the agent. Push to remote yourself if needed."}}
EOF
  exit 0
fi

if is_git_write_command "$command"; then
  cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"This git command is commit, reset, rebase, or clean. Confirm it was explicitly ordered."}}
EOF
  exit 0
fi

exit 0
