# User rules (Claude Code / Codex)

**Generated; do not edit.** Sources: `rules/manifest.json`, `BASE.md` (edit together with `BASE.mdc`), and the bodies it names: `body.from: mdc` sections are that `.mdc` verbatim; `body.from: file` sections live in `agents.d/`. Run `bin/generate-agents-md.py --apply` after any change (`--check` fails when stale). Do **not** symlink `rules/` to `~/.claude/rules`: Claude auto-loads every `*.md` there and would inject this content twice.

Not mirrored: glob-scoped `enonic-*.mdc` (belong in Enonic repos' project `CLAUDE.md` / `AGENTS.md`) and Cursor-only `memory-filesystem.mdc`. `graphify.mdc` is opt-in: do not auto-run graphify or rebuild `graphify-out/`; on `/graphify` or `@graphify`, follow `skills/graphify/SKILL.md`.
