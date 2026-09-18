# User rules (Claude Code / Codex)

Constitution: `BASE.md` (Cursor loads `BASE.mdc` with `alwaysApply: true`). The BASE body is prepended below so Claude Code (`~/.claude/CLAUDE.md`) and Codex (`~/.codex/AGENTS.md`) ingest it **once**. Do **not** symlink this directory to `~/.claude/rules` or `~/.claude_personal/rules` — Claude auto-loads every `*.md` there and would inject `AGENTS.md` plus `BASE.md` again. Operational `.mdc` amendments follow.

**This file is generated.** Do not edit it. The source is `manifest.json` plus
`BASE.md` and the bodies it names; run `bin/generate-agents-md.py --apply` after
any change, and `--check` fails when the file is stale. A section whose manifest
entry says `body.from: mdc` is its `.mdc` verbatim, so edit that rule file; a
section that says `body.from: file` is a translation or a merge of several rules
and its only source is the named file under `agents.d/`.

**Keep in sync** — constitution: edit `BASE.md` and `BASE.mdc` together.

Not mirrored here (deliberately):

- `enonic-thymeleaf-negation.mdc` and `enonic-xp-nashorn-template-strings.mdc` are
  `alwaysApply: false` and glob-scoped to specific XP source paths. Claude Code /
  Codex have no glob scoping at user level, so they belong in a project-level
  `CLAUDE.md` / `AGENTS.md` inside the Enonic repos instead.
- `graphify.mdc` is `alwaysApply: false` (opt-in via `/graphify` or `@graphify`).
  Do not auto-run graphify or rebuild `graphify-out/`. When the user invokes it,
  follow that vendor's `skills/graphify/SKILL.md`. The standing git rule below
  still applies.
- `memory-filesystem.mdc` describes Cursor-only session memory: markdown under
  `~/.cursor/memory/`, injected by the Cursor `sessionStart` hook and scoped to
  the workspace. Claude Code and Codex do not run that hook and have their own
  memory. Mirroring it here would name a mechanism this harness does not have.
