# Installing

Two steps, in order. They are separate because they need different privileges
and different network access, and pretending otherwise is how installers end up
writing root-owned files into a user's home.

| Step | Installs | Writes config | Privilege |
|------|----------|---------------|-----------|
| `bootstrap.sh` | packages | no | `sudo`, scoped to package transactions |
| `install.py` | nothing | yes | your own user; refuses root |

## Step 1: dependencies

```bash
./bootstrap.sh --profile enonic            # dry run: prints the plan, changes nothing
./bootstrap.sh --profile enonic --apply
```

It detects your distribution family through `ID_LIKE`, so a derivative is
handled as its parent without needing its own entry.

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
`bootstrap.sh` detects your shell startup files and reports them; it does not
edit them unless you pass `--wire-path`. On a box with both `.bash_profile` and
`.profile`, it writes to `.bash_profile`.

## Step 2: configuration

```bash
./install.py --profile enonic              # dry run
./install.py --profile enonic --apply
./install.py --profile enonic --verify     # report state, write nothing
```

This creates the profile's config directories, projects its skills, rules and
knowledge base as symlinks into `core/`, renders the vendor configs, writes the
Tier 1 wrappers and Tier 2 launchers, recolours the icons, and records a
provenance file.

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
