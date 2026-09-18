---
id: how-to-apply-tgrep-cursor-patches
when_skills: [run-plan]
inputs: [~/Workspace/Personal/tgrep, ~/.agents/vendor/tgrep-cursor]
outputs: [~/.local/bin/tgrep, ~/.cache/tgrep/build/<sha>]
stop_if: [git apply rejects]
read: whole
prose: caveman-lite
---

# Apply tgrep-cursor patches

Recorded series under `~/.agents/vendor/tgrep-cursor/patches/` onto a disposable worktree. Does not reset `~/Workspace/Personal/tgrep` `main`.

## Scope

Replay FR-1–FR-7 (hidden meta, serve, watcher, search, tests) after an upstream tgrep upgrade.

## Prerequisites

- Clone at `~/Workspace/Personal/tgrep` tracking `origin/main`
- `~/.cargo/bin/cargo`
- `UPSTREAM` file with `sha=` of the parent the patches were made against

## Procedure

1. Dry-run: `python3 ~/.agents/bin/tgrep-cursor-apply.py --dry-run`
2. Apply, test `cursor_hidden_argv`, release-install: `python3 ~/.agents/bin/tgrep-cursor-apply.py --apply`
3. Binary lands at `~/.local/bin/tgrep`. Worktree stays at `~/.cache/tgrep/build/<sha>/`.
4. Skip-if-done: if `~/.cache/tgrep/build/<sha>/` is already this repo’s worktree at `UPSTREAM.sha` and the series is applied (or the tree is still clean at the pin), a second `--dry-run` / `--apply` reuses it. It must not `worktree remove --force`, `branch -D`, or `rmtree`. `--apply` may still refresh `~/.local/bin/tgrep`.
5. On `git apply` reject (exit 2): read `~/.cache/tgrep/replay-request.md` (filled from `REPLAY.md`). Re-port the four patch intents; emit a new `git format-patch` series; stop for operator review. Do not install the Cursor apt hook from a replay.

`--install-cursor-hook` is refused in this user script. Root hook is `install-cursor-tgrep-rg.sh`.

## Pitfalls

- Do not `git reset` operator `main`. The apply script uses `git worktree add -b tgrep-cursor-build/<sha12>`.
- Dummy-patch tests use `--no-cargo`. Real apply runs cargo.
- `~/.local/bin/tgrep` is a cargo install, not a harness PATH shim.
