#!/usr/bin/env bash
# devkit step 1: install dependencies. Writes no configuration.
#
# Bash, not Python, for one reason: this runs before Python is guaranteed. Every
# other helper in the kit is Python 3.12 stdlib (prefer-python-over-shell).
#
# Privilege rule (D18): sudo is scoped to package transactions. This script never
# writes into a user's home and never touches configuration — that is install.py's
# job, and install.py refuses to run as root.
#
# Usage:
#   ./bootstrap.sh                    # dry run: print the plan, change nothing
#   ./bootstrap.sh --apply            # install
#   ./bootstrap.sh --profile enonic --apply
#   ./bootstrap.sh --apply --wire-path
#
set -euo pipefail

: "${HOME:?HOME is not set; export it and re-run}"

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="core"
APPLY=0
WIRE_PATH=0
ALLOW_THIRD_PARTY=""
LOCAL_BIN="$HOME/.local/bin"

usage() {
  cat <<'USAGE'
Usage: bootstrap.sh [options]

Installs the dependencies a profile declares. Writes no configuration.

Options:
  --profile NAME       Profile whose deps to install (default: core)
  --apply              Actually install. Without it this is a dry run.
  --wire-path          Add ~/.local/bin to PATH in your shell profile, after
                       reporting which file would change.
  --third-party yes|no Answer the third-party repository prompt up front.
  -h, --help           Show this message.

Exit codes: 0 ok, 1 a dependency could not be resolved, 2 bad invocation.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="${2:?--profile needs a name}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --wire-path) WIRE_PATH=1; shift ;;
    --third-party) ALLOW_THIRD_PARTY="${2:?--third-party needs yes or no}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'bootstrap.sh: unknown option %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$1" >&2; [ -n "${2:-}" ] && printf 'fix:   %s\n' "$2" >&2; exit 1; }
run()  { if [ "$APPLY" -eq 1 ]; then say "  + $*"; "$@"; else say "  would run: $*"; fi; }

# ---------------------------------------------------------------- family (D12)

detect_family() {
  [ -r /etc/os-release ] || { echo unknown; return; }
  # shellcheck disable=SC1091
  . /etc/os-release
  local candidates="${ID:-} ${ID_LIKE:-}"
  case " $candidates " in
    *" debian "*|*" ubuntu "*) echo debian ;;
    *" fedora "*|*" rhel "*|*" centos "*) echo rhel ;;
    *" arch "*) echo arch ;;
    *) echo "${ID:-unknown}" ;;
  esac
}

FAMILY="$(detect_family)"
case "$FAMILY" in
  debian) PKG_MANAGER=apt;    PKG_KEY=apt ;;
  rhel)   PKG_MANAGER=dnf;    PKG_KEY=dnf ;;
  arch)   PKG_MANAGER=pacman; PKG_KEY=pacman ;;
  *) die "unsupported distribution family: $FAMILY" \
         "supported: debian/ubuntu, rhel/fedora, arch. Open an issue with your /etc/os-release." ;;
esac

command -v "$PKG_MANAGER" >/dev/null 2>&1 \
  || die "$PKG_MANAGER is not on PATH but $FAMILY was detected" "check your PATH"

say "devkit bootstrap"
say "  profile:        $PROFILE"
say "  family:         $FAMILY ($PKG_MANAGER)"
say "  mode:           $([ "$APPLY" -eq 1 ] && echo apply || echo 'dry run')"
say ""

# ---------------------------------------------------------------- the plan

# devkit needs only python3 stdlib, and python3 is itself a dependency, so read
# the manifest with python3 when it exists and fall back to a minimal parse when
# it does not.
if command -v python3 >/dev/null 2>&1; then
  PLAN="$(python3 "$KIT_DIR/devkit_cli/bootstrap_plan.py" --profile "$PROFILE" --manager "$PKG_KEY")"
