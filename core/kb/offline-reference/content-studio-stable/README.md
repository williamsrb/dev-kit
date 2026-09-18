# Offline Content Studio stable Docs (LLM-dense)

Cascade snapshots for AI lookup only (not human-oriented).

| Seed | Offline tree |
| --- | --- |
| https://developer.enonic.com/docs/content-studio/stable | `docs/content-studio/stable/**` |

## Format

- LLM-dense markdown (`format:llm-dense content-studio-stable`)
- Routing: [`llm-index.md`](llm-index.md) — matching page + heading only (v2: topic + keywords)
- Listing: [`index.md`](index.md)

## Refresh

```bash
python3 ~/.agents/kb/offline-reference/scripts/sync-content-studio-docs.py --channel stable
```
