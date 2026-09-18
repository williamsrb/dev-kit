# Profiles

A profile is an instantiated vendor instance, not just a skill set. Creating one
gives you a config directory, a projected skill set, a launcher, an icon colour,
and a name that shows up in the status line and the dock.

## What gets created

```
~/.agents-profiles/<profile>/            # the profile root
~/.agents-profiles/<profile>/core        # symlink to the kit's core/
~/.agents-profiles/<profile>/<vendor>/   # the vendor's config dir
    skills/  rules/  kb/                 # per-entry symlinks into core/
    .devkit-profile.json                 # provenance
~/.config/<Vendor>-<profile>/            # GUI user-data dir
~/.local/bin/<vendor>-<profile>          # Tier 1 wrapper
~/.local/share/applications/...          # Tier 2 launcher
~/.local/share/icons/.../...png          # recoloured icon
```

Layers are projected as **symlinks**, not copies. An update to `core/` therefore
reaches every profile without a re-copy, and a profile costs kilobytes rather
than a duplicate of a 20M tree.

## Commands

```bash
./devkit profile list                    # what exists, what is installed
./devkit profile show enonic             # the resolved manifest
./devkit profile create enonic --apply
./devkit profile sync enonic --apply     # after a manifest change
./devkit profile adopt core --vendor claude --config-dir ~/.claude --apply
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
