# Troubleshooting

Refusal messages in this kit name the command that fixes them. If one sent you
here, find it below.

## `refusing to write configuration as root`

`install.py` and `devkit` write configuration as your own user. Run without
`sudo`, or name the account:

```bash
sudo ./install.py --profile enonic --user yourname --apply
```

`refusing to install for uid 0` and `refusing to install into /root` have no
override. Name a real user account.

## `<path> exists and was not written by devkit`

The kit will not overwrite a file it did not create. Look at the file. If you
want it replaced, `--force` backs it up first, timestamped, beside the original.

## `core/ has not been exported yet`

```bash
./devkit export --apply
```

## `<profile>/<vendor>: stale`

The kit moved on since that instance was installed:

```bash
./devkit profile sync <profile> --apply
```

## `N path(s) not owned by you`

Something was installed with `sudo` that should not have been. Fix the
ownership, then stop doing that:

```bash
sudo chown -R "$(id -u)" ~/.agents-profiles/<profile>/<vendor>
```

## `home-root CLAUDE.md is populated`

`~/CLAUDE.md` and `~/AGENTS.md` load in addition to the config-dir versions,
because both vendors walk up to `$HOME` collecting instruction files. Sitting
outside every profile, they leak into all of them at once.

```bash
./devkit fix-home-rules --apply
```

The kit never moves those files silently. See
[profiles.md](profiles.md#home-root-instruction-files).

## `<profile>/<vendor>: app fork missing` / `app fork stale`

The launcher points at `/usr/lib/devkit/<vendor>-<profile>/`, which is a
dpkg-unowned copy of the stock app. Create it, or rebuild it after an apt
update of Claude / ChatGPT / Cursor:

```bash
./devkit profile apps-sync --user "$USER" --install-hook --apply
```

That prints the plan, then asks `sudo` for a password. The hooks
(`99-devkit-profile-apps` and `60devkit-profile-apps`) do the same after
future package updates. They do not replace the Cursor recolor hooks. Config
under `~/.agents-profiles` is not involved.

## `could not badge <vendor> icon`

ImageMagick is missing (the kit tries `magick`, else `convert`), or the shield
emblem is missing (`templates/icons/profile-emblem.png`, or the installed copy
at `/usr/lib/devkit/profile-emblem.png`). This is a warning: the launcher falls
back to the stock icon and the install completes.

## `lint-paths: N violation(s)`

See [paths.md](paths.md). The short version: `~` does not expand in a parsed
value, so use `${HOME}` there.

If a violation is a false positive, add it to the `allow` map in
`path-contract.json` against the specific rule id, with the reason. Do not
disable the rule.

## `gitleaks found N finding(s) in the export`

Something in `core/` looks like a credential. Read the findings before anything
else. If they are genuinely false positives, allowlist them in `.gitleaks.toml`
scoped as tightly as the finding allows — by path *and* by pattern — so the rule
keeps working everywhere else.

## `agentctl` sees every profile's skills

The host shim at `~/.local/bin/agentctl` reads `$HOME/.agents` unless
`AGENTS_HOME` is set. Start the session through the profile wrapper
(`claude-dummy`) or the desktop launcher so `DEVKIT_PROFILE` / `AGENTS_HOME` and
the profile `bin/` are on `PATH`. After a kit update that added those wrappers:

```bash
./devkit profile sync dummy --apply
```

## Graft MCP is missing from a new profile

That is the default. Graft is **parked** (CLI + `graft.mdc` stay). The live MCP
set is `context7`, plus `gitlab` on Enonic and `atlassian-rovo-preview` on
`client`. See [profiles.md](profiles.md#mcp).

## Login opened the wrong app (or nowhere)

Browser OAuth returns through `claude://`, `codex://` or `cursor://`. Linux has
one default handler per scheme. The kit's dispatcher should own those defaults
after `profile create` / `profile sync`. Start login from that profile's
launcher so a pending marker is written; `devkit doctor` reports the current
handler.

```bash
./devkit doctor
./devkit profile sync dummy --apply
./devkit profile auth restore --apply    # back to stock handlers
```

### `ambiguous …:// callback`

More than one copy of that vendor is running and nothing wrote a pending marker.
Close the extras, or start login again from one profile's launcher.

### `no profile claimed this …:// callback`

No pending marker and no running profile GUI for that vendor. Open the
profile's desktop launcher (or CLI) and start login from there.

## `sudo is not on PATH`

Desktop forks and package installs need `sudo` on a terminal, or `pkexec` /
`sudo -A` when stdin and stdout are not terminals. Install one of those, or
re-run the printed commands as root. The plan is always printed before that
prompt; a cancelled password leaves user-owned config in place. The elevated
command is the start (`bootstrap.sh --apply`) or the end
(`devkit profile apps-sync --apply`), so it can be run on its own.

## Codex warns about helper binaries under a temporary directory

```
Refusing to create helper binaries under temporary dir
```

`CODEX_HOME` is pointing somewhere under `/tmp`. Real profiles live under
`~/.agents-profiles/`, so this only appears in test harnesses. Codex warns and
proceeds; the install is degraded, not failed.

## A projected skill directory is a real directory

```
error: <path> is a real directory, not a projection
```

Something replaced a symlink with actual content. Move it aside by hand and
re-run `profile sync`. The kit will not delete a real directory it did not
create.
