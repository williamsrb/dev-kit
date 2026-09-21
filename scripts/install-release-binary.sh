#!/usr/bin/env bash
# Install a single binary from a GitHub release into a target directory.
#
# Thin on purpose: bootstrap.sh calls it once per binary dependency, and it is
# shell rather than Python only because it is a one-line wrapper around curl and
# tar that bootstrap.sh already has the context for.
#
# Usage: install-release-binary.sh <owner/repo> <binary-name> <target-dir>
set -euo pipefail

REPO="${1:?usage: install-release-binary.sh <owner/repo> <binary> <target-dir>}"
NAME="${2:?missing binary name}"
TARGET="${3:?missing target directory}"

command -v curl >/dev/null 2>&1 || { echo "error: curl is required" >&2; exit 1; }

# GitHub release pages 302 to a short-lived CDN URL. -L follows that hop.
# Retry from the original URL: a 504 on the CDN must not reuse an expired link.
fetch() {
  curl --retry 5 --retry-delay 2 --retry-all-errors --retry-max-time 180 \
    -fsSL -A 'devkit-bootstrap' "$@"
}

# Projects name the same architecture at least four ways. trivy ships
# "Linux-64bit", gitleaks ships "linux_x64", others ship "amd64" — matching only
# the uname spelling silently finds nothing and looks like a missing release.
case "$(uname -m)" in
  x86_64|amd64) ARCH_PATTERNS='x86_64|amd64|x64|64bit' ;;
  aarch64|arm64) ARCH_PATTERNS='aarch64|arm64|ARM64' ;;
  *) echo "error: unsupported architecture $(uname -m)" >&2; exit 1 ;;
esac

API="https://api.github.com/repos/$REPO/releases/latest"
mapfile -t MATCHES < <(fetch -H 'Accept: application/vnd.github+json' "$API" \
  | grep -oE '"browser_download_url": *"[^"]+"' \
  | cut -d'"' -f4 \
  | grep -iE "linux" \
  | grep -iE "$ARCH_PATTERNS" \
  | grep -ivE '(^|[^0-9])(32bit|386|i686|armv[567])' \
  | grep -ivE '\.(sha256|asc|sig|pem|deb|rpm|apk|msi|json|txt|sbom|spdx)$' \
  | grep -ivE '(sigstore|checksums|attestation)')

# Accelerator builds (ollama mlx/rocm/jetpack) match "linux" + "amd64" and sort
# ahead of the plain archive. Take a plain archive when one exists.
ASSET_URL=""
for candidate in "${MATCHES[@]}"; do
  case "$candidate" in
    *[Mm]lx*|*[Rr]ocm*|*[Jj]etpack*|*[Cc]uda*) continue ;;
  esac
  ASSET_URL="$candidate"
  case "$candidate" in
    *.tar.gz|*.tgz|*.tar.xz|*.tar.zst|*.zip) break ;;
  esac
done
if [ -z "$ASSET_URL" ] && [ "${#MATCHES[@]}" -gt 0 ]; then
  ASSET_URL="${MATCHES[0]}"
fi

if [ -z "$ASSET_URL" ]; then
  echo "error: no linux asset for $(uname -m) in the latest $REPO release" >&2
  echo "fix:   install $NAME by hand and re-run bootstrap.sh --apply" >&2
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "    fetching $ASSET_URL"
fetch "$ASSET_URL" -o "$WORK/asset"

case "$ASSET_URL" in
  *.tar.gz|*.tgz) tar -xzf "$WORK/asset" -C "$WORK" ;;
  *.tar.xz)       tar -xJf "$WORK/asset" -C "$WORK" ;;
  *.tar.zst)      command -v zstd >/dev/null 2>&1 || { echo "error: zstd required" >&2; exit 1; }
                  tar --zstd -xf "$WORK/asset" -C "$WORK" ;;
  *.zip)          command -v unzip >/dev/null 2>&1 || { echo "error: unzip required" >&2; exit 1; }
                  unzip -qo "$WORK/asset" -d "$WORK" ;;
  *)              mv "$WORK/asset" "$WORK/$NAME" ;;
esac

FOUND="$(find "$WORK" -type f -name "$NAME" -print -quit)"
[ -n "$FOUND" ] || FOUND="$(find "$WORK" -type f -perm -u+x ! -name 'asset' -print -quit)"

if [ -z "$FOUND" ]; then
  echo "error: could not find a '$NAME' binary in the $REPO release asset" >&2
  exit 1
fi

mkdir -p "$TARGET"
install -m 0755 "$FOUND" "$TARGET/$NAME"
echo "    installed $TARGET/$NAME"
