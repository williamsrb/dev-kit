---
id: how-to-fork-devkit-profile-desktop-apps
when_skills: [run-plan]
inputs: [/usr/lib/claude-desktop, /usr/lib/chatgpt, /usr/share/cursor, /etc/apt/apt.conf.d/99-cursor-recolor, /etc/dpkg/dpkg.cfg.d/60cursor-recolor]
outputs: [/usr/lib/devkit, /etc/apt/apt.conf.d/99-devkit-profile-apps, /etc/dpkg/dpkg.cfg.d/60devkit-profile-apps]
stop_if: [editing vendor postinst, writing stock trees]
read: whole
prose: caveman-lite
---

# Fork devkit profile desktop apps

Each profile GUI is a dpkg-unowned rsync of stock, with a patched identity.
Apt/dpkg overwrite stock only. Dual hooks rebuild every fork. Do not touch
stock, or the existing Cursor recolor/tgrep hooks.

## Prerequisites

- Stock packages: `claude-desktop`, `chatgpt`, `cursor`
- Canonical worker: kit `devkit_cli/appfork.py`
- Installed worker: `/usr/local/bin/sync-devkit-profile-apps.py` (copy, not a home symlink)
- Apt hook: `/etc/apt/apt.conf.d/99-devkit-profile-apps` (`DPkg::Post-Invoke`)
- Dpkg hook: `/etc/dpkg/dpkg.cfg.d/60devkit-profile-apps` (same shape as `60cursor-recolor` — apt's `DPkg::Post-Invoke` does not run for bare `dpkg -i`)

## Procedure

1. Do **not** edit vendor `postinst`. It is rewritten on every `configure`.
2. User config: `devkit profile create … --apply` writes launchers that `Exec` the fork path. Config stays in `~/.agents-profiles` / `~/.config`.
3. Root once: `sudo devkit profile apps-sync --user "$USER" --install-hook --apply`. Copies the worker, writes both hooks, rsyncs stock → `/usr/lib/devkit/<vendor>-<profile>/`.
4. After `apt upgrade` or `dpkg -i` of a vendor package, the hook runs `/usr/local/bin/sync-devkit-profile-apps.py >>/var/log/devkit-profile-apps.log 2>&1 || true`.
5. Cheap gates (exit 0, no copy): package not installed; stock tree missing; fork `version` already equals stock **and** identity is patched.
6. Rebuild: `rsync -aH --delete` stock → fork. Preserves `chrome-sandbox` mode `4755`. If the fork is running, still copy; do not SIGTERM; log a restart reminder.
7. Patch identity only in the copy:
   - Claude / Codex: asar `desktopName` → `Claude-<profile>.desktop` / `Codex-<profile>.desktop`. Rewrite that file's header `integrity` SHA256. Leave `productName`.
   - Cursor: unpacked `resources/app/package.json` `desktopName` and `product.json` `nameShort` (WM_CLASS is `Cursor` from `nameShort`, not from asar).
8. Recolor in-tree icons from **stock** assets with the profile colour. Do not use `cursor-recolor-apply.sh` on the fork (that script writes stock `/usr/share/cursor`).
9. AppArmor: unconfined + `userns` profile attached to the fork binary.
10. Manual: `sudo /usr/local/bin/sync-devkit-profile-apps.py`. Dry-run: `--dry-run` (no root required for the kit command). Icons only: `--icons-only`.

## Pitfalls

- A launch flag for `--user-data-dir` is not enough. Electron bakes `desktopName` into `app.asar`; Chromium derives WM_CLASS / Wayland `app_id` from it. Cursor uses `product.json` `nameShort`.
- Asar header has per-file `integrity.algorithm=SHA256`. Changing the blob without updating that hash is an incomplete patch.
- Apt's `DPkg::Post-Invoke` does not run for bare `dpkg -i`. Profile forks need the apt hook and the dpkg hook, or a vendor `.deb` installed with `dpkg -i` leaves stale identity.
- Hook is global. Version+identity gate must run before rsync (Claude ~550MB, ChatGPT ~1.4G, Cursor ~1G).
- Worker failure must not fail apt (`|| true`). Do not add this basename to `PATH_SHIMS`; unattended-upgrades uses `/usr/local/bin`.
- Never write `/usr/lib/claude-desktop`, `/usr/lib/chatgpt`, or `/usr/share/cursor`.
- Do not modify `99-cursor-recolor`, `99-cursor-tgrep-rg`, or their dpkg twins.
- Do not touch session data under `~/.agents-profiles` or `~/.config/<Vendor>-<profile>`.

## Sample data (minimal)

| Field | Example |
|-------|---------|
| Stock Claude version | `/usr/lib/claude-desktop/version` |
| Fork | `/usr/lib/devkit/claude-dummy/` |
| desktopName | `Claude-dummy.desktop` |
| WM_CLASS | `Claude-dummy` |
| Log skip | `claude-dummy already at 44.2.0 with desktopName=Claude-dummy.desktop` |
