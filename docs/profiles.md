# Profiles

A profile is an instantiated vendor instance, not just a skill set. The **type**
(`profiles/enonic.json`, `profiles/php.json`, …) is the template. The
**instance name** is yours: `dummy` can be an Enonic-typed profile, and no
other profile — of any type — may reuse that name.

```bash
./devkit profile create dummy --type enonic --apply
./devkit profile create enonic --apply          # name-equals-type still works
```

Creating one gives you a config directory, a projected skill set, a uniquely
named CLI wrapper, a launcher, an icon colour, and (in Claude Code) a name that
shows up in the status line. Launchers and forks are written only for a vendor
whose stock GUI is installed (otherwise `create` prints `skip   desktop <vendor>
(GUI not installed)` and the instance stays CLI-only) and only when the profile
is not headless. Several profiles can run at once. Each desktop is a fork of the
stock app (its own copy under `/usr/lib/devkit/`, patched `desktopName` /
`WM_CLASS`, stock icons badged with a coloured shield). Stock Claude, ChatGPT,
and Cursor stay as they are. The fork is rebuilt after apt/dpkg updates of the
original package.

`create` / `sync` / `install.py --apply` write user-owned files first. Then, if
that profile's desktop fork is missing or stale or the apt/dpkg hooks are not
installed, they print the rsync/asar/hook plan and ask `sudo` (on a terminal;
without one, `pkexec`, else `sudo -A`; with none of them the step fails with
`pkexec and sudo are not on PATH`); otherwise they stop there. A failed or
cancelled elevation does not fail the command: it prints `note: desktop forks
were not applied (exit N)` and exits 0, so run `devkit doctor` to see it. `install.py --apply` on a terminal, with no profiles yet, offers to
create a first one (type, then name) unless you passed `--profile` or `--name`.
Without a terminal it creates the `--profile` type (default `core`) under that
same name.

A profile is not the only way to give a repo the harness: `devkit project build`
links skills and an `AGENTS.md` into the repo itself. See [project.md](project.md).

```bash
./devkit profile apps-sync --user "$USER" --install-hook --apply
```

## Syncing sessions between profiles

`devkit profile session-sync` copies agent sessions from one instance to another.
Names are installed profiles, or `stock` for the unprefixed installs
(`~/.config/Claude`, `~/.claude`, `~/.codex`, `~/.config/Cursor`). One direction
per run; swap the two names for the other way. `--agent` takes a comma-separated
list (`claude`, `codex`, `cursor`) or `all` for every agent both sides have; the
default is `claude`. Each agent is copied from the source's instance into the
target's instance of the same agent, and a profile that lacks that instance is
refused.

```bash
devkit profile session-sync --source stock --target dummy            # dry run
devkit profile session-sync --source stock --target dummy --apply
devkit profile session-sync --source dummy --target other --agent claude,codex,cursor --apply
devkit profile session-sync --source dummy --target other --agent all
```

Common rules. A file or row is copied when the target lacks it or the source
copy is newer. Nothing is deleted and a newer target is never overwritten, but
an older target is replaced and the old version is not kept (Codex is narrower;
see below). SQLite databases are backed up beside themselves
(`<name>.devkit-backup-<timestamp>`) before the first write, and the command
refuses unless there is free space for 1.1 times the database. Backups are never
pruned; remove old ones yourself. The dry run prints counts per agent and names
apps that would block `--apply`: quit the agents' apps on the target first.
Stock and a profile are often different accounts; copied Claude Desktop chats
then appear under the target's account, and the command prints a note.

What each agent copies:

- **claude**: Code transcripts (every file under `<config dir>/projects`) and
  Desktop chats (the `local_*.json` index files, written into the target's own
  organization folder, the only one its sidebar lists). The target must have
  signed in and started one chat first, or the command refuses.
  `scheduled-tasks.json` is not copied. `--only code|desktop` limits it.
  `--indexeddb` also replaces the target's Desktop IndexedDB (claude.ai web
  history); it replaces, never merges, keeps the old one beside it, and needs the
  source Desktop quit too. Cookies and `.claude.json` trust flags are not copied.
