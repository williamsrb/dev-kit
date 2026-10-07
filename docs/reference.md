# Command reference

Generated from the CLI itself by `devkit docs generate`. If this file and the
CLI disagree, CI fails.

Bare invocation and `--help` produce identical output and exit 0, for every
group. Only a genuine mistake — an unknown subcommand or a bad flag — writes
usage to stderr and exits 2.

<!-- devkit:generated:cli-reference -->

```
usage: devkit [-h] GROUP ...

Install and manage isolated agent-harness profiles.

devkit keeps several agent harnesses on one machine without collision: each
profile has its own config dir, skills, rules, kb, MCP set, CLI wrapper,
desktop launcher, and a GUI fork (unique desktopName / WM_CLASS).
Wrappers export DEVKIT_PROFILE and AGENTS_HOME and prepend the profile bin to
PATH, so agentctl and other harness tools see only that profile. PATH alone is
not enough: those tools read AGENTS_HOME, not $HOME/.agents.

Common examples:
  devkit export --check              # is core/ behind the export source?
  devkit lint-paths                  # no home paths in machine-consumed positions
  devkit profile list
  devkit profile create dummy --type enonic
  devkit profile create enonic
  devkit profile apps-sync --apply   # prints the fork plan, then asks sudo
  devkit profile auth restore
  devkit profile session-sync --source stock --target dummy   # dry run
  devkit project init . --layer core --apply   # then: devkit project build . --apply
  devkit update check
  devkit doctor
  devkit deps --profile enonic       # are the declared binaries on PATH?

Run 'devkit GROUP --help' or 'devkit GROUP COMMAND --help' for details.

options:
  -h, --help        show this help message and exit

command groups:
  GROUP
    export          Copy the allowlisted subset of the harness into core/.
    lint-paths      Fail on home paths in machine-consumed positions.
    doctor          Check instances for staleness, ownership, auth handlers, and
                    desktop forks.
    deps            Check that every binary a profile declares is on PATH.
    profile         Create, inspect, sync, and rebuild isolated harness
                    profiles.
    project         Apply the harness (skills, instructions) to a work repo,
                    alongside profiles.
    update          Check, stage, and apply kit updates (one direction).
    origin          Inspect and adopt the kit this instance came from.
    docs            Generate and verify the documentation tree.
    fix-home-rules  Move a home-root CLAUDE.md/AGENTS.md into its vendor config
                    dir.
```

### `devkit export`

```
usage: devkit export [-h] [--check] [--apply] [--source DIR] [--no-scan]

Copy the allowlisted subset of the harness into core/.

options:
  -h, --help    show this help message and exit
  --check       Exit 1 when core/ is behind the source. Writes nothing.
  --apply       Write the export. Without it, this is a dry run.
  --source DIR  Export source. Default: the allowlist's source key.
  --no-scan     Skip the gitleaks gate. For offline use only.
```

### `devkit lint-paths`

```
usage: devkit lint-paths [-h] [--contract FILE] [PATH ...]

Fail on home paths in machine-consumed positions.

positional arguments:
  PATH             Files or directories to check. Default: the whole repo.

options:
  -h, --help       show this help message and exit
  --contract FILE  Path contract. Default: path-contract.json.
```

### `devkit doctor`

```
usage: devkit doctor [-h] [--profile NAME]

Check instances for staleness, ownership, auth handlers, and desktop forks.

options:
  -h, --help      show this help message and exit
  --profile NAME  Check only this profile.
```

### `devkit deps`

```
usage: devkit deps [-h] [--profile TYPE] [--manager {apt,dnf,pacman}] [--family NAME] [--third-party-declined]

Check that every binary a profile declares is on PATH.

options:
  -h, --help            show this help message and exit
  --profile TYPE        Profile type whose deps to check (default: core).
  --manager {apt,dnf,pacman}
                        Package manager. Default: derived from --family.
  --family NAME         Distribution family (debian, rhel, fedora, arch).
                        Default: /etc/os-release.
  --third-party-declined
                        Binaries that only live in a third-party repo are
                        skipped, not missing.
```

