#!/usr/bin/env bash
#
# Health sweep over the agent roots. Reports, in order of severity:
#
#   CYCLE       symlink that cannot be resolved (ELOOP) — always a bug
#   DEAD        symlink whose target does not exist
#   CHAIN       symlink whose target is itself a symlink  (the rule: none allowed)
#   CROSS       shared asset still pointing at ~/.cursor instead of ~/.agents
#   TANGIBLE    real directory where only a projection link belongs
#
# Exit 0 only when the tree is clean.

set -uo pipefail

# No fallback: a default here would bake one machine's home into every
# other machine (plan devkit, F4).
: "${HOME:?HOME is not set; export it and re-run}"
HOME_DIR="$HOME"
AGENTS="$HOME_DIR/.agents"
ROOTS=("$AGENTS" "$HOME_DIR/.cursor" "$HOME_DIR/.claude")
# Deliberately NOT here: `agents`. Cursor and Codex ship their own builds of the same
# subagents (~/.cursor/agents/*.md differ from ~/.claude's; ~/.codex/agents/*.toml are a
# different format entirely), so a flat shared-asset list reports them as CROSS/TANGIBLE when
# they are legitimately vendor-local. `midas harness verify --links` checks agents correctly,
# because it knows per-vendor which projections apply. Same reason `~/.codex` is absent from
# ROOTS: `.codex/rules/default.rules` is Codex's own config.
SHARED=(history hooks kb plans prds rules skills)
# Claude Code auto-loads every ~/.claude/rules/*.md. The constitution is already
# prepended in AGENTS.md and ingested via CLAUDE.md, so a whole-dir symlink of
# ~/.agents/rules would double-load BASE. Cursor still whole-dir-links rules/.
CLAUDE_RULES_PATHS=(
  "$HOME_DIR/.claude/rules"
)

cycles=0; dead=0; chains=0; cross=0; tangible=0

hdr() { printf '\n\033[1m%s\033[0m\n' "$*"; }
hit() { printf '   \033[31m%-9s\033[0m %s\n' "$1" "$2"; }

hdr "symlink integrity"

