# Offline XP 7.x Docs Cache (LLM-dense)

Local markdown snapshots of **Enonic XP 7.x** documentation for AI lookup.

Source base: https://developer.enonic.com/docs/platform/7.x  
(`stable` is XP 8 — do not use it for this skill.)

## Format

- Files are **LLM-dense markdown** (`format:llm-dense`), not raw HTML dumps.
- Site chrome (nav, menus, empty TOC) is stripped; headings, prose, code, and tables are kept.
- Routing index: [`llm-index.md`](llm-index.md) (v2 chooser: `api` / `development` / `framework`). Open matching subtree index, then page + heading only.
- Human listing: [`index.md`](index.md).

## Refresh cache

From `~/.agents/skills/develop-xp7-backend`:

```bash
python3 scripts/sync-xp-docs.py
```

Default output: `~/.agents/kb/offline-reference/xp7/`

Writes:

- `development/*.md`
- `framework/*.md`
- `api/*.md`
- `index.md`
- `llm-index.md`

## Notes

- Snapshots are generated, not canonical.
- Prefer official 7.x docs when behavior is unclear or critical.