### `devkit profile`

```
usage: devkit profile [-h] COMMAND ...

Create, inspect, sync, and rebuild isolated harness profiles.

options:
  -h, --help      show this help message and exit

commands:
  COMMAND
    list          Show known profiles and their instances.
    show          Show one profile's resolved manifest.
    create        Materialize a named instance from a profile type.
    sync          Re-materialize after a manifest change.
    adopt         Record an existing dir as an instance.
    migrate       Move an instance to another fork.
    auth          Install or restore URL-redirect auth handlers.
    apps-sync     Rebuild per-profile desktop app forks (rsync + asar identity).
    session-sync  Copy agent sessions (Claude, Codex, Cursor) between instances.
```

#### `devkit profile list`

```
usage: devkit profile list [-h]

options:
  -h, --help  show this help message and exit
```

#### `devkit profile show`

```
usage: devkit profile show [-h] name

positional arguments:
  name

options:
  -h, --help  show this help message and exit
```

#### `devkit profile create`

```
usage: devkit profile create [-h] [--type TYPE] [--vendor VENDOR] [--color HEX] [--apply] [--force] name

Write a named profile instance: vendor config dirs, projected skills/rules/kb, AGENTS_HOME tree, CLI wrappers, and desktop launchers. Wrappers pin DEVKIT_PROFILE and AGENTS_HOME so agentctl sees only this profile. --apply writes user-owned config, then prints the desktop-fork plan and asks sudo.

positional arguments:
  name

options:
  -h, --help       show this help message and exit
  --type TYPE      Profile type (profiles/<TYPE>.json). Default: NAME when that
                   type exists.
  --vendor VENDOR  Limit to these vendors (repeatable).
  --color HEX      Badge colour (#RRGGBB). Must be unique across profiles.
                   Default: type colour if free, else a random free palette
                   colour.
  --apply          Write user-owned config, then print the desktop-fork plan and
                   ask sudo. Default: dry run.
  --force          Proceed past a collision, after a timestamped backup. Does
                   not bypass a duplicate name.
```

#### `devkit profile sync`

```
usage: devkit profile sync [-h] [--apply] name

Re-write the instance from the current manifest: prune a leftover core/ symlink, refresh AGENTS_HOME projections, restore a missing devkit-uninstall.sh, keep spawned playwright-<id> MCP entries. --apply writes user-owned config, then prints the desktop-fork plan and asks sudo.

positional arguments:
  name

options:
  -h, --help  show this help message and exit
  --apply     Write user-owned config, then print the desktop-fork plan and ask
              sudo. Default: dry run.
```

#### `devkit profile adopt`

```
usage: devkit profile adopt [-h] [--type TYPE] --vendor VENDOR --config-dir CONFIG_DIR [--apply] name

positional arguments:
  name

options:
  -h, --help            show this help message and exit
  --type TYPE           Profile type. Default: NAME when that type exists.
  --vendor VENDOR
  --config-dir CONFIG_DIR
  --apply               Write. Default: dry run.
```

#### `devkit profile migrate`

```
usage: devkit profile migrate [-h] --to-fork TO_FORK [--apply] name

positional arguments:
  name

options:
  -h, --help         show this help message and exit
  --to-fork TO_FORK
  --apply            Write. Default: dry run.
```

#### `devkit profile auth`

```
usage: devkit profile auth [-h] COMMAND ...

Linux allows one default handler per URL scheme. Profile launchers do not claim vendor schemes; a NoDisplay dispatcher routes the callback to the profile that started login.

options:
  -h, --help  show this help message and exit

commands:
  COMMAND
    restore   Put stock scheme handlers back.
```

#### `devkit profile apps-sync`

