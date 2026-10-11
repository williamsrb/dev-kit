# Updating

Three commands, one direction of travel. The installed kit lives in
`~/.local/share/devkit/` (see [install.md](install.md#the-installed-kit)); an
update installs a new release there and flips `current`. The repository, local or
remote, is only the source.

| Command | Network | Writes | Safe unattended |
|---------|---------|--------|-----------------|
| `devkit update check` | refs only | nothing | yes |
| `devkit update fetch` | for a git URL | staging cache | no |
| `devkit update apply` | **no** (unless `--from` names a git URL) | the kit home and the instances | no |

```bash
devkit update check  [--from SRC] [--ref REF] [--profile NAME]
devkit update fetch  [--from SRC] [--ref REF]
devkit update apply  [--from SRC] [--ref REF] [--profile NAME] --apply
```

## Choosing the source

`--from SRC` is a local directory or a git URL (`https://`, `http://`, `ssh://`,
`git@host:path`, `file://`). Without it devkit uses the source the installed kit
recorded, and only when none was recorded `upstream` in `devkit.yaml`. A recorded
directory that no longer exists is an error; it does not fall through to
`upstream`. If none resolves,
`fetch` and `apply` refuse and name `--from`; `check` prints a note and reports
local state only.

| Source | What is installed | Lineage |
|--------|-------------------|---------|
| directory with `.git` | the working tree, payload files only: tracked plus untracked, ignored files out. Marked dirty when it differs from HEAD | the root commit; a shallow clone or a repo with no commit falls back to the declared `lineage_id`, unverified by history |
| directory without `.git` | the payload files found by walking it | only the `lineage_id` its own `devkit.yaml` declares; `check` and `fetch` say it is unverified by history |
| git URL | `--ref` (default `HEAD`), cloned and stripped of `.git` | the root commit |

A foreign lineage is refused for every source, with no override, before
anything is staged or installed.

`apply --from SRC` (or `--ref REF`) stages the source first and installs it in
one step; without either it installs what was staged last. Its dry run stages
into a temporary directory that it deletes, so it leaves nothing for a later
bare `apply` to pick up, but for a git URL it still clones.

## check

Reports the installed kit and the source on one line, with whether an update is
available, then one row per instance: INSTANCE, INSTALLED commit, SCHEMA and
STATE. STATE is a blocker (foreign lineage, fork mismatch, installer too old)
or else compares the instance with the installed kit's commit, not with the
source, so a row can read `up to date` while the header line says `update
available`. With no installed instance it prints `no installed instances found.`
and stops. For a git URL it asks the remote for the ref (`ls-remote`); for a
directory it compares the payload digest with the installed release. It also
lists installs that still link into a checkout, with the command that fixes
them. It never writes, which makes it safe to run against profiles this
installer is too old to touch — and safe to put in a cron job or a shell prompt.

When the source has the same commit as the installed release but a different
payload digest, the first line says `same commit, payload differs (release built
by an older devkit, or the source changed)` and the next line names the repair,
`devkit update apply --from <source> --apply`. A dirty source says so instead.

It never fails the machine. It reports blockers instead.

## fetch

It touches the network for a git URL, as `check` (`ls-remote`) and
`apply --from <git URL>` (a clone) also do. It resolves `--ref` in the fresh
clone, records that commit, and resolves `lineage_id` from
the fetched repository's root commit. Only the runtime payload is staged.

A lineage mismatch fails **here**, before anything is staged, so a foreign kit
is rejected rather than half-installed.

A shallow clone has no root commit to resolve. `fetch` unshallows rather than
accepting an unknown lineage, because "could not verify" is not "verified".

## Who installs: the incoming tree

Any command that installs a tree runs with that tree's own code. An installed
devkit that decided what ships would drop a payload entry added by the version
it installs, stamp a digest over the smaller set, and later report a phantom
update. So when a source tree declares `HANDOFF_PROTOCOL` in
`devkit_cli/update.py`, the installed devkit resolves the source and checks the
lineage, then runs that tree's `devkit.py` (`update stage-tree`, `update
inspect-tree` for a directory `check`, and `update apply --staged`) as a
subprocess with `DEVKIT_HANDOFF=1`, which stops it handing off again. It prints
`note: <what> with the incoming tree's own code (<tree>)` first. A tree without
the constant prints `note: <tree> predates the hand-off; ...` and is handled by
the installed code, as before. The first upgrade onto a version that has the
hand-off still runs the old code once. Git sources hand off after the lineage
check, so the cloned code runs at fetch time.

Every release is verified against its own `PAYLOAD` (the tuple in its
`kithome.py`) and its stamped digest before `current` flips. A failure removes
the new release and leaves `current` alone.

## Migrations

`devkit_cli/migrations.py` holds a registry of repairs, each with a `needs`
predicate over real state. `devkit doctor` lists the ones that are needed with
their fix command. `update apply` runs them after the flip and records their
names in the provenance `history` entry (`migrations`); `profile sync` runs them
after it syncs. `release-payload-complete` reports an installed release that
fails verification and prints the command that reinstalls it.

## apply

Offline. It copies the staged payload into a temp directory, renames it into
`releases/`, flips `current` with an atomic symlink replace, then re-syncs each
instance (after a backup) and appends a history entry recording the `from` and
`to` commits. A payload identical to `current` installs nothing and reports up
to date. After a success the releases other than `current` and the previous one
are pruned. Staged payloads under `~/.cache/devkit/staged` are not pruned.

The provenance file is never updated before the tree it describes. A failure
mid-apply flips `current` back to the previous release (when there is one) and
restores each instance's vendor config directory from its backup (with no
previous release `current` stays on the new one, because the auth scripts
already name it; the failed release directory stays in `releases/`), so the
provenance describes the pre-apply state and the instance is never labelled as
something it is not. What the re-sync writes outside that directory (the
profile's `agents/`, `bin/` and `hooks/`, wrappers, launchers, auth dispatchers)
is not backed up; `devkit profile sync <name> --apply` rewrites it from the
restored `current`.

`apply` re-materializes each instance, wrappers and launchers included, but does
not rebuild desktop forks or relink `~/.local/bin/devkit`. After a kit apply,
`devkit profile sync <name> --apply` does both: if desktop forks are missing or
stale it prints the rsync plan and asks `sudo`. Apt/dpkg hooks rebuild forks
when the original vendor package updates; they do not replace this step after a
kit-only change.

## Updating from your own checkout (no upstream)

The kit you cloned is its own origin: `devkit.yaml` has `upstream: null`. The
installed kit records the directory it was installed from, so `devkit update
check` and `devkit update fetch` without `--from` re-read that directory, and
`devkit update apply` installs what `fetch` staged. Pass `--from` to name another
one:

```bash
git pull                                    # or edit, or commit your own changes
devkit update check --from ~/src/devkit     # "update available" when the payload differs
devkit update apply --from ~/src/devkit     # dry run; stages nothing
devkit update apply --from ~/src/devkit --apply
devkit doctor
```

A working tree with uncommitted changes installs as it is and is marked dirty in
the stamp, which is how you test a change against the real install. The
checkout is not needed afterwards: delete it and `devkit update apply --from
<git URL> --apply` still works.

`devkit profile sync <name> --apply` run as `<checkout>/devkit` does the same
for one profile: it installs the checkout as the current release (nothing is
copied when the payload is already current), then re-materializes the profile
through `current`. It keeps everything in the profile's `.claude.json` outside
`mcpServers` (login state, trust flags). Quit that profile's Claude first: a
running process rewrites `.claude.json` and can undo the write. `sync` also
relinks `~/.local/bin/devkit` when it still points at a checkout. Do not use a
bare `install.py --apply` for this on an installed machine: it creates a new
profile named after the type.

### Migrating an install that links into a checkout

Profiles created before the kit home existed link into the checkout.
`devkit doctor` and `devkit update check` list them as `legacy`. One command
makes a profile standalone, then the checkout can move:

```bash
<checkout>/devkit profile sync <name> --apply    # dry run without --apply
devkit profile apps-sync --install-hook --apply  # refreshes the root worker and emblem
```

## Forks and lineage

`devkit.yaml` declares the topology:

```yaml
lineage_id: <this repository's root commit>   # inherited, never hand-edited
fork_id: devkit
upstream: git@...                             # null on the origin fork
```

A team forking the kit changes `fork_id` and sets `upstream`. `lineage_id` is
inherited, which is what lets `update` tell a fork of your kit from a different
kit that happens to use the same command name.

A commit cannot contain its own SHA, so the root commit is made first and the
next commit records it. That is why the kit's first two commits exist.

## When apply refuses

Most refusals name the fix (`<ref> does not exist in <url>` and a failed `git`
call do not):

| Refusal | Means | Fix |
|---------|-------|-----|
| nothing is staged | you skipped `fetch` | `devkit update fetch`, or pass `--from` |
| no update source is known | the kit was never installed from one and has no `upstream` | pass `--from <directory or git URL>` |
| lineage mismatch | the source is a different kit, not a fork | none — and that is intentional |
| fork mismatch | the instance belongs to a different fork of your lineage | `devkit profile migrate <name> --to-fork <id>` |
| installer too old | the instance was installed by a newer devkit | update this kit; there is no override |
| no installed instances to update | `--profile` matched nothing, or none exist | `devkit profile create <name> --type TYPE --apply` |
| the staged payload changed after it was staged | the staging cache was modified | `devkit update fetch` again |
| release ... is incomplete | the release does not match its own `PAYLOAD` or digest; nothing was changed | fix the source tree and apply again |
| could not resolve the lineage | the source's history is unavailable | use a full clone |
| absolute or escaping symlink | the payload has a link that leaves the kit | remove it from the source |
| not a devkit tree / not a directory | `--from` names something else | pass the directory holding `devkit.py` |
| foreign lineage | this is a different kit, not a fork | none — and that is intentional |

The schema refusal has no override on purpose. An older installer writing an
instance it does not understand is how you get a corrupted profile that looks
fine until it does not.
