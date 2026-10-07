# Updating

Three commands, one direction of travel.

| Command | Network | Writes | Safe unattended |
|---------|---------|--------|-----------------|
| `devkit update check` | refs only | cache only | yes |
| `devkit update fetch` | yes | staging cache | no |
| `devkit update apply` | **no** | the instance | no |

```bash
./devkit update check
./devkit update fetch
./devkit update apply --apply
```

## check

Reports, per instance: the installed commit, what is available, whether this
installer can apply it, and whether the origin matches. It never writes to an
instance, which makes it safe to run against profiles this installer is too old
to touch — and safe to put in a cron job or a shell prompt.

It never fails the machine. It reports blockers instead.

## fetch

The only command that touches the network. It verifies that what it downloaded
is the commit it asked for, and resolves `lineage_id` from the fetched
repository's root commit.

A lineage mismatch fails **here**, before anything is staged, so a foreign kit
is rejected rather than half-installed.

A shallow clone has no root commit to resolve. `fetch` unshallows rather than
accepting an unknown lineage, because "could not verify" is not "verified".

## apply

Offline and per-instance. It backs the instance up, installs, then appends a
history entry recording the `from` and `to` commits.

The provenance file is never updated before the tree it describes. A failure
mid-apply restores from the backup and leaves the provenance describing the
pre-apply state, so the instance is never labelled as something it is not.

After a kit apply, `devkit profile sync <name> --apply` refreshes launchers and
wrappers. If desktop forks are missing or stale, that command prints the rsync
plan and asks `sudo`. Apt/dpkg hooks rebuild forks when the original vendor
package updates; they do not replace this step after a kit-only change.

## Updating the origin fork (no upstream)

The kit you cloned is its own origin: `devkit.yaml` has `upstream: null`, so
`fetch` refuses and there is nothing to stage. `~/.local/bin/devkit` is a link to
`devkit.py` in your checkout, so the CLI is already whatever the checkout holds.
To bring installed profiles in line with it:

```bash
git pull                                    # or commit your own changes
./devkit update check                       # profiles at an older commit say "update available"
./devkit profile sync <name> --apply        # per profile; dry run without --apply
./devkit doctor
```

`sync` re-materializes the profile from the checkout and records its commit, so
`update check` then reports "up to date". It keeps everything in the profile's
`.claude.json` outside `mcpServers` (login state, trust flags). Quit that
profile's Claude first: a running process rewrites `.claude.json` and can undo
the write. `sync` also re-creates `~/.local/bin/devkit` when the link is missing
or the checkout moved; run it as `<checkout>/devkit profile sync <name> --apply`.
Do not use a bare `install.py --apply` for this on an installed machine: it
creates a new profile named after the type.

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

Every refusal names the fix:

| Refusal | Means | Fix |
|---------|-------|-----|
| nothing is staged | you skipped `fetch` | `devkit update fetch` |
| fork mismatch | the instance belongs to a different fork of your lineage | `devkit profile migrate <name> --to-fork <id>` |
| installer too old | the instance was installed by a newer devkit | update this kit; there is no override |
| foreign lineage | this is a different kit, not a fork | none — and that is intentional |

The schema refusal has no override on purpose. An older installer writing an
instance it does not understand is how you get a corrupted profile that looks
fine until it does not.