- **codex**: rollout files under `sessions/` and `archived_sessions/`, the
  `threads` rows in `state_N.sqlite` that list them (paths rewritten to the
  target home; project and section ids left unset), and `session_index.jsonl`.
  For a thread the target already has, a newer source only moves its
  `updated_at` columns forward; the rest of the row stays the target's.
  `session_index.jsonl` gains the ids it lacks and existing lines are never
  rewritten. The history projection database is not copied; Codex rebuilds it.
  Threads merge only into a target database with the same `state_N.sqlite` name
  as the source's newest; without one only the files are copied and Codex
  indexes them on its first start.
- **cursor**: IDE chats. For each chat the target lacks or has older, its
  `composerHeaders` row and its `cursorDiskKV` rows (`composerData`, `bubbleId`,
  `checkpointId`, `codeBlockDiff`, and the other per-chat families) are copied in
  one transaction; the source database is opened read-only. The target must have started once so its `state.vscdb` exists. The
  content-addressed rows (`agentKv:blob:*`, `composer.content.*`) and the
  per-workspace databases are not copied, because their keys name no chat. A chat
  may not list under a folder until that folder is opened in the target. The
  backup copies the whole target database, so the target needs that much free
  disk again.

## What gets created

```
~/.agents-profiles/<profile>/            # the profile root
~/.agents-profiles/<profile>/hooks       # per-file links into kit hooks/ + statusline
~/.agents-profiles/<profile>/agents      # AGENTS_HOME: ~/.agents-shaped tree
    skills/  rules/  kb/                 # this profile's subset, not siblings'
    bin/ bin-vendor/ benchmarks/         # symlinks into kit core/ (tools and the
    mcp/ share/ config                   # bench inputs, read-only); a
                                         # client_overlay profile gets a real config/
                                         # with client-overlay.json beside the links;
                                         # written once with placeholders, kept by sync
    hooks -> <profile root>/hooks        # absolute link
    prds/ plans/ .playwright-mcp/        # profile-local state
    .auth/                               # profile-local; token YAML may be shared
~/.agents-profiles/<profile>/<vendor>/   # the vendor's config dir
    skills/  rules/  kb/                 # per-entry symlinks into the kit home's core/;
                                         # an entry narrowed by a deeper entry or a
                                         # <layer>_excludes path is a real dir of finer links
    hooks -> <profile root>/hooks        # absolute link
    .devkit-profile.json                 # provenance
    settings.json hooks.json config.toml mcp.json   # per vendor, as that vendor uses them
    .claude.json                         # Claude only: MCP servers, merged not replaced
~/.agents-profiles/<profile>/<vendor>-data/   # vendor data dir (Cursor extensions, ...)
~/.config/Claude-<profile>/              # Claude Desktop Chromium profile
~/.config/Codex-<profile>/               # ChatGPT Desktop Chromium profile
~/.agents-profiles/<profile>/cursor      # Cursor IDE --user-data-dir (not ~/.config)
~/.local/bin/<vendor>-<profile>          # public wrapper (not a stock name)
~/.local/bin/devkit  devkit-uninstall.sh # kit link and the uninstaller (see install.md)
~/.agents-profiles/<profile>/bin/<cli>   # unprefixed vendor CLI + agentctl
~/.local/share/applications/...          # launcher (Exec is the fork)
~/.local/share/icons/hicolor/<size>/apps/<vendor>-<profile>.png   # badged, 16 to 512
/usr/lib/devkit/<vendor>-<profile>/      # identity fork (root, apt-rebuilt)
```

Layers are projected as **symlinks**, not copies, and they point into the kit
home (`~/.local/share/devkit/current/core/`), not into the checkout. `create`,
`sync` and `install.py --apply` first install the payload as a release there;
editing `core/` in the checkout reaches no profile until one of them, or
`devkit update apply`, installs a new release. Every profile then shares the one
copy, so the harness side of a profile costs kilobytes. The desktop fork is the
exception: a full rsync of the stock app so identity can be patched. Cheap
gates skip that copy when the fork's version and `desktopName` already match.

