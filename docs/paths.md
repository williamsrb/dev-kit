# Paths and `${HOME}`

One rule: **`${HOME}` is the only home-anchored token in kit source.** A literal
`/home/someone` never ships, and `~/` never appears where a program will parse
it.

## Why `~` is not a path

`~` is a shell construct. It expands only in a shell, unquoted, at word start.
It does not expand in:

- a markdown link target — `[x](~/.agents/foo)` resolves to `./~/.agents/foo`,
  which is the broken link the visual apps display
- a JSON or TOML value
- a `.desktop` `Exec=` line
- a symlink target
- cron's command position
- a quoted shell string — `"~/x"` stays literal even in bash

This was measured rather than assumed. The relative markdown links under
`skills/` resolve identically through every projection identity, so relative
links are portable and `~/` is the real breakage — the opposite of the initial
hypothesis.

## The gate

```bash
./devkit lint-paths                 # the whole repo
./devkit lint-paths core/skills     # a subtree
```

Files are classified by extension (plus the bare filenames `crontab` and
`config`, which are machine-consumed); a file in no class is not checked. Rules
apply per class:

| Class | Examples | `~/` allowed? |
|-------|----------|---------------|
| machine-consumed | `.json`, `.toml`, `.desktop`, `.js` | no — nothing expands it |
| prose | `.md`, `.mdc`, `.txt` | yes, except in a link target |
| shell | `.sh`, `.bash` | no inside quotes |
| scripts | `.py` | a literal home path is still an error |

## Rules that needed tightening

Two rules were too blunt when first written, and the fix is worth knowing
because it explains what they do *not* flag:

- **`literal-home`** is anchored to a harness dotdir (`/home/x/.agents`,
  `/home/x/.claude`, …). A bare `/home/<user>/` also matches container paths
  like `/enonic-xp/home/` and a Dockerfile's `/home/builder`, which are correct
  as written and are not this machine's home.
- **`quoted-tilde`** applies to shell only. In Python a `"~/..."` literal is
  usually prose in a help string, or is about to go through `expanduser()`.

One rule is easy to miss because it is not about `~`: **`home-fallback`** flags
`${HOME:-/some/path}` in scripts and shell. A fallback bakes one machine's home
into every other machine; require `HOME` instead.

## Exemptions

`path-contract.json` has an `allow` map keyed by file path. An exemption is a
claim that a human reads that line and no program resolves it, so each one is
listed against specific rule ids rather than blanket-disabling a file.

`tests/test_devkit.py` carries deliberate positive fixtures — a test proving a
rule fires has to contain the string the rule matches — so it is exempt by name.
Other test files, `tests/test_project.py` included, are checked like any code.

`ignore` is the blunter list beside it: paths the gate does not read at all,
rather than a file it reads with one rule switched off. It covers generated and
vendored content, and local state that git already ignores — `.security-local/`
and `.cache/` (this repo's `.gitignore`), `.ruff_cache/` (its own `.gitignore`)
and `graft/` (the global ignore). A security scan embeds commit messages in its
JSON output, so without that entry a routine scan can turn the gate red over a
path nobody wrote.

## Rendering

`${HOME}` and `${PROFILE_*}` are rendered at install time, per context, by every
command that materializes a profile (`install.py`, `devkit profile create` and
`sync`, `devkit update apply`). Going the other way, `devkit export` rewrites
literal home paths back to `${HOME}` as files leave the harness, so a path that
leaks into the source gets normalised on the way out rather than shipping.
