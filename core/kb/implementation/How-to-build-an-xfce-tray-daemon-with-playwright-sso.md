---
id: how-to-build-an-xfce-tray-daemon-with-playwright-sso
when_skills: [run-plan, plan-implementation]
topic: xfce-tray
keywords: [build, xfce, tray, daemon, playwright, sso, ayatana, appindicator, autostart, systemd-run, journal, dbusmenu, gdbus, chromium, executablepath, microsoft, session, renew]
inputs: [a per-user background job that needs a tray icon on Xubuntu/Xfce X11 and a Microsoft-SSO web session]
outputs: [autostarted daemon with journal logs, tray state icon, silent session renewal]
stop_if: []
read: whole
prose: caveman-lite
---

# Build an Xfce tray daemon with Playwright SSO

Learned on `g8-ipd` (`~/Workspace/Personal/g8-ipd`, 2026-10-28). It is a stdlib Python daemon with an Ayatana tray icon that keeps a Microsoft-SSO web form session alive.

## Scope

Xubuntu, Xfce 4.20, X11. System Python with `gi`. No pip. Node `playwright-core` under `~/.local/node_modules`.

## Procedure

1. **Tray:** `gi.require_version("AyatanaAppIndicator3", "0.1")`. Call `Indicator.new(id, icon_name, APPLICATION_STATUS)` + `set_icon_theme_path(<dir with svgs>)` + `set_icon_full(name, desc)`. The Xfce 4.20 `systray` plugin hosts it as a StatusNotifierItem. The "libayatana-appindicator is deprecated" warning on start is harmless.
2. **Thread rule:** run network work in a worker thread. Push UI updates with `GLib.idle_add`. Handle SIGTERM with `GLib.unix_signal_add` so `systemctl --user stop` quits cleanly.
3. **Autostart:** `graphical-session.target` is **inactive** under Xfce, so a `WantedBy=graphical-session.target` unit never starts. Use `~/.config/autostart/<app>.desktop` with:
   `Exec=systemd-run --user --unit=<app> --collect -p Restart=on-failure -p RestartSec=10 -p SyslogIdentifier=<app> --setenv=DISPLAY --setenv=XAUTHORITY --setenv=DBUS_SESSION_BUS_ADDRESS --setenv=XDG_RUNTIME_DIR -- <abs launcher> run`
   This gives journal logs (`journalctl --user -t <app>`), restart on crash, and a unit-name clash that blocks a second instance. `.desktop` `Exec` does not expand `~`, so write absolute paths at install time.
4. **Node from autostart:** autostart has no nvm PATH. `install`, run from an interactive shell, records `shutil.which("node")` in a config file.
5. **Playwright browser revision drift:** `playwright-core/browsers.json` may name a Chromium revision (e.g. 1247) that is not installed (1248 present). Pass `executablePath` = newest `~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome`. Use the same full Chrome for headed sign-in and headless renewal, so the persistent profile is never opened by two different builds.
6. **SSO session:** `chromium.launchPersistentContext(profileDir, {headless})`. Start at the app's SSO start URL (find the "Sign in with Microsoft" link target; the plain `/login` page does not redirect). `waitForURL` back on the app host. Export `context.cookies(base)` to a 0600 JSON. The Python side loads it into `http.cookiejar` and saves rotated cookies back after each request. Headless renewal worked silently after the user answered "Yes" to "Stay signed in?".
7. **Serialize browser runs:** headed and headless share one profile. Guard them with one lock.

## Pitfalls

- After a failed sync, clear the "last sync" timestamp. Otherwise the next poll short-circuits to "no change" and shows green.
- In needs-sign-in state, do not relaunch the headless browser every poll. Retry only on a manual trigger or when the cookie file mtime changes.
- `ip -o monitor address route` sees IPv6 temp-address churn without root. Coalesce with an earliest-deadline-wins debounce so a steady event stream cannot postpone the poll.

## Test the tray without clicking

```bash
gdbus call --session -d org.kde.StatusNotifierWatcher -o /StatusNotifierWatcher \
  -m org.freedesktop.DBus.Properties.Get org.kde.StatusNotifierWatcher RegisteredStatusNotifierItems
# -> ':1.N/org/ayatana/NotificationItem/<id>'
gdbus call --session -d :1.N -o /org/ayatana/NotificationItem/<id>/Menu \
  -m com.canonical.dbusmenu.GetLayout -- 0 -1 "['label']"          # labels + item ids
gdbus call --session -d :1.N -o /org/ayatana/NotificationItem/<id>/Menu \
  -m com.canonical.dbusmenu.Event -- <item-id> clicked "<int32 0>" 0   # click an item
```

Use `--` before the arguments, because `-1` otherwise parses as an option. Icon state: `Properties.Get org.kde.StatusNotifierItem IconName`. Panel screenshot: `import -window root` then crop the panel strip.
