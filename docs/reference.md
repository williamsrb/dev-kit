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
profile has its own config dir, skills, rules, kb, MCP set, launcher and icon.

Common examples:
  devkit export --check              # is core/ behind the export source?
  devkit lint-paths                  # no home paths in machine-consumed positions
  devkit profile list
  devkit profile create enonic --vendor claude
  devkit update check
  devkit doctor

Run 'devkit GROUP --help' or 'devkit GROUP COMMAND --help' for details.

options:
  -h, --help        show this help message and exit

command groups:
  GROUP
    export          Copy the allowlisted subset of the harness into core/.
    lint-paths      Fail on home paths in machine-consumed positions.
    doctor          Check installed instances for staleness and bad ownership.
    profile         Create, inspect, and sync harness profiles.
    update          Check, stage, and apply kit updates (one direction).
    origin          Inspect and adopt the kit this instance came from.
    docs            Generate and verify the documentation tree.
    fix-home-rules  Move a home-root CLAUDE.md/AGENTS.md into its vendor
                    config dir.
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

Check installed instances for staleness and bad ownership.

options:
  -h, --help      show this help message and exit
  --profile NAME  Check only this profile.
```

### `devkit profile`

```
usage: devkit profile [-h] COMMAND ...

Create, inspect, and sync harness profiles.

options:
  -h, --help  show this help message and exit

commands:
  COMMAND
    list      Show known profiles and their instances.
    show      Show one profile's resolved manifest.
    create    Materialize a profile's instances.
    sync      Re-materialize after a manifest change.
    adopt     Record an existing dir as an instance.
    migrate   Move an instance to another fork.
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
usage: devkit profile create [-h] [--vendor VENDOR] [--apply] [--force] name

positional arguments:
  name

options:
  -h, --help       show this help message and exit
  --vendor VENDOR  Limit to these vendors (repeatable).
  --apply          Write. Default: dry run.
  --force          Proceed past a collision, after a timestamped backup.
```

#### `devkit profile sync`

```
usage: devkit profile sync [-h] [--apply] name

positional arguments:
  name

options:
  -h, --help  show this help message and exit
  --apply     Write. Default: dry run.
```

#### `devkit profile adopt`

```
usage: devkit profile adopt [-h] --vendor VENDOR --config-dir CONFIG_DIR
                            [--apply]
                            name

positional arguments:
  name

options:
  -h, --help            show this help message and exit
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

### `devkit update`

```
usage: devkit update [-h] COMMAND ...

Check, stage, and apply kit updates (one direction).

options:
  -h, --help  show this help message and exit

commands:
  COMMAND
    check     Report available updates. Never writes.
    fetch     Download and verify into the staging cache.
    apply     Install a staged update. Offline.
```

#### `devkit update check`

```
usage: devkit update check [-h] [--profile NAME]

options:
  -h, --help      show this help message and exit
  --profile NAME
```

#### `devkit update fetch`

```
usage: devkit update fetch [-h] [--ref REF]

options:
  -h, --help  show this help message and exit
  --ref REF
```

#### `devkit update apply`

```
usage: devkit update apply [-h] [--profile NAME] [--apply]

options:
  -h, --help      show this help message and exit
  --profile NAME
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
usage: devkit origin adopt [-h] --fork-id FORK_ID --upstream UPSTREAM
                           [--apply]

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
