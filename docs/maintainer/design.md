# Why the kit is built this way

The decisions, with the evidence behind them. The working record is the plan
folder this was written from; this is the part that stays true after the plan
is finished.

## Two steps, not one

`bootstrap.sh` installs packages and writes no configuration (with one opt-in
exception: `--wire-path` appends a `PATH` line to your shell profile).
`install.py` writes configuration and installs no packages.

They are split because they need different privileges. Distro packages need
`sudo` (nvm, uv tools and release binaries go into `$HOME` without it);
configuration must **not** have it, because a config file owned by root in a
user's home is a support ticket. Keeping them in one script means one privilege
level for both, and the wrong one for at least one of them.

Every elevation prints the plan first, then asks for administrator privileges.
A terminal on stdin or stdout uses `sudo`. When neither is a terminal, the
command runs under `pkexec`, or `sudo -A`
when `pkexec` is absent. Package elevation is the start of the workflow
(`bootstrap.sh --apply`). `install.py --apply` writes user-owned config, then
the `/usr/lib/devkit` rsyncs are the end (`devkit profile apps-sync`). Each
elevated command can be run on its own before or after the rest. A dry run does
not prompt: `bootstrap.sh` labels its commands `would run (as root):`, and
`apps-sync` prints the fork plan followed by `dry-run: no writes`.

They also assume nothing about each other. Either can run on a machine where the
other has not.

## The installed kit is a copy, not a link

Profile projections used to be symlinks into the checkout's `core/`, and the
auth scripts put the checkout on `PYTHONPATH`. Measured on the owner's machine
on 2026-10-07: 326 symlinks reached the repo (325 under `~/.agents-profiles`
plus `~/.local/bin/devkit`), so deleting or moving the clone broke every
profile and the desktop launchers. Everything else devkit writes (wrappers,
vendor configs, `.desktop` files, icons, the uninstaller, the app-fork worker)
was already a copy.

devkit now copies a release of itself into `${XDG_DATA_HOME:-~/.local/share}/devkit/`
and points every projection at it. The reasons for each choice:

- **One shared kit home, not a copy per profile.** The payload is 16.7M of
  tracked plus untracked files (measured 2026-10-07); a copy per profile is the
  cost this document already rejects for `core/`. One shared copy keeps it once.
- **Immutable `releases/<id>` plus a `current` symlink.** Projections link
  through `current`, so an upgrade flips one link and never rewrites the 325
  profile links. Replacing one directory in place would be neither atomic nor
  reversible.
- **Under `~/.local/share`, not `~/.agents` or `~/.cache`.** Launcher icons and
  desktop files already live there. `~/.agents` is the export source and must
  not hold a runtime copy; `~/.cache` is clearable, which a runtime must not be.
  `XDG_DATA_HOME` counts only when it lies under `$HOME`, so a `--user` run or a
  test cannot write into the caller's data dir, and the static uninstaller can
  apply the same rule.
- **The runtime allowlist, not the repository.** `core/` ships whole,
  `skills-vendor` included, so a release matches what `export` produced;
  filtering inside it would be a second allowlist with no consumer. Bootstrap and
  install stay checkout-only (first install), docs and tests stay in the repo.
- **Release id is the payload digest.** An identical re-install is a no-op, and a
  dirty working tree gets a distinct id, which a git commit alone cannot name.
- **Source order is `--from`, the recorded source, then `upstream`.** The origin
  fork has `upstream: null`, so the recorded checkout path makes a bare
  `devkit update` re-pull from where it was installed.
- **A local source is its working tree, not HEAD.** Testing an uncommitted
  change against the real install is the main local use, and the allowlist
  bounds what is copied.
