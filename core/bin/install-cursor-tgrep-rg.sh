#!/bin/bash
# Install Cursor tgrep-rg wrap hooks (apt + dpkg) and apply once.
# Run as root:  pkexec "$HOME/.agents/bin/install-cursor-tgrep-rg.sh"
#
# Copies the apply script into /usr/local/bin (never a symlink into $HOME).

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "run as root (pkexec or sudo)" >&2
  exit 1
fi

HERE="$(cd "$(dirname -- "$0")" && pwd)"
SRC="$HERE/cursor-tgrep-rg-apply.py"
[ -f "$SRC" ] || { echo "missing $SRC" >&2; exit 1; }

install -m 755 "$SRC" /usr/local/bin/cursor-tgrep-rg-apply

umask 022
cat > /etc/apt/apt.conf.d/99-cursor-tgrep-rg <<'EOF'
// Re-wrap Cursor @vscode/ripgrep/bin/rg after apt/dpkg updates the cursor package.
DPkg::Post-Invoke {"/usr/local/bin/cursor-tgrep-rg-apply apply >>/var/log/cursor-tgrep-rg.log 2>&1 || true";};
EOF
chmod 644 /etc/apt/apt.conf.d/99-cursor-tgrep-rg

cat > /etc/dpkg/dpkg.cfg.d/60cursor-tgrep-rg <<'EOF'
# Re-wrap Cursor rg after dpkg -i / unpack (apt's DPkg::Post-Invoke does not
# run for bare dpkg). Second run in the same apt transaction is a no-op.
post-invoke "/usr/local/bin/cursor-tgrep-rg-apply apply >>/var/log/cursor-tgrep-rg.log 2>&1 || true"
EOF
chmod 644 /etc/dpkg/dpkg.cfg.d/60cursor-tgrep-rg

touch /var/log/cursor-tgrep-rg.log
chmod 644 /var/log/cursor-tgrep-rg.log

/usr/local/bin/cursor-tgrep-rg-apply apply >>/var/log/cursor-tgrep-rg.log 2>&1
echo "installed hooks and ran apply"
