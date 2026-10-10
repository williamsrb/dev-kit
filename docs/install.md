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

Two rungs run remote installers: nvm (v0.40.1) and `uv` are fetched with
`curl … | bash` and `curl … | sh`. The release-binary rung takes the latest
GitHub release asset by file-name pattern and does not verify a checksum or
signature. On Arch the package step uses `pacman -Sy` without `-u`.

### Third-party repositories

On RHEL derivatives some packages, `ffmpeg` in particular, are not in the base
repositories. `bootstrap.sh` asks before enabling anything (the enable commands run before
the package plan is printed), and a decline is
recorded as skipped rather than failing the run. Answer up front with
`--third-party yes` or `--third-party no`; in a non-interactive shell it
declines by default.

Nothing on Arch requires the AUR.

### PATH

`~/.local/bin` must be on your `PATH` for the profile wrappers and the `devkit`
command to work. `install.py` links `~/.local/bin/devkit` to
`~/.local/share/devkit/current/devkit.py`, the installed kit (an existing file
or foreign link there is left alone).
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
(default type `core`). The offer is made only when no profile is installed. With
profiles already present, a bare `./install.py --apply` does not ask: it writes
(or rewrites) an instance named `core` of type `core`, so always pass `--name`
and `--profile`. `install.py` does not refuse a name that is already taken
(`devkit profile create` does); it rebinds that instance.

```bash
./install.py                               # dry run; notes the offer
./install.py --apply                       # TTY: Create a first profile?
./install.py --profile enonic --apply      # skip the offer; name = enonic
./install.py --name dummy --profile enonic --apply
./install.py --name dummy --profile enonic --verify   # report state, write nothing
```

This creates the profile's config directories, projects its skills, rules and
knowledge base as per-entry symlinks (the profile's subset, not the whole kit
`core/` tree; `<layer>_excludes` carve paths out, so a narrowed entry becomes a
real directory of finer links), renders the vendor configs, writes the Tier 1 wrappers (with
`DEVKIT_PROFILE` / `AGENTS_HOME`) and desktop launchers, badges the icons with a
coloured shield emblem, and records a provenance file. Desktop launchers are
written only for a vendor whose stock GUI is installed and only for a profile
that is not headless. `install.py` badges with the type's colour; it does not
pick a unique one, so two instances of one type installed this way share a badge.
Use `devkit profile create NAME --type TYPE [--color HEX]` for the second one. Wrappers and launchers
also export `GRAFT_NO_GITIGNORE=1` and `GRAFT_NO_IGNORE=1`, so graft stops
writing `.gitignore` and `.ignore` into every repo it builds in. Instead, the
kit's ignore block (graft, graphify and agentctl security-scan output, at any
depth) is appended to your global git ignore: the file `core.excludesFile`
names, or `$XDG_CONFIG_HOME/git/ignore` (`~/.config/git/ignore` when that is
unset). It is skipped when every pattern is already
there, or when git is not installed. Desktop identity forks (patched asar /
`WM_CLASS`) rsync into `/usr/lib/devkit/`. When the profile's fork is missing or
stale, or the apt/dpkg hooks are not installed, `install.py --apply` prints that
plan and then asks for administrator privileges (`sudo` on a terminal, `pkexec`
or `sudo -A` without one). If that step fails or is cancelled, `install.py`
still prints `Installed.` and exits 0, with `note: desktop forks were not
applied`; `devkit doctor` is what reports it. Re-run later with:

```bash
./devkit profile apps-sync --user "$USER" --install-hook --apply
```

`apps-sync` without `--apply` lists the same privileged commands without
prompting. `install.py` without `--apply` does not get that far: it prints no
fork plan.

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

Every created path is then owned by that account: devkit switches to its uid
and groups before writing anything, and takes root back only for the
desktop-fork step at the end. Resolution to uid 0 or a `/root` home is refused
outright, with or without `--user`.

### Headless and containers

On a terminal-only machine, such as a container built from a Dockerfile, pass
`--headless` (or set `DEVKIT_HEADLESS=1`):

```bash
./install.py --profile core --headless --apply
```

A headless instance writes no `.desktop` launchers, no launcher or fork icon
badges, no URL-scheme handlers, no app-fork apt/dpkg hooks, and no profile
colour, and it never asks sudo for forks. The mode is stored in the instance's
provenance (`"headless": true`), so `devkit profile sync` and
`devkit update apply` keep it. Precedence: flag, then `DEVKIT_HEADLESS`, then
the stored value; `--no-headless` or `DEVKIT_HEADLESS=0` switches back. The mode
is never auto-detected. `--headless` on an installed desktop profile only stops
maintaining its launchers and forks; remove them with `devkit-uninstall.sh`.

`devkit doctor` skips the auth-handler check when `DEVKIT_HEADLESS` is on or
every installed instance is headless, and `devkit profile show` reports
`headless: true` in place of `colors`.

`install.py` still refuses to run as root, so a Dockerfile creates a non-root
user with passwordless sudo for `bootstrap.sh`, as `Dockerfile.agent` does. A
root-only image is not supported: bootstrap installs node, uv and release
binaries into `$HOME`, which as root is `/root` and not usable by the
unprivileged user.

### When a path already exists

Writing a file over an existing one that devkit did not write (it carries no
`devkit` marker) aborts and names it. That is deliberate: the kit does not know
whether that file is yours. Projection links are different: a file or link
where a projection goes is replaced, and only a real directory there refuses.

```
error: /home/you/.agents-profiles/enonic/codex/config.toml exists and was not written by devkit
fix:   re-run with --force to back it up and proceed
```

`--force` makes a timestamped backup beside the file, then proceeds.
`devkit profile sync` always runs with `--force`: it rewrites the profile it
owns, backing up anything it replaces.