- **Flip, then re-sync, and roll the flip back on failure.** Projections link
  through `current`, so they cannot be written against a release that is not yet
  current. The rollback is `devkit update apply`'s; `profile create`, `profile
  sync` and `install.py` install a release and flip without one, because they
  re-sync a single profile that a re-run repairs.
- **Maintainer commands refuse from a release.** `export` and `docs generate`
  write into `core/` and `docs/`, and `lint-paths` with no path scans them; all
  three only exist as sources in a checkout.
- **`REPO_ROOT` keeps its name**, documented as "the tree the running code lives
  in". It resolves symlinks, so a running installed devkit sees a release
  directory: anything written for later use names `current`, never `REPO_ROOT`.
- **Keep the current and the previous release** (about 34M). Rollback needs one;
  more is cost without a use. The prune runs after every install, so repeated
  `profile sync` from an edited checkout does not accumulate releases.
- **The uninstaller removes the kit home**, guarded by the release stamps, and
  stays static shell. `README.md` promises it removes everything the kit wrote.

The app-fork worker run as root (`/usr/local/bin/sync-devkit-profile-apps.py`)
and `/usr/lib/devkit/*` are unchanged. `profile apps-sync` re-executes the CLI
under sudo, so root runs user-owned code: the installed release, or the
checkout when devkit runs from one. The same trust level, not addressed here.

## Profile isolation is config plus a GUI fork, not containers

Config isolation is environment variables, a uniquely named CLI wrapper, and a
`.desktop` file. Dock identity needs more: Electron bakes `desktopName` into
`app.asar`, so several profiles of the same vendor would otherwise share one
`WM_CLASS`. Each profile GUI is a rsync of the stock app under
`/usr/lib/devkit/`, with a patched identity. Stock Claude, ChatGPT, and Cursor
stay untouched.

PATH prepend is required so `agentctl` resolves to the profile's `bin/`, but it
is not sufficient: `agentctl` and other harness tools used to hardcode
`$HOME/.agents` and would see every profile's skills, plans, and Playwright
instances. Wrappers therefore also export `DEVKIT_PROFILE` and `AGENTS_HOME`
pointing at `~/.agents-profiles/<name>/agents`. That tree is shaped like
`~/.agents` but holds only this profile's projected skills/kb/rules, plus
profile-local plans and Playwright state. Sibling profiles are not on that
path. The profile root does not contain a `core/` symlink: that tree holds
every exported skill and would leak Enonic into PHP. Tools are reached through
`agents/bin` (kit `core/bin` only). True filesystem hiding of
`~/.agents-profiles` would need a container; the isolation unit is the env +
PATH, which child processes inherit.

Linux also allows one default URL handler per scheme. Profile launchers do not
claim `claude://` / `codex://` / `cursor://`; a `NoDisplay` dispatcher routes
the callback.

Containerizing to obtain that would cost a rebuild per profile switch, and
profile switching is the frequent operation.

The blocker is nested runtime, not the GUI. A containerized harness driving
`docker compose` or `enonic sandbox` needs either DinD or a mounted
`/var/run/docker.sock`, and a mounted socket is root-equivalent on the host —
which erases the isolation the container was built for.

Cost per profile matters too: Playwright browsers are ~400MB per image, the
kit's `core/` tree is 16M (21M on disk), and Ollama models are GB-scale and
should never be duplicated.

Docker does earn its place for a headless CLI-agent image — see
[container.md](container.md).

## `${HOME}`, never `~`

`~` is a shell construct that expands only in a shell, unquoted, at word start.
Everywhere else — link targets, JSON, TOML, `.desktop`, cron, quoted strings —
it is a literal character.

The measurement that settled this: relative markdown links resolve identically
through every projection identity, so relative links are portable and `~/` is
the real breakage. That was the opposite of the starting hypothesis, which is
why it is worth recording.

## The export is one-way

`~/.agents` is the source; `core/` is a curated copy. Edits go to the source and
flow outward. The alternative — editing `core/` and syncing back — means two
places to look when something is wrong, and a merge whenever they disagree.

`devkit export --check` makes the drift visible instead of letting it
accumulate.

## Generated files say so

`core/`, `rules/AGENTS.md` and `docs/reference.md` are generated, and each says
so in its own text. A generated file that still reads like a source file will be
edited, and the edit will be lost.

`AGENTS.md` in particular was hand-maintained beside the Cursor `.mdc` rules,
guarded only by a "keep in sync" note. It drifted: the aggregate told the agent
to edit an existing Jira comment in place while the rule file and the skill both
required a new one. Nothing detected the contradiction, because nothing compared
them.

The generator was proved by reproducing the previous file **byte for byte**
before any content changed. That gate is the whole safety net — without it, a
content bug hides inside a large diff.

## Project mode is content, not runtime

`devkit project` applies the harness to a work repo as a third target next to
profiles. The decisions that outlive the plan it was built from:

- **Composes with profiles, does not replace them.** A project carries what the
  agent knows (skills, instructions); a profile keeps what the agent runs on
  (hooks, MCP, auth, env, GUI identity). Putting those in a repo would lose
  auth, session and tool isolation and the desktop forks, so the project mode
  writes none of them.
- **Layers are profile types.** `harness/project.json` names types and the
  build unions their skills. That gives stack composition (`core` + `enonic`)
  without changing the manifest format; a list-valued `extends` stays deferred
  until something needs it.
- **The build only reads an installed kit.** `ensure_installed` writes the kit
  home, and a smoke run of a write command with a temp `HOME` once created a
  real profile because those commands take the home from the passwd entry. A
  project build never installs, never writes the home, and refuses without
  `current`.
- **Client repos stay clean.** Generated paths go into a managed block of
  `.git/info/exclude`, keyed per worktree because a linked worktree shares the
  common dir's file. Tracked paths are skipped with a warning, never replaced.
  Repo-owned links are not excluded, so the repo can commit them and a
  teammate without devkit gets them from `git clone`.
- **Base rules are opt-in (`--rules`).** A profile already projects them, so
  embedding them by default would load them twice. `AGENTS.md` carries the
  repo's own `harness/AGENTS.md` unless asked.
- **Drift is the entry set, not the release.** Links go through `current`, so a
  kit release that does not change the resolved skills needs no rebuild;
  `status` reports it as informational.
- **No static export, no overlay by repo name, no `doctor` integration in v1.**
  None has a consumer yet. `--config FILE` already keeps a client repo free of
  `harness/`, and `status` is the per-project check because there is no
  registry of built projects.

## Refusals name the fix

A refusal prints the command that resolves it wherever one exists. A refusal
the user cannot act on is just an outage with extra steps. Where no command
fixes it (a missing ref, a path that does not exist, a failed `git`), the
message names the input to correct instead.

The exceptions are deliberate: a foreign lineage and a too-old installer have no
override, because the failure modes they prevent are worse than the
inconvenience of stopping.

## Dry run is the default

Every command that writes the machine plans first and prints what it would do.
`--apply` is the exception, not the default. Two commands write without it,
because what they write is inside the kit: `docs generate` regenerates
`docs/` in a checkout (`--check` is its dry run), and `update fetch` writes only
the staging cache. This matches the contract the harness's existing
projection scripts already use, so the kit does not introduce a second
convention.

## JSON, not YAML

The installer parses its own manifests with the Python standard library, which
has no YAML parser. Keeping `.yaml` would mean vendoring a parser, making PyYAML
a dependency that must be installed *before* the installer can read the manifest
that says what to install, or hand-rolling a subset reader that misparses the
first anchor someone writes.

The cost is comments, which JSON lacks. Every manifest carries a `_comment`
array as its first key instead. `devkit.yaml` stays YAML because it is flat
`key: value` lines, which a line reader parses exactly; it must stay flat.
