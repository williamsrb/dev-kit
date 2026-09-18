# Offline React4XP 5.x Docs Cache (LLM-dense)

Cascade snapshots of **React4XP 5.x** for AI lookup. XP 7 exclusive — **legacy**; use only for maintenance of existing 5.x apps. Prefer `react4xp-6.x/` for new XP 7 React4XP work.

| Seed | Offline tree |
| --- | --- |
| https://developer.enonic.com/learn/react4xp-tutorial/5.x | `learn/react4xp-tutorial/5.x/**` |

Shared base: `learn/react4xp-tutorial/5.x/*` (in-scope links → `learn/...md`).

## Format

- LLM-dense markdown (`format:llm-dense react4xp-5.x`)
- Routing: [`llm-index.md`](llm-index.md) — matching page + heading only (v2: topic + keywords)
- Listing: [`index.md`](index.md)

## Refresh

```bash
python3 ~/.agents/skills/develop-react4xp-v5/scripts/sync-react4xp-docs.py
```

Docs live at `~/.agents/kb/offline-reference/react4xp-5.x/` (not under the skill).