else
  warn "python3 is absent; installing it first, then re-reading the plan"
  case "$PKG_MANAGER" in
    apt)    run sudo apt-get update; run sudo apt-get install -y python3 ;;
    dnf)    run sudo dnf install -y python3 ;;
    pacman) run sudo pacman -Sy --noconfirm python ;;
  esac
  if [ "$APPLY" -eq 0 ]; then
    say ""
    say "Dry run stops here: the rest of the plan needs python3 to read the manifest."
    exit 0
  fi
  PLAN="$(python3 "$KIT_DIR/devkit_cli/bootstrap_plan.py" --profile "$PROFILE" --manager "$PKG_KEY")"
fi

PACKAGES="$(printf '%s\n' "$PLAN" | awk -F'\t' '$1=="pkg"     {print $2}')"
NPM_PKGS="$(printf '%s\n' "$PLAN" | awk -F'\t' '$1=="npm"     {print $2}')"
UV_PKGS="$(printf '%s\n'  "$PLAN" | awk -F'\t' '$1=="uv"      {print $2}')"
BINARIES="$(printf '%s\n' "$PLAN" | awk -F'\t' '$1=="binary"  {print $2}')"
NEEDS_NODE="$(printf '%s\n' "$PLAN" | awk -F'\t' '$1=="nvm"   {print $2}')"
THIRD_PARTY="$(printf '%s\n' "$PLAN" | awk -F'\t' '$1=="thirdparty" {print $2}')"

# ------------------------------------------------- third-party repos (D13)

if [ -n "$THIRD_PARTY" ] && [ "$FAMILY" = "rhel" ]; then
  say "These packages need a third-party repository on $FAMILY:"
  printf '  %s\n' $THIRD_PARTY
  say ""
  if [ -z "$ALLOW_THIRD_PARTY" ]; then
    if [ -t 0 ]; then
      printf 'Enable it? [y/N] '; read -r reply
      case "$reply" in [Yy]*) ALLOW_THIRD_PARTY=yes ;; *) ALLOW_THIRD_PARTY=no ;; esac
    else
      ALLOW_THIRD_PARTY=no
      say "  not a terminal; declining by default. Pass --third-party yes to enable."
    fi
  fi
  if [ "$ALLOW_THIRD_PARTY" != "yes" ]; then
    say "  declined. Those packages resolve from a lower rung or are recorded as skipped."
    say "  The run continues; this is never a hard failure (D13)."
    for skipped in $THIRD_PARTY; do
      PACKAGES="$(printf '%s\n' "$PACKAGES" | grep -vx "$skipped" || true)"
    done
  fi
  say ""
fi

# ---------------------------------------------------------------- rung 1: distro

if [ -n "$PACKAGES" ]; then
  say "Distribution packages ($PKG_MANAGER):"
  case "$PKG_MANAGER" in
    apt)    run sudo apt-get update
            # shellcheck disable=SC2086
            run sudo apt-get install -y $PACKAGES ;;
    dnf)    # shellcheck disable=SC2086
            run sudo dnf install -y $PACKAGES ;;
    pacman) # shellcheck disable=SC2086
            run sudo pacman -Sy --noconfirm --needed $PACKAGES ;;
  esac
  say ""
fi

# ---------------------------------------------------------------- rung 2: node

if [ -n "$NEEDS_NODE" ] && ! command -v node >/dev/null 2>&1; then
  say "Node $NEEDS_NODE via nvm (the distro node lags behind what the kit needs):"
  NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    run sh -c "curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
  fi
  if [ "$APPLY" -eq 1 ] && [ -s "$NVM_DIR/nvm.sh" ]; then
    # shellcheck disable=SC1091
    . "$NVM_DIR/nvm.sh"
    nvm install "$NEEDS_NODE"
    nvm alias default "$NEEDS_NODE"
  fi
  say ""
fi

# One package failing must not abort the other twenty. Collect the failures,
# report them by name at the end, and let the --verify step decide whether the
# run is actually short of anything required.
FAILED_OPTIONAL=""

try_install() {
  # try_install <label> <command...>
  local label="$1"; shift
  if [ "$APPLY" -eq 0 ]; then say "  would run: $*"; return 0; fi
  say "  + $*"
  if "$@"; then return 0; fi
  warn "$label failed; continuing"
  FAILED_OPTIONAL="$FAILED_OPTIONAL $label"
  return 0
}

