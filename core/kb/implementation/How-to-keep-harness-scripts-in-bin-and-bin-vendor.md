---
id: how-to-keep-harness-scripts-in-bin-and-bin-vendor
when_skills: []
inputs: [~/.agents/bin, ~/.agents/bin-vendor]
outputs: [vendor scripts/ links, ~/.local/bin PATH shims]
stop_if: [target is a hook or a skill script]
read: whole
prose: caveman-lite
---

# Keep harness scripts in bin and bin-vendor

Scripts scattered because each vendor grew its own `scripts/` and PATH copies were duplicated into `~/.local/bin`. Canonical copies live in `~/.agents`. Usage paths are links.

## Procedure

1. Shared harness tool (cron, PATH, every vendor): put the real file in `~/.agents/bin/<name>`. If it must stay on PATH, add the basename to `PATH_SHIMS` in `~/.agents/bin/sync-bin-projections.sh`.
2. Vendor-only script (Claude / Codex / Cursor): put the real file in `~/.agents/bin-vendor/<vendor>/<name>`. Same idea as `skills-vendor`.
3. Project: `~/.agents/bin/sync-bin-projections.sh` (dry run) then `--apply`. Vendor roots get `~/.<vendor>/scripts/<name>` → `bin-vendor`. PATH shims get `~/.local/bin/<name>` → `bin`.
4. Do not copy scripts into `~/.claude/scripts`, `~/.codex/scripts`, `~/.cursor/scripts`, or `~/.local/bin`. Those directories are projections.
5. Leave hooks (`~/.agents/hooks`, vendor `hooks/`) and skill scripts (`skills/*/scripts/`) where they are. This projector does not touch them.
6. Leave third-party PATH installs in `~/.local/bin` (uv, ruff, poetry, claude CLI, cursor-agent, pip entry points). They are not harness scripts.
7. Leave personal helpers that are not agent harness (`git-amend-date`, `automated-encrypt`, `vl`/`vs`, `open-design-default`) in `~/.local/bin`.

## Pitfalls

- A real file in a projection root that differs from the canonical is not deleted. Resolve by hand, then re-run `--apply`.
- Byte-identical real files are replaced by a symlink.
- Cron already calls `~/.agents/bin` with an absolute path. Do not add those names to `PATH_SHIMS` unless they are also typed on PATH.
- `verify-links.sh` flags a real file under vendor `scripts/` as TANGIBLE.