## Commands

```bash
./devkit profile list                    # installed instances (name + type)
./devkit profile show dummy            # the instance, or a type if not installed
./devkit profile create dummy --type enonic --apply
./devkit profile create enonic --apply
./devkit profile sync dummy --apply    # after a manifest change
./devkit profile adopt mine --vendor claude --type core --config-dir ~/.agents-profiles/mine/claude --apply
./devkit profile auth restore            # put stock URL handlers back
./devkit profile session-sync --source stock --target dummy --agent all --apply   # copy sessions
./devkit profile apps-sync --user "$USER" --apply   # prints plan, then sudo
./devkit profile migrate dummy --to-fork devkit --apply  # re-home onto another fork id
```

Every command that writes is a dry run without `--apply`; `list` and `show` only read.
`list` prints one row per vendor instance (PROFILE, TYPE, VENDOR, STATE, CONFIG
DIR), or `no installed profiles.`

## Composition

`extends` composes parent-first. Lists concatenate and drop duplicates;
`instances`, `color`, `settings`, `client_overlay` and `todo` are replaced by the
child; other maps merge key by key, the child winning.

That distinction matters: a PHP profile declaring `claude` and `codex` means
exactly those two vendors, not those two plus whatever `core` happened to
declare.

Layer lists can be literal, or an `@allowlist:` reference:

```json
"skills": "@allowlist:skills.core"
```

The reference points into `export-allowlist.json`, so the export boundary and
the profile manifest cannot disagree about what a layer contains. There is one
list, and the profile names it.

## The `extract` type

`extract` is a slim type for headless images that run extract-kit. It does
not extend `core`: `bootstrap.sh` installs every dependency a profile declares,
and `core` declares 34 entries (40 binaries). `extract` carries only git,
python3, a C toolchain, node, graft, serena, graphify, `playwright-cli` (optional)
and 7z, plus the `graft` and `playwright-cli` skills, the `implementation/**`
kb and the Serena MCP. Its layer lists are literal and it sets no `settings`.
graft, serena, graphify, node and `playwright-cli` are pinned so an image build
is reproducible. Install it with `./bootstrap.sh --profile extract --apply`
then `./install.py --profile extract --headless --apply`.

## MCP

The profile `mcp` list is the default-alive set, matching the reference
Cursor / Claude / Codex configs. **Always on:** `context7` and `serena` (every
profile); `gitlab` on Enonic and above; `atlassian-rovo-preview` on
`client`. **Parked** (catalog `parked`, snippets under
`$HOME/.agents/.auth/mcp-on-demand/`): Slack, the Playwright stub, and
browser-control. Graft has no MCP server at all (catalog `skip`): it is the CLI
plus `graft.mdc`. Playwright is spawned per task id (`playwright.py spawn
<id> --enable`), not registered as a stub. From a profile, `--enable` writes
`playwright-<id>` only onto that profile's Cursor/Claude/Codex MCP files
(and does not touch stock `~/.cursor` / `~/.claude` / `~/.codex` or sibling
profiles). From the host harness, it still fans out to stock configs and every
provenance-marked instance. Sync keeps every entry already in the instance's MCP
file that the profile list does not name, except parked names. That covers the
spawned `playwright-<id>` entries, and also a server you removed from the list:
delete it from the instance file by hand. Slack is
on-demand for worklogs.

## Colour

A profile type may declare `color` (`light` / `dark`). On
`devkit profile create`, the instance gets a unique badge colour:

1. `--color '#RRGGBB'` if passed (any hex; not limited to the palette)
2. else the type's `color.light` when no other installed profile uses it
3. else a random free entry from the 16-colour palette (vivid on black)

Colours are unique across profiles, the same way names are: a collision
refuses create. Sync keeps the colour written into provenance at create time;
it does not re-roll.

