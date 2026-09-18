#!/usr/bin/env bash
#
# Project ~/.agents/skills (shared) + ~/.agents/skills-vendor/<vendor> (builds
# that genuinely differ per agent vendor) into each agent root as a directory
# of per-skill symlinks.
#
#   ~/.cursor/skills            <- shared + skills-vendor/cursor
#   ~/.claude/skills            <- shared + skills-vendor/claude
#   ~/.claude_personal/skills   <- shared + skills-vendor/claude
#   ~/.codex/skills             <- shared + skills-vendor/codex (preserves .system)
#
# Idempotent. Run it after adding, renaming, or removing any skill.
#
#   sync-skill-projections.sh            # report drift, change nothing
#   sync-skill-projections.sh --apply    # create, repair, prune
#
# Invariants:
#   * every projected entry is a symlink whose target is a REAL directory
#     (external package skills such as playwright-cli are resolved to their
#     endpoint, so no symlink -> symlink)
#   * a real directory sitting in a projection root is never deleted, only
#     reported — that is how an accidental clobber gets caught
#   * a vendor build always wins over a shared skill of the same name
#   * skill aliases are NOT extra directories; they live on SKILL.md
#     description + metadata.aliases

set -euo pipefail

# No fallback: a default here would bake one machine's home into every
# other machine (plan devkit, F4).
: "${HOME:?HOME is not set; export it and re-run}"
HOME_DIR="$HOME"
AGENTS="$HOME_DIR/.agents"
POOL="$AGENTS/skills"
VENDOR="$AGENTS/skills-vendor"

# root:vendor
TARGETS=(
  "$HOME_DIR/.cursor/skills:cursor"
  "$HOME_DIR/.claude/skills:claude"
  "$HOME_DIR/.claude_personal/skills:claude"
  "$HOME_DIR/.codex/skills:codex"
)

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

created=0; repaired=0; pruned=0; problems=0

say()  { printf '   %s\n' "$*"; }
add()  { printf '   \033[32m+\033[0m %s\n' "$*"; }
fix()  { printf '   \033[36m~\033[0m %s\n' "$*"; }
cut_() { printf '   \033[35m-\033[0m %s\n' "$*"; }
bad()  { printf '   \033[31m!\033[0m %s\n' "$*"; problems=$((problems+1)); }

[[ -d "$POOL" ]] || { echo "no shared pool at $POOL" >&2; exit 1; }

# Resolve an entry to the real directory it ultimately denotes. Pool entries
# may still be package-skill symlinks (playwright-cli); projecting those
# verbatim would build a symlink -> symlink chain.
canonical_of() {
  local p="$1" r
  r="$(readlink -f "$p" 2>/dev/null || true)"
  [[ -n "$r" && -d "$r" ]] && printf '%s\n' "$r"
}

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
    bad "$link is a real file/dir, not a link — left untouched, resolve by hand"
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

  printf '\n\033[1m-- %s\033[0m  (shared + vendor:%s)\n' "$root" "$vendor"

  if [[ -L "$root" ]]; then
    bad "$root is still a whole-directory symlink; migration Phase 4 did not run"
    continue
  fi
  [[ -d "$root" ]] || { (( APPLY )) && mkdir -p "$root"; add "mkdir $root"; }
  [[ -d "$root" ]] || continue

  declare -A want=()

  # shared pool first
  while IFS= read -r -d '' e; do
    name="$(basename "$e")"
    tgt="$(canonical_of "$e")"
    if [[ -z "$tgt" ]]; then
      bad "$e does not resolve to a directory — skipped"
      continue
    fi
    want["$name"]="$tgt"
  done < <(find "$POOL" -mindepth 1 -maxdepth 1 -print0 2>/dev/null)

  # vendor builds override same-named shared skills
  vdir="$VENDOR/$vendor"
  if [[ -d "$vdir" ]]; then
    while IFS= read -r -d '' e; do
      name="$(basename "$e")"
      tgt="$(canonical_of "$e")"
      [[ -z "$tgt" ]] && { bad "$e does not resolve to a directory"; continue; }
      [[ -n "${want[$name]:-}" ]] && say "vendor build overrides shared: $name"
      want["$name"]="$tgt"
    done < <(find "$vdir" -mindepth 1 -maxdepth 1 -print0)
  fi

  for name in "${!want[@]}"; do
    link_to "${want[$name]}" "$root/$name"
  done

  # prune links whose source disappeared; never touch real dirs
  while IFS= read -r -d '' l; do
    name="$(basename "$l")"
    [[ -n "${want[$name]:-}" ]] && continue
    cut_ "$root/$name (no longer in pool or vendor dir)"
    (( APPLY )) && rm "$l"
    pruned=$((pruned+1))
  done < <(find "$root" -mindepth 1 -maxdepth 1 -type l -print0)

  while IFS= read -r -d '' d; do
    # Codex owns this real system-skill directory; it is not a projected skill.
    [[ "$root" == "$HOME_DIR/.codex/skills" && "$(basename "$d")" == ".system" ]] && continue
    bad "$d is a real directory inside a projection root — it shadows the pool"
  done < <(find "$root" -mindepth 1 -maxdepth 1 -type d -print0)

  unset want
done

printf '\n   created %d · repaired %d · pruned %d · problems %d\n' \
       "$created" "$repaired" "$pruned" "$problems"
(( APPLY )) || printf '   (dry run — re-run with --apply)\n'
(( problems == 0 ))
