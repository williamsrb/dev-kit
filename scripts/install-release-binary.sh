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

case "$(uname -m)" in
  x86_64|amd64) ARCH_PATTERNS='x86_64|amd64|x64' ;;
  aarch64|arm64) ARCH_PATTERNS='aarch64|arm64' ;;
  *) echo "error: unsupported architecture $(uname -m)" >&2; exit 1 ;;
esac

API="https://api.github.com/repos/$REPO/releases/latest"
ASSET_URL="$(curl -fsSL "$API" \
  | grep -oE '"browser_download_url": *"[^"]+"' \
  | cut -d'"' -f4 \
  | grep -iE "linux" \
  | grep -iE "$ARCH_PATTERNS" \
  | grep -ivE '\.(sha256|asc|sig|deb|rpm|apk)$' \
  | head -1)"

if [ -z "$ASSET_URL" ]; then
  echo "error: no linux asset for $(uname -m) in the latest $REPO release" >&2
  echo "fix:   install $NAME by hand and re-run bootstrap.sh --apply" >&2
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "    fetching $ASSET_URL"
curl -fsSL "$ASSET_URL" -o "$WORK/asset"

case "$ASSET_URL" in
  *.tar.gz|*.tgz) tar -xzf "$WORK/asset" -C "$WORK" ;;
  *.tar.xz)       tar -xJf "$WORK/asset" -C "$WORK" ;;
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
