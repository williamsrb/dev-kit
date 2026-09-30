#!/bin/bash
# Reapply Cursor tray icon recolor after package updates.
# Light-theme glyphs (black) → purple. Dark-theme glyphs (white) → purple.
# Also replace mid-grey #808080 → purple.
#
# 16/22/24 PNGs ship as grayscale. ImageMagick 7 keeps that colorspace, so a
# direct -fill purple is a no-op. Recolor RGB with alpha extracted, then
# restore the mask.
#
# Canonical: ~/.agents/bin/cursor-recolor-apply.sh
# Installed:  /usr/local/bin/cursor-recolor-apply.sh  (copy, not a home symlink)

set -euo pipefail

ICON_DIR="/usr/share/cursor/resources/app/resources/linux"

[ -d "$ICON_DIR" ] || exit 0

if command -v magick >/dev/null 2>&1; then
  IM=(magick)
elif command -v convert >/dev/null 2>&1; then
  IM=(convert)
else
  exit 0
fi

# Black-on-alpha silhouettes (Electron light: !shouldUseDarkColors).
LIGHT=(
  trayNotifyWhite.png
  trayNotifyWhite-16.png
  trayNotifyWhite-22.png
  trayNotifyWhite-24.png
  trayNotifyWhite-32.png
  trayNotifyWhite-48.png
  trayTemplate.png
  trayTemplate-16.png
  trayTemplate-22.png
  trayTemplate-24.png
  trayTemplate-32.png
  trayTemplate-48.png
)

# White-on-alpha silhouettes (Electron dark). Do not -opaque black: that
# would fill the inner cutout. Leave trayNotifyDark* stock (red badge).
DARK=(
  trayTemplateDark.png
  trayTemplateDark-16.png
  trayTemplateDark-22.png
  trayTemplateDark-24.png
  trayTemplateDark-32.png
  trayTemplateDark-48.png
)

# Skip only when purple is present and grey #808080 is gone.
already_done() {
  command -v identify >/dev/null 2>&1 || return 1
  local info
  info="$(identify -verbose "$1" 2>/dev/null || true)"
  echo "$info" | grep -q '#808080' && return 1
  echo "$info" | grep -q '#800080'
}

recolor() {  # $1=src  $2=opaque-color  (black|white)
  local src="$1" from="$2"
  local rgb mask out
  rgb="$(mktemp --suffix=".png")"
  mask="$(mktemp --suffix=".png")"
  out="$(mktemp --suffix=".png")"
  "${IM[@]}" "$src" -alpha extract "$mask"
  "${IM[@]}" "$src" -alpha off -colorspace sRGB -fuzz 10% \
    -fill '#800080' -opaque "$from" \
    -fill '#800080' -opaque '#808080' \
    "$rgb"
  "${IM[@]}" "$rgb" "$mask" -compose CopyOpacity -composite PNG32:"$out"
  cp -f "$out" "$ICON_DIR/$(basename "$src")"
  rm -f "$rgb" "$mask" "$out"
}

did=0
for name in "${LIGHT[@]}"; do
  f="$ICON_DIR/$name"
  [ -f "$f" ] || continue
  already_done "$f" && continue
  recolor "$f" black
  did=1
done
for name in "${DARK[@]}"; do
  f="$ICON_DIR/$name"
  [ -f "$f" ] || continue
  already_done "$f" && continue
  recolor "$f" white
  did=1
done

[ "$did" -eq 1 ] && echo "$(date -Iseconds) cursor tray icons recolored"
