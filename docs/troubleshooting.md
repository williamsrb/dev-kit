# Troubleshooting

Refusal messages in this kit name the command that fixes them. If one sent you
here, find it below.

## `refusing to write configuration as root`

`install.py` and `devkit` write configuration as your own user. Run without
`sudo`, or name the account:

```bash
sudo ./install.py --profile enonic --user yourname --apply
```

`refusing to install for uid 0` and `refusing to install into /root` have no
override. Name a real user account.

## `<path> exists and was not written by devkit`

The kit will not overwrite a file it did not create. Look at the file. If you
want it replaced, `--force` backs it up first, timestamped, beside the original.

## `core/ has not been exported yet`

```bash
./devkit export --apply
```

## `<profile>/<vendor>: stale`

The kit moved on since that instance was installed:

```bash
./devkit profile sync <profile> --apply
```

## `N path(s) not owned by you`

Something was installed with `sudo` that should not have been. Fix the
ownership, then stop doing that:

```bash
sudo chown -R "$(id -u)" ~/.agents-profiles/<profile>/<vendor>
```

## `home-root CLAUDE.md is populated`

`~/CLAUDE.md` and `~/AGENTS.md` load in addition to the config-dir versions,
because both vendors walk up to `$HOME` collecting instruction files. Sitting
outside every profile, they leak into all of them at once.

```bash
./devkit fix-home-rules --apply
```

The kit never moves those files silently. See
[profiles.md](profiles.md#home-root-instruction-files).

## `could not recolour <vendor> icon`

ImageMagick is missing, or only version 7 is present and something is looking
for `convert`. The kit tries `magick` first. This is a warning: the launcher
falls back to the stock icon and the install completes.

## `lint-paths: N violation(s)`

See [paths.md](paths.md). The short version: `~` does not expand in a parsed
value, so use `${HOME}` there.

If a violation is a false positive, add it to the `allow` map in
`path-contract.json` against the specific rule id, with the reason. Do not
disable the rule.

## `gitleaks found N finding(s) in the export`

Something in `core/` looks like a credential. Read the findings before anything
else. If they are genuinely false positives, allowlist them in `.gitleaks.toml`
scoped as tightly as the finding allows — by path *and* by pattern — so the rule
keeps working everywhere else.

## Codex warns about helper binaries under a temporary directory

```
Refusing to create helper binaries under temporary dir
```

`CODEX_HOME` is pointing somewhere under `/tmp`. Real profiles live under
`~/.agents-profiles/`, so this only appears in test harnesses. Codex warns and
proceeds; the install is degraded, not failed.

## A projected skill directory is a real directory

```
error: <path> is a real directory, not a projection
```

Something replaced a symlink with actual content. Move it aside by hand and
re-run `profile sync`. The kit will not delete a real directory it did not
create.
