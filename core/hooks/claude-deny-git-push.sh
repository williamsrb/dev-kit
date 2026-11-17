#!/usr/bin/env bash
# Kept so existing profile and Codex wiring keeps working; policy lives in claude-git-guard.py.
exec python3 "$(dirname "${BASH_SOURCE[0]}")/claude-git-guard.py"
