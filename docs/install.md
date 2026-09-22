# Installing

Driving this install as an assistant? Read [Agent runbook](#agent-runbook)
first: the same commands as ordered steps, each with its success signal and its
stop condition. The prose below is the reference those steps link into.

Two steps, in order. They are separate because they need different privileges
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
and records a provenance file. Wrappers and launchers also export
`GRAFT_NO_GITIGNORE=1` and `GRAFT_NO_IGNORE=1`, so graft stops writing
`.gitignore` and `.ignore` into every repo it builds in. Instead, the kit's
ignore block (graft, graphify and agentctl security-scan output, at any depth)
is appended to your global git ignore: the file `core.excludesFile` names, or
`~/.config/git/ignore`. It is skipped when every pattern is already there, or
when git is not installed.
Desktop identity forks (patched asar / `WM_CLASS`) rsync into `/usr/lib/devkit/`. `install.py --apply` prints that plan and then
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
./install.py --profile enonic --verify    # 0 ok, 1 a problem, 2 bad invocation
./devkit doctor
./devkit deps --profile enonic
```

`devkit deps` lists every declared binary, whether it was found, and which rung
of the ladder it came from. It is the check `bootstrap.sh` runs at the end of
step 1; `bootstrap_plan.py` remains a module entry point because bash calls it
before `devkit` is guaranteed to work.

## Uninstalling

`install.py`, `devkit profile create` and `devkit profile sync` write
`~/.local/bin/devkit-uninstall.sh`. Every command that writes a profile leaves
one, so there is no order of commands that produces a profile you cannot remove,
and `devkit doctor` reports an installed machine that has lost it. That shell
file is not in this checkout. It does not import the kit and does not call
`devkit`.

```bash
devkit-uninstall.sh                 # dry run; the command stays
devkit-uninstall.sh --apply         # remove, then ask sudo
devkit-uninstall.sh --user NAME --apply
```

A dry run prints the plan and leaves the command in place. `--apply` removes
what devkit wrote, then deletes `~/.local/bin/devkit-uninstall.sh`. A path that
was never created is skipped, so the command exits 0 when nothing is installed.
If the root-owned step fails, the command stays and the exit code is the one
from `sudo`. The next `--apply` of any profile-writing command writes it again.

Removed:

- `~/.agents-profiles`
- `~/.local/bin/<vendor>-<name>` wrappers and their `.devkit-backup-*` copies
- any other file in `~/.local/bin` or `~/.local/share/applications` carrying the
  `Generated by devkit` marker
- desktop launchers, badge icons, and `~/.config/Claude-<name>`,
  `Codex-<name>`, and `Cursor-<name>` data directories
- auth dispatchers (`~/.local/bin/devkit-auth-launch`,
  `~/.local/bin/devkit-auth-dispatch`, and the `devkit-auth-*.desktop`
  handlers), with stock URL handlers put back, and the state they kept in
  `~/.local/state/devkit`
- the PATH block `bootstrap.sh --wire-path` added, from `.bash_profile`,
  `.profile`, `.zshrc` and `.bashrc`
- the kit's block in the global git ignore file, between its
  `# Added by devkit` and `# End of devkit block.` lines
- with sudo: `/usr/lib/devkit`, `/usr/local/bin/sync-devkit-profile-apps.py`,
  `/etc/apt/apt.conf.d/99-devkit-profile-apps`,
  `/etc/dpkg/dpkg.cfg.d/60devkit-profile-apps`,
  `/var/log/devkit-profile-apps.log`, and any `/etc/apparmor.d/devkit-*`
  profile, unloaded with `apparmor_parser -R` before it is deleted

Left in place: this checkout, `~/.agents`, and packages `bootstrap.sh`
installed. Bootstrap does not record which packages it added.

Run it as the account that owns the profiles. As root it refuses unless you
name that account with `--user NAME`, and a `--user` resolving to uid 0 is
refused outright.

## Agent runbook

For an assistant running the install or the uninstall. One step, one command,
one success signal. Every command below is also documented above; nothing here
is a shortcut that skips a refusal.

Ask the operator first, and do not guess:

1. profile type — `core`, `enonic`, `php`, or `client`
2. instance name — unused; it becomes the wrapper suffix, as in `claude-<name>`
3. badge colour — `#RRGGBB`, or none

Standing rules for the whole run:

- Always pass `--name` and `--profile` to `install.py`. Either flag suppresses
  the interactive first-profile offer, which you cannot answer reliably.
- Run the dry run of each step, show its output, and ask before the `--apply`.
- Never run `install.py` under `sudo` without `--user NAME`; it refuses root.
- Never supply a password to `sudo` or `pkexec`. Both prompt the operator, and
  the plan is printed before the prompt.
- A refusal prints `error:` and a `fix:` line. Do that fix; do not work around
  it. Unfamiliar refusals are indexed in
  [troubleshooting.md](troubleshooting.md).

### Install sequence

1. Dependencies, dry run. Prints the plan and changes nothing.

   ```bash
   ./bootstrap.sh --profile enonic
   ```

   Exit 0 ok, 1 a dependency could not be resolved, 2 bad invocation.

2. Dependencies, apply. Prints every root command, then asks for administrator
   privileges.

   ```bash
   ./bootstrap.sh --profile enonic --apply --third-party no
   ```

   Answer the third-party repository question with the flag rather than the
   prompt. Add `--wire-path` only if the operator agreed to have a shell
   startup file edited; otherwise confirm `~/.local/bin` is already on `PATH`.

3. Configuration, dry run. Writes nothing and lists every change.

   ```bash
   ./install.py --name dummy --profile enonic
   ```

   Stop on `core/ has not been exported yet`: run `./devkit export --apply`,
   then repeat this step.

4. Configuration, apply. Writes user-owned config first, then prints the
   desktop-fork plan and asks `sudo`.

   ```bash
   ./install.py --name dummy --profile enonic --apply
   ```

   Exit 0 ok, 1 a refusal or a `--verify` problem, 2 bad invocation — the same
   three as `bootstrap.sh`. Success ends with `Installed. Start it
   with the wrappers in …`. Re-running over a profile devkit wrote is not a
   collision; it rewrites its own files. A collision on a file devkit did not
   write names the path — report it and ask before `--force`.

   When the operator named a badge colour, create the profile with `devkit`
   instead, because `install.py` has no `--color`:

   ```bash
   ./devkit profile create dummy --type enonic --color '#RRGGBB' --apply
   ```

   Either command writes `~/.local/bin/devkit-uninstall.sh`, so the choice does
   not change how the machine is removed later.

5. Verify. Report all three outputs verbatim.

   ```bash
   ./install.py --profile enonic --verify
   ./devkit deps --profile enonic
   ./devkit doctor
   ```

   Each exits 1 on a problem — `verify: N problem(s)`, a `MISSING` row, or
   `doctor: N problem(s)`. Do not declare the install finished on a non-zero
   exit.

6. Hand back the wrapper name (`claude-dummy`) and note that `~/.local/bin`
   must be on `PATH` in the shell the operator will use.

### Uninstall sequence

1. Dry run. Lists everything that would go and removes nothing.

   ```bash
   devkit-uninstall.sh
   ```

   `uninstall: nothing to remove.` means nothing is installed; stop there. If
   the command is not on `PATH`, call it as
   `~/.local/bin/devkit-uninstall.sh`. If the file does not exist and profiles
   are installed, restore it with `./devkit profile sync <profile> --apply`
   rather than removing paths by hand.

2. Show that list to the operator and get an explicit yes. The removal covers
   profile data directories, not only launchers.

3. Apply.

   ```bash
   devkit-uninstall.sh --apply
   ```

   It removes the user-owned paths, then asks for administrator privileges for
   `/usr/lib/devkit` and the package-manager hooks. A non-zero exit means the
   root-owned half failed; the command deletes itself only on success, so
   re-run it rather than removing those paths yourself.

4. Never run it as root without `--user NAME`, and never pass `--user root`.
   Both are refused.

### Prompt to hand over

Paste this to an assistant that has this checkout. The `{{ask …}}` slots are
questions to put to the operator, not values.

```text
Install devkit locally, following docs/install.md#agent-runbook exactly.
Run each dry run first and show me its output.
Ask before running each next step of installation.
Set up an enonic profile named {{ask profile name}}
with color {{ask profile badge color}}.
```