```
usage: devkit profile apps-sync [-h] [--user NAME] [--profile NAME] [--vendor VENDOR] [--install-hook] [--icons-only] [--apply]

Rebuild per-profile desktop app forks from the stock packages. Rsync into /usr/lib/devkit/, patch desktopName / WM_CLASS, and badge in-tree icons with a coloured shield emblem. Never writes stock trees. --apply prints the plan, then asks sudo.

options:
  -h, --help       show this help message and exit
  --user NAME      Account whose ~/.agents-profiles to sync. Default: you, or
                   all homes from the apt hook.
  --profile NAME   Only this profile.
  --vendor VENDOR  Only this vendor.
  --install-hook   Install apt + dpkg post-invoke hooks and copy the worker to
                   /usr/local/bin.
  --icons-only     Badge fork icons from stock; skip rsync/asar.
  --apply          Write. Prints the plan, then asks sudo. Default: dry run.
```

#### `devkit profile session-sync`

```
usage: devkit profile session-sync [-h] --source NAME --target NAME [--agent LIST] [--only {code,desktop}] [--indexeddb] [--apply]

Copy sessions from --source to --target. Names are installed profiles, or 'stock' for the unprefixed installs. --agent picks which agents to copy (claude: Code transcripts and Desktop chats; codex: rollouts and the thread index; cursor: IDE chats from state.vscdb), each from the source's instance into the target's instance of the same agent. One direction per run: swap the two for the other. A file or row is copied when the target lacks it or the source is newer; nothing is deleted. Databases are backed up first. Quit the agents' apps on the target first.

options:
  -h, --help            show this help message and exit
  --source NAME         Instance to read from: a profile name or 'stock'.
  --target NAME         Instance to write to: a profile name or 'stock'.
  --agent LIST          Comma-separated: claude, codex, cursor, or 'all' for
                        every agent both sides have (default: claude).
  --only {code,desktop}
                        Claude only: copy just Code transcripts or just Desktop
                        chats.
  --indexeddb           Claude only: also replace the target's Desktop IndexedDB
                        (claude.ai web history) with the source's. Replaces,
                        never merges; the old one is kept beside it. Quit the
                        source too.
  --apply               Write. Default: dry run.
```

### `devkit project`

```
usage: devkit project [-h] COMMAND ...

Apply the harness (skills, instructions) to a work repo, alongside profiles.

options:
  -h, --help  show this help message and exit

commands:
  COMMAND
    init      Write harness/project.json naming the layers.
    build     Link the layers' skills into the repo and exclude them from git.
    status    Check a built project for drift and broken links.
    clean     Remove what the build wrote.
```

#### `devkit project init`

```
usage: devkit project init [-h] [--layer TYPE] [--force] [--apply] [PATH]

Write harness/project.json in the repo. Each --layer is a profile type of the installed kit (core, enonic, ...); the build links the union of their skills. Dry run without --apply.

positional arguments:
  PATH          Root of the git work tree (default: .).

options:
  -h, --help    show this help message and exit
  --layer TYPE  Profile type to apply (repeatable, at least one).
  --force       Overwrite an existing harness/project.json.
  --apply       Write. Default: dry run.
```

#### `devkit project build`

```
usage: devkit project build [-h] [--config FILE] [--rules | --no-rules] [--apply] [PATH]

Link the skills of the layers in harness/project.json into .agents/skills (Codex, Cursor) and .claude/skills (Claude Code), link repo-owned skills from harness/skills, write AGENTS.md and a CLAUDE.md link when the repo has neither, and list every generated path in .git/info/exclude. Tracked files are never modified. Reads the installed kit; never installs one. Dry run without --apply.

positional arguments:
  PATH                 Root of the git work tree (default: .).

options:
  -h, --help           show this help message and exit
  --config FILE        Project config. Default: <PATH>/harness/project.json.
  --rules, --no-rules  Also embed the kit's rules (core, plus client for client layers) in the generated AGENTS.md. Default: the
                       choice the last build recorded.
  --apply              Write. Default: dry run.
```

#### `devkit project status`

