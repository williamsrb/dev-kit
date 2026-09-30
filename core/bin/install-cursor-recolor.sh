#!/bin/bash
# Install Cursor tray recolor hooks (apt + dpkg) and apply once.
# Run as root:  pkexec "$HOME/.agents/bin/install-cursor-recolor.sh"
#
# Copies the apply script into /usr/local/bin (never a symlink into $HOME).

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root (pkexec or sudo)" >&2
  exit 1
fi

HERE="$(cd "$(dirname -- "$0")" && pwd)"
SRC="$HERE/cursor-recolor-apply.sh"
[ -f "$SRC" ] || { echo "missing $SRC" >&2; exit 1; }

install -m 755 "$SRC" /usr/local/bin/cursor-recolor-apply.sh

umask 022
cat > /etc/apt/apt.conf.d/99-cursor-recolor <<'EOF'
// Reapply Cursor tray icon recolor after any apt/dpkg run that updates
// the "cursor" package (stock update overwrites the tray PNGs).
DPkg::Post-Invoke {"/usr/local/bin/cursor-recolor-apply.sh >>/var/log/cursor-recolor.log 2>&1 || true";};
EOF
chmod 644 /etc/apt/apt.conf.d/99-cursor-recolor

cat > /etc/dpkg/dpkg.cfg.d/60cursor-recolor <<'EOF'
# Reapply Cursor tray recolor after dpkg -i / unpack (apt's DPkg::Post-Invoke
# does not run for bare dpkg). Second run in the same apt transaction is a no-op.
post-invoke "/usr/local/bin/cursor-recolor-apply.sh >>/var/log/cursor-recolor.log 2>&1 || true"
EOF
chmod 644 /etc/dpkg/dpkg.cfg.d/60cursor-recolor

touch /var/log/cursor-recolor.log
chmod 644 /var/log/cursor-recolor.log

if ! command -v convert >/dev/null 2>&1; then
  echo "convert (ImageMagick) not found; hooks installed, icons not recolored yet" >&2
  exit 0
fi

/usr/local/bin/cursor-recolor-apply.sh >>/var/log/cursor-recolor.log 2>&1
echo "installed hooks and ran apply"
if command -v identify >/dev/null 2>&1 \
   && [ -f /usr/share/cursor/resources/app/resources/linux/trayTemplate-32.png ]; then
  identify -verbose /usr/share/cursor/resources/app/resources/linux/trayTemplate-32.png \
    | grep '#800080FF' || echo "warning: trayTemplate-32.png has no purple pixels yet"
fi
