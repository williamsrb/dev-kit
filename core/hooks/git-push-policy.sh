#!/usr/bin/env bash
# Shared git command policy used by Cursor deny-git-push.sh, Claude
# claude-deny-git-push.sh, and Codex, so the three agents can't drift.
#
# Usage: source this file, then call
#   is_git_push_command "$command"   -> 0 when the command pushes to a remote (deny)
#   is_git_write_command "$command"  -> 0 when the command is commit/reset/rebase/clean (ask)
#
# Both scan every segment of a compound command and tolerate RTK-rewritten and
# env-prefixed forms, e.g.:
#   rtk git push
#   RTK_DISABLED=1 git push
#   cd repo && git commit -m wip
#   git -C /some/repo commit --amend

# Force-prompt list is narrow: checkout/switch/branch/add/fetch/pull/merge/stash
# stay unprompted. Model-facing .mdc rules still forbid unordered commits.
# Prompt: commit (includes --amend), reset, rebase, clean.
# Deny: push (handled separately).
GIT_WRITE_SUBCOMMANDS=" commit reset rebase clean "

_git_segments() {
  local command="$1"
  command="${command//&&/$'\n'}"
  command="${command//||/$'\n'}"
  command="${command//;/$'\n'}"
  command="${command//|/$'\n'}"
  printf '%s\n' "$command"
}

# Strip leading whitespace, ENV=value assignments, and transparent wrappers.
_git_normalize_segment() {
  local command="$1"
  command="${command#"${command%%[![:space:]]*}"}"

  while [[ "$command" =~ ^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+(.*)$ ]]; do
    command="${BASH_REMATCH[1]}"
    command="${command#"${command%%[![:space:]]*}"}"
  done

  while [[ "$command" =~ ^(rtk|env|command|sudo|nohup|time)[[:space:]]+(.*)$ ]]; do
    command="${BASH_REMATCH[2]}"
    command="${command#"${command%%[![:space:]]*}"}"
  done

  printf '%s' "$command"
}

# Echo the git subcommand of one segment, skipping git's global options.
# Returns 1 when the segment does not invoke git.
_git_subcommand() {
  local segment
  segment=$(_git_normalize_segment "$1")
  [[ "$segment" =~ ^git([[:space:]]|$) ]] || return 1

  local -a tokens
  read -r -a tokens <<<"${segment#git}"

  local i=0
  while ((i < ${#tokens[@]})); do
    case "${tokens[i]}" in
      # Global options that consume the next token as their value.
      -C|-c|--git-dir|--work-tree|--namespace|--exec-path) i=$((i + 2)) ;;
      -*) i=$((i + 1)) ;;
      *) printf '%s' "${tokens[i]}"; return 0 ;;
    esac
  done
  return 1
}

# Read-only forms of the dual-mode subcommands above: `git branch -d x` writes,
# but `git branch --show-current` only reads. Prompting on the read form trains
# click-through on the gate that is supposed to catch real writes, so read forms
# pass. Conservative allowlist - a write flag anywhere, or any form not listed,
# still asks.
_GIT_READONLY_FORMS='^(branch|tag|remote|reflog|notes|submodule)$|^branch (--show-current|--list|-l|-a|--all|-r|--remotes|-v|-vv|--verbose|--merged|--no-merged|--contains|--points-at|--format|--sort)|^tag (-l|--list|-n|--contains|--points-at|--sort|--format)|^remote (show|get-url|-v|--verbose)|^config (--get|--get-all|--get-regexp|--list|-l)|^stash (list|show)|^worktree list|^submodule (status|summary)|^reflog show|^notes (list|show)'

_git_segment_is_readonly() {
  local segment args
  segment=$(_git_normalize_segment "$1")
  [[ "$segment" =~ ^git([[:space:]]|$) ]] || return 1

  args=$(printf '%s' "${segment#git}" | tr -s '[:space:]' ' ')
  args="${args# }"
  args="${args% }"

  case " $args " in
    *" -d "*|*" -D "*|*" -m "*|*" -M "*|*" -c "*|*" -C "*|*" -f "*|*" -u "*|\
    *" --delete "*|*" --move "*|*" --copy "*|*" --force "*|*" --set-upstream-to "*|\
    *" --unset "*|*" --unset-all "*|*" --add "*|*" --replace-all "*) return 1 ;;
  esac

  [[ "$args" =~ $_GIT_READONLY_FORMS ]]
}

# $3 = "yes" lets recognized read-only forms pass. The push gate never exempts.
_git_has_subcommand() {
  local wanted_list=" $1 " command="$2" skip_readonly="${3:-no}" segment subcommand
  while IFS= read -r segment; do
    subcommand=$(_git_subcommand "$segment") || continue
    [[ "$wanted_list" == *" $subcommand "* ]] || continue
    if [[ "$skip_readonly" == "yes" ]] && _git_segment_is_readonly "$segment"; then
      continue
    fi
    return 0
  done < <(_git_segments "$command")
  return 1
}

is_git_push_command() {
  _git_has_subcommand "push" "$1"
}

is_git_write_command() {
  _git_has_subcommand "$GIT_WRITE_SUBCOMMANDS" "$1" yes
}