Icons keep the stock artwork. A shield emblem from
`templates/icons/profile-emblem.png` is resized to the icon canvas (shield in
the top-left corner, rest transparent), its black fill is tinted to the
profile colour (white rim kept), and it is composited over the original. A
full-bleed icon (opaque art touching all four edges, such as Claude's in-tree
`resources/icon.png`) is first shrunk to 84% and centred, the margin the stock
hicolor icons have, so the shield overhangs the tile instead of covering it;
tray icons are never shrunk. The
same badge is applied to launcher icons, written at 16, 32, 48, 128, 256 and
512 px under `~/.local/share/icons/hicolor/<size>x<size>/apps/` (GTK ignores a
1024 px file in `512x512/`), and to in-tree icons inside `/usr/lib/devkit/<vendor>-<profile>/`. Badging needs
ImageMagick (`magick`, else `convert`). If Magick or the emblem is missing the
launcher keeps the previous badge, or falls back to the stock icon when there
is none, and says so — it does not fail the install. After writing launchers the kit rebuilds `icon-theme.cache` there with
`gtk-update-icon-cache` (or `gtk4-update-icon-cache`); without it GNOME can keep
showing the stock icon. The apt/dpkg hook installs a copy of the emblem at
`/usr/lib/devkit/profile-emblem.png` for the root worker.

