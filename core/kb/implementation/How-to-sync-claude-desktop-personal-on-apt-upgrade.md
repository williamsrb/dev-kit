---
id: how-to-sync-claude-desktop-personal-on-apt-upgrade
when_skills: [run-plan]
inputs: [/usr/lib/claude-desktop, /etc/apt/apt.conf.d/99-cursor-recolor]
outputs: [/usr/lib/claude-desktop-personal, /etc/apt/apt.conf.d/99-claude-personal-sync]
stop_if: [editing vendor postinst]
read: whole
prose: caveman-lite
---

# Sync Claude Personal on apt upgrade of claude-desktop

Personal is a dpkg-unowned fork of `/usr/lib/claude-desktop`. Apt only updates stock. A `DPkg::Post-Invoke` hook rebuilds Personal from the tree just installed, then re-applies identity (asar `desktopName`, `.desktop` Exec, recolored icons, AppArmor).

## Prerequisites

- Stock package `claude-desktop` installed under `/usr/lib/claude-desktop`
- Worker: `~/.agents/bin/sync-claude-desktop-personal.py` (canonical) copied to `/usr/local/bin/sync-claude-desktop-personal.py` (root, not a home symlink)
- Hook: `/etc/apt/apt.conf.d/99-claude-personal-sync` (same shape as `99-cursor-recolor`)
- Recolor: `${HOME}/.agents/bin/recolor-white-black-icons.sh` (skip icons if missing; do not fail the rest)

## Procedure

1. Do **not** edit `/var/lib/dpkg/info/claude-desktop.postinst`. It is rewritten on every `configure`.
2. After `apt upgrade claude-desktop`, the hook runs `/usr/local/bin/sync-claude-desktop-personal.py >>/var/log/claude-personal-sync.log 2>&1 || true`.
3. Cheap gates (exit 0, no copy): package not installed; stock tree missing; Personal `version` already equals stock **and** asar `desktopName` is `com.anthropic.ClaudePersonal.desktop`.
4. Rebuild: `rsync -aH --delete` stock → `/usr/lib/claude-desktop-personal/`. Preserves `chrome-sandbox` mode `4755`. If Personal is running, still copy; do not SIGTERM; log a restart reminder.
5. Patch Personal `resources/app.asar` only: `desktopName` `com.anthropic.Claude.desktop` → `com.anthropic.ClaudePersonal.desktop`. Append if +8 bytes; rewrite that file's header `integrity` SHA256. Leave `productName=Claude`. Never write `/usr/lib/claude-desktop`.
6. Recolor from **stock** assets (never from already-recolored Personal files):
   - Dark-theme white-on-alpha tray glyphs → pure yellow `#FFFF00`
   - Light-theme black-on-alpha tray glyphs → pure purple `#800080`
   - Mixed orange+white brand (`icon.png`, hicolor) → swap: orange background becomes white, white spark becomes orange. Then `-channel RGB -level 10%,90%` (alpha unchanged). Drop-shadow fringe stays dark.
   Do not use `recolor-white-black-icons.sh` here (that script is for Cursor tray; it would turn the spark yellow and leave the orange).
7. Regenerate `com.anthropic.ClaudePersonal.desktop` from current stock: Exec uses `CLAUDE_CONFIG_DIR=${HOME}/.claude_personal` and `--user-data-dir=${HOME}/.config/ClaudePersonal`; `StartupWMClass=com.anthropic.ClaudePersonal`; `Name=Claude Personal` (stock work app stays `Name=Claude`). Rewrite `~/.local/share/applications/...` if present.
8. Manual rerun: `sudo /usr/local/bin/sync-claude-desktop-personal.py`. Dry-run: `--dry-run` (no root required). Icons only (from stock, no rsync): `--icons-only`. Desktop files only: `--desktop-only`.

## Pitfalls

- A launch flag for `--user-data-dir` is not enough. Electron bakes `desktopName` into `app.asar`; Chromium derives WM_CLASS / Wayland `app_id` from it. Same binary → dock merge.
- Asar header has per-file `integrity.algorithm=SHA256`. Changing the blob without updating that hash is an incomplete patch. Root `package.json` has no `asarIntegrity` key (measured 2026-08-26).
- Recolor without `-i` writes `*.recolor.png` sidecars and leaves stock icons in place. Claude Personal does not use that script.
- Brand icons are orange+white. White→yellow / black→purple on those files leaves a yellow spark on orange — wrong. Invert the pair instead, then `-level 10%,90%` on RGB only.
- Hook is global (`DPkg::Post-Invoke`). Version+desktopName gate must run before rsync (550MB).
- Worker failure must not fail apt (`|| true`). Do not add this basename to `PATH_SHIMS`; unattended-upgrades uses `/usr/local/bin`.
- Do not touch `~/.claude`, `~/.claude_personal`, `~/.config/Claude`, or `~/.config/ClaudePersonal` session data.
- Do not modify `/etc/apt/apt.conf.d/99-cursor-recolor`.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| Stock version file | `/usr/lib/claude-desktop/version` → `42.10.0` |
| Personal desktopName | `com.anthropic.ClaudePersonal.desktop` |
| Log | `/var/log/claude-personal-sync.log` skip line: `Personal already at 42.10.0 with desktopName=...` |