while IFS= read -r -d '' l; do
  raw="$(readlink "$l")"
  case "$raw" in /*) abs="$raw" ;; *) abs="$(dirname "$l")/$raw" ;; esac

  if ! err="$(stat -L "$l" 2>&1 >/dev/null)"; then
    # ELOOP and ENOENT both fail stat -L; the kernel message tells them apart
    if [[ "$err" == *"Too many levels of symbolic links"* ]]; then
      hit CYCLE "$l -> $raw"; cycles=$((cycles+1))
    else
      hit DEAD "$l -> $raw"; dead=$((dead+1))
    fi
    continue
  fi

  # target exists — is it itself a link?
  if [[ -L "$abs" ]]; then
    hit CHAIN "$l -> $raw -> $(readlink "$abs")"; chains=$((chains+1))
  fi
done < <(find "${ROOTS[@]}" -type l -print0 2>/dev/null | sort -zu)

hdr "shared assets resolve to ~/.agents"

for root in "${ROOTS[@]:1}"; do
  [[ -d "$root" ]] || continue
  for a in "${SHARED[@]}"; do
    if [[ "$a" == "rules" && "$root" == "$HOME_DIR/.claude" ]]; then
      continue
    fi
    p="$root/$a"
    [[ -e "$p" || -L "$p" ]] || continue
    if [[ "$a" == "skills" ]]; then
      if [[ -L "$p" ]]; then
        hit CROSS "$p is a whole-dir link; it must be a real dir of per-skill links"
        cross=$((cross+1))
      else
        n=$(find "$p" -mindepth 1 -maxdepth 1 -type l 2>/dev/null | wc -l)
        printf '   \033[32mok\033[0m        %s (%s links)\n' "$p" "$n"
      fi
      continue
    fi
    tgt="$(readlink -f "$p" 2>/dev/null || true)"
    case "$tgt" in
      "$AGENTS"/*) printf '   \033[32mok\033[0m        %s -> %s\n' "$p" "$tgt" ;;
      *)           hit CROSS "$p -> ${tgt:-<unresolved>}"; cross=$((cross+1)) ;;
    esac
  done
done

hdr "no tangible assets left outside ~/.agents"

for root in "${ROOTS[@]:1}"; do
  for a in "${SHARED[@]}"; do
    if [[ "$a" == "rules" && "$root" == "$HOME_DIR/.claude" ]]; then
      continue
    fi
    p="$root/$a"
    [[ "$a" == "skills" ]] && continue
    if [[ -d "$p" && ! -L "$p" ]]; then
      hit TANGIBLE "$p is a real directory"; tangible=$((tangible+1))
    fi
  done
done
printf '   %s\n' "$( ((tangible==0)) && echo 'clean' || echo "$tangible found" )"

hdr "Claude does not whole-dir-link rules (BASE already in CLAUDE.md)"
for p in "${CLAUDE_RULES_PATHS[@]}"; do
  if [[ ! -e "$p" && ! -L "$p" ]]; then
    printf '   \033[32mok\033[0m        %s absent\n' "$p"
    continue
  fi
  tgt="$(readlink -f "$p" 2>/dev/null || true)"
  if [[ "$tgt" == "$AGENTS/rules" ]]; then
    hit CROSS "$p -> $tgt (Claude auto-loads *.md; BASE is already in CLAUDE.md)"
    cross=$((cross+1))
    continue
  fi
  if [[ -e "$p/AGENTS.md" || -e "$p/BASE.md" ]]; then
    hit CROSS "$p contains AGENTS.md or BASE.md (would double-load constitution)"
    cross=$((cross+1))
    continue
  fi
  printf '   \033[32mok\033[0m        %s (not the shared rules dir)\n' "$p"
done

hdr "vendor scripts/ project to ~/.agents/bin-vendor"
SCRIPT_ROOTS=(
  "$HOME_DIR/.claude/scripts:$AGENTS/bin-vendor/claude"
  "$HOME_DIR/.codex/scripts:$AGENTS/bin-vendor/codex"
  "$HOME_DIR/.cursor/scripts:$AGENTS/bin-vendor/cursor"
)
for spec in "${SCRIPT_ROOTS[@]}"; do
  root="${spec%%:*}"; want_prefix="${spec##*:}"
  if [[ ! -d "$root" ]]; then
    printf '   \033[32mok\033[0m        %s absent\n' "$root"
    continue
  fi
  while IFS= read -r -d '' e; do
    name="$(basename "$e")"
    if [[ -L "$e" ]]; then
      tgt="$(readlink -f "$e" 2>/dev/null || true)"
      case "$tgt" in
        "$want_prefix"/*) printf '   \033[32mok\033[0m        %s -> %s\n' "$e" "$tgt" ;;
        *) hit CROSS "$e -> ${tgt:-<unresolved>}"; cross=$((cross+1)) ;;
      esac
    elif [[ -f "$e" ]]; then
      hit TANGIBLE "$e is a real file in a projection root"; tangible=$((tangible+1))
    fi
  done < <(find "$root" -mindepth 1 -maxdepth 1 -print0)
done

hdr "impeccable resolves per vendor"
for p in "$HOME_DIR/.cursor/skills/impeccable" \
         "$HOME_DIR/.claude/skills/impeccable"; do
  if [[ -e "$p" ]]; then
    id=$(grep -o 'IMPECCABLE_PROVIDER_ID = "[^"]*"' "$p/scripts/lib/provider.mjs" 2>/dev/null | head -1)
    printf '   %-46s %s\n' "$p" "${id:-<provider.mjs unreadable>}"
  else
    hit DEAD "$p missing"; dead=$((dead+1))
  fi
done

hdr "summary"
printf '   cycles %d · dead %d · chains %d · cross-refs %d · stray tangible %d\n' \
       "$cycles" "$dead" "$chains" "$cross" "$tangible"

total=$((cycles+dead+chains+cross+tangible))
if (( total == 0 )); then
  printf '   \033[32mclean\033[0m\n'; exit 0
fi
printf '   \033[31m%d problem(s)\033[0m\n' "$total"; exit 1
