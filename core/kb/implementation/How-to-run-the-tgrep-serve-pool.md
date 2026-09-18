---
id: how-to-run-the-tgrep-serve-pool
when_skills: [run-plan]
inputs: [~/.local/bin/tgrep, ~/.config/Cursor/User/workspaceStorage]
outputs: [~/.cache/tgrep/pool.json, tgrep serve PIDs]
stop_if: [root is $HOME]
read: whole
prose: caveman-lite
---

# Run the tgrep serve pool

Cap 7 ranked git repos plus at most one extra for the current chat git root (cap 8). Indexes at `~/.cache/tgrep/<sha256-16 of canonical root>/` (TBD-1 **(a)**, operator 2026-09-12). Deny `$HOME`, `~/Downloads`, `~/.config`, `~/.cursor`, `~/.agents`, `~/.cache`, `~/.wine` as serve roots. Do not `git` from `~/.cursor/projects/<slug>` (that repo is `~/.cursor`).

## Scope

US-004 / FR-10 / FR-13. XFCE autostart + sessionStart ensure.

## Prerequisites

- Patched `~/.local/bin/tgrep`
- Git roots only (v1)

## Procedure

1. Rank: `python3 ~/.agents/bin/tgrep-serve-pool.py rank`
2. Login: XFCE `~/.config/autostart/tgrep-serve-pool.desktop` runs `start-ranked`.
3. New chat: `cursor-memory.py` `cmd_recall` writes the JSON line first, then best-effort `tgrep-serve-pool.py ensure --cwd <workspace>`. `~/.cursor/hooks/memory-recall.sh` stays `exec python3 … recall`. Ensure never fails the hook and never passes `$HOME`.
4. Status: `python3 ~/.agents/bin/tgrep-serve-pool.py status`. Orphans in `pool.json` whose PIDs are dead are dropped.

## Pitfalls

- `~/.cache/tgrep/` is storage, not a serve root.
- Cold serve has `meta.complete=false`; the rg wrapper must use `rg.stock` until complete.
- Ranker may read `~/.config/Cursor/User/workspaceStorage` for scoring only; that path is not a serve root.
