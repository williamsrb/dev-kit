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
named CLI wrapper, a launcher, an icon colour, and a name that shows up in the
status line. Several profiles can run at once. Each desktop is a Personal-style
fork of the stock app (its own copy under `/usr/lib/devkit/`, patched
`desktopName` / `WM_CLASS`, stock icons badged with a coloured shield). Stock Claude, ChatGPT,
Cursor, and Claude Personal stay as they are. The fork is rebuilt after apt/dpkg
updates of the original package.

`create` / `sync` / `install.py --apply` write user-owned files first, then
print the rsync/asar/hook plan and ask `sudo`. `install.py --apply` with no
profiles yet offers to create a first one (type, then name) unless you passed
`--profile` or `--name`.

```bash
./devkit profile apps-sync --user "$USER" --install-hook --apply
```

## What gets created

```
~/.agents-profiles/<profile>/            # the profile root
~/.agents-profiles/<profile>/hooks       # per-file links into kit hooks/ + statusline
~/.agents-profiles/<profile>/agents      # AGENTS_HOME: ~/.agents-shaped tree
    skills/  rules/  kb/                 # this profile's subset, not siblings'
    bin/ mcp/ share/ config              # symlinks into kit core/ (tools only)
    hooks -> ../hooks
    prds/ plans/ .playwright-mcp/        # profile-local state
    .auth/                               # profile-local; token YAML may be shared
~/.agents-profiles/<profile>/<vendor>/   # the vendor's config dir
    skills/  rules/  kb/                 # per-entry symlinks into kit core/
    hooks -> ../hooks
    .devkit-profile.json                 # provenance
~/.config/Claude-<profile>/              # Claude Desktop Chromium profile
~/.config/Codex-<profile>/               # ChatGPT Desktop Chromium profile
~/.agents-profiles/<profile>/cursor      # Cursor IDE --user-data-dir (not ~/.config)
~/.local/bin/<vendor>-<profile>          # public wrapper (not a stock name)
~/.agents-profiles/<profile>/bin/<cli>   # unprefixed vendor CLI + agentctl
~/.local/share/applications/...          # launcher (Exec is the fork)
~/.local/share/icons/.../...png          # stock icon + coloured shield badge
/usr/lib/devkit/<vendor>-<profile>/      # identity fork (root, apt-rebuilt)
```

Layers are projected as **symlinks**, not copies. An update to `core/` therefore
reaches every profile without a re-copy, and the harness side of a profile
costs kilobytes rather than a duplicate of a 20M tree. The desktop fork is the
exception: a full rsync of the stock app so identity can be patched. Cheap
gates skip that copy when the fork's version and `desktopName` already match.

## Commands

```bash
./devkit profile list                    # installed instances (name + type)
./devkit profile show dummy            # the instance, or a type if not installed
./devkit profile create dummy --type enonic --apply
./devkit profile create enonic --apply
./devkit profile sync dummy --apply    # after a manifest change
./devkit profile adopt core --vendor claude --config-dir ~/.claude --apply
./devkit profile auth restore            # put stock URL handlers back
./devkit profile apps-sync --user "$USER" --apply   # prints plan, then sudo
```

Every one of these is a dry run without `--apply`.

## Composition

`extends` composes parent-first. Lists concatenate; `instances`, `color`,
`settings` and `client_overlay` are replaced by the child.

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

## MCP

The profile `mcp` list is the default-alive set, matching the reference
Cursor / Claude / Codex configs. **Always on:** `context7` (every profile);
`gitlab` on Enonic and above; `atlassian-rovo-preview` on `client`.
**Parked** (catalog `parked`, snippets under `$HOME/.agents/.auth/mcp-on-demand/`):
graft, Slack, the Playwright stub, and browser-control. Graft stays the CLI
plus `graft.mdc`. Playwright is spawned per task id (`playwright.py spawn
<id> --enable`), not registered as a stub. From a profile, `--enable` writes
`playwright-<id>` only onto that profile's Cursor/Claude/Codex MCP files
(and does not touch stock `~/.cursor` / `~/.claude` / `~/.codex` or sibling
profiles). From the host harness, it still fans out to stock configs and every
provenance-marked instance. Sync keeps those spawned entries. Slack is
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
the top-left quarter, rest transparent), its black fill is tinted to the
profile colour (white rim kept), and it is composited over the original. The
same badge is applied to launcher icons under `~/.local/share/icons` and to
in-tree icons inside `/usr/lib/devkit/<vendor>-<profile>/`. Badging needs
ImageMagick (`magick`, else `convert`). If Magick or the emblem is missing the
launcher falls back to the stock icon and says so — it does not fail the
install. The apt/dpkg hook installs a copy of the emblem at
`/usr/lib/devkit/profile-emblem.png` for the root worker.