## The installed kit

Step 2 copies the kit out of the checkout. Profiles, the `devkit` command and the
auth launchers point at that copy, so the checkout can be moved or deleted after
step 2 and everything keeps working. The checkout is only needed as the source
of an upgrade.

```text
~/.local/share/devkit/            # ${XDG_DATA_HOME}/devkit when XDG_DATA_HOME is under $HOME
  releases/<release-id>/          # immutable copy of the runtime payload
  current -> releases/<release-id>
```

A release holds `devkit.py`, `devkit`, `devkit_cli/`, `core/`, `templates/`,
`profiles/`, `flavors/`, `devkit.yaml`, `export-allowlist.json` and `path-contract.json`,
plus a `.devkit-install.json` stamp (commit, whether the working tree was
dirty, lineage, source, payload digest). It leaves out `.git`, `tests/`,
`docs/`, `scripts/`, `bootstrap.sh` and `install.py`. The release id is the
first 12 hex characters of the payload digest, so installing the same payload
twice copies nothing.

Every link a profile holds goes through `current`. An upgrade installs a new
release and flips that one link; no profile link is rewritten. The current and
the previous release are kept for rollback, the rest are pruned.

`devkit export`, `devkit docs generate` and `devkit lint-paths` (without a
path) need sources an installed release does not have. They refuse and print the
command to run from your checkout.

A profile created before the kit home existed links into the checkout and keeps
working until you re-sync it. `devkit doctor` and `devkit update check` list it:

```bash
<checkout>/devkit profile sync <name> --apply     # dry run without --apply
```

## Verifying

```bash
./install.py --name dummy --profile enonic --verify   # 0 ok, 1 a problem, 2 bad invocation
./devkit doctor
./devkit deps --profile enonic
```

`devkit deps` lists every declared binary, whether it was found, and which rung
of the ladder declares it. It is the check `bootstrap.sh` runs at the end of
step 1; `bootstrap_plan.py` remains a module entry point because bash calls it
before `devkit` is guaranteed to work.

## Uninstalling

`install.py`, `devkit profile create` and `devkit profile sync` write
`~/.local/bin/devkit-uninstall.sh`. Every command that creates or syncs a profile
leaves one (`devkit update apply` re-syncs instances that already have it), so
no sequence of create and sync commands produces a profile you cannot remove.
`devkit profile adopt` writes none, and `devkit doctor` reports an installed
machine that has lost it. That shell
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
- the installed kit, `~/.local/share/devkit` (only when it holds
  `releases/*/.devkit-install.json` stamps; `${XDG_DATA_HOME}/devkit` when that
  is under `$HOME`)
- the update staging cache, `~/.cache/devkit` (only when it holds
  `staged/*/.devkit-staged.json` markers)
- `~/.local/bin/devkit`, when it is a link to a `devkit.py`
- `~/.local/bin/<vendor>-<name>` wrappers and their `.devkit-backup-*` copies
- any other file in `~/.local/bin` or `~/.local/share/applications` carrying the
  `Generated by devkit` marker
- desktop launchers, badge icons, and `~/.config/Claude-<name>`,
  `Codex-<name>` data directories, and `Cursor-<name>` when one exists (the kit
  keeps Cursor data under `~/.agents-profiles/<name>/cursor`)
- auth dispatchers (`~/.local/bin/devkit-auth-launch`,
  `~/.local/bin/devkit-auth-dispatch`, and the `devkit-auth-*.desktop`
  handlers), with stock URL handlers put back, and the state they kept in
  `~/.local/state/devkit`
- the PATH block `bootstrap.sh --wire-path` added, from `.bash_profile`,
  `.profile`, `.zshrc` and `.bashrc`
- the kit's block in the global git ignore file, between its
  `# Added by devkit: regenerable harness output, any depth.` and
  `# End of devkit block.` lines
- with sudo: `/usr/lib/devkit`, `/usr/local/bin/sync-devkit-profile-apps.py`,
  `/etc/apt/apt.conf.d/99-devkit-profile-apps`,
  `/etc/dpkg/dpkg.cfg.d/60devkit-profile-apps`,
  `/var/log/devkit-profile-apps.log`, and any `/etc/apparmor.d/devkit-*`
  profile, unloaded with `apparmor_parser -R` before it is deleted

Left in place: this checkout, `~/.agents`, the files `devkit project build`
wrote into your repos (run `devkit project clean` there first), and packages
`bootstrap.sh` installed. Bootstrap does not record which packages it added. What
`devkit fix-home-rules` (or `install.py --fix-home-rules`) did is also left: the
rules it moved into `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md` are your
content in the stock vendor directories, and the 1-byte mode-000 stubs at
`~/CLAUDE.md` and `~/AGENTS.md` keep the vendors from reading home-root rules.
Their `.devkit-backup-*` copies hold the originals.

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

   Exit 0 ok, 1 a dependency could not be resolved, 2 an unknown option. A
   missing value (`--profile` alone) and an unknown profile name also exit 1,
   and an unrecognised `--third-party` value is treated as a decline.

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
   ./install.py --name dummy --profile enonic --verify
   ./devkit deps --profile enonic
   ./devkit doctor
   ```

   Each exits 1 on a problem — `verify: N problem(s)`, a `MISSING` row, or
   `doctor: N problem(s)`. Do not declare the install finished on a non-zero
   exit.

6. Check the commands resolve, in a fresh login shell, and report the output:

   ```bash
   bash -lc 'command -v devkit claude-dummy'
   ```

   A missing line means `~/.local/bin` is not on `PATH` there. Say so; do not
   edit a shell startup file without the operator's yes.

7. Hand back the wrapper name (`claude-dummy`) and the `devkit` command.

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
