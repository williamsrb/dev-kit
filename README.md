# Dev kit

An AI-tooling kit that installs on a fresh machine in two steps, with profile
isolation so several agent harnesses run side by side on one box without
colliding. An Enonic developer and a PHP developer can share a laptop and not
share a single skill, rule, or MCP registration.

## Install

Run from the checkout, in this order. Every step has a dry run (omit
`--apply`); read it before applying.

```bash
./bootstrap.sh --profile enonic --apply    # 1. dependencies, no config
./install.py --name dummy --profile enonic --apply    # 2. profile, wrappers, `devkit` on PATH
./install.py --name dummy --profile enonic --verify   # 3. check
./devkit doctor
claude-dummy                               # 4. start the profile
```

`core/` is tracked, so a clone already has it. Run `./devkit export --apply`
before step 2 only when `install.py` says `core/` is not exported; it needs the
harness at `~/.agents` as its source.

What step 2 leaves on your machine, all under `~/.local/bin` (which must be on
`PATH`; pass `--wire-path` to step 1 or edit your shell profile yourself):

| File | Purpose |
|------|---------|
| `devkit` | Link to the installed kit's `devkit.py`, so `devkit` runs from any directory. |
| `<vendor>-<name>` (`claude-dummy`) | The profile's CLI wrappers. |
| `devkit-uninstall.sh` | Removes everything the kit wrote, except projects built with `devkit project build` (run `devkit project clean` in each repo first) and the home-root rules `fix-home-rules` moved ([docs/install.md#uninstalling](docs/install.md#uninstalling)). |

The kit is also copied to `~/.local/share/devkit/`, and every profile links into that copy, not into this checkout. Once step 2 has run you can move or delete the checkout; it is only the source of an upgrade (see [docs/updates.md](docs/updates.md)).

Open a new shell after install so `PATH` changes apply. Without `--name` or
`--profile`, `install.py --apply` on a terminal with no profiles installed asks
which first profile to create.

Installing as an assistant rather than reading this: go to
[docs/install.md#agent-runbook](docs/install.md#agent-runbook) before running
anything. It is the same steps as ordered commands, each with its success
signal, its exit codes and its stop condition, plus the uninstall sequence and
the questions to put to the operator first. Do not stop at the install
command: the verify step and the PATH check are part of the install. The rest
of this README is orientation, not a procedure.

Neither step assumes the other had network access. Privileged work prints its
plan, then asks for administrator privileges — never the other way around. A
terminal uses `sudo`. A non-interactive shell (no terminal on stdin or stdout)
uses `pkexec`, or `sudo -A` when `pkexec` is absent. Step 1 is that elevation
at the start, for package transactions. Step 2 writes configuration as your
user (it refuses to write home as root) and only then elevates, at the end,
for the desktop identity forks. Each elevated command can be run on its own
before or after the rest.

## What a profile is

Not a skill set — an instantiated vendor instance. Each profile gets its own
config directory, skills, rules, knowledge base, MCP set, launcher, icon badge,
and a visible name in the status line and the dock.

<!-- devkit:generated:profile-table -->

| Profile | Extends | Skills | Rules | Vendors | Required tools |
|---------|---------|--------|-------|---------|----------------|
| `client` | `enonic` | 46 | 31 | claude, codex, cursor | 38 |
| `core` | `—` | 35 | 24 | claude, codex, cursor | 36 |
| `enonic` | `core` | 46 | 26 | claude, codex, cursor | 38 |
| `php` | `core` | 35 | 24 | claude, codex | 38 |

<!-- /devkit:generated:profile-table -->

`extends` composes, so the PHP profile inherits the core knowledge base without
inheriting 3.4M of Enonic XP reference.

## Compatibility

Every row was measured on the reference machine, not inferred from
documentation. "Tier 1" is a CLI wrapper; "Tier 2" adds a desktop launcher with
an isolated config directory. "Tier 3" is a fork of the GUI so
each profile has its own `desktopName`, `WM_CLASS`, and badged in-app icons. Apt/dpkg
hooks rebuild those forks after the original package updates.

| Vendor | Tier 1 mechanism | Tier 2 | Tier 3 fork | Status |
|--------|------------------|--------|-------------|--------|
| Claude Code / Desktop | `CLAUDE_CONFIG_DIR` | yes | `/usr/lib/devkit/claude-<profile>/` | verified |
| Codex CLI / ChatGPT Desktop | `CODEX_HOME` (the launcher adds `CODEX_ELECTRON_USER_DATA_PATH`) | yes | `/usr/lib/devkit/codex-<profile>/` | verified |
| Cursor (IDE) | none: `cursor-<profile>` is the `cursor-agent` wrapper | yes, with `--user-data-dir` + `--extensions-dir` | `/usr/lib/devkit/cursor-<profile>/` | verified |
| `cursor-agent` (CLI) | `XDG_CONFIG_HOME` + `CURSOR_DATA_DIR` | n/a | n/a | verified |

Two details worth knowing before you debug something:

- **Codex** relocates config via `CODEX_HOME` and the ChatGPT Desktop Chromium
  profile via `CODEX_ELECTRON_USER_DATA_PATH=~/.config/Codex-<profile>`. The
  stock ChatGPT package stays shared as the rsync source; each profile launches
  its fork.
- **Claude Desktop** uses `--user-data-dir=~/.config/Claude-<profile>`. Stock
  `~/.config/Claude` is untouched. Cursor's GUI user-data is the profile dir
  (`~/.agents-profiles/<name>/cursor`), not `~/.config/Cursor-<name>`.
- **`cursor-agent`** reads `XDG_CONFIG_HOME`, which is a *generic* variable.
  Its wrapper sets it on the `exec` line only, never exports it, because
  exporting it would relocate the config directory of every XDG-aware program in
  that shell.

| Distribution family | Package manager | Status |
|---------------------|-----------------|--------|
| Debian / Ubuntu | apt | verified on the reference machine |
| Fedora / RHEL / Rocky | dnf | package names proposed; the CI matrix is the test |
| Arch | pacman | package names proposed; the CI matrix is the test |

Nothing on Arch may require the AUR.

## Documentation

| Guide | Read it when |
|-------|--------------|
| [docs/install.md](docs/install.md) | Installing on a new machine, or a step failed |
| [docs/install.md#agent-runbook](docs/install.md#agent-runbook) | An assistant is running the install or the uninstall |
| [docs/install.md#uninstalling](docs/install.md#uninstalling) | Removing profiles, launchers, and desktop forks |
| [docs/profiles.md](docs/profiles.md) | Creating, syncing, or adopting a profile |
| [docs/project.md](docs/project.md) | Applying the harness to a work repo instead of a profile |
| [docs/paths.md](docs/paths.md) | Something rendered `~/...` literally, or a link is broken |
| [docs/updates.md](docs/updates.md) | Updating, or an update refused to apply |
| [docs/troubleshooting.md](docs/troubleshooting.md) | A refusal message sent you here |
| [docs/reference.md](docs/reference.md) | Looking up a command or flag |
| [docs/maintainer/export.md](docs/maintainer/export.md) | Changing what ships in `core/` |
| [docs/maintainer/design.md](docs/maintainer/design.md) | Why the kit is built this way |

## Gates

Every gate runs as an ordinary local command. CI makes them non-optional, but
nothing here is CI-only. A gate is never left red on purpose: fix the failure,
or delete the test and say why in the commit. A known-red gate teaches everyone
to ignore red.

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
| `bootstrap.sh` | Step 1. Dependencies only. Bash, because it runs before Python is guaranteed. |
| `install.py` | Step 2. Configuration only. Refuses root. |
| `devkit` | Profile, export, update and diagnostic CLI. `install.py` links it to `~/.local/bin/devkit`. |
| `profiles/` | Profile manifests. `core` is the base; the rest extend it. |
| `devkit_cli/project.py` | `devkit project`: applies skills and instructions to a work repo ([docs/project.md](docs/project.md)). |
| `core/` | The curated export of the harness. Generated — never edit directly. |
| `templates/` | Vendor configs, CLI wrappers, desktop launchers, auth dispatchers. |
| `export-allowlist.json` | What ships, per layer, with a recorded reason for every exclusion. |
| `path-contract.json` | The `${HOME}` rules `devkit lint-paths` enforces. |
| `devkit.yaml` | Fork topology: `lineage_id`, `fork_id`, `upstream`. |

## Why not Docker

The kit does not containerize the harness for profile isolation. Config
isolation is environment variables, a wrapper, and a `.desktop` file; dock
identity is a copy of the vendor GUI. Containerizing to obtain
that would cost a rebuild per profile switch. A containerized harness driving
`docker compose` or `enonic sandbox` needs a mounted Docker socket, which is
root-equivalent on the host and erases the isolation the container was for.

Docker does earn its place for a headless CLI-agent image: see
[docs/maintainer/container.md](docs/maintainer/container.md).
