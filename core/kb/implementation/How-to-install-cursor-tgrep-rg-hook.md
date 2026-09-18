---
id: how-to-install-cursor-tgrep-rg-hook
when_skills: [run-plan]
inputs: [~/.agents/bin/cursor-tgrep-rg-apply.py, /usr/share/cursor/resources/app/node_modules/@vscode/ripgrep/bin]
outputs: [/usr/local/bin/cursor-tgrep-rg-apply, /etc/apt/apt.conf.d/99-cursor-tgrep-rg]
stop_if: [JSON fixture failed]
read: whole
prose: caveman-lite
---

# Install Cursor tgrep-rg hook

Wrap only `@vscode/ripgrep/bin/rg`. Keep `rg.stock`. Copy the Python apply script to `/usr/local/bin/cursor-tgrep-rg-apply` (not a `$HOME` symlink). Same apt+dpkg shape as `install-cursor-recolor.sh`.

## Scope

US-002 / US-003 / FR-8–FR-11. Do not wrap `/usr/bin/rg` or PATH `rg`.

## Prerequisites

- Phase 0 tests passed (`cargo test -p tgrep-cli --test cursor_hidden_argv`)
- Content JSON fixture passed (`cursor-tgrep-rg-apply.py compare-json`) on a hidden `.github` UTF-8 file vs `rg.stock`
- Do not enable the apt hook if that fixture fails
- Operator GO 2026-09-12: O1 (TBD-1 **(a)** cache indexes, TBD-3 **(a)** content JSON, `--files` → `rg.stock`).

## Procedure

1. Dry-run: `python3 ~/.agents/bin/cursor-tgrep-rg-apply.py apply --dry-run` prints `src=` `dst=` `stock=`.
2. Content fixture (tmp git repo + one-off `tgrep serve --hidden --no-require-git --index-path <idx> <repo>`, wait `meta.complete`). Do not start the XFCE ranker.

```bash
python3 ~/.agents/bin/cursor-tgrep-rg-apply.py compare-json \
  --stock /usr/share/cursor/resources/app/node_modules/@vscode/ripgrep/bin/rg \
  --tgrep ~/.local/bin/tgrep \
  --cwd <tmp-repo> \
  --pattern <needle> \
  --index-path <idx>
```

Need `begin`/`match`/`end`/`summary` and matching path/line keys. Kill the one-off serve after. Second `apply` on an already-wrapped `rg` must not copy the wrapper onto `rg.stock`.
3. Root once: `pkexec ${HOME}/.agents/bin/install-cursor-tgrep-rg.sh`. Re-run overwrites the same `/etc` files and `/usr/local/bin/cursor-tgrep-rg-apply` and exits 0.
4. After a Cursor deb upgrade the hook runs `cursor-tgrep-rg-apply apply` with `|| true`. ELF `rg` is copied to `rg.stock`, then the wrapper is installed as `rg`. Marker: `rg.wrapper-id`. Detect wrapper vs stock with `--tgrep-wrapper-version` or a non-ELF shebang. Never skip refreshing `rg.stock` when apt restored an ELF `rg`.

## Pitfalls

- Copying `tgrep` onto `bin/rg` clashes subcommands and false-negatives on an empty index. The wrapper execs `~/.local/bin/tgrep` only when `pool.json` + live `serve.json` + `meta.complete`.
- Do not strip `--hidden`.
- Hook failure must not fail apt (`|| true`).
- `--files` goes to `rg.stock` (O1 2026-09-12). Hidden-complete tgrep indexes list `.git/**`; stock does not. Content `--json` still uses tgrep when the pool is warm.
