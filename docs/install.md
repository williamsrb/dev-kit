# Installing

`install.py` writes `~/.local/bin/devkit-uninstall.sh`. That shell file is not
in this checkout. It does not import the kit and does not call `devkit`. After
a successful `--apply` it deletes itself. The next `install.py --apply` writes
it again. On a machine where nothing was installed it exits 0.

```bash
devkit-uninstall.sh            # dry run; the PATH copy stays
devkit-uninstall.sh --apply    # remove, ask sudo, then the PATH copy deletes itself
```

It removes `~/.agents-profiles`, the `<vendor>-<name>` wrappers, desktop
launchers, badge icons, auth dispatchers, the PATH block
`bootstrap.sh --wire-path` added, and — with sudo — `/usr/lib/devkit`, the
apt/dpkg hooks, and `/usr/local/bin/sync-devkit-profile-apps.py`. A missing
path is skipped. It does not delete this checkout, `~/.agents`, or packages
`bootstrap.sh` installed. A dry run does not delete the script.

Two steps follow. They are separate because they need different privileges
and different network access, and pretending otherwise is how installers end up
writing root-owned files into a user's home.

| Step | Installs | Writes config | Privilege |
|------|----------|---------------|-----------|
| `bootstrap.sh` | packages | no | elevation, after the plan |
| `install.py` | nothing | yes | your own user; refuses root |

## Step 1: dependencies

```bash
./bootstrap.sh --profile enonic            # dry run: prints the plan, changes nothing
./bootstrap.sh --profile enonic --apply
```

It detects your distribution family through `ID_LIKE`, so a derivative is
handled as its parent without needing its own entry. `--apply` prints every
root command, then asks for administrator privileges. A terminal on stdin or
stdout uses `sudo`. When neither is a terminal, the same commands run under
`pkexec`, or under `sudo -A` when `pkexec` is
absent. That block is the start of the workflow, so it can be run on its own
before `install.py`. Without `--apply` the same commands show as
`would run (as root): sudo …`.

Dependencies resolve down a ladder: distribution package first, then nvm for
Node, then npm, then `uv` for Python tools, then a direct binary from a GitHub
release. A tool is satisfied when the binaries it *provides* are on `PATH`,
whatever rung supplied them — which is what lets apt, dnf and pacman disagree
about package names while the check still answers one question.

### Third-party repositories

On RHEL derivatives some packages, `ffmpeg` in particular, are not in the base
repositories. `bootstrap.sh` asks before enabling anything, and a decline is
recorded as skipped rather than failing the run. Answer up front with
`--third-party yes` or `--third-party no`; in a non-interactive shell it
declines by default.

Nothing on Arch requires the AUR.

### PATH

`~/.local/bin` must be on your `PATH` for the profile wrappers to work.
Public wrappers are named `<vendor>-<profile>` (`claude-dummy`), never a stock
CLI name, and they exec the stock binary by full path. Each profile also has
`~/.agents-profiles/<name>/bin/` with the unprefixed vendor names so the GUI
can find that profile's CLI, plus harness tools such as `agentctl`. Wrappers
export `DEVKIT_PROFILE` and `AGENTS_HOME`; a PATH override by itself would
still leave `agentctl` reading `$HOME/.agents` and seeing every profile.

`bootstrap.sh` detects your shell startup files and reports them; it does not
edit them unless you pass `--wire-path`. On a box with both `.bash_profile` and
`.profile`, it writes to `.bash_profile`.

## Step 2: configuration

On a TTY, `./install.py --apply` with no profiles yet **offers to create a
first one** (type, then instance name). Passing `--profile TYPE` skips the
offer and uses the type as the name. Non-interactive runs do the same
(default type `core`).

```bash
./install.py                               # dry run; notes the offer
./install.py --apply                       # TTY: Create a first profile?
./install.py --profile enonic --apply      # skip the offer; name = enonic
./install.py --name dummy --profile enonic --apply
./install.py --profile enonic --verify     # report state, write nothing
```

This creates the profile's config directories, projects its skills, rules and
knowledge base as per-entry symlinks (the profile's subset, not the whole kit
`core/` tree), renders the vendor configs, writes the Tier 1 wrappers (with
`DEVKIT_PROFILE` / `AGENTS_HOME`) and desktop launchers, badges the icons with a
coloured shield emblem,
and records a provenance file. Desktop identity forks (patched asar / `WM_CLASS`)
rsync into `/usr/lib/devkit/`. `install.py --apply` prints that plan and then
asks `sudo` for a password. Re-run later with:

```bash
./devkit profile apps-sync --user "$USER" --install-hook --apply
```

Dry-run (no `--apply`) lists the same privileged commands without prompting.

Then use the wrappers:

```bash
claude-enonic
codex-enonic
cursor-enonic
```

### Running under sudo

`install.py` refuses to run as root, because a config file owned by root in your
home is a support ticket. If you must run the whole thing elevated, name the
target account:

```bash
sudo ./install.py --profile enonic --user yourname --apply
```

Every created path is then owned by that account. Resolution to uid 0 or a
`/root` home is refused outright, with or without `--user`.

### When a path already exists

Any write to an existing path aborts and names it. That is deliberate: the kit
does not know whether that file is yours.

```
error: /home/you/.agents-profiles/enonic/codex/config.toml exists and was not written by devkit
fix:   re-run with --force to back it up and proceed
```

`--force` makes a timestamped backup beside the file, then proceeds.

## Verifying

```bash
./install.py --profile enonic --verify
./devkit doctor
python3 devkit_cli/bootstrap_plan.py --profile enonic --verify
```

The last one lists every declared binary, whether it was found, and which rung
of the ladder it came from.
