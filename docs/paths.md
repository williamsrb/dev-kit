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

Files are classified by extension, and rules apply per class:

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

## Exemptions

`path-contract.json` has an `allow` map keyed by file path. An exemption is a
claim that a human reads that line and no program resolves it, so each one is
listed against specific rule ids rather than blanket-disabling a file.

The test suite carries deliberate positive fixtures — a test proving a rule
fires has to contain the string the rule matches — so it is exempt by name.

## Rendering

`${HOME}` and `${PROFILE_*}` are rendered at install time, per context, by
`install.py`. Going the other way, `devkit export` rewrites literal home paths
back to `${HOME}` as files leave the harness, so a path that leaks into the
source gets normalised on the way out rather than shipping.
