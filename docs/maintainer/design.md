# Why the kit is built this way

The decisions, with the evidence behind them. The working record is the plan
folder this was written from; this is the part that stays true after the plan
is finished.

## Two steps, not one

`bootstrap.sh` installs packages and writes no configuration. `install.py`
writes configuration and installs no packages.

They are split because they need different privileges. Packages need `sudo`;
configuration must **not** have it, because a config file owned by root in a
user's home is a support ticket. Keeping them in one script means one privilege
level for both, and the wrong one for at least one of them.

Every elevation prints the plan first, then asks `sudo` for a password.
`bootstrap.sh --apply` lists the package commands; `install.py --apply` writes
user-owned config, then lists the `/usr/lib/devkit` rsyncs. Dry-run labels the
same commands `would run (as root):` and does not prompt.

They also assume nothing about each other. Either can run on a machine where the
other has not.

## Profile isolation is config plus a GUI fork, not containers

Config isolation is environment variables, a uniquely named CLI wrapper, and a
`.desktop` file. Dock identity needs more: Electron bakes `desktopName` into
`app.asar`, so several profiles of the same vendor would otherwise share one
`WM_CLASS`. Each profile GUI is a Personal-style rsync of the stock app under
`/usr/lib/devkit/`, with a patched identity. Stock Claude, ChatGPT, Cursor, and
Claude Personal stay untouched.

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
skills tree is 20M, and Ollama models are GB-scale and should never be
duplicated.

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

## Refusals name the fix

Every refusal in this kit prints the command that resolves it. A refusal the
user cannot act on is just an outage with extra steps.

The exceptions are deliberate: a foreign lineage and a too-old installer have no
override, because the failure modes they prevent are worse than the
inconvenience of stopping.

## Dry run is the default

Every writing command plans first and prints what it would do. `--apply` is the
exception, not the default. This matches the contract the harness's existing
projection scripts already use, so the kit does not introduce a second
convention.

## JSON, not YAML

The installer parses its own manifests with the Python standard library, which
has no YAML parser. Keeping `.yaml` would mean vendoring a parser, making PyYAML
a dependency that must be installed *before* the installer can read the manifest
that says what to install, or hand-rolling a subset reader that misparses the
first anchor someone writes.

The cost is comments, which JSON lacks. Every manifest carries a `_comment`
array as its first key instead. `devkit.yaml` stays YAML because nothing parses
it at runtime.