if [ -n "$NPM_PKGS" ]; then
  say "npm packages:"
  if command -v npm >/dev/null 2>&1 || [ "$APPLY" -eq 0 ]; then
    for pkg in $NPM_PKGS; do try_install "npm:$pkg" npm install -g "$pkg"; done
  else
    warn "npm is not on PATH; skipping: $(printf '%s ' $NPM_PKGS)"
  fi
  say ""
fi

# ---------------------------------------------------------------- rung 3: uv

if [ -n "$UV_PKGS" ]; then
  say "Python tools via uv:"
  if ! command -v uv >/dev/null 2>&1; then
    run sh -c "curl -fsSL https://astral.sh/uv/install.sh | sh"
  fi
  if command -v uv >/dev/null 2>&1 || [ "$APPLY" -eq 0 ]; then
    for pkg in $UV_PKGS; do try_install "uv:$pkg" uv tool install "$pkg"; done
  else
    warn "uv is not on PATH; skipping: $(printf '%s ' $UV_PKGS)"
  fi
  say ""
fi

# ---------------------------------------------------------------- rung 4: binary

if [ -n "$BINARIES" ]; then
  say "Direct binary installs:"
  mkdir -p "$LOCAL_BIN"
  for spec in $BINARIES; do
    name="${spec%%=*}"; repo="${spec#*=}"
    if command -v "$name" >/dev/null 2>&1; then
      say "  ok (present): $name"
      continue
    fi
    say "  $name from github.com/$repo"
    try_install "binary:$name" "$KIT_DIR/scripts/install-release-binary.sh" \
      "$repo" "$name" "$LOCAL_BIN"
  done
  say ""
fi

# ------------------------------------------------------------ PATH (D19)

if ! printf '%s' ":$PATH:" | grep -q ":$LOCAL_BIN:"; then
  say "PATH: $LOCAL_BIN is not on your PATH."
  for candidate in "$HOME/.bash_profile" "$HOME/.profile" "$HOME/.zshrc" "$HOME/.bashrc"; do
    [ -f "$candidate" ] || continue
    say "  shell startup file detected: $candidate"
    if [ "$WIRE_PATH" -eq 1 ]; then
      run sh -c "printf '\n# Added by devkit bootstrap.sh\nexport PATH=\"\$HOME/.local/bin:\$PATH\"\n' >> '$candidate'"
      break
    fi
  done
  [ "$WIRE_PATH" -eq 1 ] || say "  not edited. Re-run with --wire-path, or add it yourself (D19)."
  say ""
fi

# nvm puts node under $NVM_DIR/versions/..., reachable only in shells that source
# nvm.sh. This script sources it in-process, so its own verify passes while a
# fresh shell still cannot find node. Say so rather than letting the next command
# fail with "node: not found".
if [ -n "$NEEDS_NODE" ] && [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then
  if ! env -i HOME="$HOME" PATH="$PATH" sh -lc 'command -v node' >/dev/null 2>&1; then
    say "Node: installed through nvm, but a fresh login shell cannot see it yet."
    say "  nvm adds it by sourcing \$NVM_DIR/nvm.sh from your shell startup file."
    say "  Open a new shell, or: . \"${NVM_DIR:-\$HOME/.nvm}/nvm.sh\""
    say ""
  fi
fi

# ---------------------------------------------------------------- verify

if [ -n "$FAILED_OPTIONAL" ]; then
  say "These installs failed and were skipped:"
  for item in $FAILED_OPTIONAL; do say "  $item"; done
  say "  The verify step below decides whether any of them was actually required."
  say ""
fi

if [ "$APPLY" -eq 1 ] && command -v python3 >/dev/null 2>&1; then
  say "Verifying what the profile declares:"
  python3 "$KIT_DIR/devkit_cli/bootstrap_plan.py" --profile "$PROFILE" --manager "$PKG_KEY" --verify \
    || die "some required dependencies are still missing" \
           "re-run, or install the named tools by hand and re-run --verify"
  say ""
  say "Step 1 complete. No configuration was written."
  say "Next: ./install.py --profile $PROFILE --apply"
else
  say "Dry run complete. Re-run with --apply to install."
fi
