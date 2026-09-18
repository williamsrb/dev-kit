#!/usr/bin/env bash
# Git policy for the Cursor agent (user-level hook).
# Filename is deny-git-push.sh on purpose: this does not block git reads.
#   git push                              -> deny
#   git commit / reset / rebase / clean   -> ask
#   anything else (status, log, diff, …)  -> allow
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/git-push-policy.sh"

input=$(cat)
command=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('command',''))" <<<"$input")

if is_git_push_command "$command"; then
  cat <<'EOF'
{"permission":"deny","user_message":"git push is disabled for the agent. Push to remote yourself if needed.","agent_message":"git push is blocked by user hook policy. Do not retry git push."}
EOF
  exit 0
fi

if is_git_write_command "$command"; then
  cat <<'EOF'
{"permission":"ask","user_message":"This git command is commit, reset, rebase, or clean.","agent_message":"git commit/reset/rebase/clean require an explicit operator order. Do not retry without approval."}
EOF
  exit 0
fi

echo '{"permission":"allow"}'
