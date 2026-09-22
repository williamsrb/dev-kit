---
id: how-to-dispatch-linux-vendor-auth-callbacks
when_skills: [run-plan]
inputs: [xdg-open, ~/.agents-profiles, ~/.local/share/applications]
outputs: [devkit-auth-<scheme>.desktop, pending-auth.json]
stop_if: [inventing per-profile OAuth URI schemes]
read: section
prose: caveman-lite
---

# Dispatch Linux vendor auth callbacks across profiles

Linux allows **one** `xdg-mime` default per `x-scheme-handler/<scheme>`. Vendor
login URLs (`claude://`, `claude-cli://`, `codex://`,
`codex-browser-sidebar://`, `cursor://`) cannot be forked per profile.

## Prerequisites

- Profile copies share the vendor binary (Tier 2). Distinct dock icons need an
  install fork under `/usr/lib/devkit/`; that does not fix scheme ownership.
- Tests that call `xdg-mime` must pass `HOME` / `XDG_CONFIG_HOME` /
  `XDG_DATA_HOME` for the fake home, or they rewrite the operator's
  `mimeapps.list`.

## Procedure

1. Install one `NoDisplay` `.desktop` per scheme. Set it as the `xdg-mime`
   default. Do **not** put `x-scheme-handler/*` on per-profile launchers
   (Cursor may keep `application/x-cursor-workspace`).
2. Profile GUI `Exec` goes through a launch wrapper that writes a pending
   marker `{profile, vendor, at}` under `~/.local/state/devkit/` (TTL ~30 min).
3. On `xdg-open <scheme>://…`, the dispatcher routes: pending marker for that
   vendor → else exactly one running instance → else refuse and log (no stdin
   chooser; a `NoDisplay` handler has no TTY).
4. Snapshot the previous default before claiming the scheme. Restore puts that
   handler back (stock ids if none was recorded).
5. ChatGPT Desktop isolation is two variables: `CODEX_HOME` (config) and
   `CODEX_ELECTRON_USER_DATA_PATH` (Electron userData / single-instance lock).

## Pitfalls

- `StartupWMClass=` only matches. The process still emits asar `desktopName`
  / Cursor `product.json`. Same binary → dock grouping.
- One handler for `claude://` still cannot multiplex N profiles.
- `xdg-mime default` follows process `HOME`, not a Python `home=` argument,
  unless you pass the env explicitly.
