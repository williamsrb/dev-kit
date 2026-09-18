# Offline React4XP 6.x Docs Cache (LLM-dense)

Cascade snapshots of **React4XP 6.x** for AI lookup. XP 7 exclusive — preferred for new React4XP work on XP 7.

| Seed | Offline tree |
| --- | --- |
| https://developer.enonic.com/learn/react4xp-tutorial/6.x | `learn/react4xp-tutorial/6.x/**` |
| https://developer.enonic.com/docs/react4xp/6.x | `docs/react4xp/6.x/**` |

## Format

- LLM-dense markdown (`format:llm-dense react4xp-6.x`)
- Routing: [`llm-index.md`](llm-index.md) — chooser (`docs` / `learn`), then matching page + heading only
- Listing: [`index.md`](index.md)

## Refresh

```bash
python3 ~/.agents/skills/develop-react4xp-v6/scripts/sync-react4xp-docs.py
```

Docs live at `~/.agents/kb/offline-reference/react4xp-6.x/` (not under the skill).