```
usage: devkit project status [-h] [--config FILE] [PATH]

Compare the repo with what a build would write now. Exit 1 on a missing or dangling link or a changed entry set; a newer kit release alone is informational. Warns when the active profile provides a skill of the same name. Writes nothing.

positional arguments:
  PATH           Root of the git work tree (default: .).

options:
  -h, --help     show this help message and exit
  --config FILE  Project config. Default: <PATH>/harness/project.json.
```

#### `devkit project clean`

```
usage: devkit project clean [-h] [--apply] [PATH]

Remove the links and files the stamp lists (only while they still point where the build put them), this worktree's exclude block, the stamp, and the directories left empty. Repo-owned links and tracked files stay. Dry run without --apply.

positional arguments:
  PATH        Root of the git work tree (default: .).

options:
  -h, --help  show this help message and exit
  --apply     Write. Default: dry run.
```

### `devkit update`

```
usage: devkit update [-h] COMMAND ...

Check, stage, and apply kit updates (one direction).

options:
  -h, --help  show this help message and exit

commands:
  COMMAND
    check     Report available updates. Never writes.
    fetch     Verify a source and stage it in the cache.
    apply     Install a staged update as a new kit release. Offline unless
              --from names a git URL, which is staged first.
```

#### `devkit update check`

```
usage: devkit update check [-h] [--profile NAME] [--from SRC] [--ref REF]

options:
  -h, --help      show this help message and exit
  --profile NAME
  --from SRC      Update source: a local directory (its working tree, payload
                  files only) or a git URL. Default: the source the installed
                  kit recorded, then devkit.yaml upstream.
  --ref REF       Ref to take from a git URL (default: HEAD). A local directory
                  is always read as its working tree.
```

#### `devkit update fetch`

```
usage: devkit update fetch [-h] [--from SRC] [--ref REF]

options:
  -h, --help  show this help message and exit
  --from SRC  Update source: a local directory (its working tree, payload files
              only) or a git URL. Default: the source the installed kit
              recorded, then devkit.yaml upstream.
  --ref REF   Ref to take from a git URL (default: HEAD). A local directory is
              always read as its working tree.
```

#### `devkit update apply`

```
usage: devkit update apply [-h] [--profile NAME] [--from SRC] [--ref REF] [--apply]

options:
  -h, --help      show this help message and exit
  --profile NAME
  --from SRC      Update source: a local directory (its working tree, payload
                  files only) or a git URL. Default: the source the installed
                  kit recorded, then devkit.yaml upstream.
  --ref REF       Ref to take from a git URL (default: HEAD). A local directory
                  is always read as its working tree.
  --apply         Write. Default: dry run.
```

### `devkit origin`

```
usage: devkit origin [-h] COMMAND ...

Inspect and adopt the kit this instance came from.

options:
  -h, --help  show this help message and exit

commands:
  COMMAND
    show      Show lineage, fork and upstream.
    adopt     Point an instance at a different fork.
```

#### `devkit origin show`

```
usage: devkit origin show [-h]

options:
  -h, --help  show this help message and exit
```

#### `devkit origin adopt`

```
usage: devkit origin adopt [-h] --fork-id FORK_ID --upstream UPSTREAM [--apply]

options:
  -h, --help           show this help message and exit
  --fork-id FORK_ID
  --upstream UPSTREAM
  --apply              Write. Default: dry run.
```

### `devkit docs`

```
usage: devkit docs [-h] COMMAND ...

Generate and verify the documentation tree.

options:
  -h, --help  show this help message and exit

commands:
  COMMAND
    generate  Regenerate the generated docs sections.
```

#### `devkit docs generate`

```
usage: devkit docs generate [-h] [--check]

options:
  -h, --help  show this help message and exit
  --check     Exit 1 on any diff.
```

### `devkit fix-home-rules`

```
usage: devkit fix-home-rules [-h] [--vendor VENDOR] [--apply] [--force]

Move a home-root CLAUDE.md/AGENTS.md into its vendor config dir.

options:
  -h, --help       show this help message and exit
  --vendor VENDOR
  --apply          Write. Default: dry run.
  --force          Append under a marked block when the target already exists.
```

<!-- /devkit:generated:cli-reference -->
