# Offline React4XP stable / 7.x Docs Cache (LLM-dense)

Cascade snapshots of **React4XP stable (7.x)** for AI lookup. Default for **XP 8** React4XP development.

| Seed | Offline tree |
| --- | --- |
| https://developer.enonic.com/learn/react4xp-tutorial/stable | `learn/react4xp-tutorial/stable/**` |
| https://developer.enonic.com/docs/react4xp/stable | `docs/react4xp/stable/**` |

## Format

- LLM-dense markdown (`format:llm-dense react4xp-7.x`)
- Routing: [`llm-index.md`](llm-index.md) — chooser (`docs` / `learn`), then matching page + heading only
- Listing: [`index.md`](index.md)

## Refresh

```bash
python3 ~/.agents/skills/develop-react4xp-v7/scripts/sync-react4xp-docs.py
```

Docs live at `~/.agents/kb/offline-reference/react4xp-stable/` (not under the skill).