A headless instance (`--headless`, see [install.md](install.md#headless-and-containers))
has no colour: no `--color`, no `color` in provenance, no badge.

## Adopting an existing setup

`profile adopt` records a directory you already have as an instance. It writes
one provenance file and relocates nothing:

```bash
./devkit profile adopt mine --vendor claude --type core \
    --config-dir ~/.agents-profiles/mine/claude --apply
```

The directory must already sit at `~/.agents-profiles/<name>/<dir>`, because
that is the only place `profile list`, `doctor`, `sync` and `update` look for
instances. Anywhere else (a stock `~/.claude`, say) is refused: the provenance
file would land in a directory devkit never reads again. Re-running it is a
no-op.

## Home-root instruction files

Claude Code and Codex collect instruction files by walking up from the working
directory to `$HOME`. So a populated `~/CLAUDE.md` loads *in addition to*
`~/.claude/CLAUDE.md` — and because it sits outside every profile's config
directory, it leaks into all of them at once. A PHP profile would inherit the
Enonic and Jira rules through it no matter how cleanly the profile-scoped rules
are split.

`install.py` and `devkit doctor` report this; they never move your files
silently. `install.py --fix-home-rules` does the same move as part of an install.
To fix it on its own:

```bash
./devkit fix-home-rules --apply
```

That backs the file up, moves its content into the vendor's config directory,
and leaves a 1-byte mode-`000` stub at the home root. The stub is deliberate: a
deleted file gets recreated by the next vendor update, whereas an unreadable
stub survives and keeps failing closed. Re-running is a no-op.

If the vendor file already exists, `fix-home-rules` aborts and names it;
`--force` appends under a marked block rather than overwriting.

## Stock apps and profile forks

Stock Claude, ChatGPT/Codex, and Cursor stay launchable from their own
`.desktop` files. The kit never writes those trees.

Each profile desktop is a dpkg-unowned rsync copy of the stock app. Claude and
Codex get `desktopName` patched in `app.asar`; Cursor has no asar, so
`desktopName` is patched in `resources/app/package.json` and `nameShort` plus
`linuxIconName` in `product.json`. In-tree icons are badged from **stock**
assets with a coloured shield emblem, and `chrome-sandbox` keeps mode `4755`.
When `/etc/apparmor.d/abi/4.0` exists, each fork also gets an unconfined
AppArmor profile with `userns` at `/etc/apparmor.d/devkit-<vendor>-<profile>`,
loaded with `apparmor_parser` when AppArmor is enabled; the worker logs to
`/var/log/devkit-profile-apps.log`. Apt only updates stock, so a pair of hooks
rebuild every fork afterwards:

- `/etc/apt/apt.conf.d/99-devkit-profile-apps` (`DPkg::Post-Invoke`)
- `/etc/dpkg/dpkg.cfg.d/60devkit-profile-apps` (`post-invoke` — apt's hook does
  not run for bare `dpkg -i`)

The worker is `/usr/local/bin/sync-devkit-profile-apps.py` (a copy, not a home
symlink). Failure must not fail apt (`|| true`). Cheap gates skip the copy when
the fork's version already matches stock **and** the patched identity is in
place. Do not edit vendor `postinst` files; they are rewritten on every
`configure`.

Config, skills, wrappers, and session data live under `~/.agents-profiles` and
(for Claude/Codex desktops) `~/.config/Claude-<name>` / `~/.config/Codex-<name>`
— package upgrades never touch them. Stock `~/.config/Claude` and
`~/.config/Cursor` stay the stock apps.

A headless instance has no forks: `finish_appforks`, `apps-sync` and the apt
hook worker skip it, and `DEVKIT_HEADLESS=1` makes `profile apps-sync` a no-op.

## Desktop user-data

A profile named `dummy` splits harness config from the desktop user-data dir.
It is not a fake `$HOME`:

| | Profile `dummy` |
|---|---|
| Harness / CLI | `~/.agents-profiles/dummy/<vendor>` |
| Claude Desktop | `~/.config/Claude-dummy` |
| ChatGPT Desktop | `~/.config/Codex-dummy` (`CODEX_ELECTRON_USER_DATA_PATH`) |
| Cursor IDE | `--user-data-dir=~/.agents-profiles/dummy/cursor` |

`$HOME`, `~/.ssh`, `~/.gitconfig`, and `~/Workspace` stay the real ones.
`cursor-agent` sets `XDG_CONFIG_HOME` on its exec line only and never exports it.

From a terminal, call the public wrapper (`claude-dummy`). It execs the stock
CLI by full path, exports `DEVKIT_PROFILE`, `DEVKIT_PROFILE_HOME`, `AGENTS_HOME`,
`GRAFT_NO_GITIGNORE` and `GRAFT_NO_IGNORE` (plus `CLAUDE_CONFIG_DIR` or
`CODEX_HOME`; the Cursor wrapper sets `CURSOR_DATA_DIR` and
`CURSOR_WORKTREES_ROOT` on its exec line), and prepends
`~/.agents-profiles/<name>/bin/` to `PATH`. That directory has the unprefixed
vendor names (`claude`, `codex`, `cursor-agent`) and harness tools (`agentctl`)
that pin the same env. PATH alone is not enough: `agentctl` reads `AGENTS_HOME`
(this profile's `agents/` tree), not `$HOME/.agents`, so it cannot see sibling
profiles' skills, plans, or Playwright instances. The desktop launcher binds
the same env before exec so the GUI and its integrated terminals inherit it.

Profile launchers and the auth dispatcher also set `XDG_CURRENT_DESKTOP` with
`GNOME` appended, for example `XFCE:GNOME`. Claude Desktop draws its white
tray glyph only when that list names GNOME or its own theme is dark, so
without it a light GTK theme on a dark panel shows a black glyph. A blank
value falls back to `XDG_SESSION_DESKTOP`, then `DESKTOP_SESSION`. Stock
vendor launchers are not touched.

## URL-redirect auth

Linux allows one default handler per URL scheme (`claude://`, `claude-cli://`,
`codex://`, `codex-browser-sidebar://`, `cursor://`). Profile launchers do not
claim those schemes. On create/sync the kit installs a `NoDisplay` dispatcher
and sets it as the default. Starting a profile's GUI records a pending marker
so the browser callback returns to that profile; the marker expires after 30
minutes. Without a live marker the dispatcher routes the callback to the one
running profile of that vendor. With more than one running it refuses
(`ambiguous <scheme>:// callback`), and with none it refuses (`no profile claimed
this <scheme>:// callback`), rather than guessing. A refusal also raises a
desktop notification.

```bash
./devkit profile auth restore --apply    # stock handlers again
./devkit doctor                          # reports whether the dispatcher is default
```
