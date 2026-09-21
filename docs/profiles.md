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
`desktopName` / `WM_CLASS`, recoloured in-app icons). Stock Claude, ChatGPT,
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
~/.agents-profiles/<profile>/core        # symlink to the kit's core/
~/.agents-profiles/<profile>/<vendor>/   # the vendor's config dir
    skills/  rules/  kb/                 # per-entry symlinks into core/
    .devkit-profile.json                 # provenance
~/.config/<Vendor>-<profile>/            # GUI user-data dir
~/.local/bin/<vendor>-<profile>          # public wrapper (not a stock name)
~/.agents-profiles/<profile>/bin/<cli>   # unprefixed name for the GUI PATH
~/.local/share/applications/...          # launcher (Exec is the fork)
~/.local/share/icons/.../...png          # recoloured launcher icon
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

## Colour

A profile may declare `color`. If it does not, a hue is derived
deterministically from the profile name, so two profiles never collide by
accident and a given name always gets the same colour on every machine.

Icon recolouring needs ImageMagick. Version 7 ships `magick` and may not ship
`convert`, so the kit tries `magick` first. If neither is present the launcher
falls back to the stock icon and says so — it does not fail the install.

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
patches `nameShort` in `product.json`), recolor in-tree icons from **stock**
assets, keep `chrome-sandbox` mode `4755`. Apt only updates stock, so a pair of
hooks rebuild every fork afterwards:

- `/etc/apt/apt.conf.d/99-devkit-profile-apps` (`DPkg::Post-Invoke`)
- `/etc/dpkg/dpkg.cfg.d/60devkit-profile-apps` (`post-invoke` — apt's hook does
  not run for bare `dpkg -i`)

The worker is `/usr/local/bin/sync-devkit-profile-apps.py` (a copy, not a home
symlink). Failure must not fail apt (`|| true`). Cheap gates skip the copy when
the fork's version already matches stock **and** the patched identity is in
place. Do not edit vendor `postinst` files; they are rewritten on every
`configure`.

Config, skills, wrappers, and session data live under `~/.agents-profiles` and
`~/.config` — package upgrades never touch them.

From a terminal, call the public wrapper (`claude-dummy`). It execs the stock
CLI by full path. Each profile also has `~/.agents-profiles/<name>/bin/` with
the unprefixed names (`claude`, `codex`, `cursor-agent`) pointing at those
wrappers. The desktop launcher prepends that directory to `PATH` so the GUI
finds the profile CLI without replacing the rest of `PATH`.

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
