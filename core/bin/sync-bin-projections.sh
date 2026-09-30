#!/usr/bin/env bash
#
# Project harness scripts from ~/.agents into the places they are used today.
#
# Vendor-specific (like skills-vendor):
#   ~/.claude/scripts            <- bin-vendor/claude
#   ~/.codex/scripts             <- bin-vendor/codex
#   ~/.cursor/scripts            <- bin-vendor/cursor
#
# Shared harness tools live in ~/.agents/bin. Names listed in PATH_SHIMS are
# also linked from ~/.local/bin so they stay on PATH. Cron jobs keep calling
# ~/.agents/bin directly and do not need a shim.
#
# Idempotent.
#
#   sync-bin-projections.sh            # report drift, change nothing
#   sync-bin-projections.sh --apply    # create, repair, prune
#
# Invariants:
#   * every projected entry is a symlink to a real file under bin or bin-vendor
#   * a real file that is byte-identical to the canonical is replaced by a link
#   * a real file that differs is never deleted — reported only
#   * ~/.local/bin entries that are not PATH_SHIMS are never touched
#   * hooks and skills trees are never touched

set -euo pipefail

# No fallback: a default here would bake one machine's home into every
# other machine (plan devkit, F4).
: "${HOME:?HOME is not set; export it and re-run}"
HOME_DIR="$HOME"
AGENTS="$HOME_DIR/.agents"
VENDOR="$AGENTS/bin-vendor"
BIN="$AGENTS/bin"
LOCAL_BIN="$HOME_DIR/.local/bin"

# root:vendor
TARGETS=(
  "$HOME_DIR/.claude/scripts:claude"
  "$HOME_DIR/.codex/scripts:codex"
  "$HOME_DIR/.cursor/scripts:cursor"
)

# Basenames in ~/.agents/bin that are used on PATH today.
PATH_SHIMS=(
  agentctl
  export-canvas-html
  recolor-white-black-icons.sh
  review-auth
)

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

created=0; repaired=0; pruned=0; problems=0

say()  { printf '   %s\n' "$*"; }
add()  { printf '   \033[32m+\033[0m %s\n' "$*"; }
fix()  { printf '   \033[36m~\033[0m %s\n' "$*"; }
cut_() { printf '   \033[35m-\033[0m %s\n' "$*"; }
bad()  { printf '   \033[31m!\033[0m %s\n' "$*"; problems=$((problems+1)); }

[[ -d "$VENDOR" ]] || { echo "no bin-vendor at $VENDOR" >&2; exit 1; }
[[ -d "$BIN" ]] || { echo "no bin at $BIN" >&2; exit 1; }

link_to() {  # $1 = desired target, $2 = link path
  local want="$1" link="$2" have=""
  if [[ -L "$link" ]]; then
    have="$(readlink "$link")"
    if [[ "$have" == "$want" ]]; then
      return 0
    fi
    fix "$link  ->  $want   (was: $have)"
    (( APPLY )) && ln -sfn "$want" "$link"
    repaired=$((repaired+1))
  elif [[ -e "$link" ]]; then
    if [[ -f "$link" ]] && cmp -s "$link" "$want"; then
      fix "$link  ->  $want   (identical real file)"
      (( APPLY )) && ln -sfn "$want" "$link"
      repaired=$((repaired+1))
    else
      bad "$link is a real file/dir, not a link — left untouched, resolve by hand"
    fi
  else
    add "$link  ->  $want"
    (( APPLY )) && ln -s "$want" "$link"
    created=$((created+1))
  fi
}

for spec in "${TARGETS[@]}"; do
  root="${spec%%:*}"; vendor="${spec##*:}"
  parent="$(dirname "$root")"
  [[ -d "$parent" ]] || { say "skip $root (no $parent)"; continue; }

  printf '\n\033[1m-- %s\033[0m  (vendor:%s)\n' "$root" "$vendor"

  [[ -d "$root" ]] || { (( APPLY )) && mkdir -p "$root"; add "mkdir $root"; }
  [[ -d "$root" ]] || continue

  declare -A want=()
  vdir="$VENDOR/$vendor"
  if [[ -d "$vdir" ]]; then
    while IFS= read -r -d '' e; do
      name="$(basename "$e")"
      [[ -f "$e" ]] || { bad "$e is not a regular file — skipped"; continue; }
      want["$name"]="$e"
    done < <(find "$vdir" -mindepth 1 -maxdepth 1 -type f -print0)
  else
    say "no vendor dir $vdir"
  fi

  for name in "${!want[@]}"; do
    link_to "${want[$name]}" "$root/$name"
  done

  while IFS= read -r -d '' l; do
    name="$(basename "$l")"
    [[ -n "${want[$name]:-}" ]] && continue
    cut_ "$root/$name (no longer in bin-vendor/$vendor)"
    (( APPLY )) && rm "$l"
    pruned=$((pruned+1))
  done < <(find "$root" -mindepth 1 -maxdepth 1 -type l -print0)

  unset want
done

printf '\n\033[1m-- %s\033[0m  (PATH shims)\n' "$LOCAL_BIN"
if [[ -d "$LOCAL_BIN" ]]; then
  declare -A path_want=()
  for name in "${PATH_SHIMS[@]}"; do
    src="$BIN/$name"
    if [[ ! -f "$src" ]]; then
      bad "$src missing — PATH shim skipped"
      continue
    fi
    path_want["$name"]="$src"
    link_to "$src" "$LOCAL_BIN/$name"
  done

  while IFS= read -r -d '' l; do
    name="$(basename "$l")"
    [[ -n "${path_want[$name]:-}" ]] && continue
    have="$(readlink "$l")"
    case "$have" in
      "$BIN"/*) ;;
      *) continue ;;
    esac
    cut_ "$LOCAL_BIN/$name (points at bin/ but is not a PATH_SHIM)"
    (( APPLY )) && rm "$l"
    pruned=$((pruned+1))
  done < <(find "$LOCAL_BIN" -mindepth 1 -maxdepth 1 -type l -print0)

  unset path_want
else
  say "skip $LOCAL_BIN (absent)"
fi

printf '\n   created %d · repaired %d · pruned %d · problems %d\n' \
       "$created" "$repaired" "$pruned" "$problems"
(( APPLY )) || printf '   (dry run — re-run with --apply)\n'
(( problems == 0 ))
