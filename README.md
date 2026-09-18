# devkit

An AI-tooling kit that installs on a fresh machine in two steps, with profile
isolation so several agent harnesses run side by side on one box without
colliding. An Enonic developer and a PHP developer can share a laptop and not
share a single skill, rule, or MCP registration.

```bash
./bootstrap.sh --profile enonic --apply    # step 1: dependencies, no config
./install.py   --profile enonic --apply    # step 2: config, no packages
claude-enonic                              # step 3: work
```

Neither step assumes the other had network access. Step 1 scopes `sudo` to
package transactions; step 2 refuses to run as root outright.

## What a profile is

Not a skill set — an instantiated vendor instance. Each profile gets its own
config directory, skills, rules, knowledge base, MCP set, launcher, icon colour,
and a visible name in the status line and the dock.

<!-- devkit:generated:profile-table -->

| Profile | Extends | Skills | Rules | Vendors | Required tools |
|---------|---------|--------|-------|---------|----------------|
| `client` | `enonic` | 45 | 29 | claude, codex, cursor | 37 |
| `core` | `—` | 33 | 22 | claude, codex, cursor | 35 |
| `enonic` | `core` | 45 | 24 | claude, codex, cursor | 37 |
| `php` | `core` | 33 | 22 | claude, codex | 37 |

<!-- /devkit:generated:profile-table -->

`extends` composes, so the PHP profile inherits the core knowledge base without
inheriting 3.4M of Enonic XP reference.

## Compatibility

Every row was measured on the reference machine, not inferred from
documentation. "Tier 1" is a CLI wrapper; "Tier 2" adds a desktop launcher with
its own window class and icon.

| Vendor | Tier 1 mechanism | Tier 2 | Status |
|--------|------------------|--------|--------|
| Claude Code / Desktop | `CLAUDE_CONFIG_DIR` | yes | verified |
| Codex | `CODEX_HOME` | CLI only | verified |
| Cursor (IDE) | `--user-data-dir` + `--extensions-dir` | yes | verified |
| `cursor-agent` (CLI) | `XDG_CONFIG_HOME` + `CURSOR_DATA_DIR` | n/a | verified |

Two details worth knowing before you debug something:

- **Codex** relocates config, logs and its sqlite state, but the runtime package
  stays shared. That is deliberate: a profile should not cost a second install.
- **`cursor-agent`** reads `XDG_CONFIG_HOME`, which is a *generic* variable.
  Its wrapper sets it on the `exec` line only, never exports it, because
  exporting it would relocate the config directory of every XDG-aware program in
  that shell.

| Distribution family | Package manager | Status |
|---------------------|-----------------|--------|
| Debian / Ubuntu | apt | verified on the reference machine |
| Fedora / RHEL / Rocky | dnf | package names proposed; the CI matrix is the test (R15) |
| Arch | pacman | package names proposed; the CI matrix is the test (R15) |

Nothing on Arch may require the AUR.

## Documentation

| Guide | Read it when |
|-------|--------------|
| [docs/install.md](docs/install.md) | Installing on a new machine, or a step failed |
| [docs/profiles.md](docs/profiles.md) | Creating, syncing, or adopting a profile |
| [docs/paths.md](docs/paths.md) | Something rendered `~/...` literally, or a link is broken |
| [docs/updates.md](docs/updates.md) | Updating, or an update refused to apply |
| [docs/troubleshooting.md](docs/troubleshooting.md) | A refusal message sent you here |
| [docs/reference.md](docs/reference.md) | Looking up a command or flag |
| [docs/maintainer/export.md](docs/maintainer/export.md) | Changing what ships in `core/` |
| [docs/maintainer/design.md](docs/maintainer/design.md) | Why the kit is built this way |

## Gates

Every gate runs as an ordinary local command. CI makes them non-optional, but
nothing here is CI-only.

```bash
./devkit export --check                     # core/ is not behind its source
./devkit lint-paths                         # no home paths in parsed positions
./devkit docs generate --check              # generated docs match the CLI
./devkit doctor                             # installed instances are healthy
python3 -m unittest discover -s tests       # the acceptance checklist
```

## Layout

| Path | Contents |
|------|----------|
| `bootstrap.sh` | Step 1. Dependencies only. The one bash file, because it runs before Python is guaranteed. |
| `install.py` | Step 2. Configuration only. Refuses root. |
| `devkit` | Profile, export, update and diagnostic CLI. |
| `profiles/` | Profile manifests. `core` is the base; the rest extend it. |
| `core/` | The curated export of the harness. Generated — never edit directly. |
| `templates/` | Vendor configs, Tier 1 wrappers, Tier 2 launchers. |
| `export-allowlist.json` | What ships, per layer, with a recorded reason for every exclusion. |
| `path-contract.json` | The `${HOME}` rules `devkit lint-paths` enforces. |
| `devkit.yaml` | Fork topology: `lineage_id`, `fork_id`, `upstream`. |

## Why not Docker

The kit does not containerize the harness for profile isolation. A profile is
two environment variables and a `.desktop` file; containerizing to obtain that
would cost a rebuild per profile switch. A containerized harness driving
`docker compose` or `enonic sandbox` needs a mounted Docker socket, which is
root-equivalent on the host and erases the isolation the container was for.

Docker does earn its place for a headless CLI-agent image: see
[docs/maintainer/container.md](docs/maintainer/container.md).