## Adopting an existing setup

`profile adopt` records a directory you already have as an instance. It writes
one provenance file and relocates nothing:

```bash
./devkit profile adopt core --vendor claude --config-dir ~/.claude --apply
```

Re-running it is a no-op.

## Home-root instruction files

Claude Code and Codex collect instruction files by walking up from the working
directory to `$HOME`. So a populated `~/CLAUDE.md` loads *in addition to*
`~/.claude/CLAUDE.md` — and because it sits outside every profile's config
directory, it leaks into all of them at once. A PHP profile would inherit the
Enonic and Jira rules through it no matter how cleanly the profile-scoped rules
are split.

`install.py` and `devkit doctor` report this; they never move your files
silently. To fix it:

```bash
./devkit fix-home-rules --apply
```

That backs the file up, moves its content into the vendor's config directory,
and leaves a 1-byte mode-`000` stub at the home root. The stub is deliberate: a
deleted file gets recreated by the next vendor update, whereas an unreadable
stub survives and keeps failing closed. Re-running is a no-op.

If the vendor file already exists, `fix-home-rules` aborts and names it;
`--force` appends under a marked block rather than overwriting.

## Stock apps, Claude Personal, and profile forks

Stock Claude, ChatGPT/Codex, Cursor, and Claude Personal stay launchable from
their own `.desktop` files. The kit never writes those trees.

Each profile desktop is a dpkg-unowned rsync copy of the stock app, the same
recipe as Claude Personal: patch `desktopName` in `app.asar` (Cursor also
patches `nameShort` in `product.json`), badge in-tree icons from **stock**
assets with a coloured shield emblem, keep `chrome-sandbox` mode `4755`. Apt
only updates stock, so a pair of hooks rebuild every fork afterwards:

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
— package upgrades never touch them. Stock `~/.config/Claude`,
`~/.config/ClaudePersonal`, and `~/.config/Cursor` stay the stock/Personal apps.

## Desktop user-data (same idea as Claude Personal)

Claude Personal is `CLAUDE_CONFIG_DIR=~/.claude_personal` plus
`--user-data-dir=~/.config/ClaudePersonal`. A profile named `dummy` is the same
split, not a fake `$HOME`:

| | Claude Personal | Profile `dummy` |
|---|---|---|
| Harness / CLI | `~/.claude_personal` | `~/.agents-profiles/dummy/<vendor>` |
| Claude Desktop | `~/.config/ClaudePersonal` | `~/.config/Claude-dummy` |
| ChatGPT Desktop | n/a | `~/.config/Codex-dummy` (`CODEX_ELECTRON_USER_DATA_PATH`) |
| Cursor IDE | n/a | `--user-data-dir=~/.agents-profiles/dummy/cursor` |

`$HOME`, `~/.ssh`, `~/.gitconfig`, and `~/Workspace` stay the real ones.
`cursor-agent` sets `XDG_CONFIG_HOME` on its exec line only and never exports it.

From a terminal, call the public wrapper (`claude-dummy`). It execs the stock
CLI by full path, exports `DEVKIT_PROFILE` and `AGENTS_HOME`, and prepends
`~/.agents-profiles/<name>/bin/` to `PATH`. That directory has the unprefixed
vendor names (`claude`, `codex`, `cursor-agent`) and harness tools (`agentctl`)
that pin the same env. PATH alone is not enough: `agentctl` reads `AGENTS_HOME`
(this profile's `agents/` tree), not `$HOME/.agents`, so it cannot see sibling
profiles' skills, plans, or Playwright instances. The desktop launcher binds
the same env before exec so the GUI and its integrated terminals inherit it.

## URL-redirect auth

Linux allows one default handler per URL scheme (`claude://`, `claude-cli://`,
`codex://`, `codex-browser-sidebar://`, `cursor://`). Profile launchers do not
claim those schemes. On create/sync the kit installs a `NoDisplay` dispatcher
and sets it as the default. Starting a profile's GUI records a pending marker
so the browser callback returns to that profile. If nothing claimed the
callback and more than one copy is running, the dispatcher refuses rather than
guessing.

```bash
./devkit profile auth restore --apply    # stock/Personal handlers again
./devkit doctor                          # reports whether the dispatcher is default
```
