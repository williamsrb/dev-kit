# Replay tgrep-cursor patches after an upstream upgrade

Use this only when `~/.agents/bin/tgrep-cursor-apply.py --apply` exits 2
because `git apply` rejected a hunk. Do not widen Cursor scope. Do not
silently "fix while you're here".

## Scope

Re-port these four intents onto current microsoft/tgrep, then stop for
operator review:

1. `IndexMeta` persists `include_hidden` and `no_require_git` (serde default false).
2. `tgrep serve` accepts `--hidden`, builds with it, and the watcher admits
   hidden paths the walk indexed while still skipping `.git` internals.
3. Search uses the index for `--hidden` / `--no-require-git` when meta matches.
   Widening flags (`--no-ignore*`, encoding, `--text`, `--binary`, named file)
   still walk. Do not strip `--hidden`.
4. Tests in `tgrep-cli/tests/cursor_hidden_argv.rs` only.

## Procedure

1. Read `{{REJECTS}}` below (filled by the apply script).
2. Work in a disposable worktree, not the clone's `main`.
3. Re-port the four intents. Emit a new series with `git format-patch`.
4. Copy the new patches to `~/.agents/vendor/tgrep-cursor/patches/` and update
   `UPSTREAM.sha` to the parent you applied onto.
5. Stop. Do not install the Cursor apt hook from this replay.

## REJECTS

{{REJECTS}}
